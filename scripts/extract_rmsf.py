#!/usr/bin/env python
"""Extract mean Cα RMSF from MD trajectories.

For each /home/yasu/tmp/mdclaw/job_nano_*/ with a completed production trajectory,
compute per-Cα RMSF over the final 30% of frames (after iterative alignment to
the average structure) and report the mean as a single scalar feature per nanobody.

Output: data/md/nanobody_rmsf.csv with columns
  [pdb_id, seq, rmsf_mean, rmsf_max, n_frames_used, seq_len, ddg_scaled01]
ddg_scaled01 = MinMax-scaled rmsf_mean (lower RMSF = more stable → maps to higher Tm-like signal).
"""

import os
import sys
import glob
import time
import multiprocessing as mp

import numpy as np
import pandas as pd
import mdtraj as md

MDCLAW_ROOT = "/home/yasu/tmp/mdclaw"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(REPO_ROOT, "data", "md", "nanobody_rmsf.csv")

LAST_FRAC = 0.30  # final 30% of frames

THREE_TO_ONE = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V',
    'HID': 'H', 'HIE': 'H', 'HIP': 'H',
    'ASH': 'D', 'GLH': 'E', 'LYN': 'K', 'CYX': 'C', 'CYM': 'C',
}


def extract_sequence(pdb_path: str) -> str:
    seq, seen = [], set()
    with open(pdb_path) as f:
        for line in f:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            if line[12:16].strip() != "CA":
                continue
            key = (line[21], line[22:26].strip(), line[26])
            if key in seen:
                continue
            seen.add(key)
            one = THREE_TO_ONE.get(line[17:20].strip().upper())
            if one is None:
                continue
            seq.append(one)
    return "".join(seq)


def compute_rmsf(traj_path: str, prmtop: str) -> tuple[float, float, int, int]:
    """Return (mean_rmsf_nm, max_rmsf_nm, n_frames_used, n_ca_atoms).

    Uses Cα atoms only, aligns to the mean structure (one pass), then
    computes per-atom std over the tail frames.
    """
    topology = md.load_prmtop(prmtop)
    ca_idx = topology.select("protein and name CA")
    if len(ca_idx) == 0:
        raise ValueError("no Cα atoms")

    # Stream trajectory, collect Cα coordinates only (memory-friendly)
    coords = []
    for chunk in md.iterload(traj_path, top=topology, chunk=500, atom_indices=ca_idx):
        coords.append(chunk.xyz)
    xyz = np.concatenate(coords, axis=0)  # (frames, n_ca, 3) in nm
    n_total = xyz.shape[0]

    n_tail = max(1, int(n_total * LAST_FRAC))
    tail = xyz[-n_tail:]  # (n_tail, n_ca, 3)

    # Align tail frames to their own mean structure (Kabsch via mdtraj.Trajectory)
    sub_top = topology.subset(ca_idx)
    sub_traj = md.Trajectory(xyz=tail, topology=sub_top)
    sub_traj.superpose(sub_traj, frame=0)

    # Per-atom RMSF after superposition
    mean_xyz = sub_traj.xyz.mean(axis=0)  # (n_ca, 3)
    diff = sub_traj.xyz - mean_xyz[None, :, :]
    per_atom = np.sqrt((diff ** 2).sum(axis=-1).mean(axis=0))  # (n_ca,)

    return float(per_atom.mean()), float(per_atom.max()), n_tail, len(ca_idx)


def _process_one(job: str):
    pdb_id = os.path.basename(job).replace("job_nano_", "")
    traj = os.path.join(job, "nodes", "prod_001", "artifacts", "trajectory.dcd")
    native = os.path.join(job, "nodes", "prep_001", "artifacts", "merge", "merged.pdb")
    prmtop = os.path.join(job, "nodes", "topo_001", "artifacts", "system.parm7")
    if not (os.path.exists(traj) and os.path.exists(native) and os.path.exists(prmtop)):
        return (pdb_id, None, "missing files")
    try:
        seq = extract_sequence(native)
        if len(seq) < 50:
            return (pdb_id, None, f"seq too short ({len(seq)})")
        rmsf_mean, rmsf_max, n_frames, n_ca = compute_rmsf(traj, prmtop)
    except Exception as e:
        return (pdb_id, None, f"{type(e).__name__}: {e}")
    return (pdb_id, {
        "pdb_id": pdb_id,
        "seq": seq,
        "rmsf_mean": rmsf_mean,
        "rmsf_max": rmsf_max,
        "n_frames_used": n_frames,
        "seq_len": len(seq),
    }, f"ok rmsf={rmsf_mean:.3f}nm n_ca={n_ca}")


def main():
    job_dirs = sorted(glob.glob(os.path.join(MDCLAW_ROOT, "job_nano_*")))
    print(f"Found {len(job_dirs)} job_nano_* dirs", flush=True)

    n_workers = 8
    print(f"Parallel workers: {n_workers}", flush=True)
    rows, skipped = [], []
    t0 = time.time()
    with mp.Pool(n_workers) as pool:
        for i, (pdb_id, row, msg) in enumerate(pool.imap_unordered(_process_one, job_dirs)):
            if row is None:
                skipped.append((pdb_id, msg))
                continue
            rows.append(row)
            if (i + 1) % 100 == 0:
                rate = (i + 1) / (time.time() - t0)
                eta = (len(job_dirs) - i - 1) / rate
                print(f"[{i+1:4d}/{len(job_dirs)}] rate={rate:.1f}/s eta={eta/60:.1f}min", flush=True)

    print(f"\nDone: {len(rows)} processed, {len(skipped)} skipped in {time.time()-t0:.0f}s", flush=True)
    for pdb_id, reason in skipped[:10]:
        print(f"  skip {pdb_id}: {reason}", flush=True)

    if not rows:
        sys.exit(1)

    df = pd.DataFrame(rows)
    # Lower RMSF = more stable → invert so higher ddg_scaled01 means more stable
    rmin, rmax = df["rmsf_mean"].min(), df["rmsf_mean"].max()
    df["ddg_scaled01"] = 1.0 - (df["rmsf_mean"] - rmin) / (rmax - rmin) if rmax > rmin else 0.5
    print(f"\nRMSF range: [{rmin:.4f}, {rmax:.4f}] nm", flush=True)
    print(f"RMSF mean/std: {df['rmsf_mean'].mean():.4f} ± {df['rmsf_mean'].std():.4f} nm", flush=True)

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV} ({len(df)} rows)", flush=True)


if __name__ == "__main__":
    main()
