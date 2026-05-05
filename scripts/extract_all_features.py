#!/usr/bin/env python
"""Run all MD-feature extractors that experiments.yaml depends on.

Default: skips outputs that already exist (incremental). Use --force to overwrite.
Calls each existing extractor as a subprocess so per-script logging is unchanged.

Outputs (under data/md/):
    nanobody_qvalue_hphil.csv     ← scripts/extract_q_values.py
    nanobody_rmsf.csv             ← scripts/extract_rmsf.py
    feat_q_highflex.csv           ← scripts/extract_features_pilot.py
    feat_q_lowflex.csv            ← scripts/extract_features_pilot.py
    feat_saltbridge.csv           ← scripts/extract_features_pilot.py
    rosetta_qvalue_hphil.csv      ← scripts/extract_rosetta_qvalues.py  (needs Rosetta trajectories)
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO_ROOT, "scripts")
DATA = os.path.join(REPO_ROOT, "data", "md")

JOBS = [
    {
        "name": "MD Q-value (hphil)",
        "script": "extract_q_values.py",
        "produces": ["nanobody_qvalue_hphil.csv"],
    },
    {
        "name": "MD RMSF",
        "script": "extract_rmsf.py",
        "produces": ["nanobody_rmsf.csv"],
    },
    {
        "name": "MD pilot features (q_highflex / q_lowflex / saltbridge)",
        "script": "extract_features_pilot.py",
        "produces": [
            "feat_q_highflex.csv", "feat_q_lowflex.csv", "feat_saltbridge.csv",
        ],
    },
    {
        "name": "Rosetta Q-value (hphil)",
        "script": "extract_rosetta_qvalues.py",
        "produces": ["rosetta_qvalue_hphil.csv"],
        "note": "requires data/md/rosetta_traj/ from run_rosetta_backrub.py",
    },
]


def needs_run(produces: list[str], force: bool) -> bool:
    if force:
        return True
    return not all(os.path.exists(os.path.join(DATA, p)) for p in produces)


def run_one(job: dict, force: bool) -> int:
    if not needs_run(job["produces"], force):
        print(f"[skip] {job['name']} (outputs exist; use --force to redo)")
        return 0
    print(f"[run]  {job['name']}  → {job['script']}")
    cmd = ["uv", "run", "python", os.path.join(SCRIPTS, job["script"])]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="rerun even if output CSVs already exist")
    ap.add_argument("--only", type=str, default=None,
                    help="comma-separated subset of script basenames to run "
                         "(e.g. extract_q_values.py)")
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else None
    overall_rc = 0
    for job in JOBS:
        if only is not None and job["script"] not in only:
            continue
        rc = run_one(job, force=args.force)
        if rc != 0:
            print(f"[fail] {job['script']} exited with rc={rc}", file=sys.stderr)
            overall_rc = max(overall_rc, rc)
    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
