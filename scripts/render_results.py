#!/usr/bin/env python
"""Aggregate results/<name>/scaling.json into summary tables and figures.

Outputs (in plot/):
  - figures (PNG, PDF):
      fig_scaling_mae.{png,pdf}        MAE vs n_md across MD-feature variants (frozen)
      fig_scaling_combo.{png,pdf}      same but adding combo + Rosetta + DDG comparison
      fig_encoder_mode.{png,pdf}       best MAE for frozen / lora / hot at fixed Q_LOWFLEX, 8M
      fig_model_size.{png,pdf}         8M vs 650M, hot vs lora
      fig_md_weight_grid.{png,pdf}     MAE vs MD_WEIGHT (fixed-weight MTL scan)
      fig_overall_summary.{png,pdf}    horizontal bar chart of best MAE for all loaded experiments
  - paper/results_summary.md           markdown table of best MAE / CI / ΔMAE per experiment
  - paper/results_summary.tsv          tab-separated mirror

Run after experiments are complete:
    uv run python scripts/render_results.py
"""

import json
import os
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO_ROOT, "results")
PLOT_DIR = os.path.join(REPO_ROOT, "plot")
PAPER_DIR = os.path.join(REPO_ROOT, "paper")
EXP_YAML = os.path.join(REPO_ROOT, "experiments.yaml")

os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(PAPER_DIR, exist_ok=True)

# Publication style
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "legend.frameon": False,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

PALETTE = {
    "frozen": "#777777",
    "lora": "#3B82F6",
    "hot": "#DC2626",
    "rosetta": "#10B981",
    "Q_HPHIL": "#444444",
    "Q_LOWFLEX": "#1D4ED8",
    "Q_HIGHFLEX": "#DC2626",
    "SALTBRIDGE": "#F59E0B",
    "8M": "#6B7280",
    "650M": "#7C3AED",
}


def load_all_results() -> dict[str, dict]:
    """Load every results/<name>/scaling.json into a dict keyed by exp name."""
    results = {}
    for path in sorted(glob(os.path.join(RESULTS_DIR, "*", "scaling.json"))):
        name = os.path.basename(os.path.dirname(path))
        with open(path) as f:
            results[name] = json.load(f)
    return results


def load_registry() -> dict:
    with open(EXP_YAML) as f:
        return yaml.safe_load(f)["experiments"]


def best_of(data: dict) -> tuple[int, float, float]:
    return data["best"]["n"], data["best"]["mae"], data["best"]["ci_width"]


# ------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------

def write_summary_table(results: dict[str, dict], registry: dict):
    rows = []
    for name in registry:
        if name not in results:
            continue
        r = results[name]
        cfg = registry[name]
        bn, bm, bcw = best_of(r)
        rows.append({
            "name": name,
            "description": cfg.get("description", ""),
            "encoder": r.get("resolved_encoder_mode", ""),
            "base_model": r.get("hparams", {}).get("base_model_name", "").split("/")[-1],
            "md_source": r.get("args", {}).get("md_source", ""),
            "md_aux": r.get("args", {}).get("md_aux_source", ""),
            "ddg_source": r.get("args", {}).get("ddg_source", ""),
            "n_runs": r.get("args", {}).get("n_runs", ""),
            "best_n": bn,
            "best_mae": bm,
            "best_ci_width": bcw,
            "delta_mae_full": r.get("paired_bootstrap", {}).get("full_range", {}).get("delta_mae"),
            "p_value": r.get("paired_bootstrap", {}).get("full_range", {}).get("p_positive"),
        })

    md_path = os.path.join(PAPER_DIR, "results_summary.md")
    tsv_path = os.path.join(PAPER_DIR, "results_summary.tsv")

    with open(md_path, "w") as f:
        f.write("# Experiment Results Summary\n\n")
        f.write("| Experiment | Encoder | Base | MD source | aux | best n | **best MAE** | CI width | ΔMAE (full) | p |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            d_mae = r["delta_mae_full"]
            d_str = f"{d_mae:+.3f}" if d_mae is not None else "—"
            p_str = f"{r['p_value']:.4f}" if r["p_value"] is not None else "—"
            f.write(
                f"| `{r['name']}` | {r['encoder']} | {r['base_model']} | "
                f"{r['md_source']} | {r['md_aux'] or '—'} | {r['best_n']} | "
                f"**{r['best_mae']:.3f}** | {r['best_ci_width']:.3f} | "
                f"{d_str} | {p_str} |\n"
            )
    with open(tsv_path, "w") as f:
        f.write("name\tencoder\tbase\tmd_source\tmd_aux\tddg_source\tn_runs\t"
                "best_n\tbest_mae\tbest_ci_width\tdelta_mae\tp_value\n")
        for r in rows:
            f.write(
                f"{r['name']}\t{r['encoder']}\t{r['base_model']}\t"
                f"{r['md_source']}\t{r['md_aux']}\t{r['ddg_source']}\t{r['n_runs']}\t"
                f"{r['best_n']}\t{r['best_mae']:.4f}\t{r['best_ci_width']:.4f}\t"
                f"{r['delta_mae_full'] if r['delta_mae_full'] is not None else ''}\t"
                f"{r['p_value'] if r['p_value'] is not None else ''}\n"
            )

    print(f"  wrote {md_path}")
    print(f"  wrote {tsv_path}")
    return rows


# ------------------------------------------------------------------
# Figures
# ------------------------------------------------------------------

def _plot_scaling(ax, scaling_pts, label, color, marker="o"):
    if not scaling_pts:
        return
    ns = [p["n"] for p in scaling_pts]
    maes = [p["mae"] for p in scaling_pts]
    los = [p["ci_lo"] for p in scaling_pts]
    his = [p["ci_hi"] for p in scaling_pts]
    ax.plot(ns, maes, marker=marker, color=color, label=label,
            linewidth=1.6, markersize=5)
    ax.fill_between(ns, los, his, color=color, alpha=0.10, linewidth=0)


def fig_scaling_mae(results: dict[str, dict]):
    """Frozen MD-feature variants: MAE vs n_md."""
    fig, ax = plt.subplots(figsize=(5.5, 4))
    plot_specs = [
        ("frozen_q_hphil_full",      "Q hphil-all",      PALETTE["Q_HPHIL"], "o"),
        ("frozen_q_lowflex_full",    "Q LOWFLEX (FW)",   PALETTE["Q_LOWFLEX"], "s"),
        ("frozen_q_highflex_full",   "Q HIGHFLEX (CDR)", PALETTE["Q_HIGHFLEX"], "^"),
        ("frozen_saltbridge_full",   "Salt bridge",      PALETTE["SALTBRIDGE"], "D"),
    ]
    for name, label, color, marker in plot_specs:
        if name in results:
            _plot_scaling(ax, results[name]["scaling"], label, color, marker)
    ax.set_xscale("log")
    ax.set_xlabel("n_md (auxiliary samples)")
    ax.set_ylabel("Tm prediction MAE (°C)")
    ax.set_title("MD feature comparison (frozen ESM-2 8M)")
    ax.legend(loc="upper right")
    ax.grid(True, which="both", alpha=0.2)
    out = os.path.join(PLOT_DIR, "fig_scaling_mae")
    fig.savefig(out + ".png"); fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"  wrote {out}.png/pdf")


def fig_scaling_combo(results: dict[str, dict]):
    """Same as fig_scaling_mae but extending with the combo + Rosetta."""
    fig, ax = plt.subplots(figsize=(5.5, 4))
    plot_specs = [
        ("frozen_q_hphil_full",            "Q hphil",       PALETTE["Q_HPHIL"], "o"),
        ("frozen_q_lowflex_full",          "Q LOWFLEX",     PALETTE["Q_LOWFLEX"], "s"),
        ("rosetta_full",                   "Rosetta MC",    PALETTE["rosetta"], "v"),
        ("combo_lowflex_highflex_frozen",  "LOWFLEX+HIGHFLEX combo", "#7C3AED", "P"),
        ("hot_lowflex_sweep",              "8M Hot + LOWFLEX",       PALETTE["hot"], "*"),
    ]
    for name, label, color, marker in plot_specs:
        if name in results:
            _plot_scaling(ax, results[name]["scaling"], label, color, marker)
    ax.set_xscale("log")
    ax.set_xlabel("n_md (auxiliary samples)")
    ax.set_ylabel("Tm prediction MAE (°C)")
    ax.set_title("Scaling: best configurations")
    ax.legend(loc="upper right")
    ax.grid(True, which="both", alpha=0.2)
    out = os.path.join(PLOT_DIR, "fig_scaling_combo")
    fig.savefig(out + ".png"); fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"  wrote {out}.png/pdf")


def _bar(ax, labels, values, errors, colors, ylabel, title):
    x = np.arange(len(labels))
    bars = ax.bar(x, values, yerr=errors, color=colors,
                  capsize=4, error_kw={"linewidth": 1, "alpha": 0.7})
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.2)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.01, f"{v:.2f}",
                ha="center", va="bottom", fontsize=9)


def fig_encoder_mode(results: dict[str, dict]):
    """Best MAE for frozen / hot at fixed Q_LOWFLEX (and LoRA at 650M as proxy)."""
    setups = [
        ("frozen_q_lowflex_full", "Frozen 8M",     PALETTE["frozen"]),
        ("hot_lowflex_sweep",     "Hot 8M",        PALETTE["hot"]),
        ("lora_650m_lowflex_640", "LoRA 650M",     PALETTE["lora"]),
        ("hot_650m_lowflex_640",  "Hot 650M",      "#7C3AED"),
    ]
    labels, values, errors, colors = [], [], [], []
    for name, label, color in setups:
        if name not in results:
            continue
        bn, bm, bcw = best_of(results[name])
        labels.append(label); values.append(bm); errors.append(bcw / 2)
        colors.append(color)
    fig, ax = plt.subplots(figsize=(5, 4))
    _bar(ax, labels, values, errors, colors,
         "Best Tm MAE (°C)", "Encoder mode × base size (Q_LOWFLEX, n=640)")
    ax.set_ylim(min(values) - 0.4, max(values) + 0.5)
    out = os.path.join(PLOT_DIR, "fig_encoder_mode")
    fig.savefig(out + ".png"); fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"  wrote {out}.png/pdf")


def fig_md_weight_grid(results: dict[str, dict]):
    weights, maes, errs = [], [], []
    for w_str in ["0.5", "1.0", "2.0", "4.0", "8.0"]:
        name = f"md_weight_w{w_str}"
        if name in results:
            bn, bm, bcw = best_of(results[name])
            weights.append(float(w_str)); maes.append(bm); errs.append(bcw / 2)
    if not weights:
        return
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.errorbar(weights, maes, yerr=errs, marker="o",
                color="#1D4ED8", linewidth=1.5, capsize=4)
    ax.set_xscale("log")
    ax.set_xlabel("MD task weight (fixed-weight MTL)")
    ax.set_ylabel("Tm MAE (°C) at n_md=320, 5 runs")
    ax.set_title("Fixed MD-weight grid (8M frozen, Q_HPHIL)")
    ax.grid(True, which="both", alpha=0.2)
    out = os.path.join(PLOT_DIR, "fig_md_weight_grid")
    fig.savefig(out + ".png"); fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"  wrote {out}.png/pdf")


def fig_v2_features(results: dict[str, dict]):
    """Compare v2 lightweight features under frozen and hot encoder."""
    feats = ["q_min", "q_std", "q_slope", "rmsf_max", "rg_std"]
    frozen_mae, hot_mae, frozen_ci, hot_ci = [], [], [], []
    for f in feats:
        fz = results.get(f"frozen_{f}")
        ht = results.get(f"hot_{f}")
        if not fz or not ht:
            return
        frozen_mae.append(fz["best"]["mae"])
        hot_mae.append(ht["best"]["mae"])
        frozen_ci.append(fz["best"]["ci_width"] / 2)
        hot_ci.append(ht["best"]["ci_width"] / 2)

    x = np.arange(len(feats))
    w = 0.38
    fig, ax = plt.subplots(figsize=(6, 4))
    b1 = ax.bar(x - w / 2, frozen_mae, w, yerr=frozen_ci,
                color=PALETTE["frozen"], label="Frozen", capsize=3)
    b2 = ax.bar(x + w / 2, hot_mae, w, yerr=hot_ci,
                color=PALETTE["hot"], label="Hot", capsize=3)
    for bars, vals in [(b1, frozen_mae), (b2, hot_mae)]:
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(feats)
    ax.set_ylabel("Best Tm MAE (°C)")
    ax.set_title("Round-2 features × encoder mode (n_md best per cell)")
    ax.set_ylim(min(hot_mae) - 0.3, max(frozen_mae) + 0.4)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.2)
    out = os.path.join(PLOT_DIR, "fig_v2_features")
    fig.savefig(out + ".png"); fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"  wrote {out}.png/pdf")


def fig_overall_summary(results: dict[str, dict], registry: dict):
    """Horizontal bar chart: every loaded experiment, sorted by best MAE."""
    items = []
    for name, r in results.items():
        cfg = registry.get(name, {})
        bn, bm, bcw = best_of(r)
        # Color by encoder mode
        enc = r.get("resolved_encoder_mode", "frozen")
        color = PALETTE.get(enc, "#999999")
        items.append((name, bm, bcw, color, cfg.get("description", "")))
    items.sort(key=lambda x: x[1])

    fig, ax = plt.subplots(figsize=(7, 0.32 * len(items) + 1.5))
    y = np.arange(len(items))
    maes = [it[1] for it in items]
    errs = [it[2] / 2 for it in items]
    colors = [it[3] for it in items]
    names = [it[0] for it in items]
    ax.barh(y, maes, xerr=errs, color=colors, capsize=3,
            error_kw={"linewidth": 1, "alpha": 0.7})
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Best Tm MAE (°C)")
    ax.set_title("All experiments — best MAE (color = encoder mode)")
    ax.set_xlim(min(maes) - 0.3, max(maes) + 0.5)
    for yi, m in zip(y, maes):
        ax.text(m + 0.05, yi, f"{m:.2f}", va="center", fontsize=8)
    ax.grid(axis="x", alpha=0.2)
    # Legend
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=PALETTE["frozen"], label="frozen"),
               Patch(facecolor=PALETTE["lora"], label="lora"),
               Patch(facecolor=PALETTE["hot"], label="hot")]
    ax.legend(handles=handles, loc="lower right")
    out = os.path.join(PLOT_DIR, "fig_overall_summary")
    fig.savefig(out + ".png"); fig.savefig(out + ".pdf")
    plt.close(fig)
    print(f"  wrote {out}.png/pdf")


def main():
    results = load_all_results()
    if not results:
        print(f"No results found in {RESULTS_DIR} — run experiments first.")
        return
    registry = load_registry()
    print(f"Loaded {len(results)} experiment results")
    print("--- tables ---")
    write_summary_table(results, registry)
    print("--- figures ---")
    fig_scaling_mae(results)
    fig_scaling_combo(results)
    fig_encoder_mode(results)
    fig_md_weight_grid(results)
    fig_v2_features(results)
    fig_overall_summary(results, registry)
    print("done.")


if __name__ == "__main__":
    main()
