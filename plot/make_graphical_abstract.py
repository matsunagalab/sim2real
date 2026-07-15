#!/usr/bin/env python3
"""Graphical abstract for the BPPB manuscript (single 300-dpi figure).

Summarizes two comparisons: (left) two independently developed MD data sets;
(right) FEP and MD labels with frozen and fine-tuned encoders. Numbers are
held-out paired ΔMAE values versus each series' Tm-only reference at n=320.
Output: plot/ and paper/tex/figures/ as PNG (300 dpi), PDF, SVG.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

REPO = Path(__file__).resolve().parent.parent
OUT = [REPO / "plot", REPO / "paper" / "tex" / "figures"]

COL = {"fep": "#009E73", "mdq": "#D55E00", "base": "#4D4D4D",
       "gray": "#8A8A8A", "green_soft": "#E6F4EF", "red_soft": "#F8E7DF",
       "blue": "#0072B2", "ink": "#222222"}

plt.rcParams.update({"font.family": "sans-serif", "font.size": 8.5,
                     "svg.fonttype": "none"})

fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.0, 1.05]})
fig.suptitle("Computed stability labels differ in how well they support\n"
             "nanobody melting-temperature (Tm) prediction",
             fontsize=9.6, fontweight="bold", y=1.06)

# ---------------- Left: independently developed MD data sets ----------------
axL.set_title("1. MD data sets\n(frozen-encoder comparison)", fontsize=8.8, fontweight="bold")
rows = [("heterogeneous PDB panel", -0.05, COL["gray"], "$-$0.05$^\\circ$C"),
        ("matched mutation scan", -0.20, COL["mdq"], "$-$0.20$^\\circ$C")]
for i, (name, dmae, c, tag) in enumerate(rows):
    y = 1 - i
    axL.barh(y, dmae, height=0.42, color=c, alpha=0.9, zorder=3)
    axL.text(0.02, y + 0.30, name, fontsize=8.2, fontweight="bold", ha="left")
    axL.text(dmae - 0.008 if dmae < 0 else 0.01, y, tag, va="center",
             ha="right" if dmae < 0 else "left", fontsize=7.6)
axL.axvline(0, color=COL["base"], lw=1.1, ls="--", zorder=2)
axL.text(0.01, -0.62, "same native-contact Q form; protocols and\nmodel searches also differ",
         fontsize=7.4, color=COL["gray"], style="italic")
axL.set_xlim(-0.32, 0.16)
axL.set_ylim(-0.75, 1.7)
axL.set_yticks([])
axL.set_xlabel(r"$\Delta$MAE vs Tm-only ($^\circ$C), frozen encoder", fontsize=7.8)
for s in ("top", "right", "left"):
    axL.spines[s].set_visible(False)
axL.tick_params(axis="x", labelsize=7.2)

# ---------------- Right: computed-property comparison ----------------
axR.set_title("2. Computed property\n(frozen and fine-tuned encoders)", fontsize=8.8, fontweight="bold")
axR.set_xlim(0, 1); axR.set_ylim(0, 1); axR.axis("off")
# column headers (encoder regime), row headers (observable)
axR.text(0.55, 0.90, "frozen\nencoder", ha="center", fontsize=8.0, fontweight="bold")
axR.text(0.82, 0.90, "fine-tuned\nencoder", ha="center", fontsize=8.0, fontweight="bold")
labels = [
    ("free energy (FEP)", COL["fep"], 0.60,
     [("$-$0.22", "CI below 0"), ("$-$0.15", "CI includes 0")]),
    ("native-contact Q (MD)", COL["mdq"], 0.28,
     [("$-$0.20", "CI below 0"), ("+0.03", "CI includes 0")]),
]
for name, c, y, results in labels:
    axR.add_patch(FancyBboxPatch((0.02, y - 0.085), 0.40, 0.17,
                  boxstyle="round,pad=0.01,rounding_size=0.02",
                  fc=(COL["green_soft"] if c == COL["fep"] else COL["red_soft"]),
                  ec=c, lw=1.4))
    axR.text(0.22, y, name, ha="center", va="center", fontsize=8.0, fontweight="bold")
    for xc, (value, interval) in zip((0.55, 0.82), results):
        axR.text(xc, y + 0.025, value, ha="center", va="center",
                 fontsize=8.3, color=c, fontweight="bold")
        axR.text(xc, y - 0.055, interval, ha="center", va="center",
                 fontsize=6.2, color=COL["gray"])
axR.text(0.02, 0.045,
         "FEP had the lowest MAE in both settings. Only the frozen-encoder\n"
         "FEP and MD intervals were below zero.",
         fontsize=7.2, color=COL["gray"], style="italic")

fig.tight_layout(rect=(0, 0, 1, 0.99))
for d in OUT:
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / "graphical_abstract.png", dpi=300, bbox_inches="tight")
    fig.savefig(d / "graphical_abstract.pdf", bbox_inches="tight")
print("wrote graphical_abstract.{png,pdf} to", ", ".join(str(d) for d in OUT))
