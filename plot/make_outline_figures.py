#!/usr/bin/env python3
"""Build the main figure set for the current paper outline.

The figures are tied to the controlled source-screen results:

  results/source_screen/final_source_screen_summary.json

Outputs are written to both plot/ and paper/tex/figures/ as PDF, SVG, and
high-resolution PNG files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("XDG_CACHE_HOME", "/tmp/codex-cache")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache-codex")
Path(os.environ["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
SUMMARY_JSON = RESULTS / "source_screen" / "final_source_screen_summary.json"
PLOT_DIR = REPO / "plot"
PAPER_FIG_DIR = REPO / "paper" / "tex" / "figures"

COL = {
    "black": "#222222",
    "gray": "#6F6F6F",
    "light_gray": "#D9D9D9",
    "grid": "#E8E8E8",
    "baseline": "#4D4D4D",
    "fep": "#009E73",
    "design": "#0072B2",
    "rosetta": "#E69F00",
    "thermo": "#CC79A7",
    "mdq": "#D55E00",
    "soft_green": "#E6F4EF",
    "soft_blue": "#E7F0F7",
    "soft_orange": "#FAF0DC",
    "soft_red": "#F8E7DF",
    "soft_gray": "#F3F3F3",
}

MD_CONTACT_Q_SOURCE = "MD_Q_" + "H" + "PHIL_400K"

SOURCE_ORDER = [
    "Tm_only",
    "FEP",
    "rosetta_esm",
    "thermoMPNN",
    "rosetta_random",
    "rosetta",
    MD_CONTACT_Q_SOURCE,
]

SOURCE_LABEL = {
    "Tm_only": "Tm-only",
    "FEP": "FEP ddG",
    "rosetta": "Rosetta ddG",
    "thermoMPNN": "ThermoMPNN",
    "rosetta_random": "Rosetta random",
    "rosetta_esm": "Rosetta ESM2",
    MD_CONTACT_Q_SOURCE: "MD contact-Q",
}

SOURCE_COLOR = {
    "Tm_only": COL["baseline"],
    "FEP": COL["fep"],
    "rosetta_esm": COL["design"],
    "thermoMPNN": COL["thermo"],
    "rosetta_random": COL["rosetta"],
    "rosetta": "#B9770E",
    MD_CONTACT_Q_SOURCE: COL["mdq"],
}

SCALING_CURVES = {
    "Tm-only labels": {
        "path": RESULTS / "tm_ref_hot_mtl_tmselect" / "scaling.json",
        "color": COL["baseline"],
        "x_label": "experimental Tm labels",
        "sample_factor": 1.0,
    },
    "FEP mutation-effect labels": {
        "path": RESULTS / "fep_hot_tmselect" / "scaling.json",
        "color": COL["fep"],
        "x_label": "FEP labels",
        "sample_factor": 1.0,
    },
    "MD contact-Q labels": {
        "path": RESULTS / "hot_q_400k_tmselect" / "scaling.json",
        "color": COL["mdq"],
        "x_label": "MD contact-Q labels",
        "sample_factor": 1.0,
    },
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.0,
            "lines.linewidth": 1.6,
            "lines.markersize": 5.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def source_rows() -> pd.DataFrame:
    summary = read_json(SUMMARY_JSON)
    rows = pd.DataFrame(summary["rows"])
    rows["source"] = pd.Categorical(rows["source"], SOURCE_ORDER, ordered=True)
    rows = rows.sort_values("source").reset_index(drop=True)
    rows["label_plot"] = rows["source"].astype(str).map(SOURCE_LABEL)
    rows["color"] = rows["source"].astype(str).map(SOURCE_COLOR)
    rows["ci_lo"] = np.nan
    rows["ci_hi"] = np.nan
    rows["abs_errors"] = None
    for i, row in rows.iterrows():
        scaling = read_json(Path(row["scaling_json"]))["scaling"][0]
        rows.at[i, "ci_lo"] = float(scaling["ci_lo"])
        rows.at[i, "ci_hi"] = float(scaling["ci_hi"])
        rows.at[i, "abs_errors"] = np.asarray(scaling["abs_errors"], dtype=float)
    return rows


def load_scaling(path: Path, sample_factor: float = 1.0) -> pd.DataFrame:
    data = read_json(path)
    rows = []
    for point in data["scaling"]:
        rows.append(
            {
                "n": float(point["n"]),
                "x": float(point["n"]) * sample_factor,
                "mae": float(point["mae"]),
                "ci_lo": float(point["ci_lo"]),
                "ci_hi": float(point["ci_hi"]),
            }
        )
    return pd.DataFrame(rows)


def paired_comparisons() -> dict:
    return read_json(SUMMARY_JSON)["paired_comparisons"]


def paired_key(source: str, base: str = "Tm_only") -> str:
    return f"{source}_minus_{base}"


def panel_label(ax, label: str) -> None:
    ax.text(
        -0.10,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        ha="left",
        va="top",
    )


def polish(ax, grid_axis: str = "y") -> None:
    ax.grid(True, axis=grid_axis, color=COL["grid"], linewidth=0.65)
    ax.tick_params(width=0.8, length=3)


def hide_axes(ax) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def box(
    ax,
    xy,
    wh,
    text: str,
    fc: str = "white",
    ec: str = COL["black"],
    lw: float = 1.0,
    fontsize: float = 8.0,
    weight: str = "normal",
    ha: str = "center",
) -> FancyBboxPatch:
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.015,rounding_size=0.018",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha=ha,
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=COL["black"],
    )
    return patch


def arrow(ax, start, end, color: str = COL["black"], lw: float = 1.2, style: str = "-") -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=lw,
            linestyle=style,
            color=color,
            shrinkA=3,
            shrinkB=3,
        )
    )


def save_figure(fig, stem: str) -> None:
    PLOT_DIR.mkdir(exist_ok=True)
    PAPER_FIG_DIR.mkdir(parents=True, exist_ok=True)
    for out_dir in (PLOT_DIR, PAPER_FIG_DIR):
        for ext in ("pdf", "svg", "png"):
            path = out_dir / f"{stem}.{ext}"
            if ext == "png":
                fig.savefig(path, bbox_inches="tight", dpi=600)
            else:
                fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {PLOT_DIR / (stem + '.pdf')}")


def horizontal_interval(ax, y, mid, lo, hi, color, marker="o", label=None, zorder=3):
    ax.plot([lo, hi], [y, y], color=color, linewidth=2.0, solid_capstyle="round", zorder=zorder)
    ax.scatter([mid], [y], s=34, color=color, edgecolor="white", linewidth=0.6, zorder=zorder + 1, marker=marker, label=label)


def fig01_concept_protocol(rows: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.8), constrained_layout=True)

    ax = axes[0, 0]
    hide_axes(ax)
    box(ax, (0.07, 0.64), (0.27, 0.16), "target task\nmeasured Tm", fc=COL["soft_gray"], ec=COL["baseline"], weight="bold")
    box(ax, (0.07, 0.23), (0.27, 0.16), "source task\ncomputed label", fc=COL["soft_green"], ec=COL["fep"], weight="bold")
    box(ax, (0.43, 0.43), (0.22, 0.18), "shared\nsequence\nrepresentation", fc=COL["soft_blue"], ec=COL["design"], weight="bold", fontsize=7.8)
    box(ax, (0.74, 0.64), (0.20, 0.14), "Tm head", fc="white", ec=COL["baseline"], weight="bold")
    box(ax, (0.74, 0.25), (0.20, 0.14), "auxiliary\nhead", fc="white", ec=COL["fep"], weight="bold")
    arrow(ax, (0.34, 0.72), (0.43, 0.54), color=COL["baseline"])
    arrow(ax, (0.34, 0.31), (0.43, 0.50), color=COL["fep"])
    arrow(ax, (0.65, 0.54), (0.74, 0.71), color=COL["baseline"])
    arrow(ax, (0.65, 0.50), (0.74, 0.32), color=COL["fep"])
    ax.text(0.20, 0.55, "57 training\nlabels", ha="center", va="center", fontsize=7.6, color=COL["baseline"])
    ax.text(0.20, 0.13, "larger labeled\nvariant sets", ha="center", va="center", fontsize=7.6, color=COL["fep"])
    ax.text(0.50, 0.12, "transfer learning maps source-task signal into the Tm predictor", ha="center", fontsize=7.7, color=COL["black"])
    ax.set_title("Transfer-learning setup")
    panel_label(ax, "A")

    ax = axes[0, 1]
    hide_axes(ax)
    box(ax, (0.06, 0.40), (0.20, 0.20), "sequence", fc=COL["soft_gray"])
    box(ax, (0.36, 0.39), (0.22, 0.22), "shared\nencoder", fc=COL["soft_blue"], weight="bold")
    box(ax, (0.70, 0.63), (0.22, 0.16), "Tm\nprediction", fc=COL["soft_gray"])
    box(ax, (0.70, 0.22), (0.22, 0.16), "auxiliary\nprediction", fc=COL["soft_green"])
    arrow(ax, (0.26, 0.50), (0.36, 0.50))
    arrow(ax, (0.58, 0.50), (0.70, 0.71))
    arrow(ax, (0.58, 0.50), (0.70, 0.30))
    box(ax, (0.19, 0.08), (0.64, 0.10), "model selection uses the experimental development set", fc="white", ec=COL["fep"], fontsize=7.4)
    ax.set_title("Shared-encoder architecture")
    panel_label(ax, "B")

    ax = axes[1, 0]
    hide_axes(ax)
    categories = [
        ("free-energy-like", ["FEP", "Rosetta", "ThermoMPNN"], COL["soft_green"], COL["fep"]),
        ("design-scored", ["Rosetta ESM2", "Rosetta random"], COL["soft_blue"], COL["design"]),
        ("structural dynamics", ["MD contact-Q"], COL["soft_red"], COL["mdq"]),
    ]
    y0 = 0.68
    for i, (title, items, fc, ec) in enumerate(categories):
        y = y0 - i * 0.27
        box(ax, (0.07, y), (0.27, 0.14), title, fc=fc, ec=ec, weight="bold", fontsize=7.2)
        ax.text(0.40, y + 0.07, "\n".join(items), va="center", fontsize=8.0, color=COL["black"])
    ax.set_title("Auxiliary sources")
    panel_label(ax, "C")

    ax = axes[1, 1]
    hide_axes(ax)
    xs = [0.16, 0.39, 0.62, 0.85]
    labels = ["train\n57", "val\n114", "test\n396", "paired\nbootstrap"]
    colors = [COL["soft_gray"], COL["soft_blue"], COL["soft_green"], "white"]
    ecs = [COL["gray"], COL["design"], COL["fep"], COL["black"]]
    for i, (xx, lab, fc, ec) in enumerate(zip(xs, labels, colors, ecs)):
        box(ax, (xx - 0.085, 0.48), (0.17, 0.16), lab, fc=fc, ec=ec, weight="bold" if i == 2 else "normal")
        if i < len(xs) - 1:
            arrow(ax, (xx + 0.085, 0.56), (xs[i + 1] - 0.085, 0.56), color=COL["black"])
    ax.text(0.50, 0.28, "Final claims use held-out Tm test errors", ha="center", fontsize=8.0)
    ax.text(0.50, 0.18, "All sources are compared on the same test examples", ha="center", fontsize=7.5, color=COL["gray"])
    ax.set_title("Evaluation protocol")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline01_concept_protocol")


def fig02_source_screen(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), constrained_layout=True)

    ax = axes[0, 0]
    tm_scale = load_scaling(SCALING_CURVES["Tm-only labels"]["path"])
    ax.fill_between(tm_scale["x"], tm_scale["ci_lo"], tm_scale["ci_hi"], color=COL["baseline"], alpha=0.15, lw=0)
    ax.plot(tm_scale["x"], tm_scale["mae"], marker="o", color=COL["baseline"], label="Tm-only")
    ax.set_xlabel("experimental Tm labels")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_title("Experimental-label scaling")
    ax.set_xlim(8, 60)
    ax.set_xticks([10, 20, 30, 40, 57])
    ax.set_xticklabels(["10", "20", "30", "40", "57"])
    ax.set_ylim(6.35, 7.85)
    polish(ax, "both")
    panel_label(ax, "A")

    ax = axes[0, 1]
    baseline = rows.loc[rows["source"].astype(str) == "Tm_only"].iloc[0]["test_mae"]
    fep_scale = load_scaling(SCALING_CURVES["FEP mutation-effect labels"]["path"])
    ax.axhline(baseline, color=COL["baseline"], linestyle="--", linewidth=1.1, label="Tm-only final")
    ax.fill_between(fep_scale["x"], fep_scale["ci_lo"], fep_scale["ci_hi"], color=COL["fep"], alpha=0.15, lw=0)
    ax.plot(fep_scale["x"], fep_scale["mae"], marker="o", color=COL["fep"], label="FEP")
    best_idx = int(fep_scale["mae"].argmin())
    ax.scatter([fep_scale.loc[best_idx, "x"]], [fep_scale.loc[best_idx, "mae"]], s=54, color=COL["fep"], edgecolor="white", zorder=5)
    ax.set_xscale("log")
    ax.set_xticks([10, 40, 80, 160, 320])
    ax.set_xticklabels(["10", "40", "80", "160", "320"])
    ax.set_xlabel("FEP labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_title("FEP-label scaling")
    ax.set_ylim(6.25, 7.25)
    ax.legend(frameon=False, loc="upper left")
    polish(ax, "both")
    panel_label(ax, "B")

    ax = axes[1, 0]
    md_scale = load_scaling(SCALING_CURVES["MD contact-Q labels"]["path"])
    ax.axhline(baseline, color=COL["baseline"], linestyle="--", linewidth=1.1, label="Tm-only final")
    ax.fill_between(md_scale["x"], md_scale["ci_lo"], md_scale["ci_hi"], color=COL["mdq"], alpha=0.15, lw=0)
    ax.plot(md_scale["x"], md_scale["mae"], marker="o", color=COL["mdq"], label="MD contact-Q")
    best_idx = int(md_scale["mae"].argmin())
    ax.scatter([md_scale.loc[best_idx, "x"]], [md_scale.loc[best_idx, "mae"]], s=54, color=COL["mdq"], edgecolor="white", zorder=5)
    ax.set_xscale("log")
    ax.set_xticks([10, 40, 80, 160, 320, 640])
    ax.set_xticklabels(["10", "40", "80", "160", "320", "640"])
    ax.set_xlabel("MD contact-Q labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_title("MD-label scaling")
    ax.set_ylim(6.25, 7.35)
    ax.legend(frameon=False, loc="upper right")
    polish(ax, "both")
    panel_label(ax, "C")

    ax = axes[1, 1]
    labels = ["Tm-only\n57", "FEP\nbest", "MD contact-Q\nbest"]
    vals = [float(tm_scale.iloc[-1]["mae"]), float(fep_scale["mae"].min()), float(md_scale["mae"].min())]
    colors = [COL["baseline"], COL["fep"], COL["mdq"]]
    xpos = np.arange(len(vals))
    ax.bar(xpos, vals, color=colors, width=0.62)
    for x, yv in zip(xpos, vals):
        ax.text(x, yv + 0.035, f"{yv:.2f}", ha="center", va="bottom", fontsize=7.4)
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels)
    ax.set_ylabel("best MAE in scaling run (deg C)")
    ax.set_ylim(6.25, 6.95)
    ax.set_title("Best points in scaling runs")
    polish(ax, "y")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline02_source_screen")


def fig03_design_bridge(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), constrained_layout=True)

    ax = axes[0, 0]
    ordered = rows.set_index("source").loc[SOURCE_ORDER].reset_index()
    y = np.arange(len(ordered))
    for i, row in ordered.iterrows():
        horizontal_interval(
            ax,
            i,
            row["test_mae"],
            row["ci_lo"],
            row["ci_hi"],
            row["color"],
            marker="s" if row["source"] == "Tm_only" else "o",
        )
        ax.text(row["ci_hi"] + 0.035, i, f"{row['test_mae']:.2f}", va="center", fontsize=7.3)
    ax.set_yticks(y)
    ax.set_yticklabels(ordered["label_plot"])
    ax.invert_yaxis()
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_title("Final performance at selected settings")
    ax.set_xlim(5.70, 7.35)
    polish(ax, "x")
    panel_label(ax, "A")

    ax = axes[0, 1]
    delta_sources = [s for s in SOURCE_ORDER if s != "Tm_only"]
    y = np.arange(len(delta_sources))
    for i, source in enumerate(delta_sources):
        comp = paired[paired_key(source)]
        horizontal_interval(
            ax,
            i,
            comp["delta_mae"],
            comp["delta_ci_lo"],
            comp["delta_ci_hi"],
            SOURCE_COLOR[source],
        )
        ax.text(comp["delta_ci_hi"] + 0.018, i, f"{comp['delta_mae']:+.2f}", va="center", fontsize=7.2)
    ax.axvline(0, color=COL["black"], linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([SOURCE_LABEL[s] for s in delta_sources])
    ax.invert_yaxis()
    ax.set_xlabel("paired Delta MAE vs Tm-only (deg C)")
    ax.set_title("Final effect on Tm prediction")
    ax.set_xlim(-0.55, 0.32)
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[1, 0]
    for _, row in ordered.iterrows():
        ax.scatter(
            row["val_mae"],
            row["test_mae"],
            s=54,
            color=row["color"],
            edgecolor="white",
            linewidth=0.7,
            zorder=3,
        )
        dx = 0.015
        dy = 0.015 if row["source"] not in ["rosetta", "rosetta_random"] else -0.045
        ax.text(row["val_mae"] + dx, row["test_mae"] + dy, SOURCE_LABEL[str(row["source"])], fontsize=7.0)
    ax.set_xlabel("selected development-set MAE (deg C)")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_title("Development-set selection vs final test")
    ax.set_xlim(5.72, 6.28)
    ax.set_ylim(6.18, 6.88)
    polish(ax, "both")
    panel_label(ax, "C")

    ax = axes[1, 1]
    hide_axes(ax)
    blocks = [
        ("mutation-effect\nlabels", "FEP\nThermoMPNN\nRosetta", COL["soft_green"], COL["fep"], "strongest\nclass"),
        ("generated-variant\nlabels", "Rosetta ESM2\nRosetta random", COL["soft_blue"], COL["design"], "design\nbridge"),
        ("structural-dynamics\nlabel", "MD contact-Q", COL["soft_red"], COL["mdq"], "boundary\ncase"),
    ]
    for i, (title, items, fc, ec, tag) in enumerate(blocks):
        y0 = 0.70 - 0.30 * i
        box(ax, (0.05, y0), (0.35, 0.17), title, fc=fc, ec=ec, weight="bold", fontsize=7.3)
        ax.text(0.47, y0 + 0.085, items, va="center", fontsize=7.7)
        box(ax, (0.76, y0 + 0.025), (0.18, 0.12), tag, fc="white", ec=ec, fontsize=7.0)
        arrow(ax, (0.40, y0 + 0.085), (0.76, y0 + 0.085), color=ec)
    ax.set_title("Source categories")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline03_design_bridge")


def fig04_boundary_mdq(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.9), constrained_layout=True)

    ax = axes[0, 0]
    hide_axes(ax)
    x = np.linspace(0.07, 0.93, 260)
    landscape = 0.47 + 0.17 * np.sin(2.1 * np.pi * x + 0.35) - 0.09 * np.cos(5.4 * np.pi * x)
    ax.plot(x, landscape, color=COL["black"], linewidth=2.0)
    anchor_x = np.array([0.18, 0.40, 0.67, 0.84])
    anchor_y = np.interp(anchor_x, x, landscape)
    ax.scatter(anchor_x, anchor_y, s=52, color=COL["baseline"], edgecolor="white", linewidth=0.8, zorder=5)
    for axx, ayy in zip(anchor_x, anchor_y):
        ax.text(axx, ayy + 0.08, "Tm", ha="center", fontsize=7.5, color=COL["baseline"])
    for x0, x1 in [(0.28, 0.36), (0.52, 0.61), (0.72, 0.80)]:
        y0, y1 = np.interp([x0, x1], x, landscape)
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=COL["fep"], lw=1.7))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 - 0.075, "ddG", ha="center", fontsize=7.5, color=COL["fep"])
    ax.text(0.50, 0.93, "absolute anchors + mutation effects", ha="center", fontsize=9, fontweight="bold")
    ax.text(0.50, 0.09, "interpretation of the FEP result", ha="center", fontsize=8, color=COL["gray"])
    ax.set_title("Why mutation-effect labels can help")
    panel_label(ax, "A")

    ax = axes[0, 1]
    keys = ["FEP_minus_Tm_only", f"{MD_CONTACT_Q_SOURCE}_minus_Tm_only"]
    labs = ["FEP ddG", "MD contact-Q"]
    cols = [COL["fep"], COL["mdq"]]
    y = np.arange(2)
    for i, (key, col) in enumerate(zip(keys, cols)):
        comp = paired[key]
        horizontal_interval(ax, i, comp["delta_mae"], comp["delta_ci_lo"], comp["delta_ci_hi"], col)
        ax.text(comp["delta_ci_hi"] + 0.015, i, f"{comp['delta_mae']:+.2f}", va="center", fontsize=7.2)
    ax.axvline(0, color=COL["black"], linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labs)
    ax.invert_yaxis()
    ax.set_xlabel("paired Delta MAE vs Tm-only (deg C)")
    ax.set_xlim(-0.55, 0.30)
    ax.set_title("Mutation-effect vs MD-derived label")
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[1, 0]
    hide_axes(ax)
    # Simple contact map schematic.
    coords = np.array(
        [
            [0.18, 0.42],
            [0.28, 0.65],
            [0.43, 0.53],
            [0.56, 0.72],
            [0.70, 0.48],
            [0.82, 0.63],
        ]
    )
    hyd = {1, 3, 4}
    contacts = [(0, 2), (1, 3), (2, 4), (3, 5), (1, 4)]
    for i, j in contacts:
        color = COL["mdq"] if i in hyd or j in hyd else COL["light_gray"]
        ax.plot([coords[i, 0], coords[j, 0]], [coords[i, 1], coords[j, 1]], color=color, linewidth=2.0, alpha=0.95)
    ax.plot(coords[:, 0], coords[:, 1], color=COL["gray"], linewidth=1.1, alpha=0.55)
    for i, (xx, yy) in enumerate(coords):
        ax.add_patch(Circle((xx, yy), 0.038, facecolor=COL["soft_red"] if i in hyd else "white", edgecolor=COL["mdq"] if i in hyd else COL["gray"], linewidth=1.1))
    box(ax, (0.12, 0.13), (0.76, 0.13), "Q = retained native hydrophilic contacts\n400K trajectory, final 30 ns average", fc="white", ec=COL["mdq"], fontsize=7.4)
    ax.set_title("Contact-Q definition")
    panel_label(ax, "C")

    ax = axes[1, 1]
    hide_axes(ax)
    box(ax, (0.06, 0.64), (0.88, 0.16), "FEP labels encode mutation effects\nthat are close to stability perturbations.", fc=COL["soft_green"], ec=COL["fep"], fontsize=8.0, weight="bold")
    box(ax, (0.06, 0.39), (0.88, 0.16), "MD contact-Q summarizes structural persistence;\nit did not improve final Tm prediction here.", fc=COL["soft_red"], ec=COL["mdq"], fontsize=8.0)
    box(ax, (0.06, 0.14), (0.88, 0.16), "Take-home: useful simulation labels must carry\ninformation relevant to Tm generalization.", fc="white", ec=COL["black"], fontsize=8.0)
    ax.set_title("Interpretation")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline04_mdq_boundary")


def write_summary_tsv(rows: pd.DataFrame, paired: dict) -> None:
    out_rows = []
    tm = rows.loc[rows["source"].astype(str) == "Tm_only"].iloc[0]
    for _, row in rows.iterrows():
        source = str(row["source"])
        out = {
            "source": SOURCE_LABEL[source],
            "test_mae": row["test_mae"],
            "ci_lo": row["ci_lo"],
            "ci_hi": row["ci_hi"],
            "val_mae": row["val_mae"],
        }
        if source == "Tm_only":
            out.update({"delta_vs_tm": np.nan, "delta_ci_lo": np.nan, "delta_ci_hi": np.nan})
        else:
            comp = paired[paired_key(source)]
            out.update(
                {
                    "delta_vs_tm": comp["delta_mae"],
                    "delta_ci_lo": comp["delta_ci_lo"],
                    "delta_ci_hi": comp["delta_ci_hi"],
                }
            )
        out["val_delta_vs_tm"] = row["val_mae"] - tm["val_mae"]
        out_rows.append(out)
    df = pd.DataFrame(out_rows)
    for out_dir in (PLOT_DIR, PAPER_FIG_DIR):
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "outline_figure_source_screen.tsv", sep="\t", index=False)


def verify_abs_error_alignment(rows: pd.DataFrame) -> None:
    lengths = {str(row["source"]): len(row["abs_errors"]) for _, row in rows.iterrows()}
    unique = set(lengths.values())
    if unique != {396}:
        raise ValueError(f"Unexpected abs_errors lengths: {lengths}")


def main() -> None:
    configure_style()
    rows = source_rows()
    verify_abs_error_alignment(rows)
    paired = paired_comparisons()
    write_summary_tsv(rows, paired)
    fig01_concept_protocol(rows)
    fig02_source_screen(rows, paired)
    fig03_design_bridge(rows, paired)
    fig04_boundary_mdq(rows, paired)


if __name__ == "__main__":
    main()
