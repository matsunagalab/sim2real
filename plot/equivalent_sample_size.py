#!/usr/bin/env python3
"""Equivalent sample size between computational and experimental labels.

This reproduces, for our nanobody Tm setting, the quantity Minami et al. (2025,
npj Comput. Mater. 11:146) call the *equivalent sample size*: how many
computational (simulation) labels are worth one experimental label.

Method (Minami et al.).
  On an indifference curve {(n, m) : R(n, m) = const} of the generalization
  error R as a function of the simulation-label count n and the experimental
  -label count m, the marginal rate of substitution is
        dm/dn = -(dR/dn) / (dR/dm).
  The number of simulation labels equivalent to one experimental label is the
  reciprocal magnitude
        N_eq = (dR/dm) / (dR/dn).
  For their materials case they report N_eq = 221. In multitask learning they
  note the 2-D scaling law need not hold, and instead approximate the gradients
  from the *observed* MAE increments along each scaling curve -- which is what
  we do here, since our setting is multitask.

Our gradients.
  We have two one-dimensional scaling curves (one source varied at a time, the
  other axis held at its reference):
    * experimental Tm labels  m in {10,20,30,40,57}   -> dR/dm
    * FEP source labels       n in {10,40,80,160,320} -> dR/dn
  MAE decays roughly linearly in log(count), so we fit MAE = a + b*ln(count)
  by least squares and evaluate the slope dR/dcount = b/count at the current
  maximum count (Minami evaluate at the current maximum sample sizes). We also
  report a finite-difference estimate over the top segment as a robustness check.

Caveats.
  * The FEP curve is not monotonic (n=160 is worse than n=80), so dR/dn is
    uncertain; we report the fit and the raw points so the reader can judge.
  * N_eq depends on the operating point (here the current maxima) and on whether
    FEP labels are counted per template or in total (two template tables).

Usage:  python plot/equivalent_sample_size.py
Writes: results/equivalent_sample_size.json  (machine-readable)
        results/equivalent_sample_size.md    (human-readable summary)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# scaling.json sources (same files the main scaling figure is built from)
CURVES = {
    "experimental_Tm": RESULTS / "tm_ref_hot_mtl_tmselect" / "scaling.json",
    "FEP": RESULTS / "fep_hot_tmselect_enc3e-5" / "scaling.json",
    "MD_Qvalue": RESULTS / "hot_q_400k_tmselect" / "scaling.json",
}
# FEP source rows are sampled independently from each of two template tables,
# so the *total* number of FEP labels at per-template count n is FEP_TEMPLATES*n.
FEP_TEMPLATES = 2


def load_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = json.loads(path.read_text())
    pts = sorted(data["scaling"], key=lambda p: p["n"])
    n = np.array([p["n"] for p in pts], dtype=float)
    mae = np.array([p["mae"] for p in pts], dtype=float)
    return n, mae


def loglin_slope_at(n: np.ndarray, mae: np.ndarray, at: float) -> tuple[float, float]:
    """Fit MAE = a + b*ln(n); return (b, slope dMAE/dn at count `at` = b/at)."""
    b, a = np.polyfit(np.log(n), mae, 1)  # returns [slope, intercept]
    return b, b / at


def finite_diff_top(n: np.ndarray, mae: np.ndarray) -> float:
    """dMAE/dn over the top (largest two counts) segment."""
    return (mae[-1] - mae[-2]) / (n[-1] - n[-2])


def main() -> None:
    curves = {k: load_curve(p) for k, p in CURVES.items() if p.exists()}
    out: dict = {"method": "Minami et al. 2025 marginal rate of substitution "
                 "(equivalent sample size); gradients from observed MAE curves",
                 "curves": {}, "equivalent_sample_size": {}}

    # per-curve fits, evaluated at each curve's maximum count
    fits = {}
    for name, (n, mae) in curves.items():
        b, slope_max = loglin_slope_at(n, mae, at=n[-1])
        fd = finite_diff_top(n, mae)
        fits[name] = {"n": n, "mae": mae, "n_max": float(n[-1]),
                      "b_loglin": float(b), "slope_at_max": float(slope_max),
                      "slope_finite_diff_top": float(fd)}
        out["curves"][name] = {
            "counts": n.tolist(), "mae": mae.tolist(),
            "n_max": float(n[-1]),
            "dMAE_dn_loglin_at_max": float(slope_max),
            "dMAE_dn_finite_diff_top": float(fd),
        }

    dR_dm = fits["experimental_Tm"]["slope_at_max"]          # per Tm label, at m=57

    def n_eq(source: str) -> dict:
        f = fits[source]
        # per-template count slope -> total-label slope (chain rule, /FEP_TEMPLATES)
        dR_dn_per_template = f["slope_at_max"]
        dR_dn_total = dR_dn_per_template / FEP_TEMPLATES
        # finite-difference variants
        fd_per_template = f["slope_finite_diff_top"]
        fd_total = fd_per_template / FEP_TEMPLATES
        def ratio(num, den):
            return float("inf") if den == 0 else float(num / den)
        return {
            "per_template_loglin": ratio(dR_dm, dR_dn_per_template),
            "total_loglin": ratio(dR_dm, dR_dn_total),
            "per_template_finite_diff": ratio(dR_dm, fd_per_template),
            "total_finite_diff": ratio(dR_dm, fd_total),
        }

    for source in ("FEP", "MD_Qvalue"):
        if source in fits:
            out["equivalent_sample_size"][source] = n_eq(source)
    out["dR_dm_experimental_at_max"] = float(dR_dm)
    out["operating_point"] = {"m_experimental": fits["experimental_Tm"]["n_max"],
                              "n_source_per_template_max": fits.get("FEP", {}).get("n_max")}

    (RESULTS / "equivalent_sample_size.json").write_text(json.dumps(out, indent=2))

    # human-readable summary
    feq = out["equivalent_sample_size"].get("FEP", {})
    lines = [
        "# Equivalent sample size (computational labels per experimental Tm label)",
        "",
        "Method: marginal rate of substitution from Minami et al. 2025 "
        "(npj Comput. Mater. 11:146); gradients approximated from the observed",
        "MAE scaling curves (multitask setting). N_eq = (dMAE/dm_exp)/(dMAE/dn_sim) "
        "at the current maximum sample sizes (m=57, n=320/template).",
        "",
        f"dMAE/dm  (experimental Tm, at m=57): {dR_dm:.5f} degC per label",
        "",
        "FEP equivalent sample size (FEP labels worth one experimental Tm label):",
        f"  log-linear fit, per template : {feq.get('per_template_loglin', float('nan')):.0f}",
        f"  log-linear fit, total (x2)   : {feq.get('total_loglin', float('nan')):.0f}",
        f"  finite-diff (top), per templ : {feq.get('per_template_finite_diff', float('nan')):.0f}",
        f"  finite-diff (top), total     : {feq.get('total_finite_diff', float('nan')):.0f}",
        "",
        "MD Q-value: source MAE does not decrease with more labels, so its "
        "equivalent sample size is ~0 experimental labels (no transfer).",
        "",
        "Raw curves (count -> MAE degC):",
    ]
    for name, (n, mae) in curves.items():
        pts = ", ".join(f"{int(c)}:{v:.3f}" for c, v in zip(n, mae))
        lines.append(f"  {name}: {pts}")
    (RESULTS / "equivalent_sample_size.md").write_text("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
