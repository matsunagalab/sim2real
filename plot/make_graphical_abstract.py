#!/usr/bin/env python3
"""Graphical abstract for the BPPB manuscript (single 300-dpi figure).

Depicts the two-axis result: (left) the choice of simulated variants affects the
strength of MD native-contact transfer; (right) the physical observable determines
whether a benefit survives encoder fine-tuning. Numbers are held-out paired
ΔMAE vs each series' Tm-only reference at n=320.
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
fig.suptitle("Two choices affect how simulation labels improve\n"
             "low-data nanobody melting-temperature (Tm) prediction",
             fontsize=9.6, fontweight="bold", y=1.06)

# ---------------- Left: simulation-design axis ----------------
axL.set_title("1. Simulation design\n(how strongly does the MD label transfer?)", fontsize=8.8, fontweight="bold")
rows = [("heterogeneous screen", -0.05, COL["gray"], "$-$0.05$^\\circ$C"),
        ("matched local scan", -0.20, COL["mdq"], "$-$0.20$^\\circ$C  ✓")]
for i, (name, dmae, c, tag) in enumerate(rows):
    y = 1 - i
    axL.barh(y, dmae, height=0.42, color=c, alpha=0.9, zorder=3)
    axL.text(0.02, y + 0.30, name, fontsize=8.2, fontweight="bold", ha="left")
    axL.text(dmae - 0.008 if dmae < 0 else 0.01, y, tag, va="center",
             ha="right" if dmae < 0 else "left", fontsize=7.6)
axL.axvline(0, color=COL["base"], lw=1.1, ls="--", zorder=2)
axL.text(0.01, -0.62, "same MD native-contact observable;\ndifferent acquisition plans",
         fontsize=7.4, color=COL["gray"], style="italic")
axL.set_xlim(-0.32, 0.16)
axL.set_ylim(-0.75, 1.7)
axL.set_yticks([])
axL.set_xlabel(r"$\Delta$MAE vs Tm-only ($^\circ$C), frozen encoder", fontsize=7.8)
for s in ("top", "right", "left"):
    axL.spines[s].set_visible(False)
axL.tick_params(axis="x", labelsize=7.2)

# ---------------- Right: physical-observable axis (2x2 transfer matrix) ----------------
axR.set_title("2. Physical observable\n(does the benefit survive fine-tuning?)", fontsize=8.8, fontweight="bold")
axR.set_xlim(0, 1); axR.set_ylim(0, 1); axR.axis("off")
# column headers (encoder regime), row headers (observable)
axR.text(0.55, 0.90, "frozen\nencoder", ha="center", fontsize=8.0, fontweight="bold")
axR.text(0.82, 0.90, "fine-tuned\n(hot)", ha="center", fontsize=8.0, fontweight="bold")
labels = [("free energy (FEP)", COL["fep"], 0.60, [True, True], ["$-$0.22✓", "$-$0.15✓"]),
          ("native-contact Q (MD)", COL["mdq"], 0.28, [True, False], ["$-$0.20✓", "+0.03"])]
for name, c, y, oks, tags in labels:
    axR.add_patch(FancyBboxPatch((0.02, y - 0.085), 0.40, 0.17,
                  boxstyle="round,pad=0.01,rounding_size=0.02",
                  fc=(COL["green_soft"] if c == COL["fep"] else COL["red_soft"]),
                  ec=c, lw=1.4))
    axR.text(0.22, y, name, ha="center", va="center", fontsize=8.0, fontweight="bold")
    for xc, ok, tag in zip((0.55, 0.82), oks, tags):
        axR.text(xc, y + 0.03, "✓" if ok else "✗", ha="center", va="center",
                 fontsize=15, color=(c if ok else COL["gray"]), fontweight="bold")
        axR.text(xc, y - 0.075, tag, ha="center", va="center", fontsize=7.0,
                 color=(COL["ink"] if ok else COL["gray"]))
axR.text(0.02, 0.045,
         "Free-energy labels help after encoder fine-tuning;\n"
         "native-contact labels help only with a frozen encoder.",
         fontsize=7.2, color=COL["gray"], style="italic")

fig.tight_layout(rect=(0, 0, 1, 0.99))
for d in OUT:
    d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / "graphical_abstract.png", dpi=300, bbox_inches="tight")
    fig.savefig(d / "graphical_abstract.pdf", bbox_inches="tight")
print("wrote graphical_abstract.{png,pdf} to", ", ".join(str(d) for d in OUT))
