#!/usr/bin/env python3
"""Subsample Rosetta backrub pseudo-trajectories to 1/3 for the Zenodo deposit.

Each data/md/rosetta_traj/<pdb_id>_traj.pdb.gz is a protein-only multi-model PDB
(~304 backrub MODELs). Backrub samples are exchangeable Monte-Carlo snapshots with
no time ordering, so uniform subsampling (every STRIDE-th MODEL) is the natural
1/3 reduction. REMARK score lines inside each kept MODEL are preserved.

Output: <out>/trajectories/<pdb_id>_rosetta.pdb.gz  (kept MODELs only)
        <out>/_thin_manifest.tsv
"""
import argparse
import glob
import gzip
import os
import sys
from multiprocessing import Pool

STRIDE = 3


def thin_one(task):
    src, out_dir = task
    pdb_id = os.path.basename(src).replace("_traj.pdb.gz", "")
    dst = os.path.join(out_dir, "trajectories", f"{pdb_id}_rosetta.pdb.gz")
    try:
        counter = -1
        in_block = False
        keep = False
        n_total = 0
        n_kept = 0
        with gzip.open(src, "rt") as fin, gzip.open(dst, "wt") as fout:
            for line in fin:
                if line.startswith("MODEL"):
                    counter += 1
                    n_total += 1
                    in_block = True
                    keep = (counter % STRIDE == 0)
                    if keep:
                        n_kept += 1
                        fout.write(line)
                    continue
                if line.startswith("ENDMDL"):
                    if keep:
                        fout.write(line)
                    in_block = False
                    keep = False
                    continue
                if in_block:
                    if keep:
                        fout.write(line)
                else:
                    fout.write(line)
        return {"pdb_id": pdb_id, "status": "ok", "n_models_total": n_total,
                "n_models_kept": n_kept, "bytes": os.path.getsize(dst), "reason": ""}
    except Exception as e:  # noqa: BLE001
        return {"pdb_id": pdb_id, "status": "error", "reason": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-dir", default="data/md/rosetta_traj")
    ap.add_argument("--out", default="zenodo/rosetta_backrub_trajectories")
    ap.add_argument("--nproc", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.src_dir, "*_traj.pdb.gz")))
    if args.limit:
        files = files[: args.limit]
    tasks = [(f, args.out) for f in files]
    print(f"files={len(files)} stride={STRIDE} nproc={args.nproc}", flush=True)

    rows = []
    with Pool(args.nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(thin_one, tasks), 1):
            rows.append(r)
            if i % 100 == 0 or i == len(tasks):
                ok = sum(1 for x in rows if x["status"] == "ok")
                print(f"[{i}/{len(tasks)}] ok={ok}", flush=True)
            if r["status"] != "ok":
                print(f"  {r['status']}: {r['pdb_id']} :: {r['reason']}", flush=True)

    cols = ["pdb_id", "status", "n_models_total", "n_models_kept", "bytes", "reason"]
    path = os.path.join(args.out, "_thin_manifest.tsv")
    with open(path, "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    print(f"wrote {path}\nDONE ok={n_ok} bad={len(rows)-n_ok}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
