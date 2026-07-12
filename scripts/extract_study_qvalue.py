#!/usr/bin/env python3
"""Native-contact Q-value for the fep_md_400k WT/mutant MD study.

For each completed variant under
  mdclaw/studies/fep_md_400k_all/<vid>/jobs/main/nodes/
compute the Best-Hummer fraction of native contacts Q (backbone heavy atoms),
averaged over the COMMON first-40 ns window (first 4000 frames at dt=10 ps), using
frame 0 as the native reference. Trajectories are a mix of 40 ns and 100 ns runs;
taking the first 4000 frames gives a consistent comparison window.

Q is a per-variant fold-stability proxy. Because the downstream ML label is min-max
scaled, subtracting a constant WT reference (ΔQ) is absorbed by the scaling, so raw Q
is equivalent to ΔQ-vs-constant-WT for the transfer-learning scaling experiment.

Output: <out> CSV with columns: vid, system, mutation, seq, q_value, n_frames_used
"""
import argparse
import csv
import glob
import os
import warnings
from multiprocessing import Pool

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import MDAnalysis as mda  # noqa: E402
from MDAnalysis.lib.util import convert_aa_code  # noqa: E402

# match scripts/extract_q_values.py
BETA, LAMBDA, CUT_NM, GAP = 50.0, 1.8, 0.45, 3
N_WINDOW = 4000  # first 40 ns at dt = 10 ps

STUDY = "mdclaw/studies/fep_md_400k_all"


def variant_paths(vid):
    base = f"{STUDY}/{vid}/jobs/main/nodes"
    top = f"{base}/topo_001/artifacts/system.topology.pdb"
    dcd = f"{base}/prod_001/artifacts/trajectory.dcd"
    return top, dcd


def seq_one_letter(prot):
    out = []
    for rn in prot.residues.resnames:
        try:
            out.append(convert_aa_code(rn))
        except Exception:
            out.append("X")
    return "".join(out)


def compute_one(vid):
    top, dcd = variant_paths(vid)
    if not (os.path.exists(top) and os.path.exists(dcd)):
        return {"vid": vid, "status": "skip", "reason": "missing top/dcd"}
    try:
        u = mda.Universe(top, dcd)
        bb = u.select_atoms("backbone")
        if bb.n_atoms == 0:
            return {"vid": vid, "status": "skip", "reason": "no backbone"}
        resid = bb.resindices
        u.trajectory[0]
        x0 = bb.positions / 10.0
        d0 = np.sqrt(((x0[:, None, :] - x0[None, :, :]) ** 2).sum(-1))
        mask = (d0 < CUT_NM) & (np.abs(resid[:, None] - resid[None, :]) > GAP) \
            & np.triu(np.ones_like(d0, bool), 1)
        ii, jj = np.where(mask)
        if len(ii) == 0:
            return {"vid": vid, "status": "skip", "reason": "no native contacts"}
        dN = d0[ii, jj]
        ai, aj = bb.indices[ii], bb.indices[jj]
        n_use = min(N_WINDOW, len(u.trajectory))
        qsum = 0.0
        for _ in u.trajectory[:n_use]:
            p = u.atoms.positions / 10.0
            d = np.sqrt(((p[ai] - p[aj]) ** 2).sum(-1))
            qsum += (1.0 / (1.0 + np.exp(BETA * (d - LAMBDA * dN)))).mean()
        q = qsum / n_use
        prot = u.select_atoms("protein")
        system, _, mutation = vid.partition("_")
        return {"vid": vid, "system": system, "mutation": mutation,
                "seq": seq_one_letter(prot), "q_value": q,
                "n_frames_used": n_use, "status": "ok", "reason": ""}
    except Exception as e:  # noqa: BLE001
        return {"vid": vid, "status": "error", "reason": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="1mel", help="variant prefix filter (e.g. 1mel)")
    ap.add_argument("--out", default="data/md/study_qvalue_fep400k_1mel.csv")
    ap.add_argument("--nproc", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    vids = sorted(os.path.basename(d.rstrip("/"))
                  for d in glob.glob(f"{STUDY}/{args.system}_*/"))
    vids = [v for v in vids if os.path.exists(variant_paths(v)[1])]
    if args.limit:
        vids = vids[: args.limit]
    print(f"variants with trajectory: {len(vids)} (system={args.system}) nproc={args.nproc}", flush=True)

    rows = []
    with Pool(args.nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(compute_one, vids), 1):
            rows.append(r)
            if i % 25 == 0 or i == len(vids):
                ok = sum(1 for x in rows if x["status"] == "ok")
                print(f"[{i}/{len(vids)}] ok={ok}", flush=True)
            if r["status"] != "ok":
                print(f"  {r['status']}: {r['vid']} :: {r['reason']}", flush=True)

    ok_rows = [r for r in rows if r["status"] == "ok"]
    cols = ["vid", "system", "mutation", "seq", "q_value", "n_frames_used"]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in ok_rows:
            w.writerow(r)
    print(f"wrote {args.out}: {len(ok_rows)} ok / {len(rows)} total", flush=True)


if __name__ == "__main__":
    main()
