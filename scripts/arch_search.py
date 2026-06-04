#!/usr/bin/env python
"""Architecture pilot sweep for Tm-only vs MD-assisted training."""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = REPO_ROOT / "results" / "arch_search"
LOG_DIR = REPO_ROOT / "logs" / "arch_search"

DEFAULT_ARCHS = ["shared", "residual", "dual", "latent", "moe"]
DEFAULT_HPO_N_MD_VALUES = [0, 640]
DEFAULT_FEATURE_SOURCES = [
    "MD_Q_HPHIL_400K",
    "MD_Q_HPHIL_400K_SHUF",
    "MD_RMSF",
    "MD_RMSF_MAX",
    "MD_RG_STD",
    "MD_SALTBRIDGE",
    "MD_Q_MIN_400K",
    "MD_Q_STD_400K",
    "MD_Q_SLOPE_400K",
    "MD_RMSF_MAX_400K",
    "MD_RG_STD_400K",
    "MD_Q_CDR3",
    "MD_Q_FRAMEWORK",
    "MD_RMSF_CDR3",
    "MD_RMSF_FRAMEWORK",
    "MD_SS_DIST_MEAN",
    "MD_SS_DIST_STD",
    "MD_CDR3_LEN",
]

FINAL_CONFIGS = [
    (
        "tm_latent_drop0.30",
        "latent",
        {"dropout-rate": "0.30", "md-source": "none", "n-tm-list": "57"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "tm_residual_enc3e-4",
        "residual",
        {"encoder-lr": "3e-4", "md-source": "none", "n-tm-list": "57"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "residual_q_hphil_400k",
        "residual",
        {"encoder-lr": "3e-5", "md-source": "MD_Q_HPHIL_400K", "n-md-list": "640"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "residual_q_hphil_400k_shuf",
        "residual",
        {"encoder-lr": "3e-5", "md-source": "MD_Q_HPHIL_400K_SHUF", "n-md-list": "640"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "residual_cdr3_len",
        "residual",
        {"encoder-lr": "3e-5", "md-source": "MD_CDR3_LEN", "n-md-list": "640"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "residual_rmsf_cdr3",
        "residual",
        {"encoder-lr": "3e-5", "md-source": "MD_RMSF_CDR3", "n-md-list": "640"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "residual_ss_dist_std",
        "residual",
        {"encoder-lr": "3e-5", "md-source": "MD_SS_DIST_STD", "n-md-list": "640"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
    (
        "residual_rmsf_max",
        "residual",
        {"encoder-lr": "3e-5", "md-source": "MD_RMSF_MAX", "n-md-list": "640"},
        {"DETACH_AUX_ENCODER": "true"},
    ),
]

COMMON = {
    "n-runs": "3",
    "train-mode": "mtl",
    "selection-scope": "tm",
    "final-eval-split": "val",
    "encoder-mode": "hot",
    "ddg-source": "none",
}

TM_ONLY_HP = {
    "encoder-lr": "3e-4",
    "dropout-rate": "0.15",
}

MD640_HP = {
    "encoder-lr": "1e-4",
    "dropout-rate": "0.05",
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


def parse_csv(raw: str) -> list[str]:
    values = [x.strip() for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("CSV argument must contain at least one value")
    return values


def cli_args(options: dict[str, str]) -> list[str]:
    args: list[str] = []
    for key, value in options.items():
        args.extend([f"--{key}", value])
    return args


def parse_int_csv(raw: str) -> list[int]:
    values = [int(x) for x in parse_csv(raw)]
    if not values:
        raise ValueError("integer CSV argument must contain at least one value")
    return values


def build_pilot_jobs(archs: list[str], n_runs: int) -> list[dict]:
    jobs: list[dict] = []
    for arch in archs:
        base = {
            **COMMON,
            "n-runs": str(n_runs),
            "model-arch": arch,
        }

        exp0 = f"{arch}_nmd0"
        jobs.append({
            "arch": arch,
            "condition": "nmd0",
            "n_md": 0,
            "exp": exp0,
            "options": {
                **base,
                **TM_ONLY_HP,
                "md-source": "none",
                "n-tm-list": "57",
                "exp-name": exp0,
                "result-dir": str(RESULT_ROOT / exp0),
            },
        })

        exp640 = f"{arch}_nmd640"
        jobs.append({
            "arch": arch,
            "condition": "nmd640",
            "n_md": 640,
            "exp": exp640,
            "options": {
                **base,
                **MD640_HP,
                "md-source": "MD_Q_HPHIL_400K",
                "n-md-list": "640",
                "exp-name": exp640,
                "result-dir": str(RESULT_ROOT / exp640),
            },
        })

    return jobs


def build_hpo_jobs(archs: list[str], n_md_values: list[int], n_runs: int) -> list[dict]:
    jobs: list[dict] = []
    for arch in archs:
        for n_md in n_md_values:
            base = {
                **COMMON,
                "n-runs": str(n_runs),
                "model-arch": arch,
            }
            if n_md == 0:
                configs = [(label, hp, "noaux", {"DETACH_AUX_ENCODER": "true"}) for label, hp in BASE_CONFIGS]
            else:
                configs = []
                for label, hp in BASE_CONFIGS + AUX_EXTRA_CONFIGS:
                    configs.append((label, hp, "detach", {"DETACH_AUX_ENCODER": "true"}))
                    configs.append((label, hp, "auxenc", {"DETACH_AUX_ENCODER": "false"}))

            for label, hp, aux_mode, env in configs:
                exp = f"archhpo_{arch}_nmd{n_md}_{label}_{aux_mode}"
                options = {
                    **base,
                    **hp,
                    "exp-name": exp,
                    "result-dir": str(RESULT_ROOT / exp),
                    "md-source": "none" if n_md == 0 else "MD_Q_HPHIL_400K",
                }
                if n_md == 0:
                    options["n-tm-list"] = "57"
                else:
                    options["n-md-list"] = str(n_md)
                jobs.append({
                    "arch": arch,
                    "condition": f"nmd{n_md}",
                    "n_md": n_md,
                    "label": label,
                    "aux_mode": aux_mode,
                    "exp": exp,
                    "env": env,
                    "options": options,
                })
    return jobs


def build_feature_jobs(archs: list[str], sources: list[str], n_runs: int) -> list[dict]:
    jobs: list[dict] = []
    for arch in archs:
        for source in sources:
            exp = f"feature_{arch}_{source.lower()}"
            options = {
                **COMMON,
                "n-runs": str(n_runs),
                "model-arch": arch,
                "encoder-lr": "3e-5",
                "md-source": source,
                "n-md-list": "640",
                "exp-name": exp,
                "result-dir": str(RESULT_ROOT / exp),
            }
            jobs.append({
                "arch": arch,
                "condition": source,
                "n_md": 640,
                "label": source,
                "aux_mode": "detach",
                "exp": exp,
                "env": {"DETACH_AUX_ENCODER": "true"},
                "options": options,
            })
    return jobs


def build_final_jobs(n_runs: int) -> list[dict]:
    jobs: list[dict] = []
    for label, arch, hp, env in FINAL_CONFIGS:
        exp = f"final_{label}"
        options = {
            **COMMON,
            "n-runs": str(n_runs),
            "final-eval-split": "test",
            "model-arch": arch,
            "exp-name": exp,
            "result-dir": str(RESULT_ROOT / exp),
            **hp,
        }
        jobs.append({
            "arch": arch,
            "condition": label,
            "n_md": 0 if hp["md-source"] == "none" else int(hp.get("n-md-list", "0")),
            "label": label,
            "aux_mode": "noaux" if hp["md-source"] == "none" else "detach",
            "exp": exp,
            "env": env,
            "options": options,
        })
    return jobs


def collect_job_result(job: dict, gpu: str | None = None, rc: int | None = None) -> dict:
    row = {**job}
    row["log"] = str(LOG_DIR / f"{job['exp']}.log")
    if gpu is not None:
        row["gpu"] = gpu
    if rc is not None:
        row["rc"] = rc

    json_path = REPO_ROOT / "results" / job["exp"] / "scaling.json"
    if json_path.exists():
        data = json.loads(json_path.read_text())
        metric_key = "test_mae" if data["args"].get("final_eval_split") == "test" else "val_mae"
        row[metric_key] = data["best"]["mae"]
        row["ci_width"] = data["best"]["ci_width"]
        row["best_n"] = data["best"]["n"]
        row["hparams"] = data["hparams"]
    return row


def run_job(job: dict, gpu: str, skip_existing: bool) -> dict:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPO_ROOT / "results" / job["exp"] / "scaling.json"
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


def write_summary(results: list[dict], name: str) -> Path:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = sorted(results, key=lambda r: (r["arch"], int(r["n_md"])))
    baseline = {
        r["arch"]: r["val_mae"]
        for r in rows
        if r.get("n_md") == 0 and "val_mae" in r
    }
    for row in rows:
        base = baseline.get(row["arch"])
        if base is not None and "val_mae" in row:
            row["delta_vs_arch_nmd0"] = row["val_mae"] - base

    summary_path = RESULT_ROOT / name
    summary_path.write_text(json.dumps(rows, indent=2, default=str))
    return summary_path


def print_summary(results: list[dict], summary_path: Path) -> None:
    rows = sorted(results, key=lambda r: (r["arch"], int(r["n_md"])))
    print("\nArchitecture pilot:")
    print("  arch       n_md   val_mae  delta_vs_nmd0  ci_width")
    by_arch = {}
    for row in rows:
        by_arch.setdefault(row["arch"], {})[int(row["n_md"])] = row
    for arch in sorted(by_arch):
        base = by_arch[arch].get(0, {}).get("val_mae")
        for n_md in sorted(by_arch[arch]):
            row = by_arch[arch][n_md]
            val = row.get("val_mae")
            if val is None:
                print(f"  {arch:<10s} {n_md:>4d}   missing")
                continue
            delta = val - base if base is not None else float("nan")
            print(f"  {arch:<10s} {n_md:>4d}   {val:7.4f}  {delta:13.4f}  {row.get('ci_width', float('nan')):8.4f}")
    print(f"\nSummary: {summary_path}")


def print_best(results: list[dict], summary_path: Path, metric: str = "val_mae") -> None:
    rows = [r for r in results if metric in r]
    print("\nBest by architecture and n_md:")
    for arch in sorted({r["arch"] for r in rows}):
        for n_md in sorted({int(r["n_md"]) for r in rows if r["arch"] == arch}):
            candidates = [r for r in rows if r["arch"] == arch and int(r["n_md"]) == n_md]
            best = min(candidates, key=lambda r: r[metric])
            label = best.get("label", best.get("condition", ""))
            aux_mode = best.get("aux_mode", "")
            print(
                f"  {arch:<10s} n_md={n_md:<3d} "
                f"{label:<28s} {aux_mode:<6s} {metric}={best[metric]:.4f} "
                f"ci={best.get('ci_width', float('nan')):.4f}"
            )
    print(f"\nSummary: {summary_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["pilot", "hpo", "feature", "final"], default="pilot")
    parser.add_argument("--archs", default=",".join(DEFAULT_ARCHS),
                        help="Comma-separated architectures to run")
    parser.add_argument("--gpus", default="0,1,2,3,4,5,6",
                        help="Comma-separated CUDA device IDs")
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--n-md-values", default=",".join(map(str, DEFAULT_HPO_N_MD_VALUES)))
    parser.add_argument("--feature-sources", default=",".join(DEFAULT_FEATURE_SOURCES),
                        help="Comma-separated MD source names for --mode feature")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args()

    archs = parse_csv(args.archs)
    gpus = parse_csv(args.gpus)
    if args.mode == "pilot":
        jobs = build_pilot_jobs(archs, args.n_runs)
        summary_name = "pilot_summary.json"
    elif args.mode == "hpo":
        jobs = build_hpo_jobs(archs, parse_int_csv(args.n_md_values), args.n_runs)
        summary_name = "hpo_summary.json"
    elif args.mode == "feature":
        jobs = build_feature_jobs(archs, parse_csv(args.feature_sources), args.n_runs)
        summary_name = "feature_summary.json"
    else:
        jobs = build_final_jobs(args.n_runs)
        summary_name = "final_summary.json"
    metric = "test_mae" if args.mode == "final" else "val_mae"

    if args.collect_only:
        results = [collect_job_result(job) for job in jobs]
        summary_path = write_summary(results, summary_name)
        if args.mode == "pilot":
            print_summary(results, summary_path)
        else:
            print_best(results, summary_path, metric=metric)
        return 0 if all(metric in row for row in results) else 1

    print(f"Running {len(jobs)} architecture {args.mode} jobs on GPUs {','.join(gpus)}")
    results = []
    with cf.ThreadPoolExecutor(max_workers=len(gpus)) as ex:
        futures = {
            ex.submit(run_job, job, gpus[i % len(gpus)], not args.force): job
            for i, job in enumerate(jobs)
        }
        for fut in cf.as_completed(futures):
            row = fut.result()
            results.append(row)
            msg = f"{row['arch']:<10s} n_md={row['n_md']:<3d} rc={row['rc']}"
            if row.get("skipped"):
                msg += " skipped"
            if metric in row:
                msg += f" {metric}={row[metric]:.4f}"
            print(msg, flush=True)

    summary_path = write_summary(results, summary_name)
    if args.mode == "pilot":
        print_summary(results, summary_path)
    else:
        print_best(results, summary_path, metric=metric)
    return 0 if all(row.get("rc") == 0 for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
