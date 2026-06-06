#!/usr/bin/env python3
"""Generate paper figures (in-house, reproducible) for the sim2real MD-Q study.

Style follows the group's prior work (Sasaki HPCAsia poster / Minami 2025):
  MAE vs number of simulation samples, log-x, bootstrap-CI band,
  single-task baseline as a horizontal dashed line, power-law dotted fit.

All curves are read from results/<exp>/scaling.json produced by prepare.py,
so the figures are fully regenerable from the current pipeline.

Usage:
  uv run python plot/make_paper_figs.py            # build whatever data exists
"""
import json
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "results")
OUT = os.path.join(REPO, "plot")

# task counts: ddG has two antibody systems (1mel + 4idl), so total sim samples
# per scaling point = 2 * n_ddg. MD/real are single-source (factor 1).
SAMPLES_PER_N = {"n_ddg": 2, "n_md": 1, "n_tm": 1}


def load_curve(exp):
    """Return dict with n (raw), x (actual sample count), mae, ci_lo, ci_hi, meta.
    Returns None if the experiment dir / json is missing."""
    p = os.path.join(RES, exp, "scaling.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    args = d.get("args", {})
    # infer scaling axis name from args
    if str(args.get("n_tm_list") or "").strip():
        axis = "n_tm"
    elif (args.get("md_source") or "none") != "none":
        axis = "n_md"
    else:
        axis = "n_ddg"
    mult = SAMPLES_PER_N.get(axis, 1)
    pts = d["scaling"]
    n = np.array([p["n"] for p in pts], float)
    return {
        "exp": exp,
        "axis": axis,
        "n": n,
        "x": n * mult,
        "mae": np.array([p["mae"] for p in pts], float),
        "ci_lo": np.array([p["ci_lo"] for p in pts], float),
        "ci_hi": np.array([p["ci_hi"] for p in pts], float),
        "summary": d.get("summary", {}),
        "best": d.get("best", {}),
        "args": args,
    }


def power_law(x, a, b, c):
    return a * x ** b + c


def fit_power(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    c0 = float(np.min(y) - 0.02)
    a0 = float(max(np.max(y) - c0, 1e-3))
    try:
        popt, _ = curve_fit(
            power_law, x, y, p0=[a0, -0.2, c0],
            bounds=((1e-6, -3.0, min(y) - 1.0), (1e3, -1e-4, max(y) + 1.0)),
            maxfev=40000,
        )
        return tuple(popt)
    except Exception:
        return None


def plot_curve(ax, cur, color, label, marker="o", ls="-"):
    ax.fill_between(cur["x"], cur["ci_lo"], cur["ci_hi"], color=color, alpha=0.15, lw=0)
    ax.plot(cur["x"], cur["mae"], marker=marker, ls=ls, color=color, label=label, lw=1.8, ms=5)


def add_powerfit(ax, cur, color):
    fit = fit_power(cur["x"], cur["mae"])
    if fit is None:
        return None
    xs = np.linspace(cur["x"].min(), cur["x"].max(), 100)
    ax.plot(xs, power_law(xs, *fit), ls=":", color=color, lw=1.2, alpha=0.8)
    return fit


# --------------------------------------------------------------------------
def fig2(curves):
    """Main result: conventional MD-Q beats physics ddG. Panel-rich."""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    def baseline_line(ax, ref_exp):
        ref = curves.get(ref_exp)
        if ref is not None:
            b = float(ref["mae"][np.argmax(ref["n"])])  # MAE at largest real-data point
            ax.axhline(b, ls="--", color="crimson", lw=1.3,
                       label=f"single-task (Tm only, n={int(ref['n'].max())})")

    # (A) Q_HPHIL: baseline / FEP / MD-Q frozen+hot
    ax = axes[0, 0]
    baseline_line(ax, "tm_ref_hot")
    for exp, col, lab, mk in [
        ("fep_hot", "tab:green", "FEP ddG (hot)", "s"),
        ("frozen_q_400k", "tab:orange", "MD-Q HPHIL 400K (frozen)", "^"),
        ("hot_q_400k", "tab:blue", "MD-Q HPHIL 400K (hot)", "o"),
    ]:
        c = curves.get(exp)
        if c:
            plot_curve(ax, c, col, lab, marker=mk)
            add_powerfit(ax, c, col)
    ax.set_xscale("log")
    ax.set_xlabel("number of simulation samples")
    ax.set_ylabel("MAE (°C)")
    ax.set_title("(A) Q-value (HPHIL contacts)")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", ls=":", alpha=0.4)

    # (B) Q_SLOPE panel
    ax = axes[0, 1]
    baseline_line(ax, "tm_ref_hot")
    for exp, col, lab, mk in [
        ("fep_hot", "tab:green", "FEP ddG (hot)", "s"),
        ("hot_q_slope_400k", "tab:blue", "MD-Q SLOPE 400K (hot)", "o"),
    ]:
        c = curves.get(exp)
        if c:
            plot_curve(ax, c, col, lab, marker=mk)
            add_powerfit(ax, c, col)
    ax.set_xscale("log")
    ax.set_xlabel("number of simulation samples")
    ax.set_ylabel("MAE (°C)")
    ax.set_title("(B) Q-value (unfolding slope)")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", ls=":", alpha=0.4)

    # (C) physics ddG sources head-to-head (hot) — placeholder uses fep only for now
    ax = axes[1, 0]
    baseline_line(ax, "tm_ref_hot")
    for exp, col, lab, mk in [
        ("fep_hot", "tab:green", "FEP", "s"),
        ("rosetta_hot", "tab:red", "Rosetta", "D"),
        ("foldx_hot", "tab:purple", "FoldX", "v"),
        ("thermompnn_hot", "tab:brown", "ThermoMPNN", "P"),
    ]:
        c = curves.get(exp)
        if c:
            plot_curve(ax, c, col, lab, marker=mk)
    ax.set_xscale("log")
    ax.set_xlabel("number of simulation samples")
    ax.set_ylabel("MAE (°C)")
    ax.set_title("(C) physics-based ddG sources (hot)")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", ls=":", alpha=0.4)

    # (D) MRS bar / or slope degeneracy — filled after MRS computed
    ax = axes[1, 1]
    ax.set_title("(D) marginal rate of substitution")
    ax.text(0.5, 0.5, "MRS panel\n(filled by compute_mrs)", ha="center", va="center",
            transform=ax.transAxes, color="gray")

    fig.tight_layout()
    out = os.path.join(OUT, "fig2_main.png")
    fig.savefig(out, dpi=200)
    fig.savefig(out.replace(".png", ".pdf"))
    print("wrote", out)
    plt.close(fig)


def compute_mrs(curves):
    """Marginal rate of substitution: how many sim samples ~ 1 real Tm sample.

    Uses power-law fits on the real-data reference (MAE vs n_tm) and the sim
    curve (MAE vs n_sim); MRS = (dMAE/dn_real) / (dMAE/dn_sim) evaluated where
    the curves are compared. Reported per (encoder, sim source)."""
    rows = []
    for enc in ["frozen", "hot"]:
        ref = curves.get(f"tm_ref_{enc}")
        if ref is None:
            continue
        ref_fit = fit_power(ref["n"], ref["mae"])  # x = real sample count
        if ref_fit is None:
            continue
        a_r, b_r, c_r = ref_fit
        for src, exp in [("MD-Q HPHIL 400K", f"{'hot_q_400k' if enc=='hot' else 'frozen_q_400k'}"),
                         ("FEP ddG", f"fep_{enc}")]:
            c = curves.get(exp)
            if c is None:
                continue
            sim_fit = fit_power(c["x"], c["mae"])
            if sim_fit is None:
                rows.append((enc, src, c["best"].get("mae"), None, "sim slope undefined"))
                continue
            a_s, b_s, c_s = sim_fit
            # evaluate marginal rates at the sim curve's best (largest-x) point
            x_s = float(c["x"].max())
            dmae_dnsim = a_s * b_s * x_s ** (b_s - 1)
            # real-data marginal rate at full available real data
            n_r = float(ref["n"].max())
            dmae_dnreal = a_r * b_r * n_r ** (b_r - 1)
            if dmae_dnsim == 0:
                mrs = np.inf
            else:
                mrs = dmae_dnreal / dmae_dnsim
            rows.append((enc, src, round(float(c["best"].get("mae", np.nan)), 3),
                         round(float(mrs), 1), f"@n_sim={int(x_s)}"))
    print("\n=== Marginal Rate of Substitution (sim samples per 1 real Tm) ===")
    print(f"{'enc':6s} {'source':18s} {'best_MAE':>9s} {'MRS':>10s}  note")
    for r in rows:
        print(f"{r[0]:6s} {r[1]:18s} {str(r[2]):>9s} {str(r[3]):>10s}  {r[4]}")
    return rows


def main():
    exps = [
        # MD-Q (already present)
        "hot_q_400k", "frozen_q_400k", "hot_q_slope_400k", "hot_q_min_400k", "hot_q_std_400k",
        # references + FEP (being generated)
        "tm_ref_frozen", "tm_ref_hot", "fep_frozen", "fep_hot",
        # 300K for temperature panel
        "frozen_q_hphil_full", "hot_q_slope",
        # other ddG (optional)
        "rosetta_hot", "foldx_hot", "thermompnn_hot",
    ]
    curves = {}
    for e in exps:
        c = load_curve(e)
        if c is not None:
            curves[e] = c
    print("loaded curves:", sorted(curves.keys()))
    fig2(curves)
    compute_mrs(curves)


if __name__ == "__main__":
    main()
