#!/usr/bin/env python
"""Validation-only hyperparameter search for fair Tm/aux comparison."""

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
DEFAULT_N_MD_VALUES = [0, 10, 40, 80, 160, 320, 640]


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


def build_per_nmd_jobs(n_md_values: list[int], n_runs: int = 3) -> list[dict]:
    jobs = []
    configs = BASE_CONFIGS + AUX_EXTRA_CONFIGS

    for n_md in n_md_values:
        for label, hp in configs:
            exp = f"hpo_nmd{n_md}_{label}"
            options = {
                **COMMON,
                **hp,
                "n-runs": str(n_runs),
                "exp-name": exp,
                "result-dir": str(RESULT_ROOT / exp),
                "ddg-source": "none",
            }
            if n_md == 0:
                options.update({
                    "md-source": "none",
                    "n-tm-list": "57",
                })
            else:
                options.update({
                    "md-source": "MD_Q_HPHIL_400K",
                    "n-md-list": str(n_md),
                })
            jobs.append({
                "group": f"nmd{n_md}",
                "label": label,
                "exp": exp,
                "n_md": n_md,
                "options": options,
            })

    return jobs


def build_final_jobs(summary_path: Path, n_runs: int = 10) -> list[dict]:
    rows = json.loads(summary_path.read_text())
    best_by_n: dict[int, dict] = {}
    for row in rows:
        if "val_mae" not in row or "n_md" not in row:
            continue
        n_md = int(row["n_md"])
        if n_md not in best_by_n or row["val_mae"] < best_by_n[n_md]["val_mae"]:
            best_by_n[n_md] = row

    jobs = []
    for n_md in sorted(best_by_n):
        source = best_by_n[n_md]
        label = source["label"]
        exp = f"hpo_selected_nmd{n_md}_{label}"
        options = {
            **source["options"],
            "n-runs": str(n_runs),
            "final-eval-split": "test",
            "exp-name": exp,
            "result-dir": str(RESULT_ROOT / exp),
        }
        jobs.append({
            "group": f"nmd{n_md}",
            "label": label,
            "exp": exp,
            "n_md": n_md,
            "selected_from": source["exp"],
            "selected_val_mae": source["val_mae"],
            "options": options,
        })
    return jobs


def parse_n_md_values(raw: str) -> list[int]:
    values = [int(x) for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("--n-md-values must contain at least one integer")
    return values


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
        metric_key = "test_mae" if data["args"].get("final_eval_split") == "test" else "val_mae"
        row[metric_key] = data["best"]["mae"]
        row["ci_width"] = data["best"]["ci_width"]
        row["hparams"] = data["hparams"]
    return row


def run_job(job: dict, gpu: str, skip_existing: bool = True) -> dict:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    json_path = REPO_ROOT / "results" / job["exp"] / "scaling.json"
    if skip_existing and json_path.exists():
        row = collect_job_result(job, gpu=gpu, rc=0)
        row["skipped"] = True
        return row

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


def write_named_summary(results: list[dict], name: str) -> Path:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    results.sort(key=lambda r: (int(r.get("n_md", 0)), r.get("val_mae", r.get("test_mae", float("inf")))))
    summary_path = RESULT_ROOT / name
    summary_path.write_text(json.dumps(results, indent=2, default=str))
    return summary_path


def print_best_by_group(results: list[dict], summary_path: Path, metric: str = "val_mae") -> None:
    print("\nBest by group:")
    groups = sorted({r["group"] for r in results}, key=lambda g: int(g[3:]) if g.startswith("nmd") else 0)
    for group in groups:
        rows = [r for r in results if r["group"] == group and metric in r]
        if not rows:
            continue
        best = min(rows, key=lambda r: r[metric])
        n_md = f" n_md={best['n_md']}" if "n_md" in best else ""
        print(f"  {group}:{n_md} {best['label']} {metric}={best[metric]:.4f}")
    print(f"\nSummary: {summary_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpus", default="5,6", help="Comma-separated CUDA device IDs")
    parser.add_argument("--mode", choices=["representative", "per-nmd", "final-selected"],
                        default="representative")
    parser.add_argument("--n-md-values", default=",".join(map(str, DEFAULT_N_MD_VALUES)))
    parser.add_argument("--n-runs", type=int, default=None,
                        help="Override runs per HPO/final job; defaults to 3 for HPO, 10 for final-selected")
    parser.add_argument("--force", action="store_true", help="Rerun jobs even when scaling.json already exists")
    parser.add_argument("--collect-only", action="store_true",
                        help="Only collect existing results/<exp>/scaling.json files")
    args = parser.parse_args()

    gpus = [x.strip() for x in args.gpus.split(",") if x.strip()]
    if args.mode == "representative":
        jobs = build_jobs()
        summary_name = "summary.json"
        metric = "val_mae"
    elif args.mode == "per-nmd":
        n_runs = args.n_runs if args.n_runs is not None else 3
        jobs = build_per_nmd_jobs(parse_n_md_values(args.n_md_values), n_runs=n_runs)
        summary_name = "per_nmd_summary.json"
        metric = "val_mae"
    else:
        n_runs = args.n_runs if args.n_runs is not None else 10
        source_summary = RESULT_ROOT / "per_nmd_summary.json"
        jobs = build_final_jobs(source_summary, n_runs=n_runs)
        summary_name = "per_nmd_test_summary.json"
        metric = "test_mae"

    if args.collect_only:
        results = [collect_job_result(job) for job in jobs]
        if args.mode == "representative":
            summary_path = write_summary(results)
        else:
            summary_path = write_named_summary(results, summary_name)
        print_best_by_group(results, summary_path, metric=metric)
        missing = [r["exp"] for r in results if metric not in r]
        if missing:
            print(f"\nMissing result files: {', '.join(missing)}")
            return 1
        return 0

    print(f"Running {len(jobs)} {args.mode} jobs on GPUs {','.join(gpus)}")

    results = []
    with cf.ThreadPoolExecutor(max_workers=len(gpus)) as ex:
        futures = {
            ex.submit(run_job, job, gpus[i % len(gpus)], not args.force): job
            for i, job in enumerate(jobs)
        }
        for fut in cf.as_completed(futures):
            row = fut.result()
            results.append(row)
            val = row.get(metric)
            msg = f"{row['group']:>4s} {row['label']:<16s} rc={row['rc']}"
            if row.get("skipped"):
                msg += " skipped"
            if val is not None:
                msg += f" {metric}={val:.4f}"
            print(msg, flush=True)

    if args.mode == "representative":
        summary_path = write_summary(results)
    else:
        summary_path = write_named_summary(results, summary_name)
    print_best_by_group(results, summary_path, metric=metric)
    return 0 if all(r["rc"] == 0 for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
