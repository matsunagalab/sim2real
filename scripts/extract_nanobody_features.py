#!/usr/bin/env python
"""Nanobody-specific MD features from prod_001 (300K) trajectories.

VHH structural hallmarks used:
  - Two conserved Cys (Cys22 and Cys96-ish) form a disulfide bond
  - CDR3 sits between the second Cys and the conserved W-G-X-G motif at the end
  - Framework-4 starts with W (Trp103-ish)
  - CDRs 1/2/3 are the most variable loops; CDR3 is the longest

Heuristic CDR3 identification (no antibody numbering tool needed):
  - Find the last Cys in the sequence
  - Find the W-G immediately after it
  - CDR3 = residues between (last Cys + 1) and (W - 1)

Features extracted (over final 30% frames):
  q_cdr3             Q-value (hphil-all) restricted to CDR3 pair contacts
  q_framework        Q-value (hphil-all) over framework (everything except CDR3)
  rmsf_cdr3          mean Cα RMSF of CDR3 residues
  rmsf_framework     mean Cα RMSF of framework residues
  ss_dist_mean       Cys22-Cys96 Cα distance (mean, nm) — disulfide proxy
  ss_dist_std        std of that distance
  cdr3_len           CDR3 length (residues) — sanity check / itself a Tm predictor?

Outputs (under data/md/, PROD_NODE + FEAT_SUFFIX selectable like extract_features_v2):
  feat_q_cdr3{suffix}.csv
  feat_q_framework{suffix}.csv
  feat_rmsf_cdr3{suffix}.csv
  feat_rmsf_framework{suffix}.csv
  feat_ss_dist_mean{suffix}.csv
  feat_ss_dist_std{suffix}.csv
  feat_cdr3_len{suffix}.csv
"""

import os
import sys
import glob
import time
import multiprocessing as mp
import re

import numpy as np
import pandas as pd
import mdtraj as md

MDCLAW_ROOT = "/home/yasu/tmp/mdclaw"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "data", "md")
PROD_NODE = os.environ.get("PROD_NODE", "prod_001")
FEAT_SUFFIX = os.environ.get("FEAT_SUFFIX", "")

LAST_FRAC = 0.30
Q_SELECTION = "backbone and not element H"
BETA = 50.0
LAMBDA = 1.8
NATIVE_CUTOFF_NM = 0.45
MIN_RESID_GAP = 3
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


def find_cdr3(seq: str) -> tuple[int | None, int | None, int | None, int | None]:
    """Heuristic CDR3 boundary identification.

    Returns (cys1_idx, cys2_idx, cdr3_start, cdr3_end) — all 0-indexed,
    cdr3 is half-open [start, end). Returns None tuple if not found.

    Strategy:
      - cys1 = first C in [15:30] (residue 22-ish)
      - cys2 = last C in the sequence (~96-ish in VHH)
      - W-G after cys2: regex search past cys2
      - cdr3 = [cys2+1, W_index)  (CDR3 between the second Cys and W-G-X-G motif)
    """
    cys_positions = [i for i, aa in enumerate(seq) if aa == 'C']
    if len(cys_positions) < 2:
        return None, None, None, None

    # cys1: prefer one in range 15..30 (typical VHH numbering)
    cys1 = next((c for c in cys_positions if 15 <= c <= 35), cys_positions[0])
    # cys2: last C in the sequence, must be after cys1+30 (CDR1+CDR2 in between)
    later = [c for c in cys_positions if c > cys1 + 30]
    cys2 = max(later) if later else None
    if cys2 is None:
        return cys1, None, None, None

    # W-G-X-G motif after cys2 within ~30 residues
    tail = seq[cys2 + 1: cys2 + 1 + 40]
    m = re.search(r"WG.G", tail)
    if not m:
        # fallback: just first W after cys2
        m_w = re.search(r"W", tail)
        if not m_w:
            return cys1, cys2, None, None
        w_offset = m_w.start()
    else:
        w_offset = m.start()
    cdr3_start = cys2 + 1
    cdr3_end = cys2 + 1 + w_offset  # half-open
    if cdr3_end <= cdr3_start:
        return cys1, cys2, None, None
    return cys1, cys2, cdr3_start, cdr3_end


def compute_features(traj_path: str, prmtop: str, cdr3_start: int, cdr3_end: int,
                     cys1_idx: int, cys2_idx: int) -> dict:
    topology = md.load_prmtop(prmtop)

    bb_idx = topology.select("protein and " + Q_SELECTION)
    if len(bb_idx) == 0:
        raise ValueError("no backbone heavy atoms")
    bb_res_idx = np.array([topology.atom(a).residue.index for a in bb_idx])
    bb_resname = np.array([topology.atom(a).residue.name.upper() for a in bb_idx])
    bb_hphil = np.isin(bb_resname, list(HPHIL_RESNAMES))

    ca_idx = topology.select("protein and name CA")
    ca_res_idx = np.array([topology.atom(a).residue.index for a in ca_idx])

    # mdtraj residue.index is 0-based and only counts protein residues (matches seq)
    # cdr3 boundary in residue index space
    cdr3_residues = set(range(cdr3_start, cdr3_end))

    # cys Cα indices (by residue index)
    cys1_ca = ca_idx[cys1_idx] if cys1_idx is not None and cys1_idx < len(ca_idx) else None
    cys2_ca = ca_idx[cys2_idx] if cys2_idx is not None and cys2_idx < len(ca_idx) else None

    # Native frame
    first = md.load_frame(traj_path, 0, top=topology)
    coords_bb = first.xyz[0, bb_idx, :]
    diff = coords_bb[:, None, :] - coords_bb[None, :, :]
    dist_bb = np.sqrt((diff ** 2).sum(axis=-1))
    res_gap = np.abs(bb_res_idx[:, None] - bb_res_idx[None, :])
    hphil_pair = bb_hphil[:, None] | bb_hphil[None, :]
    base_mask = (
        (dist_bb < NATIVE_CUTOFF_NM)
        & (res_gap > MIN_RESID_GAP)
        & np.triu(np.ones_like(dist_bb, dtype=bool), k=1)
        & hphil_pair
    )

    ii, jj = np.where(base_mask)
    if len(ii) == 0:
        raise ValueError("no native hphil contacts")
    d_native_bb = dist_bb[ii, jj]
    pair_atoms = np.stack([bb_idx[ii], bb_idx[jj]], axis=1)
    pair_res_a = bb_res_idx[ii]
    pair_res_b = bb_res_idx[jj]
    # CDR3 mask: BOTH residues in CDR3
    pair_cdr3 = np.array([
        (int(a) in cdr3_residues) and (int(b) in cdr3_residues)
        for a, b in zip(pair_res_a, pair_res_b)
    ])
    # Framework: BOTH residues outside CDR3
    pair_fw = np.array([
        (int(a) not in cdr3_residues) and (int(b) not in cdr3_residues)
        for a, b in zip(pair_res_a, pair_res_b)
    ])

    # CDR3 Cα subset for RMSF
    cdr3_ca_local = np.array(
        [k for k, r in enumerate(ca_res_idx) if int(r) in cdr3_residues]
    )
    fw_ca_local = np.array(
        [k for k, r in enumerate(ca_res_idx) if int(r) not in cdr3_residues]
    )

    q_frames = []
    ca_xyz_chunks = []
    ss_dist_per_frame = []

    sub_pair_atoms = pair_atoms
    for chunk in md.iterload(traj_path, top=topology, chunk=500):
        d = md.compute_distances(chunk, sub_pair_atoms)
        q_chunk = 1.0 / (1.0 + np.exp(BETA * (d - LAMBDA * d_native_bb[None, :])))
        q_frames.append(q_chunk)
        ca_xyz_chunks.append(chunk.xyz[:, ca_idx, :].copy())
        if cys1_ca is not None and cys2_ca is not None:
            ss = np.linalg.norm(
                chunk.xyz[:, cys1_ca, :] - chunk.xyz[:, cys2_ca, :], axis=-1
            )
            ss_dist_per_frame.append(ss)

    q_all = np.concatenate(q_frames, axis=0)
    ca_xyz = np.concatenate(ca_xyz_chunks, axis=0)

    n_total = q_all.shape[0]
    n_tail = max(1, int(n_total * LAST_FRAC))

    # ---- Q variants ----
    q_tail = q_all[-n_tail:]
    q_cdr3 = float(q_tail[:, pair_cdr3].mean()) if pair_cdr3.any() else float("nan")
    q_fw = float(q_tail[:, pair_fw].mean()) if pair_fw.any() else float("nan")

    # ---- RMSF ----
    sub_top = topology.subset(ca_idx)
    sub_traj = md.Trajectory(xyz=ca_xyz[-n_tail:], topology=sub_top)
    sub_traj.superpose(sub_traj, frame=0)
    mean_xyz = sub_traj.xyz.mean(axis=0)
    diff_ca = sub_traj.xyz - mean_xyz[None, :, :]
    rmsf_per_ca = np.sqrt((diff_ca ** 2).sum(axis=-1).mean(axis=0))
    rmsf_cdr3 = float(rmsf_per_ca[cdr3_ca_local].mean()) if cdr3_ca_local.size else float("nan")
    rmsf_fw = float(rmsf_per_ca[fw_ca_local].mean()) if fw_ca_local.size else float("nan")

    # ---- SS distance ----
    if ss_dist_per_frame:
        ss_all = np.concatenate(ss_dist_per_frame)
        ss_tail = ss_all[-n_tail:]
        ss_mean = float(ss_tail.mean())
        ss_std = float(ss_tail.std())
    else:
        ss_mean = float("nan")
        ss_std = float("nan")

    return {
        "q_cdr3": q_cdr3,
        "q_framework": q_fw,
        "rmsf_cdr3": rmsf_cdr3,
        "rmsf_framework": rmsf_fw,
        "ss_dist_mean": ss_mean,
        "ss_dist_std": ss_std,
        "cdr3_len": int(cdr3_end - cdr3_start),
        "n_frames_used": n_tail,
    }


def _process_one(job: str):
    pdb_id = os.path.basename(job).replace("job_nano_", "")
    traj = os.path.join(job, "nodes", PROD_NODE, "artifacts", "trajectory.dcd")
    native = os.path.join(job, "nodes", "prep_001", "artifacts", "merge", "merged.pdb")
    prmtop = os.path.join(job, "nodes", "topo_001", "artifacts", "system.parm7")
    if not (os.path.exists(traj) and os.path.exists(native) and os.path.exists(prmtop)):
        return (pdb_id, None, "missing files")
    try:
        seq = extract_sequence(native)
        if len(seq) < 80:
            return (pdb_id, None, f"seq too short ({len(seq)})")
        cys1, cys2, cdr3_start, cdr3_end = find_cdr3(seq)
        if cdr3_start is None or cdr3_end is None or cdr3_end - cdr3_start < 3:
            return (pdb_id, None, "no cdr3")
        feats = compute_features(traj, prmtop, cdr3_start, cdr3_end, cys1, cys2)
    except Exception as e:
        return (pdb_id, None, f"{type(e).__name__}: {e}")
    return (pdb_id, {"pdb_id": pdb_id, "seq": seq, "seq_len": len(seq), **feats},
            f"ok cdr3={cdr3_end-cdr3_start}res q_cdr3={feats['q_cdr3']:.3f}")


FEATURE_DIRECTIONS = {
    "q_cdr3":         "high",   # higher Q = more stable CDR3
    "q_framework":    "high",   # higher Q = more stable framework
    "rmsf_cdr3":      "low",    # less CDR3 flexibility = more stable
    "rmsf_framework": "low",
    "ss_dist_mean":   "low",    # closer Cys-Cys = stronger disulfide (Cα ~ 0.55nm at SS bond)
    "ss_dist_std":    "low",    # less fluctuation = stable disulfide
    "cdr3_len":       "low",    # longer CDR3 may destabilize? (heuristic)
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
    out = os.path.join(OUT_DIR, f"feat_{feature}{FEAT_SUFFIX}.csv")
    sub.to_csv(out, index=False)
    print(f"  Saved: {out} ({len(sub)} rows, range [{vmin:.4f}, {vmax:.4f}], dir={direction})", flush=True)


def main():
    job_dirs = sorted(glob.glob(os.path.join(MDCLAW_ROOT, "job_nano_*")))
    print(f"Found {len(job_dirs)} job_nano_* dirs (PROD_NODE={PROD_NODE})", flush=True)

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
