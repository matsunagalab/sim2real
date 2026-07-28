#!/usr/bin/env python3
"""Fig 3 (features axis), fully condition-matched.

FEP/MD/Rosetta/FoldX on the same ddg-head, shared/separate architecture, the
identical 1MEL/4IDL variant set (421/389) sampled in the SAME order (identical
subsets per seed), and the shared Tm-only baseline. The two Rosetta proposal-design
rows (rosetta_esm/random, two-mutation variants) use their own native variant sets
and vary sequence design as well as the feature.

Reads results/fig3_<SRC>_<reg>/scaling.json and the shared baseline
results/n24_tm_<reg>_shared/scaling.json, computes dMAE = source - Tm-only at
n=320 with a paired test-protein bootstrap, and renders a forest plot.
"""
from __future__ import annotations
import json, os
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Fixed top-to-bottom order, identical in both panels (TMPNN below all Rosetta rows).
# FEP/MD/ROS/FOLDX share the identical 1MEL/4IDL variant set; the two
# Rosetta proposal-design rows (ESM / random two-mutation variants) use their own
# native variant sets — they vary sequence design as well as the feature (noted).
FEATURES = [("FEP", "FEP ΔΔG"), ("MD", "MD native-contact Q"),
            ("ROS", "Rosetta ΔΔG"), ("FOLDX", "FoldX ΔΔG"),
            ("ROSESM", "Rosetta ΔΔG (ESM variants)"),
            ("ROSRND", "Rosetta ΔΔG (random variants)")]
REG = {"frozen": "Frozen encoder", "hot": "Fine-tuned (hot) encoder"}
REP_N = 320


def point(exp, n=REP_N):
    d = json.load(open(os.path.join(REPO, "results", exp, "scaling.json")))
    cand = [p for p in d["scaling"] if int(p["n"]) == n]
    assert len(cand) == 1, f"{exp}: expected exactly one n={n} point, got {len(cand)}"
    p = cand[0]
    assert len(p["abs_errors"]) == 396, f"{exp}: {len(p['abs_errors'])} test errors (expect 396)"
    return p


def baseline_point(exp):
    """The Tm-only baseline has a single dummy scaling point (no ddG axis)."""
    d = json.load(open(os.path.join(REPO, "results", exp, "scaling.json")))
    assert len(d["scaling"]) == 1, f"{exp}: expected a single Tm-only point, got {len(d['scaling'])}"
    p = d["scaling"][0]
    assert len(p["abs_errors"]) == 396, f"{exp}: {len(p['abs_errors'])} test errors (expect 396)"
    return p


def paired(src_err, base_err, seed=42):
    d = np.asarray(src_err) - np.asarray(base_err)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (10000, len(d)))
    b = d[idx].mean(1)
    return float(d.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def rows_for(reg):
    base = baseline_point(f"n24_tm_{reg}_shared")
    out = []
    for key, label in FEATURES:
        p = point(f"fig3_{key}_{reg}")          # all features on the ddg-head, matched set
        dm, lo, hi = paired(p["abs_errors"], base["abs_errors"])
        helps = hi < 0
        hurts = lo > 0
        out.append((label, dm, lo, hi, helps, hurts, p["mae"]))
    return base["mae"], out


def source_contrasts(reg):
    """Direct candidate-vs-candidate paired contrasts (needed for source-vs-source
    claims; baseline-relative CIs alone cannot rank sources)."""
    ps = {label: point(f"fig3_{key}_{reg}")["abs_errors"] for key, label in FEATURES}
    labels = [lab for _, lab in FEATURES]
    print(f"  -- direct paired contrasts ({reg}, ΔMAE = row − col; negative = row better) --")
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            d, lo, hi = paired(ps[a], ps[b])
            sig = "*" if (hi < 0 or lo > 0) else " "
            print(f"     {a:20} vs {b:20}: {d:+.3f} [{lo:+.3f},{hi:+.3f}] {sig}")


def render(out_stem):
    """Clean fig_outline03-style forest, split into frozen and fine-tuned panels.

    Colour encodes the label source (FEP green, MD orange, the rest gray); marker
    shape/fill encodes the encoder (frozen = filled square, hot = open circle).
    Significance is read off the dashed zero line — no stars, no title/subtitle."""
    import sys
    sys.path.insert(0, os.path.join(REPO, "plot"))
    from make_outline_figures import configure_style, COL, polish, panel_label  # noqa: E402
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    configure_style()
    src_color = {"FEP": COL["fep"], "MD": COL["mdq"], "ROS": COL["gray"],
                 "FOLDX": COL["gray"], "ROSESM": COL["gray"], "ROSRND": COL["gray"]}
    marker_of = {"frozen": "s", "hot": "o"}
    titles = {"frozen": "Frozen encoder", "hot": "Fine-tuned encoder"}
    ypos = np.arange(len(FEATURES), dtype=float)

    # Each panel has one shared Tm-only baseline, so the x-axis is absolute Tm test
    # MAE with a dashed baseline line; whiskers are the paired (source - Tm-only) CI.
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), sharey=True, layout="constrained")
    for ax, reg in zip(axes, ("frozen", "hot")):
        basemae, data = rows_for(reg)              # fixed FEATURES order, both panels
        marker = marker_of[reg]
        ax.axvline(basemae, color=COL["baseline"], lw=1.1, ls="--", zorder=1)
        ax.text(basemae, 0.90, "Tm-only", transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8.0, color=COL["baseline"])
        for i, (key, _label) in enumerate(FEATURES):
            _, dm, lo, hi, _, _, mae = data[i]
            c = src_color[key]
            face = c if reg == "frozen" else "white"
            ax.errorbar(mae, ypos[i], xerr=np.array([[dm - lo], [hi - dm]]), fmt=marker,
                        markerfacecolor=face, markeredgecolor=c, markeredgewidth=1.3,
                        markersize=7.0, ecolor=c, elinewidth=1.5, capsize=3.8, capthick=1.2,
                        zorder=4)
        ax.set_ylim(len(FEATURES) - 0.5, -1.1)     # FEP (i=0) at top, room for guides
        ax.set_yticks(ypos)
        ax.set_xlim(basemae - 0.62, basemae + 0.45)
        ax.set_xlabel(r"Tm test MAE (°C)")
        ax.set_title(titles[reg], fontsize=11, fontweight="bold", color=COL["black"], pad=6)
        ax.text(0.03, 0.99, "lower Tm error", transform=ax.transAxes, ha="left", va="top",
                fontsize=8.3, color=COL["design"])
        ax.text(0.97, 0.99, "higher Tm error", transform=ax.transAxes, ha="right", va="top",
                fontsize=8.3, color=COL["rosetta"])
        ax.text(0.97, 0.03, f"n = {REP_N}", transform=ax.transAxes, ha="right", va="bottom",
                fontsize=8.3, color=COL["gray"], style="italic")
        polish(ax, "x", boxed=True)
    axes[0].set_yticklabels([lab for _, lab in FEATURES], fontsize=9.3)
    panel_label(axes[0], "A")
    panel_label(axes[1], "B")

    # out_stem is the analysis name; also write manuscript Fig 3 (fig_outline03).
    targets = [(os.path.join(REPO, "plot"), out_stem),
               (os.path.join(REPO, "paper", "analysis"), out_stem),
               (os.path.join(REPO, "paper", "tex", "figures"), "fig_outline03_physical_observable")]
    for od, stem in targets:
        os.makedirs(od, exist_ok=True)
        for ext in ("pdf", "svg", "png"):
            fig.savefig(os.path.join(od, f"{stem}.{ext}"), dpi=600 if ext == "png" else None)
    plt.close(fig)
    print("wrote", os.path.join(REPO, "paper/tex/figures/fig_outline03_physical_observable.pdf"))


def main():
    for reg in ("frozen", "hot"):
        basemae, data = rows_for(reg)
        print(f"\n=== {reg}  Tm-only baseline MAE={basemae:.3f} ===")
        for name, dm, lo, hi, helps, hurts, mae in data:  # fixed FEATURES order
            flag = "HELPS" if helps else ("HURTS" if hurts else "ns")
            print(f"  {name:22} MAE={mae:.3f} ΔMAE={dm:+.3f} [{lo:+.3f},{hi:+.3f}] {flag}")
        source_contrasts(reg)
    render("fig3_matched_forest")


if __name__ == "__main__":
    main()
