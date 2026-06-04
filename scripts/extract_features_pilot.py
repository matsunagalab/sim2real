#!/usr/bin/env python
"""Pilot feature extraction for autoresearch loop.

For each MD trajectory, computes 3 candidate scalar features in a single pass:

  - q_highflex : hydrophilic-all Q restricted to high-flex residues
                 (residues whose Cα RMSF is in the top 30% of the protein → CDR proxy)
  - q_lowflex  : hydrophilic-all Q restricted to low-flex residues (bottom 70% → framework proxy)
  - saltbridge : fraction of native salt-bridge pairs that persist (final 30% frames)

Outputs (3 CSV files, same row schema as nanobody_qvalue_hphil.csv):
  data/md/feat_q_highflex.csv
  data/md/feat_q_lowflex.csv
  data/md/feat_saltbridge.csv
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

# Q-value parameters (same as Q-hphil baseline, for fair comparison)
Q_SELECTION = "backbone and not element H"
BETA = 50.0
LAMBDA = 1.8
NATIVE_CUTOFF_NM = 0.45
MIN_RESID_GAP = 3
LAST_FRAC = 0.30
HIGH_FLEX_TOP = 0.30  # top 30% RMSF residues = "CDR proxy"

# Salt bridge parameters
SB_CUTOFF_NM = 0.40    # D/E carboxyl ↔ R/K/H basic N within 0.4 nm = native pair
SB_PERSIST_NM = 0.50   # in tail frames, treated as "persistent" if dist < 0.5 nm

# Hydrophilic residue set (Kamiya optimal)
HPHIL_RESNAMES = {'ASP', 'GLU', 'GLN', 'ASN', 'ARG', 'LYS', 'HIS',
                  'ASH', 'GLH', 'LYN', 'HID', 'HIE', 'HIP'}
ACID_RESNAMES = {'ASP', 'GLU', 'ASH', 'GLH'}
BASIC_RESNAMES = {'ARG', 'LYS', 'HIS', 'LYN', 'HID', 'HIE', 'HIP'}
ACID_ATOMS = {'OD1', 'OD2', 'OE1', 'OE2'}
BASIC_ATOMS = {'NZ', 'NH1', 'NH2', 'NE', 'ND1', 'NE2'}

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
    """Compute q_highflex, q_lowflex, saltbridge in a single trajectory pass."""
    topology = md.load_prmtop(prmtop)

    # ---- Backbone heavy atom indices for Q ----
    bb_idx = topology.select("protein and " + Q_SELECTION)
    if len(bb_idx) == 0:
        raise ValueError("no backbone heavy atoms")
    bb_res_idx = np.array([topology.atom(a).residue.index for a in bb_idx])
    bb_resname = np.array([topology.atom(a).residue.name.upper() for a in bb_idx])
    bb_hphil = np.isin(bb_resname, list(HPHIL_RESNAMES))

    # ---- Cα indices for RMSF (used to define high/low-flex residue sets) ----
    ca_idx = topology.select("protein and name CA")
    ca_res_idx = np.array([topology.atom(a).residue.index for a in ca_idx])

    # ---- Salt-bridge candidate atoms ----
    sb_atoms = []
    for a in topology.atoms:
        rn = a.residue.name.upper()
        an = a.name
        if rn in ACID_RESNAMES and an in ACID_ATOMS:
            sb_atoms.append((a.index, a.residue.index, "acid"))
        elif rn in BASIC_RESNAMES and an in BASIC_ATOMS:
            sb_atoms.append((a.index, a.residue.index, "basic"))

    # Native frame (frame 0) for reference distances
    first = md.load_frame(traj_path, 0, top=topology)
    coords_bb = first.xyz[0, bb_idx, :]
    coords_ca = first.xyz[0, ca_idx, :]
    coords_all = first.xyz[0]

    # ---- Native Q contacts (hphil-all, full protein) ----
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

    # ---- Native salt-bridge pairs from frame 0 ----
    sb_pairs = []
    sb_native_d = []
    if sb_atoms:
        acid_atoms = [a for a in sb_atoms if a[2] == "acid"]
        basic_atoms = [a for a in sb_atoms if a[2] == "basic"]
        for ai, ar, _ in acid_atoms:
            for bi, br, _ in basic_atoms:
                if abs(ar - br) <= MIN_RESID_GAP:
                    continue
                d = float(np.linalg.norm(coords_all[ai] - coords_all[bi]))
                if d < SB_CUTOFF_NM:
                    sb_pairs.append((ai, bi))
                    sb_native_d.append(d)
    n_native_sb = len(sb_pairs)

    # ---- Stream trajectory: collect Cα xyz, BB pair distances, salt-bridge distances ----
    bb_pair_atoms = np.stack(np.where(base_mask), axis=1)  # (n_pairs, 2) of bb_idx-local
    bb_pair_atom_global = np.stack([bb_idx[bb_pair_atoms[:, 0]], bb_idx[bb_pair_atoms[:, 1]]], axis=1)
    d_native_bb = dist_bb[base_mask]

    sb_pair_arr = np.array(sb_pairs, dtype=int) if sb_pairs else np.zeros((0, 2), dtype=int)

    ca_xyz_chunks = []
    bb_dist_chunks = []
    sb_dist_chunks = []

    pair_atoms_for_compute = np.concatenate([bb_pair_atom_global, sb_pair_arr], axis=0) if n_native_sb else bb_pair_atom_global

    for chunk in md.iterload(traj_path, top=topology, chunk=500):
        ca_xyz_chunks.append(chunk.xyz[:, ca_idx, :].copy())
        d = md.compute_distances(chunk, pair_atoms_for_compute)
        bb_dist_chunks.append(d[:, :len(bb_pair_atoms)])
        if n_native_sb:
            sb_dist_chunks.append(d[:, len(bb_pair_atoms):])

    ca_xyz = np.concatenate(ca_xyz_chunks, axis=0)  # (frames, n_ca, 3)
    bb_dists = np.concatenate(bb_dist_chunks, axis=0)  # (frames, n_bb_pairs)
    sb_dists = np.concatenate(sb_dist_chunks, axis=0) if n_native_sb else None

    n_total = ca_xyz.shape[0]
    n_tail = max(1, int(n_total * LAST_FRAC))

    # ---- Per-residue RMSF on final 30% frames (Cα, after self-superpose) ----
    sub_top = topology.subset(ca_idx)
    sub_traj = md.Trajectory(xyz=ca_xyz[-n_tail:], topology=sub_top)
    sub_traj.superpose(sub_traj, frame=0)
    mean_xyz = sub_traj.xyz.mean(axis=0)
    diff_ca = sub_traj.xyz - mean_xyz[None, :, :]
    rmsf_per_ca = np.sqrt((diff_ca ** 2).sum(axis=-1).mean(axis=0))  # (n_ca,)

    # Identify high-flex / low-flex residues by RMSF percentile
    rmsf_thr = np.quantile(rmsf_per_ca, 1.0 - HIGH_FLEX_TOP)
    high_flex_residues = set(int(ca_res_idx[i]) for i in range(len(ca_idx)) if rmsf_per_ca[i] >= rmsf_thr)

    # Build BB-pair masks based on residue membership
    pair_res_a = bb_res_idx[bb_pair_atoms[:, 0]]
    pair_res_b = bb_res_idx[bb_pair_atoms[:, 1]]
    pair_high = np.array([(int(a) in high_flex_residues) and (int(b) in high_flex_residues)
                          for a, b in zip(pair_res_a, pair_res_b)])
    pair_low = np.array([(int(a) not in high_flex_residues) and (int(b) not in high_flex_residues)
                         for a, b in zip(pair_res_a, pair_res_b)])

    # ---- Q timeseries (final 30% frames) ----
    q_full = 1.0 / (1.0 + np.exp(BETA * (bb_dists - LAMBDA * d_native_bb[None, :])))
    q_tail = q_full[-n_tail:]
    q_high = q_tail[:, pair_high].mean() if pair_high.any() else float("nan")
    q_low = q_tail[:, pair_low].mean() if pair_low.any() else float("nan")

    # ---- Salt-bridge persistence (final 30% frames) ----
    if n_native_sb:
        sb_tail = sb_dists[-n_tail:]
        sb_persist = float((sb_tail < SB_PERSIST_NM).mean())  # fraction of (frame,pair) with d < cutoff
    else:
        sb_persist = float("nan")

    return {
        "q_highflex": float(q_high),
        "q_lowflex": float(q_low),
        "saltbridge": float(sb_persist),
        "n_frames_used": n_tail,
        "n_bb_pairs_high": int(pair_high.sum()),
        "n_bb_pairs_low": int(pair_low.sum()),
        "n_native_sb": n_native_sb,
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
    return (pdb_id, {
        "pdb_id": pdb_id,
        "seq": seq,
        "seq_len": len(seq),
        **feats,
    }, f"ok q_hi={feats['q_highflex']:.3f} q_lo={feats['q_lowflex']:.3f} sb={feats['saltbridge']:.3f}")


def write_feature_csv(df: pd.DataFrame, feature: str, name: str):
    """Save (pdb_id, seq, ddg_scaled01) CSV with feature scaled to [0,1]."""
    sub = df[["pdb_id", "seq", "seq_len", feature]].copy()
    sub = sub.dropna(subset=[feature])
    vmin, vmax = sub[feature].min(), sub[feature].max()
    if vmax > vmin:
        sub["ddg_scaled01"] = (sub[feature] - vmin) / (vmax - vmin)
    else:
        sub["ddg_scaled01"] = 0.5
    out = os.path.join(OUT_DIR, f"feat_{name}.csv")
    sub.to_csv(out, index=False)
    print(f"  Saved: {out} ({len(sub)} rows, range [{vmin:.4f}, {vmax:.4f}])", flush=True)


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
    os.makedirs(OUT_DIR, exist_ok=True)
    write_feature_csv(df, "q_highflex", "q_highflex")
    write_feature_csv(df, "q_lowflex", "q_lowflex")
    write_feature_csv(df, "saltbridge", "saltbridge")


if __name__ == "__main__":
    main()
