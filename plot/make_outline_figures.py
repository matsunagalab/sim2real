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
FROZEN_SUMMARY_JSON = RESULTS / "source_screen" / "final_frozen_core_summary.json"
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
    "Tm_only": "Tm labels only",
    "FEP": "mutation free energy\n(FEP)",
    "rosetta": "structure mutation\nscore",
    "thermoMPNN": "learned stability\nscore",
    "rosetta_random": "random variants\n+ structure score",
    "rosetta_esm": "generated variants\n+ structure score",
    MD_CONTACT_Q_SOURCE: "MD contact persistence",
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
        "path": RESULTS / "fep_hot_tmselect_enc3e-5" / "scaling.json",
        "color": COL["fep"],
        "x_label": "FEP labels",
        "sample_factor": 1.0,
    },
    "MD contact-persistence labels": {
        "path": RESULTS / "hot_q_400k_tmselect" / "scaling.json",
        "color": COL["mdq"],
        "x_label": "MD contact-persistence labels",
        "sample_factor": 1.0,
    },
}

SIZE35_TM_JSON = RESULTS / "size35_tm_shared_drop005" / "scaling.json"
SIZE35_FEP_JSON = RESULTS / "size35_ddg_fep_enc3e-5" / "scaling.json"
SIZE650_TM_JSON = RESULTS / "size650_tm_shared_drop005" / "scaling.json"
SIZE650_FEP_JSON = RESULTS / "size650_ddg_fep_enc3e-5" / "scaling.json"


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


def encoder_core_rows() -> pd.DataFrame:
    records = []
    for encoder, path in [("frozen", FROZEN_SUMMARY_JSON), ("hot", SUMMARY_JSON)]:
        summary = read_json(path)
        for row in summary["rows"]:
            source = str(row["source"])
            if source not in ["Tm_only", "FEP", "rosetta", MD_CONTACT_Q_SOURCE]:
                continue
            scaling = read_json(Path(row["scaling_json"]))["scaling"][0]
            records.append(
                {
                    "encoder": encoder,
                    "source": source,
                    "test_mae": float(row["test_mae"]),
                    "ci_lo": float(scaling["ci_lo"]),
                    "ci_hi": float(scaling["ci_hi"]),
                }
            )
    return pd.DataFrame.from_records(records)


def model_size_rows(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    source_lookup = rows.set_index(rows["source"].astype(str))
    for size, condition, row in [
        ("8M", "Tm-only", source_lookup.loc["Tm_only"]),
        ("8M", "FEP", source_lookup.loc["FEP"]),
    ]:
        records.append(
            {
                "size": size,
                "condition": condition,
                "mae": float(row["test_mae"]),
                "ci_lo": float(row["ci_lo"]),
                "ci_hi": float(row["ci_hi"]),
                "abs_errors": np.asarray(row["abs_errors"], dtype=float),
            }
        )
    for size, condition, path in [
        ("35M", "Tm-only", SIZE35_TM_JSON),
        ("35M", "FEP", SIZE35_FEP_JSON),
        ("650M", "Tm-only", SIZE650_TM_JSON),
        ("650M", "FEP", SIZE650_FEP_JSON),
    ]:
        point = read_json(path)["scaling"][0]
        records.append(
            {
                "size": size,
                "condition": condition,
                "mae": float(point["mae"]),
                "ci_lo": float(point["ci_lo"]),
                "ci_hi": float(point["ci_hi"]),
                "abs_errors": np.asarray(point["abs_errors"], dtype=float),
            }
        )
    out = pd.DataFrame.from_records(records)
    out["size"] = pd.Categorical(out["size"], ["8M", "35M", "650M"], ordered=True)
    out["condition"] = pd.Categorical(out["condition"], ["Tm-only", "FEP"], ordered=True)
    return out.sort_values(["size", "condition"]).reset_index(drop=True)


def paired_delta_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 10000) -> tuple[float, float, float]:
    rng = np.random.default_rng(42)
    n = len(a)
    idx = rng.integers(0, n, size=(n_boot, n))
    delta = np.mean(b[idx], axis=1) - np.mean(a[idx], axis=1)
    lo, hi = np.percentile(delta, [5, 95])
    return float(np.mean(delta)), float(lo), float(hi)


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
    box(ax, (0.07, 0.23), (0.27, 0.16), "computed task\nstability label", fc=COL["soft_green"], ec=COL["fep"], weight="bold", fontsize=7.2)
    box(ax, (0.43, 0.43), (0.22, 0.18), "shared\nsequence\nrepresentation", fc=COL["soft_blue"], ec=COL["design"], weight="bold", fontsize=7.8)
    box(ax, (0.74, 0.64), (0.20, 0.14), "Tm head", fc="white", ec=COL["baseline"], weight="bold")
    box(ax, (0.74, 0.25), (0.20, 0.14), "source\nhead", fc="white", ec=COL["fep"], weight="bold")
    arrow(ax, (0.34, 0.72), (0.43, 0.54), color=COL["baseline"])
    arrow(ax, (0.34, 0.31), (0.43, 0.50), color=COL["fep"])
    arrow(ax, (0.65, 0.54), (0.74, 0.71), color=COL["baseline"])
    arrow(ax, (0.65, 0.50), (0.74, 0.32), color=COL["fep"])
    ax.text(0.20, 0.55, "57 training\nlabels", ha="center", va="center", fontsize=7.6, color=COL["baseline"])
    ax.text(0.20, 0.13, "larger labeled\nvariant sets", ha="center", va="center", fontsize=7.6, color=COL["fep"])
    ax.text(0.50, 0.12, "transfer learning maps computed-label signal into the Tm predictor", ha="center", fontsize=7.7, color=COL["black"])
    panel_label(ax, "A")

    ax = axes[0, 1]
    hide_axes(ax)
    box(ax, (0.06, 0.40), (0.20, 0.20), "sequence", fc=COL["soft_gray"])
    box(ax, (0.36, 0.39), (0.22, 0.22), "shared\nencoder", fc=COL["soft_blue"], weight="bold")
    box(ax, (0.70, 0.63), (0.22, 0.16), "Tm\nprediction", fc=COL["soft_gray"])
    box(ax, (0.70, 0.22), (0.22, 0.16), "computed-label\nprediction", fc=COL["soft_green"], fontsize=7.2)
    arrow(ax, (0.26, 0.50), (0.36, 0.50))
    arrow(ax, (0.58, 0.50), (0.70, 0.71))
    arrow(ax, (0.58, 0.50), (0.70, 0.30))
    box(ax, (0.19, 0.08), (0.64, 0.10), "model selection uses the experimental validation set", fc="white", ec=COL["fep"], fontsize=7.4)
    panel_label(ax, "B")

    ax = axes[1, 0]
    hide_axes(ax)
    categories = [
        ("mutation effects", ["mutation free energy (FEP)", "structure-based mutation score", "learned stability-change score"], COL["soft_green"], COL["fep"]),
        ("designed variants", ["language-model variants + structure score", "random variants + structure score"], COL["soft_blue"], COL["design"]),
        ("structural dynamics", ["contact persistence from MD"], COL["soft_red"], COL["mdq"]),
    ]
    y0 = 0.68
    for i, (title, items, fc, ec) in enumerate(categories):
        y = y0 - i * 0.27
        box(ax, (0.07, y), (0.27, 0.14), title, fc=fc, ec=ec, weight="bold", fontsize=7.2)
        ax.text(0.40, y + 0.07, "\n".join(items), va="center", fontsize=7.3, color=COL["black"])
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
    panel_label(ax, "D")

    save_figure(fig, "fig_outline01_concept_protocol")


def fig02_source_screen(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), constrained_layout=True)

    ax = axes[0, 0]
    tm_scale = load_scaling(SCALING_CURVES["Tm-only labels"]["path"])
    ax.fill_between(tm_scale["x"], tm_scale["ci_lo"], tm_scale["ci_hi"], color=COL["baseline"], alpha=0.15, lw=0)
    ax.plot(tm_scale["x"], tm_scale["mae"], marker="o", color=COL["baseline"], label="Tm labels only")
    ax.set_xlabel("experimental Tm labels")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(8, 60)
    ax.set_xticks([10, 20, 30, 40, 57])
    ax.set_xticklabels(["10", "20", "30", "40", "57"])
    ax.set_ylim(6.35, 7.85)
    polish(ax, "both")
    panel_label(ax, "A")

    ax = axes[0, 1]
    baseline = rows.loc[rows["source"].astype(str) == "Tm_only"].iloc[0]["test_mae"]
    fep_scale = load_scaling(SCALING_CURVES["FEP mutation-effect labels"]["path"])
    ax.axhline(baseline, color=COL["baseline"], linestyle="--", linewidth=1.1, label="Tm labels only")
    ax.fill_between(fep_scale["x"], fep_scale["ci_lo"], fep_scale["ci_hi"], color=COL["fep"], alpha=0.15, lw=0)
    ax.plot(fep_scale["x"], fep_scale["mae"], marker="o", color=COL["fep"], label="mutation free energy")
    best_idx = int(fep_scale["mae"].argmin())
    ax.scatter([fep_scale.loc[best_idx, "x"]], [fep_scale.loc[best_idx, "mae"]], s=54, color=COL["fep"], edgecolor="white", zorder=5)
    ax.text(0.96, 0.10, "best at largest\nlabel setting", transform=ax.transAxes, ha="right", va="bottom", fontsize=7.2, color=COL["fep"])
    ax.set_xscale("log")
    ax.set_xticks([10, 40, 80, 160, 320])
    ax.set_xticklabels(["10", "40", "80", "160", "320"])
    ax.set_xlabel("mutation free-energy labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_ylim(6.18, 6.75)
    ax.legend(frameon=False, loc="upper left")
    polish(ax, "both")
    panel_label(ax, "B")

    ax = axes[1, 0]
    md_scale = load_scaling(SCALING_CURVES["MD contact-persistence labels"]["path"])
    ax.axhline(baseline, color=COL["baseline"], linestyle="--", linewidth=1.1, label="Tm labels only")
    ax.fill_between(md_scale["x"], md_scale["ci_lo"], md_scale["ci_hi"], color=COL["mdq"], alpha=0.15, lw=0)
    ax.plot(md_scale["x"], md_scale["mae"], marker="o", color=COL["mdq"], label="MD contact persistence")
    best_idx = int(md_scale["mae"].argmin())
    ax.scatter([md_scale.loc[best_idx, "x"]], [md_scale.loc[best_idx, "mae"]], s=54, color=COL["mdq"], edgecolor="white", zorder=5)
    ax.set_xscale("log")
    ax.set_xticks([10, 40, 80, 160, 320, 640])
    ax.set_xticklabels(["10", "40", "80", "160", "320", "640"])
    ax.set_xlabel("MD contact-persistence labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_ylim(6.55, 7.05)
    ax.legend(frameon=False, loc="upper right")
    polish(ax, "both")
    panel_label(ax, "C")

    ax = axes[1, 1]
    labels = ["Tm labels\nonly", "mutation free\nenergy", "MD contact\npersistence"]
    vals = [float(tm_scale.iloc[-1]["mae"]), float(fep_scale["mae"].min()), float(md_scale["mae"].min())]
    colors = [COL["baseline"], COL["fep"], COL["mdq"]]
    xpos = np.arange(len(vals))
    ax.bar(xpos, vals, color=colors, width=0.62)
    for x, yv in zip(xpos, vals):
        ax.text(x, yv + 0.035, f"{yv:.2f}", ha="center", va="bottom", fontsize=7.4)
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels)
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_ylim(6.15, 6.75)
    polish(ax, "y")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline02_source_screen")


def fig03_design_bridge(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(7.4, 6.7), constrained_layout=True)

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
    ax.set_xlabel("MAE change vs Tm labels only (deg C)")
    ax.set_xlim(-0.55, 0.32)
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[0, 2]
    size_df = model_size_rows(rows)
    sizes = ["8M", "35M", "650M"]
    size_xpos = np.arange(len(sizes))
    offsets = {"Tm-only": -0.09, "FEP": 0.09}
    for condition, color, marker, label in [("Tm-only", COL["baseline"], "s", "Tm labels only"), ("FEP", COL["fep"], "o", "mutation free energy")]:
        subset = size_df[size_df["condition"] == condition].set_index("size")
        vals = np.asarray([float(subset.loc[s, "mae"]) for s in sizes])
        err_lo = np.asarray([float(subset.loc[s, "mae"] - subset.loc[s, "ci_lo"]) for s in sizes])
        err_hi = np.asarray([float(subset.loc[s, "ci_hi"] - subset.loc[s, "mae"]) for s in sizes])
        ax.errorbar(
            size_xpos + offsets[condition],
            vals,
            yerr=[err_lo, err_hi],
            marker=marker,
            markersize=4.5,
            linewidth=1.0,
            capsize=2,
            color=color,
            label=label,
            zorder=3,
        )
        for x, value in zip(size_xpos + offsets[condition], vals):
            ax.text(x, value + 0.045, f"{value:.2f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(size_xpos)
    ax.set_xticklabels(sizes)
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_ylim(6.05, 7.12)
    ax.legend(frameon=False, loc="upper left")
    polish(ax, "y")
    panel_label(ax, "C")

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
    ax.set_xlabel("selected validation-set MAE (deg C)")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(5.72, 6.28)
    ax.set_ylim(6.18, 6.88)
    polish(ax, "both")
    panel_label(ax, "D")

    ax = axes[1, 1]
    core = encoder_core_rows()
    core_sources = ["Tm_only", "FEP", "rosetta", MD_CONTACT_Q_SOURCE]
    xpos = np.arange(len(core_sources))
    width = 0.34
    for offset, encoder, hatch, alpha in [(-width / 2, "frozen", "///", 0.68), (width / 2, "hot", "", 0.95)]:
        subset = core[core["encoder"] == encoder].set_index("source")
        vals = np.asarray([float(subset.loc[s, "test_mae"]) for s in core_sources])
        err_lo = np.asarray([float(subset.loc[s, "test_mae"] - subset.loc[s, "ci_lo"]) for s in core_sources])
        err_hi = np.asarray([float(subset.loc[s, "ci_hi"] - subset.loc[s, "test_mae"]) for s in core_sources])
        bars = ax.bar(
            xpos + offset,
            vals,
            width=width,
            color=[SOURCE_COLOR[s] for s in core_sources],
            edgecolor=COL["black"],
            linewidth=0.4,
            hatch=hatch,
            alpha=alpha,
            label={"frozen": "frozen encoder", "hot": "updated encoder"}[encoder],
            zorder=3,
        )
        ax.errorbar(xpos + offset, vals, yerr=[err_lo, err_hi], fmt="none", ecolor=COL["black"], elinewidth=0.7, capsize=2, zorder=4)
        for bar, value in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.035, f"{value:.2f}", ha="center", va="bottom", fontsize=6.4, rotation=90)
    ax.set_xticks(xpos)
    ax.set_xticklabels(["Tm labels\nonly", "mutation\nfree energy", "structure\nscore", "MD\ncontact"], fontsize=6.8)
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_ylim(6.05, 7.62)
    ax.legend(frameon=False, loc="upper right")
    polish(ax, "y")
    panel_label(ax, "E")

    ax = axes[1, 2]
    delta_records = []
    for size in sizes:
        subset = size_df[size_df["size"] == size].set_index("condition")
        mean, lo, hi = paired_delta_ci(
            np.asarray(subset.loc["Tm-only", "abs_errors"], dtype=float),
            np.asarray(subset.loc["FEP", "abs_errors"], dtype=float),
        )
        delta_records.append((size, mean, lo, hi))
    vals = np.asarray([r[1] for r in delta_records])
    err_lo = vals - np.asarray([r[2] for r in delta_records])
    err_hi = np.asarray([r[3] for r in delta_records]) - vals
    bars = ax.bar(
        size_xpos,
        vals,
        width=0.52,
        color=COL["fep"],
        edgecolor=COL["black"],
        linewidth=0.5,
        zorder=3,
    )
    ax.errorbar(size_xpos, vals, yerr=[err_lo, err_hi], fmt="none", ecolor=COL["black"], elinewidth=0.7, capsize=2, zorder=4)
    ax.axhline(0, color=COL["black"], linewidth=0.9)
    for bar, value in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, value - 0.035, f"{value:+.2f}", ha="center", va="top", fontsize=7.0)
    ax.set_xticks(size_xpos)
    ax.set_xticklabels(sizes)
    ax.set_ylabel("FEP minus Tm-label-only MAE (deg C)")
    ax.set_ylim(-0.55, 0.12)
    polish(ax, "y")
    panel_label(ax, "F")

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
    ax.text(0.50, 0.09, "why mutation free-energy labels transfer", ha="center", fontsize=8, color=COL["gray"])
    panel_label(ax, "A")

    ax = axes[0, 1]
    keys = ["FEP_minus_Tm_only", f"{MD_CONTACT_Q_SOURCE}_minus_Tm_only"]
    labs = ["mutation free energy\n(FEP)", "MD contact persistence"]
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
    ax.set_xlabel("MAE change vs Tm labels only (deg C)")
    ax.set_xlim(-0.55, 0.30)
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
    box(ax, (0.12, 0.13), (0.76, 0.13), "contact persistence = retained native contacts\n400 K trajectory, final 30 ns average", fc="white", ec=COL["mdq"], fontsize=7.4)
    panel_label(ax, "C")

    ax = axes[1, 1]
    hide_axes(ax)
    box(ax, (0.06, 0.64), (0.88, 0.16), "Mutation free-energy labels encode local stability changes\nthat are close to the target phenotype.", fc=COL["soft_green"], ec=COL["fep"], fontsize=7.8, weight="bold")
    box(ax, (0.06, 0.39), (0.88, 0.16), "MD contact persistence summarizes structural dynamics;\nit did not improve final Tm prediction here.", fc=COL["soft_red"], ec=COL["mdq"], fontsize=8.0)
    box(ax, (0.06, 0.14), (0.88, 0.16), "Take-home: useful simulation labels must carry\ninformation relevant to Tm generalization.", fc="white", ec=COL["black"], fontsize=8.0)
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
