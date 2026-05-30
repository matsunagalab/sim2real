#!/usr/bin/env python
"""Small validation-only hyperparameter search for fair Tm/aux comparison."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs" / "hparam_search"
RESULT_ROOT = REPO_ROOT / "results" / "hparam_search"


COMMON = {
    "n-runs": "3",
    "train-mode": "mtl",
    "selection-scope": "tm",
    "final-eval-split": "val",
    "encoder-mode": "hot",
}


BASE_CONFIGS = [
    ("default", {}),
    ("enc3e-5", {"encoder-lr": "3e-5"}),
    ("enc3e-4", {"encoder-lr": "3e-4"}),
    ("lr1e-4_enc3e-5", {"learning-rate": "1e-4", "encoder-lr": "3e-5"}),
    ("drop0.05", {"dropout-rate": "0.05"}),
    ("drop0.30", {"dropout-rate": "0.30"}),
]


AUX_EXTRA_CONFIGS = [
    ("fixed_w0.05", {"mtl-weight-mode": "fixed", "md-weight": "0.05"}),
    ("fixed_w0.10", {"mtl-weight-mode": "fixed", "md-weight": "0.10"}),
    ("fixed_w0.25", {"mtl-weight-mode": "fixed", "md-weight": "0.25"}),
    ("fixed_w0.50", {"mtl-weight-mode": "fixed", "md-weight": "0.50"}),
]


def cli_args(options: dict[str, str]) -> list[str]:
    args = []
    for key, value in options.items():
        args.extend([f"--{key}", str(value)])
    return args


def build_jobs() -> list[dict]:
    jobs = []

    for label, hp in BASE_CONFIGS:
        exp = f"hpo_tm_{label}"
        options = {
            **COMMON,
            **hp,
            "exp-name": exp,
            "result-dir": str(RESULT_ROOT / exp),
            "ddg-source": "none",
            "md-source": "none",
            "n-tm-list": "57",
        }
        jobs.append({"group": "tm", "label": label, "exp": exp, "options": options})

    for label, hp in BASE_CONFIGS + AUX_EXTRA_CONFIGS:
        exp = f"hpo_q320_{label}"
        options = {
            **COMMON,
            **hp,
            "exp-name": exp,
            "result-dir": str(RESULT_ROOT / exp),
            "ddg-source": "none",
            "md-source": "MD_Q_HPHIL_400K",
            "n-md-list": "320",
        }
        jobs.append({"group": "q320", "label": label, "exp": exp, "options": options})

    return jobs


def collect_job_result(job: dict, gpu: str | None = None, rc: int | None = None) -> dict:
    row = {**job}
    if gpu is not None:
        row["gpu"] = gpu
    if rc is not None:
        row["rc"] = rc
    row["log"] = str(LOG_DIR / f"{job['exp']}.log")

    # prepare.py writes the structured summary to results/<exp-name>/scaling.json.
    json_path = REPO_ROOT / "results" / job["exp"] / "scaling.json"
    if json_path.exists():
        data = json.loads(json_path.read_text())
        row["best_n"] = data["best"]["n"]
        row["val_mae"] = data["best"]["mae"]
        row["ci_width"] = data["best"]["ci_width"]
        row["hparams"] = data["hparams"]
    return row


def run_job(job: dict, gpu: str) -> dict:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    cmd = ["uv", "run", "python", "prepare.py", *cli_args(job["options"])]
    log_path = LOG_DIR / f"{job['exp']}.log"
    with log_path.open("w") as fout:
        rc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, stdout=fout, stderr=subprocess.STDOUT).returncode

    return collect_job_result(job, gpu=gpu, rc=rc)


def write_summary(results: list[dict]) -> Path:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    results.sort(key=lambda r: (r["group"], r.get("val_mae", float("inf"))))
    summary_path = RESULT_ROOT / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2, default=str))
    return summary_path


def print_best_by_group(results: list[dict], summary_path: Path) -> None:
    print("\nBest by group:")
    for group in sorted({r["group"] for r in results}):
        rows = [r for r in results if r["group"] == group and "val_mae" in r]
        if not rows:
            continue
        best = min(rows, key=lambda r: r["val_mae"])
        print(f"  {group}: {best['label']} val_mae={best['val_mae']:.4f}")
    print(f"\nSummary: {summary_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpus", default="5,6", help="Comma-separated CUDA device IDs")
    parser.add_argument("--collect-only", action="store_true",
                        help="Only collect existing results/<exp>/scaling.json files")
    args = parser.parse_args()

    gpus = [x.strip() for x in args.gpus.split(",") if x.strip()]
    jobs = build_jobs()
    if args.collect_only:
        results = [collect_job_result(job) for job in jobs]
        summary_path = write_summary(results)
        print_best_by_group(results, summary_path)
        missing = [r["exp"] for r in results if "val_mae" not in r]
        if missing:
            print(f"\nMissing result files: {', '.join(missing)}")
            return 1
        return 0

    print(f"Running {len(jobs)} validation-HPO jobs on GPUs {','.join(gpus)}")

    results = []
    with cf.ThreadPoolExecutor(max_workers=len(gpus)) as ex:
        futures = {
            ex.submit(run_job, job, gpus[i % len(gpus)]): job
            for i, job in enumerate(jobs)
        }
        for fut in cf.as_completed(futures):
            row = fut.result()
            results.append(row)
            val = row.get("val_mae")
            msg = f"{row['group']:>4s} {row['label']:<16s} rc={row['rc']}"
            if val is not None:
                msg += f" val_mae={val:.4f}"
            print(msg, flush=True)

    summary_path = write_summary(results)
    print_best_by_group(results, summary_path)
    return 0 if all(r["rc"] == 0 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
