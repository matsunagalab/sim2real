#!/usr/bin/env python
"""Fair A-D comparison for Tm, ddG, MD, and ddG+MD auxiliary data."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "abcd_search"
LOG_DIR = REPO_ROOT / "logs" / "abcd_search"

DEFAULT_B_ARCHS = ["shared", "residual", "latent"]
DEFAULT_D_ARCHS = ["residual", "latent"]
DEFAULT_MD_SOURCES = ["MD_Q_HPHIL_400K", "MD_RMSF_MAX"]

COMMON = {
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

B_EXTRA_CONFIGS = [
    ("fixed", {"mtl-weight-mode": "fixed"}),
]

D_EXTRA_CONFIGS = [
    ("fixed_w0.05", {"mtl-weight-mode": "fixed", "md-weight": "0.05"}),
    ("fixed_w0.10", {"mtl-weight-mode": "fixed", "md-weight": "0.10"}),
    ("fixed_w0.25", {"mtl-weight-mode": "fixed", "md-weight": "0.25"}),
    ("fixed_w0.50", {"mtl-weight-mode": "fixed", "md-weight": "0.50"}),
]


def parse_csv(raw: str) -> list[str]:
    values = [x.strip() for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("CSV argument must contain at least one value")
    return values


def cli_args(options: dict[str, str | int | float]) -> list[str]:
    args: list[str] = []
    for key, value in options.items():
        args.extend([f"--{key}", str(value)])
    return args


def source_slug(source: str) -> str:
    return source.lower().replace("md_", "").replace("_", "-")


def build_hpo_jobs(
    b_archs: list[str],
    d_archs: list[str],
    md_sources: list[str],
    ddg_n: int,
    md_n: int,
    n_runs: int,
) -> list[dict]:
    jobs: list[dict] = []

    for arch in b_archs:
        for label, hp in BASE_CONFIGS + B_EXTRA_CONFIGS:
            exp = f"abcdhpo_B_ddg{ddg_n}_{arch}_{label}"
            options = {
                **COMMON,
                **hp,
                "n-runs": n_runs,
                "exp-name": exp,
                "result-dir": str(RESULT_ROOT / "hpo" / exp),
                "model-arch": arch,
                "ddg-source": "FEP",
                "n-ddg-list": ddg_n,
                "md-source": "none",
            }
            jobs.append({
                "condition": "B_ddG",
                "arch": arch,
                "label": label,
                "md_source": "none",
                "n_ddg": ddg_n,
                "n_md": 0,
                "exp": exp,
                "env": {"DETACH_AUX_ENCODER": "true"},
                "options": options,
            })

    for arch in d_archs:
        for md_source in md_sources:
            for label, hp in BASE_CONFIGS + D_EXTRA_CONFIGS:
                exp = f"abcdhpo_D_ddg{ddg_n}_md{md_n}_{source_slug(md_source)}_{arch}_{label}"
                options = {
                    **COMMON,
                    **hp,
                    "n-runs": n_runs,
                    "exp-name": exp,
                    "result-dir": str(RESULT_ROOT / "hpo" / exp),
                    "model-arch": arch,
                    "ddg-source": "FEP",
                    "fixed-n-ddg": ddg_n,
                    "md-source": md_source,
                    "n-md-list": md_n,
                }
                jobs.append({
                    "condition": "D_ddG_MD",
                    "arch": arch,
                    "label": label,
                    "md_source": md_source,
                    "n_ddg": ddg_n,
                    "n_md": md_n,
                    "exp": exp,
                    "env": {"DETACH_AUX_ENCODER": "true"},
                    "options": options,
                })

    return jobs


def fixed_final_jobs(ddg_n: int, md_n: int, n_runs: int) -> list[dict]:
    return [
        {
            "condition": "A_Tm",
            "arch": "latent",
            "label": "drop0.30",
            "md_source": "none",
            "n_ddg": 0,
            "n_md": 0,
            "exp": "abcdfinal_A_tm_latent_drop0.30",
            "env": {"DETACH_AUX_ENCODER": "true"},
            "options": {
                **COMMON,
                "n-runs": n_runs,
                "final-eval-split": "test",
                "exp-name": "abcdfinal_A_tm_latent_drop0.30",
                "result-dir": str(RESULT_ROOT / "final" / "abcdfinal_A_tm_latent_drop0.30"),
                "model-arch": "latent",
                "dropout-rate": "0.30",
                "ddg-source": "none",
                "md-source": "none",
                "n-tm-list": "57",
            },
        },
        {
            "condition": "C_MD",
            "arch": "residual",
            "label": "enc3e-5",
            "md_source": "MD_Q_HPHIL_400K",
            "n_ddg": 0,
            "n_md": md_n,
            "exp": "abcdfinal_C_md_q-hphil-400k_residual_enc3e-5",
            "env": {"DETACH_AUX_ENCODER": "true"},
            "options": {
                **COMMON,
                "n-runs": n_runs,
                "final-eval-split": "test",
                "exp-name": "abcdfinal_C_md_q-hphil-400k_residual_enc3e-5",
                "result-dir": str(RESULT_ROOT / "final" / "abcdfinal_C_md_q-hphil-400k_residual_enc3e-5"),
                "model-arch": "residual",
                "encoder-lr": "3e-5",
                "ddg-source": "none",
                "md-source": "MD_Q_HPHIL_400K",
                "n-md-list": md_n,
            },
        },
    ]


def build_final_jobs(hpo_summary: Path, ddg_n: int, md_n: int, n_runs: int) -> list[dict]:
    rows = json.loads(hpo_summary.read_text())
    jobs = fixed_final_jobs(ddg_n=ddg_n, md_n=md_n, n_runs=n_runs)

    for condition in ["B_ddG", "D_ddG_MD"]:
        candidates = [r for r in rows if r.get("condition") == condition and "val_mae" in r]
        if not candidates:
            continue
        best = min(candidates, key=lambda r: r["val_mae"])
        exp = "abcdfinal_" + best["exp"].replace("abcdhpo_", "")
        options = {
            **best["options"],
            "n-runs": n_runs,
            "final-eval-split": "test",
            "exp-name": exp,
            "result-dir": str(RESULT_ROOT / "final" / exp),
        }
        job = {
            **best,
            "exp": exp,
            "selected_from": best["exp"],
            "selected_val_mae": best["val_mae"],
            "options": options,
        }
        jobs.append(job)

    return jobs


def scaling_json_path(exp: str) -> Path:
    return REPO_ROOT / "results" / exp / "scaling.json"


def collect_job_result(job: dict, gpu: str | None = None, rc: int | None = None) -> dict:
    row = {**job}
    row["log"] = str(LOG_DIR / f"{job['exp']}.log")
    if gpu is not None:
        row["gpu"] = gpu
    if rc is not None:
        row["rc"] = rc

    json_path = scaling_json_path(job["exp"])
    if json_path.exists():
        data = json.loads(json_path.read_text())
        metric_key = "test_mae" if data["args"].get("final_eval_split") == "test" else "val_mae"
        row[metric_key] = data["best"]["mae"]
        row["ci_width"] = data["best"]["ci_width"]
        row["best_n"] = data["best"]["n"]
        row["hparams"] = data["hparams"]
        row["scaling_json"] = str(json_path)
    return row


def run_job(job: dict, gpu: str, skip_existing: bool) -> dict:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    json_path = scaling_json_path(job["exp"])
    if skip_existing and json_path.exists():
        row = collect_job_result(job, gpu=gpu, rc=0)
        row["skipped"] = True
        return row

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    env.update(job.get("env", {}))
    cmd = ["uv", "run", "python", "prepare.py", *cli_args(job["options"])]
    log_path = LOG_DIR / f"{job['exp']}.log"
    with log_path.open("w") as fout:
        rc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, stdout=fout, stderr=subprocess.STDOUT).returncode
    return collect_job_result(job, gpu=gpu, rc=rc)


def write_summary(results: list[dict], filename: str) -> Path:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = sorted(results, key=lambda r: (r["condition"], r["arch"], r["md_source"], r["label"]))
    path = RESULT_ROOT / filename
    path.write_text(json.dumps(rows, indent=2, default=str))
    return path


def load_abs_errors(row: dict) -> np.ndarray | None:
    json_path = row.get("scaling_json")
    if not json_path:
        return None
    data = json.loads(Path(json_path).read_text())
    scaling = data.get("scaling") or []
    if not scaling or "abs_errors" not in scaling[0]:
        return None
    return np.asarray(scaling[0]["abs_errors"], dtype=float)


def paired_delta(abs_a: np.ndarray, abs_b: np.ndarray, seed: int = 42) -> dict:
    if abs_a.shape != abs_b.shape:
        raise ValueError(f"Cannot pair arrays with shapes {abs_a.shape} and {abs_b.shape}")
    rng = np.random.default_rng(seed)
    n_boot = 10000
    n = len(abs_a)
    idx = rng.integers(0, n, size=(n_boot, n))
    delta = np.mean(abs_b[idx], axis=1) - np.mean(abs_a[idx], axis=1)
    lo, hi = np.percentile(delta, [5, 95])
    return {
        "delta_mae": float(np.mean(delta)),
        "delta_ci_lo": float(lo),
        "delta_ci_hi": float(hi),
        "p_delta_gt_0": float(np.mean(delta > 0)),
    }


def write_final_summary(results: list[dict]) -> Path:
    rows = [r for r in results if "test_mae" in r]
    rows = sorted(rows, key=lambda r: ["A_Tm", "B_ddG", "C_MD", "D_ddG_MD"].index(r["condition"]))

    by_condition = {r["condition"]: r for r in rows}
    comparisons: dict[str, dict] = {}
    if "A_Tm" in by_condition:
        abs_a = load_abs_errors(by_condition["A_Tm"])
        if abs_a is not None:
            for cond, row in by_condition.items():
                if cond == "A_Tm":
                    continue
                abs_b = load_abs_errors(row)
                if abs_b is not None:
                    comparisons[f"{cond}_minus_A_Tm"] = paired_delta(abs_a, abs_b)

    for left, right in [("D_ddG_MD", "B_ddG"), ("D_ddG_MD", "C_MD")]:
        if left in by_condition and right in by_condition:
            abs_left = load_abs_errors(by_condition[left])
            abs_right = load_abs_errors(by_condition[right])
            if abs_left is not None and abs_right is not None:
                comparisons[f"{left}_minus_{right}"] = paired_delta(abs_right, abs_left)

    out = {
        "rows": rows,
        "paired_comparisons": comparisons,
    }
    path = RESULT_ROOT / "final_abcd_summary.json"
    path.write_text(json.dumps(out, indent=2, default=str))
    return path


def print_best(results: list[dict], metric: str) -> None:
    rows = [r for r in results if metric in r]
    for condition in sorted({r["condition"] for r in rows}):
        candidates = [r for r in rows if r["condition"] == condition]
        best = min(candidates, key=lambda r: r[metric])
        print(
            f"{condition:<8s} {best['arch']:<8s} {best['md_source']:<18s} "
            f"{best['label']:<16s} {metric}={best[metric]:.4f} "
            f"ci={best.get('ci_width', float('nan')):.4f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["hpo", "final"], default="hpo")
    parser.add_argument("--gpus", default="0,1,2,3,4,5,6")
    parser.add_argument("--b-archs", default=",".join(DEFAULT_B_ARCHS))
    parser.add_argument("--d-archs", default=",".join(DEFAULT_D_ARCHS))
    parser.add_argument("--md-sources", default=",".join(DEFAULT_MD_SOURCES))
    parser.add_argument("--ddg-n", type=int, default=320)
    parser.add_argument("--md-n", type=int, default=640)
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--final-runs", type=int, default=10)
    parser.add_argument("--hpo-summary", default=str(RESULT_ROOT / "hpo_summary.json"))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()

    gpus = parse_csv(args.gpus)
    if args.mode == "hpo":
        jobs = build_hpo_jobs(
            b_archs=parse_csv(args.b_archs),
            d_archs=parse_csv(args.d_archs),
            md_sources=parse_csv(args.md_sources),
            ddg_n=args.ddg_n,
            md_n=args.md_n,
            n_runs=args.n_runs,
        )
        metric = "val_mae"
        summary_name = "hpo_summary.json"
    else:
        jobs = build_final_jobs(
            hpo_summary=Path(args.hpo_summary),
            ddg_n=args.ddg_n,
            md_n=args.md_n,
            n_runs=args.final_runs,
        )
        metric = "test_mae"
        summary_name = "final_jobs_summary.json"

    if args.collect_only:
        results = [collect_job_result(job) for job in jobs]
        summary_path = write_summary(results, summary_name)
        print_best(results, metric)
        if args.mode == "final":
            final_path = write_final_summary(results)
            print(f"Final A-D summary: {final_path}")
        print(f"Summary: {summary_path}")
        return 0 if all(metric in row for row in results) else 1

    print(f"Running {len(jobs)} A-D {args.mode} jobs on GPUs {','.join(gpus)}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=len(gpus)) as ex:
        futures = {
            ex.submit(run_job, job, gpus[i % len(gpus)], not args.force): job
            for i, job in enumerate(jobs)
        }
        for fut in cf.as_completed(futures):
            row = fut.result()
            results.append(row)
            msg = f"{row['condition']:<8s} {row['arch']:<8s} {row['label']:<16s} rc={row['rc']}"
            if row.get("skipped"):
                msg += " skipped"
            if metric in row:
                msg += f" {metric}={row[metric]:.4f}"
            print(msg, flush=True)

    summary_path = write_summary(results, summary_name)
    print_best(results, metric)
    if args.mode == "final":
        final_path = write_final_summary(results)
        print(f"Final A-D summary: {final_path}")
    print(f"Summary: {summary_path}")
    return 0 if all(row.get("rc") == 0 for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
