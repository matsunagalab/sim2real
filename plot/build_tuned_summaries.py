#!/usr/bin/env python3
"""Build tuned per-source representative scaling files + hot/frozen summary JSONs.

Reads the 14 final_* tuned scaling.json runs (hot + frozen x 7 sources), writes:

  results/tuned_rep/<source>_<regime>/scaling.json   single representative point
  results/tuned_rep/hot_summary.json                 source-screen summary (hot)
  results/tuned_rep/frozen_summary.json              source-screen summary (frozen)

Summary schema (consumed by plot/make_outline_figures.py):
  {"rows":[{source, test_mae, ci_width, val_mae, scaling_json, arch, label}],
   "best": <source>,
   "paired_comparisons": {"<source>_minus_Tm_only": {delta_mae, delta_ci_lo,
                          delta_ci_hi, p_value}}}

Representative point = n=320 for every source except Tm_only (single n=20 point).
Paired ΔMAE vs Tm_only is a paired bootstrap over the shared per-sample abs_errors
(10000 resamples, 95% CI). Every number is cross-checked against the manuscript
reference table; a PASS/FAIL line is printed per source.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
OUT_DIR = RESULTS / "tuned_rep"

# runkey -> (summary source key, final_ dir stem, reader-facing label)
SOURCES = [
    ("tm", "Tm_only", "Tm labels only"),
    ("fep", "FEP", "FEP mutation\nfree energy"),
    ("mdq", "MD_FEP400K", "MD native-contact\n(matched scan)"),
    ("tmpnn", "thermoMPNN", "ThermoMPNN\nstability score"),
    ("rosrnd", "rosetta_random", "random variants\n+ Rosetta"),
    ("ros", "rosetta", "Rosetta mutation\nscore"),
    ("rosesm", "rosetta_esm", "ESM2-proposed\nvariants + Rosetta"),
]

REGIMES = ["hot", "frozen"]

# Representative n per source (ddg-label count). Tm_only has only its n=20 point.
REP_N = 320

# Reference table (tuned, test, n=396). regime -> {source_key: (mae, dmae)}.
REFERENCE = {
    "frozen": {
        "Tm_only": (7.229, 0.0),
        "FEP": (7.008, -0.221),
        "MD_FEP400K": (7.034, -0.195),
        "thermoMPNN": (7.089, -0.141),
        "rosetta_random": (7.216, -0.013),
        "rosetta": (7.231, +0.002),
        "rosetta_esm": (7.312, +0.083),
    },
    "hot": {
        "Tm_only": (6.548, 0.0),
        "FEP": (6.395, -0.153),
        "MD_FEP400K": (6.577, +0.029),
        "thermoMPNN": (6.621, +0.073),
        "rosetta": (6.625, +0.078),
        "rosetta_random": (6.692, +0.144),
        "rosetta_esm": (6.959, +0.411),
    },
}
TOL = 0.011


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def rep_point(stem: str, regime: str) -> tuple[dict, dict]:
    """Return (representative scaling point, full run dict) for a final_ run."""
    run = read_json(RESULTS / f"final_{stem}_{regime}" / "scaling.json")
    points = run["scaling"]
    if len(points) == 1:
        pt = points[0]
    else:
        cand = [p for p in points if int(p["n"]) == REP_N]
        if not cand:
            raise ValueError(f"final_{stem}_{regime}: no n={REP_N} point")
        pt = cand[0]
    return pt, run


def paired_delta(a: np.ndarray, b: np.ndarray, n_boot: int = 10000) -> dict:
    """ΔMAE = mean(b) - mean(a), paired bootstrap 95% CI + two-sided p."""
    rng = np.random.default_rng(42)
    n = len(a)
    idx = rng.integers(0, n, size=(n_boot, n))
    d = b[idx].mean(axis=1) - a[idx].mean(axis=1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    frac_pos = float(np.mean(d > 0))
    p = 2.0 * min(frac_pos, 1.0 - frac_pos)
    return {
        "delta_mae": float(b.mean() - a.mean()),
        "delta_ci_lo": float(lo),
        "delta_ci_hi": float(hi),
        "p_value": float(p),
    }


def mae_interval(errors: np.ndarray, n_boot: int = 10000) -> tuple[float, float, float]:
    """MAE and its 95% bootstrap interval over test proteins."""
    rng = np.random.default_rng(42)
    idx = rng.integers(0, len(errors), size=(n_boot, len(errors)))
    values = errors[idx].mean(axis=1)
    lo, hi = np.percentile(values, [2.5, 97.5])
    return float(errors.mean()), float(lo), float(hi)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_pass = True

    for regime in REGIMES:
        # collect representative points + abs_errors
        rep = {}
        for stem_key, src_key, label in SOURCES:
            pt, run = rep_point(stem_key, regime)
            abs_errors = np.asarray(pt["abs_errors"], dtype=float)
            mae, ci_lo, ci_hi = mae_interval(abs_errors)
            rep[src_key] = {
                "point": pt,
                "arch": run.get("args", {}).get("model_arch", "shared"),
                "label": label,
                "abs_errors": abs_errors,
                "mae": mae,
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
            }
            # write single-point representative scaling.json
            out = {
                "args": {"final_eval_split": "test"},
                "scaling": [
                    {
                        "n": int(pt["n"]),
                        "mae": mae,
                        "ci_lo": ci_lo,
                        "ci_hi": ci_hi,
                        "ci_width": ci_hi - ci_lo,
                        "abs_errors": [float(x) for x in pt["abs_errors"]],
                    }
                ],
            }
            rep_dir = OUT_DIR / f"{src_key}_{regime}"
            rep_dir.mkdir(parents=True, exist_ok=True)
            (rep_dir / "scaling.json").write_text(json.dumps(out))

        tm_ae = rep["Tm_only"]["abs_errors"]

        rows = []
        paired = {}
        for stem_key, src_key, label in SOURCES:
            pt = rep[src_key]["point"]
            rows.append(
                {
                    "source": src_key,
                    "test_mae": rep[src_key]["mae"],
                    "ci_width": rep[src_key]["ci_hi"] - rep[src_key]["ci_lo"],
                    "val_mae": None,
                    "scaling_json": str(
                        (OUT_DIR / f"{src_key}_{regime}" / "scaling.json").relative_to(REPO)
                    ),
                    "arch": rep[src_key]["arch"],
                    "label": label,
                }
            )
            if src_key != "Tm_only":
                comp = paired_delta(tm_ae, rep[src_key]["abs_errors"])
                paired[f"{src_key}_minus_Tm_only"] = comp

        best = min((r for r in rows if r["source"] != "Tm_only"), key=lambda r: r["test_mae"])["source"]
        summary = {"rows": rows, "best": best, "paired_comparisons": paired}
        (OUT_DIR / f"{regime}_summary.json").write_text(json.dumps(summary, indent=2))

        # cross-check
        print(f"=== {regime.upper()} (baseline {rep['Tm_only']['point']['mae']:.3f}) ===")
        for stem_key, src_key, label in SOURCES:
            mae = rep[src_key]["point"]["mae"]
            ref_mae, ref_d = REFERENCE[regime][src_key]
            ok_mae = abs(mae - ref_mae) <= TOL
            if src_key == "Tm_only":
                status = "PASS" if ok_mae else "FAIL"
                all_pass &= ok_mae
                print(f"  [{status}] {src_key:16s} mae={mae:.4f} (ref {ref_mae:.3f})")
            else:
                d = paired[f"{src_key}_minus_Tm_only"]["delta_mae"]
                ok_d = abs(d - ref_d) <= TOL
                ok = ok_mae and ok_d
                all_pass &= ok
                status = "PASS" if ok else "FAIL"
                print(
                    f"  [{status}] {src_key:16s} mae={mae:.4f} (ref {ref_mae:.3f})  "
                    f"dMAE={d:+.4f} (ref {ref_d:+.3f})  "
                    f"95%CI[{paired[f'{src_key}_minus_Tm_only']['delta_ci_lo']:+.3f},"
                    f"{paired[f'{src_key}_minus_Tm_only']['delta_ci_hi']:+.3f}]"
                )

    print("\nOVERALL:", "PASS" if all_pass else "FAIL")


if __name__ == "__main__":
    main()
