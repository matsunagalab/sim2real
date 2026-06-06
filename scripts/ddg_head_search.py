#!/usr/bin/env python
"""Compare ddG auxiliary head designs under a fair Tm-selected protocol."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "ddg_head_search"
LOG_DIR = REPO_ROOT / "logs" / "ddg_head_search"

DDG_HEAD_MODES = ["separate", "shared", "context", "calibrated"]

COMMON = {
    "train-mode": "mtl",
    "selection-scope": "tm",
    "final-eval-split": "val",
    "model-arch": "shared",
    "ddg-source": "FEP",
    "md-source": "none",
}

CONFIGS = [
    ("default", {}),
    ("enc3e-5", {"encoder-lr": "3e-5"}),
    ("enc3e-4", {"encoder-lr": "3e-4"}),
    ("lr1e-4_enc3e-5", {"learning-rate": "1e-4", "encoder-lr": "3e-5"}),
    ("drop0.05", {"dropout-rate": "0.05"}),
    ("drop0.30", {"dropout-rate": "0.30"}),
    ("fixed", {"mtl-weight-mode": "fixed"}),
]


def parse_csv(raw: str) -> list[str]:
    values = [x.strip() for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("CSV argument must contain at least one value")
    return values


def mode_order(mode: str) -> int:
    return DDG_HEAD_MODES.index(mode) if mode in DDG_HEAD_MODES else len(DDG_HEAD_MODES)


def cli_args(options: dict[str, str | int | float]) -> list[str]:
    args: list[str] = []
    for key, value in options.items():
        args.extend([f"--{key}", str(value)])
    return args


def result_root_for(encoder_mode: str) -> Path:
    return RESULT_ROOT if encoder_mode == "hot" else RESULT_ROOT / encoder_mode


def log_dir_for(encoder_mode: str) -> Path:
    return LOG_DIR if encoder_mode == "hot" else LOG_DIR / encoder_mode


def exp_name(stage: str, encoder_mode: str, mode: str, label: str) -> str:
    if encoder_mode == "hot":
        return f"ddghead{stage}_{mode}_{label}"
    return f"ddghead{encoder_mode}{stage}_{mode}_{label}"


def build_hpo_jobs(
    modes: list[str],
    ddg_n: int,
    n_runs: int,
    encoder_mode: str,
    result_root: Path,
    log_dir: Path,
) -> list[dict]:
    jobs: list[dict] = []
    for mode in modes:
        for label, hp in CONFIGS:
            exp = exp_name("hpo", encoder_mode, mode, label)
            options = {
                **COMMON,
                **hp,
                "encoder-mode": encoder_mode,
                "n-runs": n_runs,
                "exp-name": exp,
                "result-dir": str(result_root / "hpo" / exp),
                "n-ddg-list": ddg_n,
                "ddg-head-mode": mode,
            }
            jobs.append({
                "condition": "B_ddG",
                "ddg_head_mode": mode,
                "arch": "shared",
                "label": label,
                "n_ddg": ddg_n,
                "encoder_mode": encoder_mode,
                "exp": exp,
                "env": {"DETACH_AUX_ENCODER": "true"},
                "options": options,
                "result_root": str(result_root),
                "log_dir": str(log_dir),
            })
    return jobs


def build_final_jobs(
    hpo_summary: Path,
    modes: list[str],
    n_runs: int,
    encoder_mode: str,
    result_root: Path,
    log_dir: Path,
) -> list[dict]:
    rows = json.loads(hpo_summary.read_text())
    jobs: list[dict] = []
    for mode in modes:
        candidates = [
            r for r in rows
            if r.get("ddg_head_mode") == mode and r.get("rc", 0) == 0 and "val_mae" in r
        ]
        if not candidates:
            continue
        best = min(candidates, key=lambda r: r["val_mae"])
        exp = exp_name("final", encoder_mode, mode, best["label"])
        options = {
            **best["options"],
            "encoder-mode": encoder_mode,
            "n-runs": n_runs,
            "final-eval-split": "test",
            "exp-name": exp,
            "result-dir": str(result_root / "final" / exp),
        }
        jobs.append({
            **best,
            "encoder_mode": encoder_mode,
            "exp": exp,
            "selected_from": best["exp"],
            "selected_val_mae": best["val_mae"],
            "options": options,
            "result_root": str(result_root),
            "log_dir": str(log_dir),
        })
    return jobs


def scaling_json_path(exp: str) -> Path:
    return REPO_ROOT / "results" / exp / "scaling.json"


def collect_job_result(job: dict, gpu: str | None = None, rc: int | None = None) -> dict:
    row = {**job}
    log_dir = Path(job.get("log_dir", LOG_DIR))
    row["log"] = str(log_dir / f"{job['exp']}.log")
    if gpu is not None:
        row["gpu"] = gpu
    if rc is not None:
        row["rc"] = rc

    json_path = scaling_json_path(job["exp"])
    if json_path.exists():
        if rc is None:
            row["rc"] = 0
        data = json.loads(json_path.read_text())
        metric_key = "test_mae" if data["args"].get("final_eval_split") == "test" else "val_mae"
        row[metric_key] = data["best"]["mae"]
        row["ci_width"] = data["best"]["ci_width"]
        row["best_n"] = data["best"]["n"]
        row["hparams"] = data["hparams"]
        row["scaling_json"] = str(json_path)
    return row


def run_job(job: dict, gpu: str, skip_existing: bool) -> dict:
    result_root = Path(job.get("result_root", RESULT_ROOT))
    log_dir = Path(job.get("log_dir", LOG_DIR))
    result_root.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    json_path = scaling_json_path(job["exp"])
    if skip_existing and json_path.exists():
        row = collect_job_result(job, gpu=gpu, rc=0)
        row["skipped"] = True
        return row

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = gpu
    env.update(job.get("env", {}))
    cmd = ["uv", "run", "python", "prepare.py", *cli_args(job["options"])]
    log_path = log_dir / f"{job['exp']}.log"
    with log_path.open("w") as fout:
        rc = subprocess.run(cmd, cwd=REPO_ROOT, env=env, stdout=fout, stderr=subprocess.STDOUT).returncode
    return collect_job_result(job, gpu=gpu, rc=rc)


def write_summary(results: list[dict], filename: str, result_root: Path) -> Path:
    result_root.mkdir(parents=True, exist_ok=True)
    rows = sorted(results, key=lambda r: (mode_order(r["ddg_head_mode"]), r["label"]))
    path = result_root / filename
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


def write_final_summary(results: list[dict], result_root: Path) -> Path:
    rows = [r for r in results if "test_mae" in r]
    rows = sorted(rows, key=lambda r: mode_order(r["ddg_head_mode"]))
    by_mode = {r["ddg_head_mode"]: r for r in rows}

    comparisons: dict[str, dict] = {}
    ref = by_mode.get("separate")
    if ref is not None:
        abs_ref = load_abs_errors(ref)
        if abs_ref is not None:
            for mode, row in by_mode.items():
                if mode == "separate":
                    continue
                abs_mode = load_abs_errors(row)
                if abs_mode is not None:
                    comparisons[f"{mode}_minus_separate"] = paired_delta(abs_ref, abs_mode)

    out = {
        "rows": rows,
        "best": min(rows, key=lambda r: r["test_mae"]) if rows else None,
        "paired_comparisons": comparisons,
    }
    path = result_root / "final_ddg_head_summary.json"
    path.write_text(json.dumps(out, indent=2, default=str))
    return path


def print_best(results: list[dict], metric: str) -> None:
    rows = [r for r in results if metric in r]
    for mode in sorted({r["ddg_head_mode"] for r in rows}, key=mode_order):
        candidates = [r for r in rows if r["ddg_head_mode"] == mode]
        best = min(candidates, key=lambda r: r[metric])
        print(
            f"{mode:<10s} {best['label']:<16s} {metric}={best[metric]:.4f} "
            f"ci={best.get('ci_width', float('nan')):.4f}"
        )


def run_jobs(jobs: list[dict], gpus: list[str], metric: str, force: bool) -> list[dict]:
    print(f"Running {len(jobs)} ddG-head jobs on GPUs {','.join(gpus)}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=len(gpus)) as ex:
        futures = {
            ex.submit(run_job, job, gpus[i % len(gpus)], not force): job
            for i, job in enumerate(jobs)
        }
        for fut in cf.as_completed(futures):
            row = fut.result()
            results.append(row)
            msg = f"{row['ddg_head_mode']:<10s} {row['label']:<16s} rc={row['rc']}"
            if row.get("skipped"):
                msg += " skipped"
            if metric in row:
                msg += f" {metric}={row[metric]:.4f}"
            print(msg, flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["hpo", "final"], default="hpo")
    parser.add_argument("--gpus", default="0,1,2,3,4,5,6")
    parser.add_argument("--encoder-mode", choices=["frozen", "lora", "hot"], default="hot")
    parser.add_argument("--ddg-head-modes", default=",".join(DDG_HEAD_MODES))
    parser.add_argument("--ddg-n", type=int, default=320)
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--final-runs", type=int, default=10)
    parser.add_argument("--hpo-summary", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()

    gpus = parse_csv(args.gpus)
    modes = parse_csv(args.ddg_head_modes)
    result_root = result_root_for(args.encoder_mode)
    log_dir = log_dir_for(args.encoder_mode)
    hpo_summary = Path(args.hpo_summary) if args.hpo_summary else result_root / "hpo_summary.json"

    if args.mode == "hpo":
        jobs = build_hpo_jobs(
            modes=modes,
            ddg_n=args.ddg_n,
            n_runs=args.n_runs,
            encoder_mode=args.encoder_mode,
            result_root=result_root,
            log_dir=log_dir,
        )
        metric = "val_mae"
        summary_name = "hpo_summary.json"
    else:
        jobs = build_final_jobs(
            hpo_summary,
            modes=modes,
            n_runs=args.final_runs,
            encoder_mode=args.encoder_mode,
            result_root=result_root,
            log_dir=log_dir,
        )
        metric = "test_mae"
        summary_name = "final_jobs_summary.json"

    if args.collect_only:
        results = [collect_job_result(job) for job in jobs]
        summary_path = write_summary(results, summary_name, result_root=result_root)
        print_best(results, metric)
        if args.mode == "final":
            final_path = write_final_summary(results, result_root=result_root)
            print(f"Final ddG-head summary: {final_path}")
        print(f"Summary: {summary_path}")
        return 0 if all(metric in row for row in results) else 1

    results = run_jobs(jobs, gpus=gpus, metric=metric, force=args.force)
    summary_path = write_summary(results, summary_name, result_root=result_root)
    print_best(results, metric)
    if args.mode == "final":
        final_path = write_final_summary(results, result_root=result_root)
        print(f"Final ddG-head summary: {final_path}")
    print(f"Summary: {summary_path}")
    return 0 if all(row.get("rc") == 0 for row in results) and all(metric in row for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
