#!/usr/bin/env python3
"""Finalize the Zenodo staging tree: per-archive MANIFEST.tsv, CHECKSUMS.sha256,
README.md, and a top-level README. Does NOT create ZIP archives (deferred until
FEP / ThermoMPNN components are added).

Run after scripts/strip_md_solvent.py and scripts/thin_rosetta_traj.py finish.
"""
import csv
import glob
import hashlib
import json
import os
from multiprocessing import Pool

ZROOT = "zenodo"
MD = {
    "300K": {"dir": f"{ZROOT}/md_trajectories_300K", "node": "prod_001",
             "qvalue": "nanobody_qvalue.csv"},
    "400K": {"dir": f"{ZROOT}/md_trajectories_400K", "node": "prod_002",
             "qvalue": "nanobody_qvalue_400K.csv"},
}
ROS = {"dir": f"{ZROOT}/rosetta_backrub_trajectories", "qvalue": "rosetta_qvalue_hphil.csv"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return path, h.hexdigest(), os.path.getsize(path)


def hash_dir(root):
    files = sorted(f for f in glob.glob(f"{root}/**/*", recursive=True) if os.path.isfile(f)
                   and not f.endswith("CHECKSUMS.sha256"))
    with Pool(12) as p:
        res = p.map(sha256, files)
    return res  # list of (path, hexdigest, size)


def read_tsv(path):
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def qvalue_ids(csv_path):
    if not os.path.exists(csv_path):
        return set()
    with open(csv_path) as fh:
        r = csv.DictReader(fh)
        key = "pdb_id" if "pdb_id" in r.fieldnames else r.fieldnames[0]
        return {row[key] for row in r}


def human(nbytes):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or u == "TB":
            return f"{nbytes:.1f} {u}"
        nbytes /= 1024


def write_checksums(root, hashes):
    rel = lambda p: os.path.relpath(p, root)
    with open(f"{root}/CHECKSUMS.sha256", "w") as fh:
        for path, dig, _ in sorted(hashes):
            fh.write(f"{dig}  {rel(path)}\n")


def finalize_md(temp):
    info = MD[temp]
    root = info["dir"]
    strip = {r["pdb_id"]: r for r in read_tsv(f"{root}/_strip_manifest.tsv")
             if r.get("status") == "ok"}
    hashes = hash_dir(root)
    write_checksums(root, hashes)
    digest = {os.path.basename(p): d for p, d, _ in hashes}

    # MANIFEST.tsv keyed by trajectory (pdb)
    ids = sorted(strip)
    cols = ["pdb_id", "temperature_K", "trajectory_dcd", "native_pdb",
            "n_frames_kept", "n_frames_total", "n_atoms_protein", "source_job",
            "dcd_sha256", "pdb_sha256"]
    with open(f"{root}/MANIFEST.tsv", "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for pid in ids:
            r = strip[pid]
            dcd = f"{pid}_{temp}.dcd"
            pdb = f"{pid}_{temp}.pdb"
            fh.write("\t".join([
                pid, temp.rstrip("K"), f"trajectories/{dcd}", f"trajectories/{pdb}",
                r["n_frames_kept"], r["n_frames_total"], r["n_atoms_protein"],
                r["source_job"], digest.get(dcd, ""), digest.get(pdb, ""),
            ]) + "\n")

    total = sum(s for _, _, s in hashes)
    qids = qvalue_ids(f"{root}/derived/{info['qvalue']}")
    covered = qids & set(ids)
    stats = {"n_trajectories": len(ids), "total_bytes": total,
             "qvalue_ids": len(qids), "qvalue_covered": len(covered),
             "qvalue_missing": sorted(qids - set(ids))}
    write_md_readme(temp, stats)
    return temp, stats


def finalize_rosetta():
    root = ROS["dir"]
    thin = {r["pdb_id"]: r for r in read_tsv(f"{root}/_thin_manifest.tsv")
            if r.get("status") == "ok"}
    hashes = hash_dir(root)
    write_checksums(root, hashes)
    digest = {os.path.basename(p): d for p, d, _ in hashes}
    ids = sorted(thin)
    cols = ["pdb_id", "trajectory_pdb_gz", "n_models_kept", "n_models_total", "sha256"]
    with open(f"{root}/MANIFEST.tsv", "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for pid in ids:
            r = thin[pid]
            f = f"{pid}_rosetta.pdb.gz"
            fh.write("\t".join([pid, f"trajectories/{f}", r["n_models_kept"],
                                r["n_models_total"], digest.get(f, "")]) + "\n")
    total = sum(s for _, _, s in hashes)
    stats = {"n_trajectories": len(ids), "total_bytes": total}
    write_rosetta_readme(stats)
    return "rosetta", stats


MD_README = """\
# Nanobody all-atom MD trajectories — {temp}

Solvent-stripped protein-only molecular-dynamics trajectories for nanobody (VHH)
domains, run at **{temp}** with OpenMM (all-atom, explicit solvent). Part of the
data deposit for the Sim2Real nanobody thermal-stability study.

## Contents
- `trajectories/<pdb_id>_{temp}.dcd` — protein-only trajectory, **final {nkept} frames**
  of the ~1000-frame (~100 ns, 100 ps/frame) production run.
- `trajectories/<pdb_id>_{temp}.pdb` — protein-only coordinates of **frame 0**, the
  Q-value native reference and the topology to load the DCD against.
- `derived/` — per-sequence quantities computed from these trajectories
  (Q-value `{qvalue}` and MD-derived descriptor features).
- `metadata/` — job manifest, run status, and SAbDab structure summary.
- `MANIFEST.tsv`, `CHECKSUMS.sha256` — per-file inventory and integrity hashes.

## Processing
Water and ions were removed (MDAnalysis `select_atoms("protein")`). To match the
published Q-value exactly, only the **final third** of each trajectory is kept
(`n_use = max(300, n_total // 3)` = {nkept} for a 1000-frame run); frame 0 is kept
separately as the native reference. This reproduces the analysis window in
`scripts/extract_q_values.py` (final 30 ns, `LAST_NS=30`).

## Loading (Python)
```python
import MDAnalysis as mda
u = mda.Universe("trajectories/1bzq_{temp}.pdb", "trajectories/1bzq_{temp}.dcd")
protein = u.select_atoms("protein")
```

## Summary
- Trajectories: **{n}**
- Total size: **{size}**
- Published {qvalue} sequences covered by these trajectories: **{cov}/{qn}**{miss}

See the paper's Methods for the full simulation protocol. Released under the deposit
license stated on the Zenodo record.
"""

ROS_README = """\
# Nanobody Rosetta backrub pseudo-trajectories

Protein-only Rosetta backrub conformational ensembles for nanobody (VHH) domains,
used as a structure-based source label in the Sim2Real nanobody thermal-stability study.

## Contents
- `trajectories/<pdb_id>_rosetta.pdb.gz` — gzipped multi-model PDB, **{nkept} of 304
  backrub MODELs** (uniformly subsampled to 1/3). REMARK score lines are preserved.
- `derived/rosetta_qvalue_hphil.csv` — per-sequence Q-value from the backrub ensembles.
- `metadata/` — SAbDab structure summary.
- `MANIFEST.tsv`, `CHECKSUMS.sha256` — per-file inventory and integrity hashes.

## Processing
Backrub MODELs are exchangeable Monte-Carlo samples (no time ordering), so every
3rd MODEL is retained (stride 3) to reach 1/3 size. Generated with Rosetta backrub
at a 300 K-equivalent `mc_kt`; see the paper's Methods.

## Summary
- Trajectories: **{n}**
- Total size: **{size}**

Released under the deposit license stated on the Zenodo record.
"""


def write_md_readme(temp, st):
    nkept = 333
    miss = ""
    if st["qvalue_missing"]:
        show = ", ".join(st["qvalue_missing"][:15])
        more = "" if len(st["qvalue_missing"]) <= 15 else f" (+{len(st['qvalue_missing'])-15} more)"
        miss = f"\n- Missing (no trajectory): {show}{more}"
    txt = MD_README.format(
        temp=temp, nkept=nkept, qvalue=MD[temp]["qvalue"], n=st["n_trajectories"],
        size=human(st["total_bytes"]), cov=st["qvalue_covered"], qn=st["qvalue_ids"],
        miss=miss)
    with open(f"{MD[temp]['dir']}/README.md", "w") as fh:
        fh.write(txt)


def write_rosetta_readme(st):
    txt = ROS_README.format(nkept=102, n=st["n_trajectories"], size=human(st["total_bytes"]))
    with open(f"{ROS['dir']}/README.md", "w") as fh:
        fh.write(txt)


TOP_README = """\
# Sim2Real nanobody thermal-stability — simulation data deposit

Large simulation-derived datasets supporting the study *Simulation-informed transfer
learning improves low-data nanobody thermal-stability prediction*. The lightweight
code, processed labels, and analysis live in the GitHub repository; this Zenodo
record holds the bulky trajectory data.

## Components
| Directory | Description | Trajectories | Size |
|---|---|---|---|
| `md_trajectories_300K/` | All-atom OpenMM MD at 300 K (solvent-stripped, final 1/3) | {n300} | {s300} |
| `md_trajectories_400K/` | All-atom OpenMM MD at 400 K (solvent-stripped, final 1/3) | {n400} | {s400} |
| `rosetta_backrub_trajectories/` | Rosetta backrub ensembles (1/3 of MODELs) | {nros} | {sros} |
{extra}

Each component has its own `README.md`, `MANIFEST.tsv`, and `CHECKSUMS.sha256`.

## Notes
- Trajectories are **protein only**; water and ions were removed to reduce size.
- MD trajectories keep the **final third** of frames, matching the published
  Q-value analysis window; frame 0 is included as the native reference.
- Regeneration scripts: `scripts/strip_md_solvent.py`, `scripts/thin_rosetta_traj.py`,
  `scripts/build_zenodo_manifest.py` (in the GitHub repository).

Total: **{ntot} trajectories, {stot}**.
"""


def write_top_readme(all_stats):
    s = dict(all_stats)
    extra = ""  # FEP / ThermoMPNN rows added when those components are staged
    ntot = sum(v["n_trajectories"] for v in s.values())
    stot = sum(v["total_bytes"] for v in s.values())
    txt = TOP_README.format(
        n300=s["300K"]["n_trajectories"], s300=human(s["300K"]["total_bytes"]),
        n400=s["400K"]["n_trajectories"], s400=human(s["400K"]["total_bytes"]),
        nros=s["rosetta"]["n_trajectories"], sros=human(s["rosetta"]["total_bytes"]),
        extra=extra, ntot=ntot, stot=human(stot))
    with open(f"{ZROOT}/README.md", "w") as fh:
        fh.write(txt)


def main():
    all_stats = {}
    for temp in ("300K", "400K"):
        k, st = finalize_md(temp)
        all_stats[k] = st
        print(f"[{k}] {st['n_trajectories']} traj, {human(st['total_bytes'])}, "
              f"qvalue cover {st['qvalue_covered']}/{st['qvalue_ids']}", flush=True)
    k, st = finalize_rosetta()
    all_stats[k] = st
    print(f"[{k}] {st['n_trajectories']} traj, {human(st['total_bytes'])}", flush=True)
    # Top-level zenodo/README.md is maintained by hand (covers FEP/ThermoMPNN too);
    # only generate it if missing so reruns don't clobber the comprehensive version.
    if not os.path.exists(f"{ZROOT}/README.md"):
        write_top_readme(all_stats)
    print("wrote per-component READMEs, MANIFESTs, CHECKSUMS (no ZIP).", flush=True)


if __name__ == "__main__":
    main()
