#!/usr/bin/env python
"""Run the manifest-defined manuscript reproduction workflow."""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "reproduce" / "manuscript_results.yaml"


@dataclass(frozen=True)
class Action:
    name: str
    kind: str
    cmd: list[str]
    outputs: list[str]
    env: dict[str, str]
    workdir: Path
    skip_in_collect_only: bool = False


def rel(path: str | Path) -> Path:
    return REPO_ROOT / Path(path)


def load_manifest(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def split_csv(raw: str) -> list[str]:
    values = [x.strip() for x in raw.split(",") if x.strip()]
    if not values:
        raise ValueError("CSV argument must contain at least one value")
    return values


def context(gpus: str) -> dict[str, str]:
    return {
        "gpus": gpus,
        "first_gpu": split_csv(gpus)[0],
        "repo": str(REPO_ROOT),
    }


def fmt(value: Any, ctx: dict[str, str]) -> str:
    return str(value).format(**ctx)


def fmt_list(values: list[Any], ctx: dict[str, str]) -> list[str]:
    return [fmt(v, ctx) for v in values]


def fmt_env(values: dict[str, Any] | None, ctx: dict[str, str]) -> dict[str, str]:
    if not values:
        return {}
    return {str(k): fmt(v, ctx) for k, v in values.items()}


def build_action(item: dict[str, Any], ctx: dict[str, str], collect_only: bool, force: bool) -> Action:
    kind = item["type"]
    name = item["name"]
    outputs = [fmt(v, ctx) for v in item.get("outputs", [])]
    env = fmt_env(item.get("env"), ctx)
    workdir = rel(fmt(item.get("workdir", "."), ctx))

    if kind == "prepare":
        cmd = ["uv", "run", "python", "prepare.py", *fmt_list(item.get("args", []), ctx)]
        env.setdefault("CUDA_VISIBLE_DEVICES", ctx["first_gpu"])
        return Action(name, kind, cmd, outputs, env, workdir, skip_in_collect_only=True)

    if kind == "script":
        cmd = ["uv", "run", "python", fmt(item["script"], ctx), *fmt_list(item.get("args", []), ctx)]
        if collect_only and item.get("supports_collect_only", True):
            cmd.append("--collect-only")
        if force and item.get("supports_force", True):
            cmd.append("--force")
        return Action(name, kind, cmd, outputs, env, workdir)

    if kind == "command":
        cmd = fmt_list(item["command"], ctx)
        return Action(
            name,
            kind,
            cmd,
            outputs,
            env,
            workdir,
            skip_in_collect_only=bool(item.get("skip_in_collect_only", True)),
        )

    if kind == "derive_abcd_with_q":
        return Action(name, kind, [], outputs, env, workdir)

    raise ValueError(f"Unknown action type: {kind}")


def build_actions(item: dict[str, Any], ctx: dict[str, str], collect_only: bool, force: bool) -> list[Action]:
    if item["type"] != "prepare_matrix":
        return [build_action(item, ctx, collect_only, force)]

    matrix = item.get("matrix", {})
    if not matrix:
        raise ValueError(f"prepare_matrix action has no matrix: {item.get('name')}")
    keys = list(matrix)
    actions: list[Action] = []
    for values in itertools.product(*(matrix[key] for key in keys)):
        matrix_ctx = {**ctx, **{key: str(value) for key, value in zip(keys, values)}}
        expanded = {k: v for k, v in item.items() if k != "matrix"}
        expanded["type"] = "prepare"
        expanded["name"] = fmt(item["name"], matrix_ctx)
        actions.append(build_action(expanded, matrix_ctx, collect_only, force))
    return actions


def expand_stages(raw: str, manifest: dict[str, Any]) -> list[str]:
    requested = split_csv(raw)
    order = manifest["stage_order"]
    known = set(order) | set(manifest.get("stages", {}))
    if "all" in requested:
        requested = list(order)
    bad = [stage for stage in requested if stage not in known]
    if bad:
        raise ValueError(f"Unknown stage(s): {', '.join(bad)}")
    return requested


def check_paths(paths: list[str], label: str, *, allow_glob: bool = False) -> list[str]:
    missing: list[str] = []
    for path in paths:
        if allow_glob and any(ch in path for ch in "*?[]"):
            if not glob.glob(str(rel(path))):
                missing.append(path)
            continue
        if not rel(path).exists():
            missing.append(path)
    if missing:
        print(f"\nMissing {label}:")
        for path in missing:
            print(f"  {path}")
    else:
        print(f"{label}: OK ({len(paths)} entries)")
    return missing


def printable_command(action: Action) -> str:
    parts: list[str] = []
    parts.extend(f"{k}={v}" for k, v in action.env.items())
    parts.extend(action.cmd)
    return " ".join(parts)


def run_action(action: Action, *, dry_run: bool, collect_only: bool, force: bool) -> int:
    if collect_only and action.skip_in_collect_only:
        return 1 if check_paths(action.outputs, f"{action.name} outputs") else 0

    if action.kind == "derive_abcd_with_q":
        return write_abcd_with_q_summary(dry_run=dry_run)

    if action.outputs and not force and not collect_only:
        if all(rel(output).exists() for output in action.outputs):
            print(f"[skip existing] {action.name}")
            return 0

    print(f"\n[run] {action.name}")
    cwd = action.workdir.relative_to(REPO_ROOT) if action.workdir != REPO_ROOT else Path(".")
    print(f"  cwd: {cwd}")
    print(f"  cmd: {printable_command(action)}")
    if dry_run:
        return 0

    env = os.environ.copy()
    env.update(action.env)
    completed = subprocess.run(action.cmd, cwd=action.workdir, env=env)
    if completed.returncode != 0:
        return completed.returncode
    return 1 if check_paths(action.outputs, f"{action.name} outputs") else 0


def read_json(path: str | Path) -> Any:
    return json.loads(rel(path).read_text())


def scaling_row(exp: str) -> tuple[dict[str, Any], np.ndarray]:
    data = read_json(Path("results") / exp / "scaling.json")
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in results/{exp}/scaling.json")
    scaling = data.get("scaling") or []
    if not scaling:
        raise ValueError(f"No scaling records in results/{exp}/scaling.json")
    point = scaling[0]
    errors = np.asarray(point.get("abs_errors"), dtype=float)
    if errors.size == 0:
        raise ValueError(f"No abs_errors in results/{exp}/scaling.json")
    return data, errors


def paired_delta(ref: np.ndarray, other: np.ndarray, seed: int = 42) -> dict[str, float]:
    if ref.shape != other.shape:
        raise ValueError(f"Cannot pair arrays with shapes {ref.shape} and {other.shape}")
    rng = np.random.default_rng(seed)
    n_boot = 10000
    n = len(ref)
    idx = rng.integers(0, n, size=(n_boot, n))
    delta = np.mean(other[idx], axis=1) - np.mean(ref[idx], axis=1)
    lo, hi = np.percentile(delta, [2.5, 97.5])
    return {
        "delta_mae": float(np.mean(delta)),
        "delta_ci_lo": float(lo),
        "delta_ci_hi": float(hi),
        "p_delta_gt_0": float(np.mean(delta > 0)),
    }


def selected_val(exp: str) -> float | None:
    rows = read_json("results/abcd_search/hpo_summary.json")
    if not isinstance(rows, list):
        raise ValueError("Expected results/abcd_search/hpo_summary.json to contain a list")
    for row in rows:
        if row.get("exp") == exp:
            return float(row["val_mae"])
    return None


def write_abcd_with_q_summary(*, dry_run: bool) -> int:
    out_path = rel("results/abcd_search/final_abcd_with_dq_summary.json")
    print("\n[derive] A-D summary with extra MD Q-value condition")
    print(f"  output: {out_path.relative_to(REPO_ROOT)}")
    if dry_run:
        return 0

    specs = [
        {
            "key": "A",
            "condition": "A_Tm",
            "exp": "abcdfinal_A_tm_latent_drop0.30",
            "arch": "latent",
            "md_source": "none",
        },
        {
            "key": "B",
            "condition": "B_ddG",
            "exp": "abcdfinal_B_ddg320_shared_lr1e-4_enc3e-5",
            "arch": "shared",
            "ddg_source": "FEP",
            "n_ddg": 320,
        },
        {
            "key": "C",
            "condition": "C_MD",
            "exp": "abcdfinal_C_md_q-hphil-400k_residual_enc3e-5",
            "arch": "residual",
            "md_source": "MD_Q_HPHIL_400K",
            "n_md": 640,
        },
        {
            "key": "D_RMSF",
            "condition": "D_ddG_MD_validation_selected",
            "exp": "abcdfinal_D_ddg320_md640_rmsf-max_latent_lr1e-4_enc3e-5",
            "hpo_exp": "abcdhpo_D_ddg320_md640_rmsf-max_latent_lr1e-4_enc3e-5",
            "arch": "latent",
            "ddg_source": "FEP",
            "n_ddg": 320,
            "md_source": "MD_RMSF_MAX",
            "n_md": 640,
        },
        {
            "key": "D_Q",
            "condition": "D_ddG_MD_extra_q_hphil",
            "exp": "abcdfinal_D_ddg320_md640_q-hphil-400k_latent_lr1e-4_enc3e-5",
            "hpo_exp": "abcdhpo_D_ddg320_md640_q-hphil-400k_latent_lr1e-4_enc3e-5",
            "arch": "latent",
            "ddg_source": "FEP",
            "n_ddg": 320,
            "md_source": "MD_Q_HPHIL_400K",
            "n_md": 640,
        },
    ]

    rows: list[dict[str, Any]] = []
    errors: dict[str, np.ndarray] = {}
    for spec in specs:
        data, abs_errors = scaling_row(spec["exp"])
        scaling = data["scaling"][0]
        row = {k: v for k, v in spec.items() if k not in {"key", "hpo_exp"}}
        if "hpo_exp" in spec:
            row["selected_val_mae"] = selected_val(spec["hpo_exp"])
        row["test_mae"] = float(scaling["mae"])
        row["ci_width"] = float(scaling["ci_width"])
        rows.append(row)
        errors[spec["key"]] = abs_errors

    payload = {
        "note": (
            "A-D final test summary with the validation-selected D/RMSF condition "
            "and an additional D/Q-value check. D/Q-value was the second-best D "
            "condition in validation candidate search."
        ),
        "rows": rows,
        "paired_comparisons": {
            "B_minus_A": paired_delta(errors["A"], errors["B"]),
            "C_minus_A": paired_delta(errors["A"], errors["C"]),
            "D_RMSF_minus_A": paired_delta(errors["A"], errors["D_RMSF"]),
            "D_RMSF_minus_B": paired_delta(errors["B"], errors["D_RMSF"]),
            "D_Q_minus_A": paired_delta(errors["A"], errors["D_Q"]),
            "D_Q_minus_B": paired_delta(errors["B"], errors["D_Q"]),
            "D_Q_minus_C": paired_delta(errors["C"], errors["D_Q"]),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--stage", default="all")
    parser.add_argument("--gpus", default="0,1,2,3,4,5,6")
    parser.add_argument("--force", action="store_true", help="Rerun training even if outputs already exist")
    parser.add_argument("--collect-only", action="store_true", help="Regenerate summaries from existing scaling.json files only")
    parser.add_argument("--check-only", action="store_true", help="Only check fixed inputs and expected outputs; write nothing")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    args = parser.parse_args()

    manifest_path = rel(args.manifest) if not Path(args.manifest).is_absolute() else Path(args.manifest)
    manifest = load_manifest(manifest_path)
    ctx = context(args.gpus)
    stages = expand_stages(args.stage, manifest)

    missing_inputs = check_paths(manifest["fixed_inputs"], "fixed source-label inputs")
    if missing_inputs:
        return 1
    if args.check_only:
        missing_outputs = check_paths(manifest.get("expected_outputs", []), "manuscript-facing outputs", allow_glob=True)
        return 1 if missing_outputs else 0

    for stage in stages:
        print(f"\n===== stage: {stage} =====")
        for item in manifest.get("stages", {}).get(stage, []):
            for action in build_actions(item, ctx, args.collect_only, args.force):
                rc = run_action(action, dry_run=args.dry_run, collect_only=args.collect_only, force=args.force)
                if rc != 0:
                    return rc

    if not args.dry_run:
        expected = list(manifest.get("expected_outputs", []))
        missing_outputs = check_paths(expected, "manuscript-facing outputs", allow_glob=True)
        if missing_outputs:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
