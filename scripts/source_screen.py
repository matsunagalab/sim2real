#!/usr/bin/env python
"""Fair screen of simulation-derived auxiliary sources for Tm prediction."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "source_screen"
LOG_DIR = REPO_ROOT / "logs" / "source_screen"

DDG_SOURCES = ["FEP", "rosetta", "thermoMPNN", "rosetta_random", "rosetta_esm"]
MD_SOURCES = ["MD_Q_HPHIL_400K"]
TM_ARCHS = ["shared", "residual", "latent"]

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

DDG_CONFIGS = BASE_CONFIGS + [
    ("fixed", {"mtl-weight-mode": "fixed"}),
]

MD_CONFIGS = BASE_CONFIGS + [
    ("fixed_w0.05", {"mtl-weight-mode": "fixed", "md-weight": "0.05"}),
    ("fixed_w0.10", {"mtl-weight-mode": "fixed", "md-weight": "0.10"}),
    ("fixed_w0.25", {"mtl-weight-mode": "fixed", "md-weight": "0.25"}),
    ("fixed_w0.50", {"mtl-weight-mode": "fixed", "md-weight": "0.50"}),
]

SOURCE_ORDER = ["Tm_only", *DDG_SOURCES, *MD_SOURCES]


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


def source_order(source: str) -> int:
    return SOURCE_ORDER.index(source) if source in SOURCE_ORDER else len(SOURCE_ORDER)


def build_hpo_jobs(
    ddg_sources: list[str],
    md_sources: list[str],
    tm_archs: list[str],
    ddg_n: int,
    md_n: int,
    n_runs: int,
    common: dict[str, str],
    exp_prefix: str = "",
) -> list[dict]:
    jobs: list[dict] = []

    for arch in tm_archs:
        for label, hp in BASE_CONFIGS:
            exp = f"{exp_prefix}sourcehpo_tm_{arch}_{label}"
            options = {
                **common,
                **hp,
                "n-runs": n_runs,
                "exp-name": exp,
                "result-dir": str(RESULT_ROOT / "hpo" / exp),
                "model-arch": arch,
                "ddg-source": "none",
                "md-source": "none",
                "n-ddg-list": "0",
            }
            jobs.append({
                "condition": "Tm_only",
                "source": "Tm_only",
                "arch": arch,
                "label": label,
                "n_ddg": 0,
                "n_md": 0,
                "exp": exp,
                "env": {"DETACH_AUX_ENCODER": "true"},
                "options": options,
            })

    for source in ddg_sources:
        for label, hp in DDG_CONFIGS:
            exp = f"{exp_prefix}sourcehpo_ddg_{source_slug(source)}_{label}"
            options = {
                **common,
                **hp,
                "n-runs": n_runs,
                "exp-name": exp,
                "result-dir": str(RESULT_ROOT / "hpo" / exp),
                "model-arch": "shared",
                "ddg-source": source,
                "n-ddg-list": ddg_n,
                "md-source": "none",
                "ddg-head-mode": "separate",
            }
            jobs.append({
                "condition": "ddG",
                "source": source,
                "arch": "shared",
                "label": label,
                "n_ddg": ddg_n,
                "n_md": 0,
                "exp": exp,
                "env": {"DETACH_AUX_ENCODER": "true"},
                "options": options,
            })

    for source in md_sources:
        for label, hp in MD_CONFIGS:
            exp = f"{exp_prefix}sourcehpo_md_{source_slug(source)}_{label}"
            options = {
                **common,
                **hp,
                "n-runs": n_runs,
                "exp-name": exp,
                "result-dir": str(RESULT_ROOT / "hpo" / exp),
                "model-arch": "residual",
                "ddg-source": "none",
                "n-ddg-list": "0",
                "md-source": source,
                "n-md-list": md_n,
            }
            jobs.append({
                "condition": "MD",
                "source": source,
                "arch": "residual",
                "label": label,
                "n_ddg": 0,
                "n_md": md_n,
                "exp": exp,
                "env": {"DETACH_AUX_ENCODER": "true"},
                "options": options,
            })

    return jobs


def build_final_jobs(hpo_summary: Path, n_runs: int) -> list[dict]:
    rows = json.loads(hpo_summary.read_text())
    jobs: list[dict] = []
    for source in SOURCE_ORDER:
        candidates = [r for r in rows if r.get("source") == source and r.get("rc") == 0 and "val_mae" in r]
        if not candidates:
            continue
        best = min(candidates, key=lambda r: r["val_mae"])
        exp = "sourcefinal_" + best["exp"].replace("sourcehpo_", "")
        options = {
            **best["options"],
            "n-runs": n_runs,
            "final-eval-split": "test",
            "exp-name": exp,
            "result-dir": str(RESULT_ROOT / "final" / exp),
        }
        jobs.append({
            **best,
            "exp": exp,
            "selected_from": best["exp"],
            "selected_val_mae": best["val_mae"],
            "options": options,
        })
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
    rows = sorted(results, key=lambda r: (source_order(r["source"]), r["arch"], r["label"]))
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


def write_final_summary(results: list[dict], filename: str = "final_source_screen_summary.json") -> Path:
    rows = [r for r in results if "test_mae" in r]
    rows = sorted(rows, key=lambda r: source_order(r["source"]))
    by_source = {r["source"]: r for r in rows}

    comparisons: dict[str, dict] = {}
    ref = by_source.get("Tm_only")
    if ref is not None:
        abs_ref = load_abs_errors(ref)
        if abs_ref is not None:
            for source, row in by_source.items():
                if source == "Tm_only":
                    continue
                abs_source = load_abs_errors(row)
                if abs_source is not None:
                    comparisons[f"{source}_minus_Tm_only"] = paired_delta(abs_ref, abs_source)

    if "FEP" in by_source:
        abs_fep = load_abs_errors(by_source["FEP"])
        if abs_fep is not None:
            for source in ["rosetta", "thermoMPNN", "rosetta_random", "rosetta_esm", "MD_Q_HPHIL_400K"]:
                if source in by_source:
                    abs_source = load_abs_errors(by_source[source])
                    if abs_source is not None:
                        comparisons[f"{source}_minus_FEP"] = paired_delta(abs_fep, abs_source)

    if "rosetta_random" in by_source and "rosetta_esm" in by_source:
        abs_random = load_abs_errors(by_source["rosetta_random"])
        abs_esm = load_abs_errors(by_source["rosetta_esm"])
        if abs_random is not None and abs_esm is not None:
            comparisons["rosetta_esm_minus_rosetta_random"] = paired_delta(abs_random, abs_esm)

    out = {
        "rows": rows,
        "best": min(rows, key=lambda r: r["test_mae"]) if rows else None,
        "paired_comparisons": comparisons,
    }
    path = RESULT_ROOT / filename
    path.write_text(json.dumps(out, indent=2, default=str))
    return path


def print_best(results: list[dict], metric: str) -> None:
    rows = [r for r in results if metric in r]
    for source in sorted({r["source"] for r in rows}, key=source_order):
        candidates = [r for r in rows if r["source"] == source]
        best = min(candidates, key=lambda r: r[metric])
        print(
            f"{source:<18s} {best['arch']:<8s} {best['label']:<16s} "
            f"{metric}={best[metric]:.4f} ci={best.get('ci_width', float('nan')):.4f}"
        )


def run_jobs(jobs: list[dict], gpus: list[str], metric: str, force: bool) -> list[dict]:
    print(f"Running {len(jobs)} source-screen jobs on GPUs {','.join(gpus)}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=len(gpus)) as ex:
        futures = {
            ex.submit(run_job, job, gpus[i % len(gpus)], not force): job
            for i, job in enumerate(jobs)
        }
        for fut in cf.as_completed(futures):
            row = fut.result()
            results.append(row)
            msg = f"{row['source']:<18s} {row['arch']:<8s} {row['label']:<16s} rc={row['rc']}"
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
    parser.add_argument("--ddg-sources", default=",".join(DDG_SOURCES))
    parser.add_argument("--md-sources", default=",".join(MD_SOURCES))
    parser.add_argument("--tm-archs", default=",".join(TM_ARCHS))
    parser.add_argument("--ddg-n", type=int, default=320)
    parser.add_argument("--md-n", type=int, default=640)
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--final-runs", type=int, default=10)
    parser.add_argument("--hpo-summary", default=str(RESULT_ROOT / "hpo_summary.json"))
    parser.add_argument("--encoder-mode", choices=["frozen", "lora", "hot"], default=COMMON["encoder-mode"])
    parser.add_argument("--base-model", default=None)
    parser.add_argument("--exp-prefix", default="")
    parser.add_argument("--summary-name", default=None)
    parser.add_argument("--final-summary-name", default="final_source_screen_summary.json")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()

    gpus = parse_csv(args.gpus)
    common = {**COMMON, "encoder-mode": args.encoder_mode}
    if args.base_model:
        common["base-model"] = args.base_model
    if args.mode == "hpo":
        jobs = build_hpo_jobs(
            ddg_sources=parse_csv(args.ddg_sources),
            md_sources=parse_csv(args.md_sources),
            tm_archs=parse_csv(args.tm_archs),
            ddg_n=args.ddg_n,
            md_n=args.md_n,
            n_runs=args.n_runs,
            common=common,
            exp_prefix=args.exp_prefix,
        )
        metric = "val_mae"
        summary_name = args.summary_name or "hpo_summary.json"
    else:
        jobs = build_final_jobs(Path(args.hpo_summary), n_runs=args.final_runs)
        metric = "test_mae"
        summary_name = args.summary_name or "final_jobs_summary.json"

    if args.collect_only:
        results = [collect_job_result(job) for job in jobs]
    else:
        results = run_jobs(jobs, gpus=gpus, metric=metric, force=args.force)

    summary_path = write_summary(results, summary_name)
    print_best(results, metric)
    if args.mode == "final":
        final_path = write_final_summary(results, args.final_summary_name)
        print(f"Final source-screen summary: {final_path}")
    print(f"Summary: {summary_path}")
    return 0 if all(row.get("rc") == 0 for row in results) and all(metric in row for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
