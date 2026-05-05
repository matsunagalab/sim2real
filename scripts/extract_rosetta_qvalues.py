#!/usr/bin/env python
"""Extract hydrophilic-all Q-value from Rosetta backrub trajectories.

Reads each data/md/rosetta_traj/<pdb_id>_traj.pdb (multi-MODEL PDB from
Rosetta backrub), computes Best-Hummer Q-value restricted to pairs where
at least one atom is on a hydrophilic residue (D/E/Q/N/R/K/H), and averages
over the final 30% of frames (analogous to the final-30ns convention used
for the all-atom MD case).

Reference structure = merged.pdb from the matching job_nano_*/prep_001/.
"""

import os
import glob
import time
import multiprocessing as mp
import numpy as np
import pandas as pd
import mdtraj as md

MDCLAW_ROOT = "/home/yasu/tmp/mdclaw"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAJ_DIR = os.path.join(REPO_ROOT, "data", "md", "rosetta_traj")
OUT_CSV = os.path.join(REPO_ROOT, "data", "md", "rosetta_qvalue_hphil.csv")

# Q-value parameters (match all-atom MD for apples-to-apples comparison)
SELECTION = "backbone and not element H"
BETA = 50.0
LAMBDA = 1.8
NATIVE_CUTOFF_NM = 0.45
MIN_RESID_GAP = 3
LAST_FRAC = 0.30  # average over final 30% of frames

HPHIL_RESNAMES = {'ASP', 'GLU', 'GLN', 'ASN', 'ARG', 'LYS', 'HIS',
                  'ASH', 'GLH', 'LYN', 'HID', 'HIE', 'HIP'}

THREE_TO_ONE = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V',
    'HID': 'H', 'HIE': 'H', 'HIP': 'H',
    'ASH': 'D', 'GLH': 'E', 'LYN': 'K', 'CYX': 'C', 'CYM': 'C',
}


def extract_sequence(pdb_path: str) -> str:
    seq = []
    seen = set()
    with open(pdb_path) as f:
        for line in f:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            if line[12:16].strip() != "CA":
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
                continue
            seq.append(one)
            # stop at first MODEL's chain end — multi-MODEL PDBs repeat
            if line.startswith("ENDMDL"):
                break
    return "".join(seq)


def compute_q_mean_rosetta(traj_pdb: str) -> tuple[float, int, int]:
    """Compute hydrophilic-all Q-value from a multi-MODEL PDB trajectory.

    Uses frame 0 as the native reference. Handles .pdb and .pdb.gz.
    """
    # Load all frames (mdtraj handles .gz transparently if pandas/mdtraj supports it;
    # otherwise decompress to tmp)
    if traj_pdb.endswith(".gz"):
        import gzip, tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdb", delete=False) as tmp:
            with gzip.open(traj_pdb, "rb") as gz:
                tmp.write(gz.read())
            tmp_path = tmp.name
        try:
            traj = md.load(tmp_path)
        finally:
            os.unlink(tmp_path)
    else:
        traj = md.load(traj_pdb)
    sel_idx = traj.topology.select("protein and " + SELECTION)
    if len(sel_idx) == 0:
        raise ValueError("protein backbone heavy atoms = 0")
    N = len(sel_idx)

    coords_native = traj.xyz[0, sel_idx, :]
    res_idx = np.array([traj.topology.atom(a).residue.index for a in sel_idx])
    resname_per_atom = np.array([traj.topology.atom(a).residue.name.upper() for a in sel_idx])
    hphil_per_atom = np.isin(resname_per_atom, list(HPHIL_RESNAMES))

    diff = coords_native[:, None, :] - coords_native[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=-1))
    res_gap = np.abs(res_idx[:, None] - res_idx[None, :])
    hphil_pair = hphil_per_atom[:, None] | hphil_per_atom[None, :]
    mask = (
        (dist < NATIVE_CUTOFF_NM)
        & (res_gap > MIN_RESID_GAP)
        & np.triu(np.ones_like(dist, dtype=bool), k=1)
        & hphil_pair
    )
    ii, jj = np.where(mask)
    if len(ii) == 0:
        raise ValueError("no native hphil contacts in frame 0")
    d_native = dist[ii, jj]
    pair_atoms = np.stack([sel_idx[ii], sel_idx[jj]], axis=1)

    dists = md.compute_distances(traj, pair_atoms)  # (frames, pairs)
    q = 1.0 / (1.0 + np.exp(BETA * (dists - LAMBDA * d_native[None, :])))
    q_frame = q.mean(axis=1)

    n_total = len(q_frame)
    n_tail = max(1, int(n_total * LAST_FRAC))
    q_tail = q_frame[-n_tail:]
    return float(q_tail.mean()), len(q_tail), len(ii)


def _process_one(traj_pdb):
    base = os.path.basename(traj_pdb)
    pdb_id = base.replace("_traj.pdb.gz", "").replace("_traj.pdb", "")
    native = os.path.join(
        MDCLAW_ROOT, f"job_nano_{pdb_id}", "nodes", "prep_001",
        "artifacts", "merge", "merged.pdb",
    )
    if not os.path.exists(native):
        return (pdb_id, None, "no merged.pdb")
    try:
        seq = extract_sequence(native)
        if len(seq) < 50:
            return (pdb_id, None, f"seq too short ({len(seq)})")
        q_mean, n_frames, n_contacts = compute_q_mean_rosetta(traj_pdb)
    except Exception as e:
        return (pdb_id, None, f"{type(e).__name__}: {e}")
    return (pdb_id, {
        "pdb_id": pdb_id,
        "seq": seq,
        "q_value_raw": q_mean,
        "n_frames_used": n_frames,
        "n_contacts": n_contacts,
        "seq_len": len(seq),
    }, f"ok {n_frames}f/{n_contacts}c")


def main():
    traj_files = sorted(
        glob.glob(os.path.join(TRAJ_DIR, "*_traj.pdb"))
        + glob.glob(os.path.join(TRAJ_DIR, "*_traj.pdb.gz"))
    )
    print(f"Found {len(traj_files)} Rosetta trajectories", flush=True)
    if not traj_files:
        print(f"No trajectories in {TRAJ_DIR}. Run scripts/run_rosetta_backrub.py first.", flush=True)
        return

    rows = []
    skipped = []
    t_start = time.time()

    n_workers = 8
    print(f"Parallel workers: {n_workers}", flush=True)

    with mp.Pool(n_workers) as pool:
        for i, (pdb_id, row, msg) in enumerate(pool.imap_unordered(_process_one, traj_files)):
            if row is None:
                skipped.append((pdb_id, msg))
                continue
            rows.append(row)
            if (i + 1) % 100 == 0:
                elapsed = time.time() - t_start
                rate = (i + 1) / elapsed
                eta = (len(traj_files) - i - 1) / rate
                print(f"[{i+1:4d}/{len(traj_files)}] rate={rate:.1f}/s, eta={eta/60:.1f}min", flush=True)

    print(f"\nDone: {len(rows)} processed, {len(skipped)} skipped in {time.time()-t_start:.0f}s")
    if skipped:
        print(f"Skipped examples:", flush=True)
        for pdb_id, reason in skipped[:10]:
            print(f"  {pdb_id}: {reason}", flush=True)

    if not rows:
        return

    df = pd.DataFrame(rows)
    q_min, q_max = df["q_value_raw"].min(), df["q_value_raw"].max()
    df["ddg_scaled01"] = (df["q_value_raw"] - q_min) / (q_max - q_min) if q_max > q_min else 0.5
    print(f"\nQ-value range: [{q_min:.4f}, {q_max:.4f}]", flush=True)
    print(f"Q-value mean/std: {df['q_value_raw'].mean():.4f} ± {df['q_value_raw'].std():.4f}", flush=True)

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV} ({len(df)} rows)", flush=True)


if __name__ == "__main__":
    main()
