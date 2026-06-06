#!/usr/bin/env python
"""Short-trajectory Q-value extraction (cost analysis).

Recompute the hydrophilic-all Best-Hummer Q-value (identical parameters to
extract_q_values.py) but truncating each trajectory to only the FIRST T ns,
to test whether a SHORT (= cheap) MD run still yields a useful auxiliary
signal. All target lengths are computed in a single pass over each trajectory.

For each length T (ns) -> data/md/feat_q_hphil_400K_t{T}ns.csv
with the same schema/loader path as the full-length file
(pdb_id, seq, q_value_raw, n_frames_used, n_contacts, seq_len, ddg_scaled01).

Defaults to the 400K production node (prod_002) and matches the exact pdb_id
set of the existing full-length file so the scaling comparison is apples-to-apples.
"""
import os
import sys
import glob
import time

import numpy as np
import pandas as pd
import mdtraj as md

MDCLAW_ROOT = "/home/yasu/tmp/mdclaw"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD_NODE = os.environ.get("PROD_NODE", "prod_002")  # 400K
REF_CSV = os.path.join(REPO_ROOT, "data", "md", "nanobody_qvalue_hphil_400K.csv")
OUT_DIR = os.path.join(REPO_ROOT, "data", "md")

# Q-value parameters — identical to extract_q_values.py
SELECTION = "backbone and not element H"
BETA = 50.0
LAMBDA = 1.8
NATIVE_CUTOFF_NM = 0.45
MIN_RESID_GAP = 3
FRAMES_PER_NS = 10  # 100 ps/frame (1000 frames = 100 ns)
TAIL_FRAC = 0.30    # average over final 30% of the (truncated) trajectory

# Target trajectory lengths in ns to emit
TARGET_NS = [int(x) for x in os.environ.get("TARGET_NS", "5,10,17,30,50,100").split(",")]

HPHIL_RESNAMES = {'ASP', 'GLU', 'GLN', 'ASN', 'ARG', 'LYS', 'HIS',
                  'ASH', 'GLH', 'LYN', 'HID', 'HIE', 'HIP'}


def q_timeseries(trajectory_file, prmtop):
    """Return the full per-frame Q-value array (hydrophilic-all contacts)."""
    topology = md.load_prmtop(prmtop)
    sel_idx = topology.select("protein and " + SELECTION)
    if len(sel_idx) == 0:
        raise ValueError("no backbone heavy atoms")
    first = md.load_frame(trajectory_file, 0, top=topology)
    coords_native = first.xyz[0, sel_idx, :]
    res_idx = np.array([topology.atom(a).residue.index for a in sel_idx])
    resname_per_atom = np.array([topology.atom(a).residue.name.upper() for a in sel_idx])
    hphil_per_atom = np.isin(resname_per_atom, list(HPHIL_RESNAMES))

    diff = coords_native[:, None, :] - coords_native[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=-1))
    res_gap = np.abs(res_idx[:, None] - res_idx[None, :])
    hphil_pair = hphil_per_atom[:, None] | hphil_per_atom[None, :]
    mask = ((dist < NATIVE_CUTOFF_NM) & (res_gap > MIN_RESID_GAP)
            & np.triu(np.ones_like(dist, dtype=bool), k=1) & hphil_pair)
    ii, jj = np.where(mask)
    if len(ii) == 0:
        raise ValueError("no native contacts")
    d_native = dist[ii, jj]
    pair_atoms = np.stack([sel_idx[ii], sel_idx[jj]], axis=1)

    q_frames = []
    for chunk in md.iterload(trajectory_file, top=topology, chunk=500):
        dists = md.compute_distances(chunk, pair_atoms)
        q = 1.0 / (1.0 + np.exp(BETA * (dists - LAMBDA * d_native[None, :])))
        q_frames.append(q.mean(axis=1))
    return np.concatenate(q_frames), len(ii)


def q_mean_for_length(q_all, n_ns):
    """Mean Q over the final TAIL_FRAC of the FIRST n_ns of the trajectory."""
    n_keep = min(int(n_ns * FRAMES_PER_NS), len(q_all))
    if n_keep <= 0:
        return np.nan, 0
    seg = q_all[:n_keep]
    n_tail = max(1, int(round(n_keep * TAIL_FRAC)))
    tail = seg[-n_tail:]
    return float(tail.mean()), len(tail)


def main():
    ref = pd.read_csv(REF_CSV)
    want = list(ref["pdb_id"].astype(str))
    seq_by_id = dict(zip(ref["pdb_id"].astype(str), ref["seq"]))
    print(f"Target nanobodies: {len(want)} (from {os.path.basename(REF_CSV)})", flush=True)
    print(f"Lengths (ns): {TARGET_NS} | PROD_NODE={PROD_NODE}", flush=True)

    rows_by_ns = {t: [] for t in TARGET_NS}
    skipped = []
    t0 = time.time()
    for i, pdb_id in enumerate(want):
        job = os.path.join(MDCLAW_ROOT, f"job_nano_{pdb_id}")
        traj = os.path.join(job, "nodes", PROD_NODE, "artifacts", "trajectory.dcd")
        prmtop = os.path.join(job, "nodes", "topo_001", "artifacts", "system.parm7")
        if not (os.path.exists(traj) and os.path.exists(prmtop)):
            skipped.append((pdb_id, "missing traj/prmtop"))
            continue
        try:
            q_all, n_contacts = q_timeseries(traj, prmtop)
        except Exception as e:
            skipped.append((pdb_id, f"{type(e).__name__}: {e}"))
            continue
        seq = seq_by_id[pdb_id]
        for t in TARGET_NS:
            qm, nfr = q_mean_for_length(q_all, t)
            rows_by_ns[t].append({
                "pdb_id": pdb_id, "seq": seq, "q_value_raw": qm,
                "n_frames_used": nfr, "n_contacts": n_contacts, "seq_len": len(seq),
            })
        if (i + 1) % 100 == 0:
            rate = (i + 1) / (time.time() - t0)
            print(f"[{i+1}/{len(want)}] rate={rate:.1f}/s eta={(len(want)-i-1)/rate/60:.1f}min", flush=True)

    for t in TARGET_NS:
        df = pd.DataFrame(rows_by_ns[t])
        if df.empty:
            print(f"[warn] no rows for {t}ns", flush=True)
            continue
        qmin, qmax = df["q_value_raw"].min(), df["q_value_raw"].max()
        df["ddg_scaled01"] = ((df["q_value_raw"] - qmin) / (qmax - qmin)
                              if qmax > qmin else 0.5)
        out = os.path.join(OUT_DIR, f"feat_q_hphil_400K_t{t}ns.csv")
        df.to_csv(out, index=False)
        print(f"Saved {out}: {len(df)} rows, Q range [{qmin:.4f},{qmax:.4f}]", flush=True)

    print(f"\nDone in {time.time()-t0:.0f}s. processed={len(want)-len(skipped)} skipped={len(skipped)}", flush=True)
    for pid, r in skipped[:15]:
        print(f"  skip {pid}: {r}", flush=True)


if __name__ == "__main__":
    main()
