#!/usr/bin/env python
"""Extract mean Q-value (native contact fraction) from MD trajectories.

For each /home/yasu/tmp/mdclaw/job_nano_*/ with a completed production trajectory,
compute the Best-Hummer Q-value timeseries against the native (merged) structure,
take the mean over the final 30 ns (or all frames if shorter), and record the
amino acid sequence.

Output: data/md/nanobody_qvalue.csv with columns [pdb_id, seq, q_value_raw, ddg_scaled01]
(ddg_scaled01 = MinMax-scaled q_value_raw, to reuse the existing DDG loader path).
"""

import os
import sys
import glob
import json
import pathlib
import time

import numpy as np
import pandas as pd
import mdtraj as md

MDCLAW_ROOT = "/home/yasu/tmp/mdclaw"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Switch the production node via env var:
#   PROD_NODE=prod_001 (default; 300K trajectories)
#   PROD_NODE=prod_002 (400K trajectories)
PROD_NODE = os.environ.get("PROD_NODE", "prod_001")
OUT_NAME = os.environ.get("OUT_NAME", "nanobody_qvalue_hphil.csv")
OUT_CSV = os.path.join(REPO_ROOT, "data", "md", OUT_NAME)

# Q-value parameters (Best-Hummer, following Kamiya et al. and mdclaw defaults)
SELECTION = "backbone and not element H"
BETA = 50.0
LAMBDA = 1.8
NATIVE_CUTOFF_NM = 0.45
MIN_RESID_GAP = 3
LAST_NS = 30.0  # average over final 30 ns

# Kamiya et al. hydrophilic residues (Asp, Glu, Gln, Asn, Arg, Lys, His)
HPHIL_RESNAMES = {'ASP', 'GLU', 'GLN', 'ASN', 'ARG', 'LYS', 'HIS',
                  'ASH', 'GLH', 'LYN', 'HID', 'HIE', 'HIP'}  # ff19SB variants

THREE_TO_ONE = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V',
    # ff19SB protonation variants
    'HID': 'H', 'HIE': 'H', 'HIP': 'H',
    'ASH': 'D', 'GLH': 'E', 'LYN': 'K', 'CYX': 'C', 'CYM': 'C',
}


def extract_sequence(pdb_path: str) -> str:
    """Extract amino acid sequence from a PDB by taking first CA per residue."""
    seq = []
    seen = set()
    with open(pdb_path) as f:
        for line in f:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            atom_name = line[12:16].strip()
            if atom_name != "CA":
                continue
            chain = line[21]
            resseq = line[22:26].strip()
            icode = line[26]
            key = (chain, resseq, icode)
            if key in seen:
                continue
            seen.add(key)
            resname = line[17:20].strip().upper()
            one = THREE_TO_ONE.get(resname)
            if one is None:
                print(f"  [warn] unknown residue {resname} in {pdb_path}", flush=True)
                continue
            seq.append(one)
    return "".join(seq)


def compute_q_mean(trajectory_file: str, prmtop: str,
                   last_ns: float = LAST_NS) -> tuple[float, int, int]:
    """Compute mean Q-value (Best-Hummer) for the final `last_ns` ns of a trajectory.

    Uses frame 0 of the trajectory (post-equilibration) as the native reference.
    This matches the topology exactly and avoids atom count mismatches between
    crystal (merged.pdb) and simulation-ready structures.

    Args:
        trajectory_file: path to trajectory.dcd
        prmtop: path to system.parm7 (matches trajectory atom count)
        last_ns: average over final this many ns

    Returns (mean_q, n_frames_used, n_native_contacts).
    """
    topology = md.load_prmtop(prmtop)
    sel_idx = topology.select("protein and " + SELECTION)
    if len(sel_idx) == 0:
        raise ValueError(f"protein backbone heavy atoms = 0 in {prmtop}")
    N = len(sel_idx)

    # Native reference = frame 0 of trajectory
    first = md.load_frame(trajectory_file, 0, top=topology)
    coords_native = first.xyz[0, sel_idx, :]  # (N, 3) in nm
    res_idx = np.array([topology.atom(a).residue.index for a in sel_idx])

    # Hydrophilic mask per atom (Kamiya: hydrophilic = {D, E, Q, N, R, K, H})
    resname_per_atom = np.array([
        topology.atom(a).residue.name.upper() for a in sel_idx
    ])
    hphil_per_atom = np.isin(resname_per_atom, list(HPHIL_RESNAMES))

    # Contact list from native coords
    diff = coords_native[:, None, :] - coords_native[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=-1))
    res_gap = np.abs(res_idx[:, None] - res_idx[None, :])
    # "Hydrophilic-all" pair: at least one atom must be on a hydrophilic residue
    hphil_pair = hphil_per_atom[:, None] | hphil_per_atom[None, :]
    mask = (
        (dist < NATIVE_CUTOFF_NM)
        & (res_gap > MIN_RESID_GAP)
        & np.triu(np.ones_like(dist, dtype=bool), k=1)
        & hphil_pair
    )
    ii, jj = np.where(mask)
    if len(ii) == 0:
        raise ValueError("no native contacts found in frame 0")
    d_native = dist[ii, jj]
    pair_atoms = np.stack([sel_idx[ii], sel_idx[jj]], axis=1)

    # Stream trajectory
    q_frames = []
    for chunk in md.iterload(trajectory_file, top=topology, chunk=500):
        dists = md.compute_distances(chunk, pair_atoms)
        q = 1.0 / (1.0 + np.exp(BETA * (dists - LAMBDA * d_native[None, :])))
        q_frames.append(q.mean(axis=1))

    q_all = np.concatenate(q_frames)
    n_total = len(q_all)

    # Assume 100 ps per frame (ff19SB default), so 30 ns = 300 frames
    # Use last_ns worth of frames if trajectory is long enough, else use all
    if n_total > 300:
        # Estimate dt from total frames: 100 ns / n_total = dt_ns
        # Use last 30% of frames as conservative "final 30 ns" proxy
        n_use = max(int(last_ns * 10), n_total // 3)  # assume 10 frames/ns
        n_use = min(n_use, n_total)
        q_tail = q_all[-n_use:]
    else:
        q_tail = q_all

    return float(q_tail.mean()), len(q_tail), len(ii)


def main():
    job_dirs = sorted(glob.glob(os.path.join(MDCLAW_ROOT, "job_nano_*")))
    print(f"Found {len(job_dirs)} job_nano_* directories", flush=True)

    rows = []
    skipped = []
    start = time.time()

    for i, job in enumerate(job_dirs):
        pdb_id = os.path.basename(job).replace("job_nano_", "")
        traj = os.path.join(job, "nodes", PROD_NODE, "artifacts", "trajectory.dcd")
        native = os.path.join(job, "nodes", "prep_001", "artifacts", "merge", "merged.pdb")
        prmtop = os.path.join(job, "nodes", "topo_001", "artifacts", "system.parm7")

        if not os.path.exists(traj):
            skipped.append((pdb_id, "no trajectory.dcd"))
            continue
        if not os.path.exists(native):
            skipped.append((pdb_id, "no merged.pdb"))
            continue
        if not os.path.exists(prmtop):
            skipped.append((pdb_id, "no system.parm7"))
            continue

        t0 = time.time()
        try:
            seq = extract_sequence(native)
            if len(seq) < 50:
                skipped.append((pdb_id, f"seq too short ({len(seq)})"))
                continue
            q_mean, n_frames, n_contacts = compute_q_mean(traj, prmtop)
        except Exception as e:
            skipped.append((pdb_id, f"{type(e).__name__}: {e}"))
            continue

        elapsed = time.time() - t0
        rows.append({
            "pdb_id": pdb_id,
            "seq": seq,
            "q_value_raw": q_mean,
            "n_frames_used": n_frames,
            "n_contacts": n_contacts,
            "seq_len": len(seq),
        })
        print(
            f"[{len(rows):3d}/{i+1}] {pdb_id}: len={len(seq)}, "
            f"Q={q_mean:.4f} ({n_frames} frames, {n_contacts} contacts) "
            f"[{elapsed:.1f}s]",
            flush=True,
        )

    print(f"\nDone: {len(rows)} processed, {len(skipped)} skipped in {time.time()-start:.0f}s", flush=True)
    if skipped:
        print("\nSkipped:", flush=True)
        for pdb_id, reason in skipped[:20]:
            print(f"  {pdb_id}: {reason}", flush=True)

    if not rows:
        print("No Q-values extracted, exiting.", flush=True)
        sys.exit(1)

    df = pd.DataFrame(rows)
    # Scale q_value_raw to [0,1] using MinMax (column name ddg_scaled01 for prepare.py compatibility)
    q_min, q_max = df["q_value_raw"].min(), df["q_value_raw"].max()
    if q_max > q_min:
        df["ddg_scaled01"] = (df["q_value_raw"] - q_min) / (q_max - q_min)
    else:
        df["ddg_scaled01"] = 0.5
    print(f"\nQ-value range: [{q_min:.4f}, {q_max:.4f}]", flush=True)
    print(f"Q-value mean/std: {df['q_value_raw'].mean():.4f} ± {df['q_value_raw'].std():.4f}", flush=True)

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV} ({len(df)} rows)", flush=True)


if __name__ == "__main__":
    main()
