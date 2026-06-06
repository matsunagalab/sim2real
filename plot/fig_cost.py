#!/usr/bin/env python3
"""Cost-analysis figure: prediction accuracy vs MD trajectory length.

Shows that a SHORT (cheap) MD run yields the same auxiliary signal as a long one,
and matches the physics ddG (FEP) baseline -- at a fraction of the simulation cost.
All numbers from the current NbBench pipeline (results/*/scaling.json), n_md=640.
"""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "results")
LENGTHS = [5, 10, 17, 30, 50, 100]


def pt(exp):
    p = os.path.join(RES, exp, "scaling.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))["scaling"]
    s = d[-1]  # single point (n_md=640) or last point
    return s["mae"], s["ci_lo"], s["ci_hi"]


def ref_best(exp):
    p = os.path.join(RES, exp, "scaling.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))["scaling"]
    return min(x["mae"] for x in d)


def ref_full(exp):
    """no-aux baseline = MAE at the largest n_tm point."""
    p = os.path.join(RES, exp, "scaling.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))["scaling"]
    return d[-1]["mae"]


fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=False)
for ax, enc in zip(axes, ["frozen", "hot"]):
    xs, mae, lo, hi = [], [], [], []
    for t in LENGTHS:
        r = pt(f"short_{enc}_t{t}")
        if r:
            xs.append(t); mae.append(r[0]); lo.append(r[1]); hi.append(r[2])
    xs = np.array(xs); mae = np.array(mae)
    ax.fill_between(xs, lo, hi, color="tab:blue", alpha=0.15, lw=0)
    ax.plot(xs, mae, "o-", color="tab:blue", lw=2, ms=7, label="short MD-Q (this work)")

    base = ref_full(f"tm_ref_{enc}")
    fep = ref_best(f"fep_{enc}")
    if base is not None:
        ax.axhline(base, ls="--", color="crimson", lw=1.4,
                   label=f"no-aux baseline ({base:.2f})")
    if fep is not None:
        ax.axhline(fep, ls=":", color="tab:green", lw=1.8,
                   label=f"FEP ddG, best ({fep:.2f})")

    ax.set_xscale("log")
    ax.set_xticks(LENGTHS)
    ax.set_xticklabels([str(t) for t in LENGTHS])
    ax.set_xlabel("MD trajectory length (ns)  →  cost ∝ length")
    ax.set_ylabel("Tm prediction MAE (°C)")
    ax.set_title(f"{enc} encoder  (n$_{{md}}$=640)")
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, which="both", ls=":", alpha=0.4)

fig.suptitle("Short conventional MD matches long MD and physics ddG (FEP) — at a fraction of the cost",
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.96])
out = os.path.join(REPO, "plot", "fig_cost.png")
fig.savefig(out, dpi=200)
fig.savefig(out.replace(".png", ".pdf"))
print("wrote", out)
