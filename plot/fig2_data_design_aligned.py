#!/usr/bin/env python3
"""Fig 2 (data-design / sequences axis), manuscript layout, ALIGNED hphil-Q data.

Reuses the outline-figure house style (configure_style/COL/polish/panel_label/
horizontal_interval) and reproduces the two-panel fig_outline02_data_design
layout, but driven by the condition-controlled aligned-Q design comparison:

  (a),(b) label-count scaling, DMAE vs Tm-only, single mutation scan (blue) vs
      heterogeneous (gray), split into separate frozen and fine-tuned panels;
  (c) design contrast at n=320: DMAE vs each regime's own Tm-only model, four rows
      (heterogeneous / single mutation scan) x (frozen / hot), two-way bootstrap CIs.

Inputs: results/design_aligned_{scan_pool,hetero}_{frozen,hot}/design.json and
results/design_tmonly_{frozen,hot}/design.json. Saved as fig2_data_design_aligned
to plot/ and paper/analysis/ (does not overwrite the tracked manuscript figure).
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "plot"))
from make_outline_figures import (  # noqa: E402
    configure_style, COL, polish, panel_label, horizontal_interval,
)

NS = [20, 80, 160, 320]
REP_N = 320


def resid(exp, n):
    d = json.load(open(os.path.join(REPO, "results", exp, "design.json")))
    return np.array([s["residuals"] for s in d["per_n"][str(n)]["subsets"]], float)  # (8,396)


def twoway_delta(A, B, seed):
    """Δ = mean(A) − mean(B), two-way (subset × protein) bootstrap CI."""
    rng = np.random.default_rng(seed)
    pt = A.mean() - B.mean()
    boot = np.empty(10000)
    for k in range(10000):
        ai = rng.integers(0, A.shape[0], A.shape[0]); bi = rng.integers(0, B.shape[0], B.shape[0])
        pj = rng.integers(0, A.shape[1], A.shape[1])
        boot[k] = A[np.ix_(ai, pj)].mean() - B[np.ix_(bi, pj)].mean()
    return pt, float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def abs_mae(design_stem, reg):
    """Absolute Tm test MAE(n) with the SAME two-way (subset × test-protein)
    bootstrap CIs used in panel (c) — just applied to the absolute mean instead of
    the paired delta. These bars carry the full per-protein sampling uncertainty
    (large and common to both designs); the between-design contrast is in (c)."""
    xs, ys, los, his = [], [], [], []
    for i, n in enumerate(NS):
        try:
            D = resid(f"design_aligned_{design_stem}_{reg}", n)
        except KeyError:
            continue
        rng = np.random.default_rng(3000 + i)
        boot = np.empty(10000)
        for k in range(10000):
            si = rng.integers(0, D.shape[0], D.shape[0]); pj = rng.integers(0, D.shape[1], D.shape[1])
            boot[k] = D[np.ix_(si, pj)].mean()
        xs.append(n); ys.append(float(D.mean()))
        los.append(float(np.percentile(boot, 2.5))); his.append(float(np.percentile(boot, 97.5)))
    return np.array(xs, float), np.array(ys), np.array(los), np.array(his)


def tmonly_mae(reg):
    return float(resid(f"design_tmonly_{reg}", 0).mean())


def scaling_delta(design_stem, reg):
    """DMAE(n) vs Tm-only for one design, with two-way bootstrap CIs."""
    T = resid(f"design_tmonly_{reg}", 0)
    xs, ys, los, his = [], [], [], []
    for i, n in enumerate(NS):
        try:
            D = resid(f"design_aligned_{design_stem}_{reg}", n)
        except KeyError:
            continue
        d, lo, hi = twoway_delta(D, T, seed=1000 + i)
        xs.append(n); ys.append(d); los.append(lo); his.append(hi)
    return np.array(xs, float), np.array(ys), np.array(los), np.array(his)


def build():
    configure_style()
    SCAN, HET = COL["design"], COL["gray"]   # blue = single mutation scan, gray = heterogeneous
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.5),
                             gridspec_kw={"width_ratios": [1.0, 1.0, 1.35]}, layout="constrained")

    # ---- (a),(b) label-count scaling, ΔMAE vs Tm-only, split by encoder ---
    scaling_axes = {"frozen": axes[0], "hot": axes[1]}
    titles = {"frozen": "Frozen encoder", "hot": "Fine-tuned encoder"}
    # Same marker style in both panels (filled circle, colour = design); the
    # encoder regime is the panel, not the marker. No error bars (the between-design
    # CIs live in panel (c)).
    for reg, ax in scaling_axes.items():
        base = tmonly_mae(reg)
        ax.axhline(base, color=COL["baseline"], lw=1.1, ls="--", zorder=1)
        ax.annotate("Tm-only", xy=(0.03, base), xycoords=ax.get_yaxis_transform(),
                    xytext=(0, -3), textcoords="offset points",
                    ha="left", va="top", fontsize=8.0, color=COL["baseline"])
        for stem, c, label in [("scan_pool", SCAN, "Single mutation scan"),
                               ("hetero", HET, "Heterogeneous")]:
            x, y, _, _ = abs_mae(stem, reg)
            ax.plot(x, y, marker="o", linestyle="-", color=c,
                    markerfacecolor=c, markeredgecolor="white", markeredgewidth=0.8,
                    markersize=6.8, label=label, zorder=3)
        ax.set_xscale("log", base=2); ax.set_xlim(16, 560)
        ax.set_xticks(NS, [str(n) for n in NS])
        ax.set_xlabel("Labels per structure and model, n")
        ax.set_ylim(6.6, 7.45)
        ax.set_title(titles[reg], fontsize=9.8, fontweight="bold", color=COL["black"], pad=4)
        polish(ax, "both", boxed=True)
    axes[0].set_ylabel("Tm test MAE (°C)")
    axes[1].tick_params(labelleft=False)
    axes[0].legend(frameon=False, loc="upper center", ncol=1, fontsize=8.3,
                   handlelength=1.6, bbox_to_anchor=(0.52, 1.02))
    panel_label(axes[0], "A")
    panel_label(axes[1], "B")

    # ---- (c) design contrast at n=320, ΔMAE vs own Tm-only ----------------
    ax = axes[2]
    rows_b = [
        ("Single mutation scan\nfrozen encoder", "scan_pool",    "frozen", SCAN, "s"),
        ("Single mutation scan\nfine-tuned encoder", "scan_pool","hot",    SCAN, "o"),
        ("Heterogeneous sequences\nfrozen encoder", "hetero",    "frozen", HET,  "s"),
        ("Heterogeneous sequences\nfine-tuned encoder", "hetero", "hot",   HET,  "o"),
    ]
    ax.axvline(0.0, color=COL["baseline"], ls="--", lw=1.0, zorder=1)
    ypos = np.arange(len(rows_b), dtype=float)
    for y, (label, stem, reg, color, marker) in zip(ypos, rows_b):
        D = resid(f"design_aligned_{stem}_{reg}", REP_N)
        T = resid(f"design_tmonly_{reg}", 0)
        d, lo, hi = twoway_delta(D, T, seed=2000 + int(y))
        horizontal_interval(ax, y, d, lo, hi, color, marker=marker,
                            face=color if reg == "frozen" else "white")
    ax.axhline(1.5, color="white", lw=2.0, zorder=1)
    ax.set_yticks(ypos); ax.set_yticklabels([r[0] for r in rows_b], fontsize=9.2)
    ax.set_ylim(len(rows_b) - 0.45, -1.30)
    ax.set_xlim(-0.62, 0.32)
    ax.set_xlabel(r"$\Delta$MAE vs own Tm-only model (°C)")
    ax.text(0.97, 0.03, "n = 320", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.4, color=COL["gray"], style="italic")
    ax.legend(handles=[
        Line2D([], [], marker="s", linestyle="none", markerfacecolor=COL["black"],
               markeredgecolor=COL["black"], markersize=7, label="frozen encoder"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="white",
               markeredgecolor=COL["black"], markeredgewidth=1.3, markersize=7, label="fine-tuned encoder"),
    ], frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.52, 0.90),
        borderaxespad=0.2, handlelength=1.3, columnspacing=1.2, fontsize=8.2)
    polish(ax, "x", boxed=True)
    panel_label(ax, "C")

    # ---- save (pdf/svg/png) to plot/ and paper/analysis/ ------------------
    stem = "fig2_data_design_aligned"
    outdirs = [os.path.join(REPO, "plot"), os.path.join(REPO, "paper", "analysis")]
    for od in outdirs:
        os.makedirs(od, exist_ok=True)
        for ext in ("pdf", "svg", "png"):
            fig.savefig(os.path.join(od, f"{stem}.{ext}"), dpi=600 if ext == "png" else None)
    plt.close(fig)
    print("wrote", os.path.join(outdirs[0], stem + ".pdf"))


if __name__ == "__main__":
    build()
