#!/usr/bin/env python3
"""Strip solvent from OpenMM nanobody MD trajectories for the Zenodo deposit.

For each job under MDCLAW_ROOT/job_nano_<tag>/nodes/:
  - 300 K production = prod_001/artifacts/trajectory.dcd
  - 400 K production = prod_002/artifacts/trajectory.dcd
  - topology        = topo_001/artifacts/system.parm7

The solvated system (~38-51k atoms) is reduced to protein only (~1.3-1.9k atoms)
and the trajectory is trimmed to the SAME final window the published Q-value used:

    n_total = number of frames
    if n_total > 300:  n_use = min(max(300, n_total // 3), n_total)   # = 333 for 1000
    else:              n_use = n_total
    keep frames[-n_use:]

(see scripts/extract_q_values.py: LAST_NS=30, n_use = max(int(last_ns*10), n_total//3))

Per trajectory we write into the staging tree:
  <out>/trajectories/<pdb_id>_<temp>.dcd   protein-only, final n_use frames
  <out>/trajectories/<pdb_id>_<temp>.pdb   protein-only frame 0 (= Q native reference + DCD topology)

frame 0 (the Q native reference) is written as the .pdb so the deposit alone
reproduces the published Q-value, and so the binary DCD has a topology to load against.

Output is a per-(job,temp) manifest row appended to <out>/_strip_manifest.tsv.
"""
import argparse
import glob
import json
import os
import sys
import warnings
from multiprocessing import Pool

warnings.filterwarnings("ignore")
import MDAnalysis as mda  # noqa: E402

LAST_NS = 30.0  # must match scripts/extract_q_values.py
TEMP_NODES = {"300K": "prod_001", "400K": "prod_002"}


def n_use_frames(n_total: int) -> int:
    """Replicate extract_q_values.py final-window selection exactly."""
    if n_total > 300:
        return min(max(int(LAST_NS * 10), n_total // 3), n_total)
    return n_total


def load_tag_to_pdb(manifest_path: str) -> dict:
    with open(manifest_path) as fh:
        data = json.load(fh)
    m = {}
    for row in data:
        tag = str(row.get("tag") or row.get("pdb"))
        pdb = str(row.get("pdb") or row.get("tag"))
        if tag:
            m[tag] = pdb
    return m


def strip_one(task):
    job_dir, tag, pdb_id, temp, out_dir = task
    node = TEMP_NODES[temp]
    top = os.path.join(job_dir, "nodes", "topo_001", "artifacts", "system.parm7")
    dcd = os.path.join(job_dir, "nodes", node, "artifacts", "trajectory.dcd")
    if not os.path.exists(top):
        return {"pdb_id": pdb_id, "temp": temp, "status": "skip", "reason": "no parm7"}
    if not os.path.exists(dcd):
        return {"pdb_id": pdb_id, "temp": temp, "status": "skip", "reason": "no trajectory.dcd"}
    try:
        u = mda.Universe(top, dcd)
        prot = u.select_atoms("protein")
        if prot.n_atoms == 0:
            return {"pdb_id": pdb_id, "temp": temp, "status": "skip", "reason": "0 protein atoms"}
        n_total = len(u.trajectory)
        n_use = n_use_frames(n_total)
        start = n_total - n_use

        traj_dir = os.path.join(out_dir, "trajectories")
        pdb_out = os.path.join(traj_dir, f"{pdb_id}_{temp}.pdb")
        dcd_out = os.path.join(traj_dir, f"{pdb_id}_{temp}.dcd")

        # frame 0 = Q native reference + topology companion
        u.trajectory[0]
        prot.write(pdb_out)

        # final n_use frames -> protein-only DCD
        with mda.Writer(dcd_out, prot.n_atoms) as w:
            for _ in u.trajectory[start:]:
                w.write(prot)

        return {
            "pdb_id": pdb_id, "temp": temp, "status": "ok", "reason": "",
            "n_atoms_protein": prot.n_atoms, "n_frames_total": n_total,
            "n_frames_kept": n_use, "source_job": os.path.basename(job_dir),
            "dcd_bytes": os.path.getsize(dcd_out),
        }
    except Exception as e:  # noqa: BLE001
        return {"pdb_id": pdb_id, "temp": temp, "status": "error",
                "reason": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/yasu/tmp/mdclaw")
    ap.add_argument("--manifest", default="data/md/metadata/nano_manifest_400K.json")
    ap.add_argument("--out-300k", default="zenodo/md_trajectories_300K")
    ap.add_argument("--out-400k", default="zenodo/md_trajectories_400K")
    ap.add_argument("--temps", default="300K,400K")
    ap.add_argument("--nproc", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="process only first N jobs (test)")
    ap.add_argument("--only", default="", help="comma-separated tags to process (test)")
    args = ap.parse_args()

    out_map = {"300K": args.out_300k, "400K": args.out_400k}
    temps = [t for t in args.temps.split(",") if t]
    tag2pdb = load_tag_to_pdb(args.manifest)

    jobs = sorted(glob.glob(os.path.join(args.root, "job_nano_*")))
    if args.only:
        keep = set(args.only.split(","))
        jobs = [j for j in jobs if os.path.basename(j).replace("job_nano_", "") in keep]
    if args.limit:
        jobs = jobs[: args.limit]

    tasks = []
    for j in jobs:
        tag = os.path.basename(j).replace("job_nano_", "")
        pdb_id = tag2pdb.get(tag, tag)
        for temp in temps:
            tasks.append((j, tag, pdb_id, temp, out_map[temp]))

    print(f"jobs={len(jobs)} temps={temps} tasks={len(tasks)} nproc={args.nproc}", flush=True)

    rows = []
    with Pool(args.nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(strip_one, tasks), 1):
            rows.append(r)
            if i % 50 == 0 or i == len(tasks):
                ok = sum(1 for x in rows if x["status"] == "ok")
                print(f"[{i}/{len(tasks)}] ok={ok}", flush=True)
            if r["status"] != "ok":
                print(f"  {r['status']}: {r['pdb_id']} {r['temp']} :: {r['reason']}", flush=True)

    # write per-temp manifest fragments
    cols = ["pdb_id", "temp", "status", "n_atoms_protein", "n_frames_total",
            "n_frames_kept", "source_job", "dcd_bytes", "reason"]
    for temp in temps:
        path = os.path.join(out_map[temp], "_strip_manifest.tsv")
        with open(path, "w") as fh:
            fh.write("\t".join(cols) + "\n")
            for r in rows:
                if r["temp"] != temp:
                    continue
                fh.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
        print(f"wrote {path}", flush=True)

    n_ok = sum(1 for r in rows if r["status"] == "ok")
    n_bad = len(rows) - n_ok
    print(f"DONE ok={n_ok} skip/err={n_bad}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
