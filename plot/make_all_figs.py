#!/usr/bin/env python3
"""Comprehensive overview figures for the sim2real MD-Q study.

Reads every results/<exp>/scaling.json from the current NbBench pipeline and
produces three multi-panel overview figures:

  fig_overview1_comparison.png : fair same-pipeline comparison (baseline / FEP / MD-Q)
  fig_overview2_cost.png       : trajectory-length (cost) analysis
  fig_overview3_survey.png     : feature & temperature survey, frozen vs hot

All numbers are regenerable; nothing is hand-entered.
"""
import json
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "results")
OUT = os.path.join(REPO, "plot")


def load(exp):
    p = os.path.join(RES, exp, "scaling.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    a = d.get("args", {})
    pts = d["scaling"]
    n = np.array([p["n"] for p in pts], float)
    return dict(
        exp=exp, args=a,
        n=n,
        mae=np.array([p["mae"] for p in pts], float),
        lo=np.array([p["ci_lo"] for p in pts], float),
        hi=np.array([p["ci_hi"] for p in pts], float),
        best=min(p["mae"] for p in pts),
        enc=a.get("encoder_mode") or d.get("resolved_encoder_mode", "?"),
    )


def x_sim(c):
    """Actual #simulation samples: FEP uses 2 antibody systems (x2)."""
    ddg = (c["args"].get("ddg_source") or "none")
    return c["n"] * (2 if ddg == "FEP" else 1)


def curve(ax, c, color, label, marker="o", x=None):
    if c is None:
        return
    xx = x if x is not None else c["n"]
    ax.fill_between(xx, c["lo"], c["hi"], color=color, alpha=0.13, lw=0)
    ax.plot(xx, c["mae"], marker=marker, color=color, label=label, lw=1.8, ms=5)


# ============================================================ FIG 1: comparison
def fig_comparison():
    fig, ax = plt.subplots(2, 2, figsize=(11, 8.5))

    for col, enc in enumerate(["frozen", "hot"]):
        a = ax[0, col]
        base = load(f"tm_ref_{enc}")
        fep = load(f"fep_{enc}")
        mdq = load(f"{'frozen_q_400k' if enc=='frozen' else 'hot_q_400k'}")
        if base is not None:
            b = base["mae"][-1]
            a.axhline(b, ls="--", color="crimson", lw=1.4, label=f"no-aux baseline ({b:.2f})")
        curve(a, fep, "tab:green", "FEP ddG", "s", x=x_sim(fep) if fep else None)
        curve(a, mdq, "tab:blue", "MD-Q HPHIL 400K", "o", x=x_sim(mdq) if mdq else None)
        a.set_xscale("log"); a.set_xlabel("# simulation samples"); a.set_ylabel("MAE (°C)")
        a.set_title(f"({'AB'[col]}) {enc}: auxiliary scaling")
        a.legend(fontsize=8); a.grid(True, which="both", ls=":", alpha=0.4)

    # (C) experimental-data scaling reference
    a = ax[1, 0]
    for enc, col in [("frozen", "tab:purple"), ("hot", "tab:orange")]:
        c = load(f"tm_ref_{enc}")
        curve(a, c, col, f"{enc}", "o", x=c["n"] if c else None)
    a.set_xlabel("# experimental Tm training samples")
    a.set_ylabel("MAE (°C)")
    a.set_title("(C) experimental-data scaling (no simulation)")
    a.legend(fontsize=8); a.grid(True, ls=":", alpha=0.4)

    # (D) best-MAE summary bars
    a = ax[1, 1]
    conds = [
        ("frozen\nbaseline", load("tm_ref_frozen"), "n_tm=57", "crimson"),
        ("frozen\n+FEP", load("fep_frozen"), None, "tab:green"),
        ("frozen\n+MD-Q", load("frozen_q_400k"), None, "tab:blue"),
        ("hot\nbaseline", load("tm_ref_hot"), "n_tm=57", "crimson"),
        ("hot\n+FEP", load("fep_hot"), None, "tab:green"),
        ("hot\n+MD-Q", load("hot_q_400k"), None, "tab:blue"),
    ]
    labels, vals, colors = [], [], []
    for lab, c, mode, col in conds:
        if c is None:
            continue
        v = c["mae"][-1] if mode == "n_tm=57" else c["best"]
        labels.append(lab); vals.append(v); colors.append(col)
    bars = a.bar(range(len(vals)), vals, color=colors, alpha=0.8)
    a.set_xticks(range(len(labels))); a.set_xticklabels(labels, fontsize=8)
    a.set_ylabel("best MAE (°C)")
    a.set_ylim(6.0, 7.7)
    a.set_title("(D) best MAE by condition")
    for b, v in zip(bars, vals):
        a.text(b.get_x() + b.get_width()/2, v + 0.01, f"{v:.2f}", ha="center", fontsize=7)
    a.grid(True, axis="y", ls=":", alpha=0.4)

    fig.suptitle("Same-pipeline comparison: conventional MD-Q ≈ physics ddG (FEP); hot encoder saturates",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    p = os.path.join(OUT, "fig_overview1_comparison.png")
    fig.savefig(p, dpi=200); fig.savefig(p.replace(".png", ".pdf")); plt.close(fig)
    print("wrote", p)


# ============================================================ FIG 2: cost
def fig_cost():
    fig, ax = plt.subplots(2, 2, figsize=(11, 8.5))
    LEN = [5, 10, 17, 30, 50, 100]

    for col, enc in enumerate(["frozen", "hot"]):
        a = ax[0, col]
        xs, mae, lo, hi = [], [], [], []
        for t in LEN:
            c = load(f"short_{enc}_t{t}")
            if c:
                xs.append(t); mae.append(c["mae"][-1]); lo.append(c["lo"][-1]); hi.append(c["hi"][-1])
        xs = np.array(xs)
        a.fill_between(xs, lo, hi, color="tab:blue", alpha=0.15, lw=0)
        a.plot(xs, mae, "o-", color="tab:blue", lw=2, ms=7, label="short MD-Q")
        base = load(f"tm_ref_{enc}"); fep = load(f"fep_{enc}")
        if base is not None:
            a.axhline(base["mae"][-1], ls="--", color="crimson", lw=1.3,
                      label=f"no-aux baseline ({base['mae'][-1]:.2f})")
        if fep is not None:
            a.axhline(fep["best"], ls=":", color="tab:green", lw=1.6,
                      label=f"FEP best ({fep['best']:.2f})")
        a.set_xscale("log"); a.set_xticks(LEN); a.set_xticklabels(LEN)
        a.set_xlabel("MD trajectory length (ns)  →  cost ∝ length")
        a.set_ylabel("MAE (°C)")
        a.set_title(f"({'AB'[col]}) {enc}: MAE vs trajectory length (n_md=640)")
        a.legend(fontsize=8); a.grid(True, which="both", ls=":", alpha=0.4)

    # (C) Q dynamic range vs length (signal grows but MAE flat)
    a = ax[1, 0]
    import pandas as pd
    qmins, qmaxs = [], []
    for t in LEN:
        f = os.path.join(REPO, "data", "md", f"feat_q_hphil_400K_t{t}ns.csv")
        if os.path.exists(f):
            df = pd.read_csv(f)
            qmins.append(df.q_value_raw.min()); qmaxs.append(df.q_value_raw.max())
        else:
            qmins.append(np.nan); qmaxs.append(np.nan)
    a.fill_between(LEN, qmins, qmaxs, color="tab:gray", alpha=0.3, label="Q range across nanobodies")
    a.plot(LEN, qmaxs, "o-", color="k", ms=4, lw=1)
    a.plot(LEN, qmins, "o-", color="k", ms=4, lw=1)
    a.set_xscale("log"); a.set_xticks(LEN); a.set_xticklabels(LEN)
    a.set_xlabel("MD trajectory length (ns)"); a.set_ylabel("Q-value (raw)")
    a.set_title("(C) Q dynamic range widens with length…")
    a.legend(fontsize=8); a.grid(True, which="both", ls=":", alpha=0.4)

    # (D) overlay frozen vs hot MAE-vs-length (normalized to own baseline)
    a = ax[1, 1]
    for enc, colr in [("frozen", "tab:purple"), ("hot", "tab:orange")]:
        xs, mae = [], []
        for t in LEN:
            c = load(f"short_{enc}_t{t}")
            if c:
                xs.append(t); mae.append(c["mae"][-1])
        base = load(f"tm_ref_{enc}")
        b = base["mae"][-1] if base else 0
        a.plot(xs, np.array(mae) - b, "o-", color=colr, lw=2, ms=6,
               label=f"{enc} (Δ vs baseline)")
    a.axhline(0, ls="--", color="gray", lw=1)
    a.set_xscale("log"); a.set_xticks(LEN); a.set_xticklabels(LEN)
    a.set_xlabel("MD trajectory length (ns)")
    a.set_ylabel("MAE − no-aux baseline (°C)")
    a.set_title("(D) …but accuracy gain stays flat (≈0)")
    a.legend(fontsize=8); a.grid(True, which="both", ls=":", alpha=0.4)

    fig.suptitle("Cost analysis: short (5 ns) MD-Q matches long MD and FEP; longer trajectories add Q range but not accuracy",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    p = os.path.join(OUT, "fig_overview2_cost.png")
    fig.savefig(p, dpi=200); fig.savefig(p.replace(".png", ".pdf")); plt.close(fig)
    print("wrote", p)


# ============================================================ FIG 3: survey
FEATS = {
    "Q HPHIL 400K": ("frozen_q_400k", "hot_q_400k"),
    "Q HPHIL 300K": ("frozen_q_hphil_full", "hot_qhphil_alone_640"),
    "Q MIN": ("frozen_q_min", "hot_q_min"),
    "Q STD": ("frozen_q_std", "hot_q_std"),
    "Q SLOPE": ("frozen_q_slope", "hot_q_slope"),
    "Q LOWFLEX": ("frozen_q_lowflex_full", "hot_lowflex_sweep"),
    "Q FRAMEWORK": ("frozen_q_framework", "hot_q_framework"),
    "RMSF MAX": ("frozen_rmsf_max", "hot_rmsf_max"),
    "RG STD": ("frozen_rg_std", "hot_rg_std"),
    "SS DIST MEAN": ("frozen_ss_dist_mean", "hot_ss_dist_mean"),
    "CDR3 LEN": ("frozen_cdr3_len", "hot_cdr3_len"),
}


def fig_survey():
    fig, ax = plt.subplots(2, 2, figsize=(12, 9))

    # (A,B) feature ranking bars per encoder
    for col, enc in enumerate(["frozen", "hot"]):
        a = ax[0, col]
        items = []
        for name, (fz, ht) in FEATS.items():
            c = load(fz if enc == "frozen" else ht)
            if c:
                items.append((name, c["best"]))
        items.sort(key=lambda x: x[1])
        names = [i[0] for i in items]; vals = [i[1] for i in items]
        cols = ["tab:blue" if "Q " in n and "LEN" not in n else "tab:gray" for n in names]
        a.barh(range(len(vals)), vals, color=cols, alpha=0.8)
        a.set_yticks(range(len(names))); a.set_yticklabels(names, fontsize=8)
        a.invert_yaxis()
        base = load(f"tm_ref_{enc}")
        if base is not None:
            a.axvline(base["mae"][-1], ls="--", color="crimson", lw=1.3,
                      label=f"no-aux baseline ({base['mae'][-1]:.2f})")
        a.set_xlabel("best MAE (°C)")
        a.set_title(f"({'AB'[col]}) {enc}: MD-feature ranking")
        a.legend(fontsize=8)
        lo = min(vals) - 0.1
        a.set_xlim(lo, max(vals) + 0.1)
        a.grid(True, axis="x", ls=":", alpha=0.4)

    # (C) temperature 300K vs 400K
    a = ax[1, 0]
    pairs = [
        ("Q_HPHIL frozen", "frozen_q_hphil_full", "frozen_q_400k", "tab:blue"),
        ("Q_SLOPE hot", "hot_q_slope", "hot_q_slope_400k", "tab:orange"),
    ]
    for label, e300, e400, colr in pairs:
        c3 = load(e300); c4 = load(e400)
        if c3:
            a.plot(c3["n"], c3["mae"], "o--", color=colr, lw=1.5, ms=5, alpha=0.6,
                   label=f"{label} 300K")
        if c4:
            a.plot(c4["n"], c4["mae"], "o-", color=colr, lw=2, ms=6,
                   label=f"{label} 400K")
    a.set_xscale("log"); a.set_xlabel("# MD samples"); a.set_ylabel("MAE (°C)")
    a.set_title("(C) temperature: 300K vs 400K")
    a.legend(fontsize=8); a.grid(True, which="both", ls=":", alpha=0.4)

    # (D) frozen vs hot scatter (best MAE per feature)
    a = ax[1, 1]
    fx, hy, labs = [], [], []
    for name, (fz, ht) in FEATS.items():
        cf = load(fz); ch = load(ht)
        if cf and ch:
            fx.append(cf["best"]); hy.append(ch["best"]); labs.append(name)
    a.scatter(fx, hy, c="tab:blue", s=40)
    for x, y, l in zip(fx, hy, labs):
        a.annotate(l, (x, y), fontsize=6, xytext=(2, 2), textcoords="offset points")
    # baselines
    bf = load("tm_ref_frozen"); bh = load("tm_ref_hot")
    if bf and bh:
        a.scatter([bf["mae"][-1]], [bh["mae"][-1]], c="crimson", s=60, marker="*",
                  label="no-aux baseline", zorder=5)
    a.set_xlabel("frozen best MAE (°C)"); a.set_ylabel("hot best MAE (°C)")
    a.set_title("(D) frozen vs hot (per feature)")
    a.legend(fontsize=8); a.grid(True, ls=":", alpha=0.4)

    fig.suptitle("Feature & temperature survey: hot ~0.6°C below frozen; no MD feature clearly beats the no-aux baseline",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    p = os.path.join(OUT, "fig_overview3_survey.png")
    fig.savefig(p, dpi=200); fig.savefig(p.replace(".png", ".pdf")); plt.close(fig)
    print("wrote", p)


if __name__ == "__main__":
    fig_comparison()
    fig_cost()
    fig_survey()
