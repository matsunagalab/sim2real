#!/usr/bin/env python
"""Round-2 MD feature extraction (lightweight): 5 scalar features per nanobody.

Computes from each /home/yasu/tmp/mdclaw/job_nano_*/nodes/prod_001/artifacts/trajectory.dcd
(over the final 30% of frames):

  q_min       min of frame-wise Q (hphil-all) — worst-case unfolding
  q_std       std of frame-wise Q over time — fluctuation magnitude
  q_slope     linear regression slope of Q vs frame index — kinetic decay
  rmsf_max    max per-Cα RMSF — worst residue's flexibility
  rg_std      std of radius of gyration over time — overall compactness fluctuation

Skipped vs the original v2 design (too slow at 1k+ trajectories):
  DSSP, SASA, Wernet-Nilsson H-bonds — these can be revisited if any of the
  above proves a strong signal.

Each feature → its own CSV with prepare.py-compatible schema:
  pdb_id, seq, seq_len, <feature>, ddg_scaled01
ddg_scaled01 is MinMax-scaled (high direction) or 1−x (low direction).
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
OUT_DIR = os.path.join(REPO_ROOT, "data", "md")

LAST_FRAC = 0.30

# Q computation params (same as baseline)
Q_SELECTION = "backbone and not element H"
BETA = 50.0
LAMBDA = 1.8
NATIVE_CUTOFF_NM = 0.45
MIN_RESID_GAP = 3
HPHIL_RESNAMES = {'ASP', 'GLU', 'GLN', 'ASN', 'ARG', 'LYS', 'HIS',
                  'ASH', 'GLH', 'LYN', 'HID', 'HIE', 'HIP'}

# Hydrophobic residue set for SASA partitioning
HPHOB_RESNAMES = {'ALA', 'VAL', 'LEU', 'ILE', 'MET', 'PHE', 'TRP', 'PRO', 'CYS', 'CYX', 'CYM'}

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


def compute_features(traj_path: str, prmtop: str) -> dict:
    topology = md.load_prmtop(prmtop)

    # ---- Backbone heavy atoms for Q ----
    bb_idx = topology.select("protein and " + Q_SELECTION)
    if len(bb_idx) == 0:
        raise ValueError("no backbone heavy atoms")
    bb_res_idx = np.array([topology.atom(a).residue.index for a in bb_idx])
    bb_resname = np.array([topology.atom(a).residue.name.upper() for a in bb_idx])
    bb_hphil = np.isin(bb_resname, list(HPHIL_RESNAMES))

    # ---- Cα for RMSF and Rg ----
    ca_idx = topology.select("protein and name CA")

    # ---- Native frame for Q-contact list ----
    first = md.load_frame(traj_path, 0, top=topology)
    coords_bb = first.xyz[0, bb_idx, :]
    diff = coords_bb[:, None, :] - coords_bb[None, :, :]
    dist_bb = np.sqrt((diff ** 2).sum(axis=-1))
    res_gap = np.abs(bb_res_idx[:, None] - bb_res_idx[None, :])
    hphil_pair = bb_hphil[:, None] | bb_hphil[None, :]
    mask = (
        (dist_bb < NATIVE_CUTOFF_NM)
        & (res_gap > MIN_RESID_GAP)
        & np.triu(np.ones_like(dist_bb, dtype=bool), k=1)
        & hphil_pair
    )
    ii, jj = np.where(mask)
    if len(ii) == 0:
        raise ValueError("no native hphil contacts")
    d_native_bb = dist_bb[ii, jj]
    pair_atoms = np.stack([bb_idx[ii], bb_idx[jj]], axis=1)

    # ---- Stream trajectory: Q distances, Cα xyz, Rg ----
    q_frames = []
    rg_per_frame = []
    ca_xyz_chunks = []

    for chunk in md.iterload(traj_path, top=topology, chunk=500):
        d = md.compute_distances(chunk, pair_atoms)
        q_chunk = 1.0 / (1.0 + np.exp(BETA * (d - LAMBDA * d_native_bb[None, :])))
        q_frames.append(q_chunk.mean(axis=1))
        ca_xyz_chunks.append(chunk.xyz[:, ca_idx, :].copy())
        rg_per_frame.append(md.compute_rg(chunk))

    q_all = np.concatenate(q_frames)
    ca_xyz = np.concatenate(ca_xyz_chunks, axis=0)
    rg_all = np.concatenate(rg_per_frame)

    n_total = len(q_all)
    n_tail = max(1, int(n_total * LAST_FRAC))

    q_tail = q_all[-n_tail:]
    q_min = float(q_tail.min())
    q_std = float(q_tail.std())

    # Linear slope of Q over frame index (units: Q per frame)
    if n_tail >= 2:
        x = np.arange(n_tail, dtype=float)
        slope, _intercept = np.polyfit(x, q_tail, deg=1)
        q_slope = float(slope)
    else:
        q_slope = 0.0

    sub_top = topology.subset(ca_idx)
    sub_traj = md.Trajectory(xyz=ca_xyz[-n_tail:], topology=sub_top)
    sub_traj.superpose(sub_traj, frame=0)
    mean_xyz = sub_traj.xyz.mean(axis=0)
    diff_ca = sub_traj.xyz - mean_xyz[None, :, :]
    rmsf_per_ca = np.sqrt((diff_ca ** 2).sum(axis=-1).mean(axis=0))
    rmsf_max = float(rmsf_per_ca.max())

    rg_std = float(rg_all[-n_tail:].std())

    return {
        "q_min": q_min,
        "q_std": q_std,
        "q_slope": q_slope,
        "rmsf_max": rmsf_max,
        "rg_std": rg_std,
        "n_frames_used": n_tail,
    }


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
        feats = compute_features(traj, prmtop)
    except Exception as e:
        return (pdb_id, None, f"{type(e).__name__}: {e}")
    return (pdb_id, {"pdb_id": pdb_id, "seq": seq, "seq_len": len(seq), **feats},
            f"ok q_min={feats['q_min']:.3f} q_std={feats['q_std']:.3f} rmsf_max={feats['rmsf_max']:.3f}")


# Direction = "high" → ddg_scaled01 ∝ value (higher value = more stable)
# Direction = "low"  → ddg_scaled01 ∝ (1 - normalized value) (lower value = more stable)
FEATURE_DIRECTIONS = {
    "q_min":    "high",  # higher minimum Q = more stable
    "q_std":    "low",   # lower std = more stable
    "q_slope":  "high",  # less negative (≈0) slope = more stable
    "rmsf_max": "low",   # less max flexibility = more stable
    "rg_std":   "low",   # less Rg fluctuation = more stable
}


def write_feature_csv(df: pd.DataFrame, feature: str):
    sub = df[["pdb_id", "seq", "seq_len", feature]].copy()
    sub = sub.dropna(subset=[feature])
    vmin, vmax = sub[feature].min(), sub[feature].max()
    if vmax > vmin:
        norm = (sub[feature] - vmin) / (vmax - vmin)
    else:
        norm = pd.Series([0.5] * len(sub), index=sub.index)
    direction = FEATURE_DIRECTIONS.get(feature, "high")
    sub["ddg_scaled01"] = norm if direction == "high" else (1.0 - norm)
    out = os.path.join(OUT_DIR, f"feat_{feature}.csv")
    sub.to_csv(out, index=False)
    print(f"  Saved: {out} ({len(sub)} rows, range [{vmin:.4f}, {vmax:.4f}], dir={direction})", flush=True)


def main():
    job_dirs = sorted(glob.glob(os.path.join(MDCLAW_ROOT, "job_nano_*")))
    print(f"Found {len(job_dirs)} job_nano_* dirs", flush=True)

    n_workers = 8
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
    os.makedirs(OUT_DIR, exist_ok=True)
    for feat in FEATURE_DIRECTIONS:
        write_feature_csv(df, feat)


if __name__ == "__main__":
    main()
