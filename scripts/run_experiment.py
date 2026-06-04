#!/usr/bin/env python
"""Run a named experiment from experiments.yaml.

Usage:
    python scripts/run_experiment.py <name>          # run an experiment
    python scripts/run_experiment.py --list          # list all named experiments
    python scripts/run_experiment.py <name> --dry-run  # print the command without executing
    python scripts/run_experiment.py <name> --check    # after running, compare best_mae vs expected

Outputs:
    logs/<name>.log                      stdout/stderr captured
    results/<name>/scaling.json          structured per-scaling data + metadata
    appended row in results.tsv (extended schema)
"""

import argparse
import json
import os
import subprocess
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP_YAML = os.path.join(REPO_ROOT, "experiments.yaml")
LOGS_DIR = os.path.join(REPO_ROOT, "logs")
RESULTS_DIR = os.path.join(REPO_ROOT, "results")


def load_registry() -> dict:
    with open(EXP_YAML) as f:
        return yaml.safe_load(f)["experiments"]


def list_experiments() -> None:
    reg = load_registry()
    print(f"{'name':<40s}  description")
    print("-" * 100)
    for name, cfg in reg.items():
        desc = cfg.get("description", "")
        if len(desc) > 60:
            desc = desc[:57] + "..."
        print(f"{name:<40s}  {desc}")


def build_command(name: str, cfg: dict) -> tuple[list[str], dict]:
    """Build the prepare.py invocation: returns (cmd, env)."""
    cmd = ["uv", "run", "python", os.path.join(REPO_ROOT, "prepare.py"),
           "--exp-name", name]
    for k, v in cfg.get("args", {}).items():
        cmd.extend([f"--{k}", str(v)])
    env = os.environ.copy()
    for k, v in cfg.get("env", {}).items():
        env[k] = str(v)
    return cmd, env


def run_one(name: str, dry_run: bool = False) -> int:
    reg = load_registry()
    if name not in reg:
        print(f"ERROR: experiment '{name}' not in {EXP_YAML}", file=sys.stderr)
        print("Available:", ", ".join(reg.keys()), file=sys.stderr)
        return 2
    cfg = reg[name]
    cmd, env = build_command(name, cfg)

    env_overlay = cfg.get("env", {})
    print(f"[run_experiment] {name}")
    print(f"  description: {cfg.get('description', '')}")
    if env_overlay:
        print(f"  env overlay: {env_overlay}")
    print(f"  cmd: {' '.join(cmd)}")
    if dry_run:
        return 0

    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = os.path.join(LOGS_DIR, f"{name}.log")
    print(f"  log: {log_path}")
    with open(log_path, "w") as fout:
        rc = subprocess.run(cmd, env=env, stdout=fout,
                            stderr=subprocess.STDOUT, cwd=REPO_ROOT).returncode
    print(f"[run_experiment] {name} exited with rc={rc}")
    return rc


def check_one(name: str, tol: float = 0.05) -> int:
    """Compare results/<name>/scaling.json against expected.best_mae."""
    reg = load_registry()
    cfg = reg.get(name)
    if cfg is None:
        print(f"unknown: {name}", file=sys.stderr)
        return 2
    expected = cfg.get("expected", {})
    if "best_mae" not in expected:
        print(f"[{name}] no expected.best_mae set — skipping")
        return 0
    json_path = os.path.join(RESULTS_DIR, name, "scaling.json")
    if not os.path.exists(json_path):
        print(f"[{name}] missing {json_path} — run first", file=sys.stderr)
        return 1
    with open(json_path) as f:
        data = json.load(f)
    got = data["best"]["mae"]
    want = float(expected["best_mae"])
    diff = abs(got - want)
    status = "OK" if diff <= tol else "MISMATCH"
    print(f"[{name}] {status}  best_mae={got:.4f} (expected {want:.4f}, |Δ|={diff:.4f}, tol={tol})")
    return 0 if diff <= tol else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?",
                        help="experiment name (omit when using --list)")
    parser.add_argument("--list", action="store_true", help="list all named experiments")
    parser.add_argument("--dry-run", action="store_true", help="print command, don't execute")
    parser.add_argument("--check", action="store_true",
                        help="after running, compare best_mae against expected")
    parser.add_argument("--check-only", action="store_true",
                        help="compare existing results/<name>/scaling.json vs expected; do not run")
    parser.add_argument("--tol", type=float, default=0.05, help="check tolerance in °C (default 0.05)")
    args = parser.parse_args()

    if args.list:
        list_experiments()
        return 0
    if not args.name:
        parser.print_usage()
        return 2

    if args.check_only:
        return check_one(args.name, tol=args.tol)

    rc = run_one(args.name, dry_run=args.dry_run)
    if args.check and not args.dry_run:
        rc = max(rc, check_one(args.name, tol=args.tol))
    return rc


if __name__ == "__main__":
    sys.exit(main())
