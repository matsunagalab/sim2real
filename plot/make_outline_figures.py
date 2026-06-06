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
from matplotlib.lines import Line2D
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
    "FEP": "FEP mutation\nfree energy",
    "rosetta": "Rosetta mutation\nscore",
    "thermoMPNN": "ThermoMPNN\nstability score",
    "rosetta_random": "random variants\n+ Rosetta",
    "rosetta_esm": "ESM2-proposed\nvariants + Rosetta",
    MD_CONTACT_Q_SOURCE: "MD Q-value",
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
    "MD Q-value labels": {
        "path": RESULTS / "hot_q_400k_tmselect" / "scaling.json",
        "color": COL["mdq"],
        "x_label": "MD Q-value labels",
        "sample_factor": 1.0,
    },
}

SIZE35_TM_JSON = RESULTS / "size35_tm_shared_drop005" / "scaling.json"
SIZE35_FEP_JSON = RESULTS / "size35_ddg_fep_enc3e-5" / "scaling.json"
SIZE650_TM_JSON = RESULTS / "size650_tm_shared_drop005" / "scaling.json"
SIZE650_FEP_JSON = RESULTS / "size650_ddg_fep_enc3e-5" / "scaling.json"

DESCRIPTOR_CONTROL_SPECS = [
    ("Tm labels only", RESULTS / "final_tm_residual_enc3e-4" / "scaling.json", COL["baseline"], "s"),
    ("raw MD Q-value", RESULTS / "final_residual_q_hphil_400k" / "scaling.json", COL["mdq"], "o"),
    ("Q-value slope", RESULTS / "final_residual_q_slope_400k" / "scaling.json", COL["mdq"], "D"),
    ("disulfide-distance\nfluctuation", RESULTS / "final_residual_ss_dist_std" / "scaling.json", COL["design"], "o"),
    ("CDR3 length", RESULTS / "final_residual_cdr3_len" / "scaling.json", COL["thermo"], "o"),
    ("CDR3 residue\nfluctuation", RESULTS / "final_residual_rmsf_cdr3" / "scaling.json", COL["rosetta"], "o"),
]


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


def descriptor_control_rows() -> pd.DataFrame:
    records = []
    for label, path, color, marker in DESCRIPTOR_CONTROL_SPECS:
        if not path.exists():
            continue
        point = read_json(path)["scaling"][0]
        records.append(
            {
                "label": label,
                "mae": float(point["mae"]),
                "ci_lo": float(point["ci_lo"]),
                "ci_hi": float(point["ci_hi"]),
                "color": color,
                "marker": marker,
            }
        )
    return pd.DataFrame.from_records(records).sort_values("mae").reset_index(drop=True)


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
        f"({label.lower()})",
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
            if ext == "svg":
                path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    plt.close(fig)
    print(f"wrote {PLOT_DIR / (stem + '.pdf')}")


def horizontal_interval(ax, y, mid, lo, hi, color, marker="o", label=None, zorder=3):
    ax.plot([lo, hi], [y, y], color=color, linewidth=2.0, solid_capstyle="round", zorder=zorder)
    ax.scatter([mid], [y], s=34, color=color, edgecolor="white", linewidth=0.6, zorder=zorder + 1, marker=marker, label=label)


def scaling_errorbar(ax, data: pd.DataFrame, color: str, label: str, marker: str = "o") -> None:
    y = data["mae"].to_numpy(float)
    yerr = np.vstack(
        [
            y - data["ci_lo"].to_numpy(float),
            data["ci_hi"].to_numpy(float) - y,
        ]
    )
    ax.errorbar(
        data["x"],
        y,
        yerr=yerr,
        fmt=f"{marker}-",
        color=color,
        ecolor=color,
        elinewidth=0.9,
        capsize=0.0,
        capthick=0.0,
        alpha=0.24,
        markerfacecolor=color,
        markeredgecolor="white",
        markeredgewidth=0.5,
        label="_nolegend_",
        zorder=2,
    )
    ax.plot(data["x"], y, marker=marker, color=color, label=label, zorder=4)


def ecdf_xy(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(x) + 1, dtype=float) / len(x)
    return x, y


def fig01_concept_protocol(rows: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.9), constrained_layout=True)

    ax = axes[0, 0]
    hide_axes(ax)
    box(ax, (0.07, 0.66), (0.28, 0.15), "target task\nmeasured Tm", fc=COL["soft_gray"], ec=COL["baseline"], weight="bold")
    box(ax, (0.07, 0.22), (0.28, 0.15), "computed task\nstability label", fc=COL["soft_green"], ec=COL["fep"], weight="bold", fontsize=7.2)
    box(ax, (0.43, 0.43), (0.24, 0.18), "shared\nsequence\nrepresentation", fc=COL["soft_blue"], ec=COL["design"], weight="bold", fontsize=7.7)
    box(ax, (0.76, 0.66), (0.19, 0.13), "Tm head", fc="white", ec=COL["baseline"], weight="bold")
    box(ax, (0.76, 0.24), (0.19, 0.13), "source\nhead", fc="white", ec=COL["fep"], weight="bold")
    arrow(ax, (0.35, 0.73), (0.43, 0.55), color=COL["baseline"])
    arrow(ax, (0.35, 0.30), (0.43, 0.49), color=COL["fep"])
    arrow(ax, (0.67, 0.55), (0.76, 0.72), color=COL["baseline"])
    arrow(ax, (0.67, 0.49), (0.76, 0.31), color=COL["fep"])
    ax.text(0.21, 0.57, "57 training labels", ha="center", va="center", fontsize=7.4, color=COL["baseline"])
    ax.text(0.21, 0.13, "larger computed-label sets", ha="center", va="center", fontsize=7.4, color=COL["fep"])
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
    box(ax, (0.23, 0.07), (0.56, 0.13), "settings selected on\nexperimental validation data", fc="white", ec=COL["fep"], fontsize=7.0)
    panel_label(ax, "B")

    ax = axes[1, 0]
    hide_axes(ax)
    categories = [
        ("mutation effects", ["FEP mutation free energy", "Rosetta mutation score", "ThermoMPNN stability score"], COL["soft_green"], COL["fep"]),
        ("variant proposals", ["ESM2-proposed variants + Rosetta", "random variants + Rosetta"], COL["soft_blue"], COL["design"]),
        ("structural dynamics", ["MD Q-value from native contacts"], COL["soft_red"], COL["mdq"]),
    ]
    y0 = 0.70
    for i, (title, items, fc, ec) in enumerate(categories):
        y = y0 - i * 0.27
        box(ax, (0.06, y), (0.32, 0.13), title, fc=fc, ec=ec, weight="bold", fontsize=6.8)
        ax.text(0.42, y + 0.065, "\n".join(items), va="center", fontsize=7.2, color=COL["black"])
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
    scaling_ylim = (5.75, 7.90)
    scaling_yticks = [6.0, 6.5, 7.0, 7.5]
    x_ticks = [10, 20, 40, 80, 160, 320, 640]

    tm_scale = load_scaling(SCALING_CURVES["Tm-only labels"]["path"])
    baseline = rows.loc[rows["source"].astype(str) == "Tm_only"].iloc[0]["test_mae"]
    fep_scale = load_scaling(SCALING_CURVES["FEP mutation-effect labels"]["path"])
    md_scale = load_scaling(SCALING_CURVES["MD Q-value labels"]["path"])
    curves = [
        ("Tm labels only", tm_scale, COL["baseline"], "s"),
        ("mutation free energy", fep_scale, COL["fep"], "o"),
        ("MD Q-value", md_scale, COL["mdq"], "o"),
    ]

    ax = axes[0, 0]
    for label, curve, color, marker in curves:
        scaling_errorbar(ax, curve, color, label, marker=marker)
    ax.set_xscale("log")
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks])
    ax.set_xlabel("labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(8, 760)
    ax.set_ylim(*scaling_ylim)
    ax.set_yticks(scaling_yticks)
    ax.legend(frameon=False, loc="upper right", handlelength=1.8)
    polish(ax, "both")
    panel_label(ax, "A")

    ax = axes[0, 1]
    ax.axhline(baseline, color=COL["baseline"], linestyle="--", linewidth=1.1, label="Tm labels only")
    scaling_errorbar(ax, fep_scale, COL["fep"], "mutation free energy")
    scaling_errorbar(ax, md_scale, COL["mdq"], "MD Q-value")
    best_idx = int(fep_scale["mae"].argmin())
    ax.scatter([fep_scale.loc[best_idx, "x"]], [fep_scale.loc[best_idx, "mae"]], s=54, color=COL["fep"], edgecolor="white", zorder=5)
    ax.text(0.96, 0.08, "best at largest\nlabel setting", transform=ax.transAxes, ha="right", va="bottom", fontsize=7.0, color=COL["fep"])
    ax.set_xscale("log")
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks])
    ax.set_xlabel("computed labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(8, 760)
    ax.set_ylim(*scaling_ylim)
    ax.set_yticks(scaling_yticks)
    ax.legend(frameon=False, loc="upper right", handlelength=1.8)
    polish(ax, "both")
    panel_label(ax, "B")

    ax = axes[1, 0]
    for label, curve, color, marker in curves:
        delta = curve.copy()
        delta["mae"] = delta["mae"] - baseline
        delta["ci_lo"] = delta["ci_lo"] - baseline
        delta["ci_hi"] = delta["ci_hi"] - baseline
        scaling_errorbar(ax, delta, color, label, marker=marker)
    ax.axhline(0, color=COL["black"], linewidth=0.9)
    ax.set_xscale("log")
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks])
    ax.set_xlabel("labels used")
    ax.set_ylabel("MAE change vs Tm labels only (deg C)")
    ax.set_xlim(8, 760)
    ax.set_ylim(-0.95, 1.35)
    ax.set_yticks([-0.5, 0.0, 0.5, 1.0])
    ax.legend(frameon=False, loc="upper right", handlelength=1.8)
    polish(ax, "both")
    panel_label(ax, "C")

    ax = axes[1, 1]
    labels = ["Tm labels\nonly", "FEP mutation\nfree energy", "MD\nQ-value"]
    best_points = [
        ("Tm labels\nonly", tm_scale.iloc[-1], COL["baseline"], "s"),
        ("FEP mutation\nfree energy", fep_scale.iloc[int(fep_scale["mae"].argmin())], COL["fep"], "o"),
        ("MD\nQ-value", md_scale.iloc[int(md_scale["mae"].argmin())], COL["mdq"], "o"),
    ]
    y = np.arange(len(best_points))
    for i, (label, point, col, marker) in enumerate(best_points):
        horizontal_interval(ax, i, point["mae"], point["ci_lo"], point["ci_hi"], col, marker=marker)
        ax.text(point["ci_hi"] + 0.015, i, f"{point['mae']:.2f}", va="center", fontsize=7.3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(6.05, 6.85)
    polish(ax, "x")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline02_source_screen")


def fig03_design_bridge(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), constrained_layout=True)
    row_lookup = rows.set_index(rows["source"].astype(str))
    sim_sources = ["Tm_only", "FEP", MD_CONTACT_Q_SOURCE]

    ax = axes[0, 0]
    ordered = row_lookup.loc[sim_sources].reset_index(drop=True)
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
    ax.set_xlim(5.95, 6.95)
    polish(ax, "x")
    panel_label(ax, "A")

    ax = axes[0, 1]
    tm_abs = np.asarray(row_lookup.loc["Tm_only", "abs_errors"], dtype=float)
    fep_abs = np.asarray(row_lookup.loc["FEP", "abs_errors"], dtype=float)
    md_abs = np.asarray(row_lookup.loc[MD_CONTACT_Q_SOURCE, "abs_errors"], dtype=float)
    delta_data = [fep_abs - tm_abs, md_abs - tm_abs]
    parts = ax.violinplot(delta_data, positions=[0, 1], vert=False, widths=0.72, showextrema=False)
    for body, color in zip(parts["bodies"], [COL["fep"], COL["mdq"]]):
        body.set_facecolor(color)
        body.set_edgecolor("none")
        body.set_alpha(0.24)
    rng = np.random.default_rng(7)
    for i, (delta, color) in enumerate(zip(delta_data, [COL["fep"], COL["mdq"]])):
        y_jitter = np.full(len(delta), i) + rng.uniform(-0.15, 0.15, len(delta))
        ax.scatter(delta, y_jitter, s=7, color=color, alpha=0.15, edgecolor="none", rasterized=True)
    for i, source in enumerate(["FEP", MD_CONTACT_Q_SOURCE]):
        comp = paired[paired_key(source)]
        horizontal_interval(
            ax,
            i,
            comp["delta_mae"],
            comp["delta_ci_lo"],
            comp["delta_ci_hi"],
            SOURCE_COLOR[source],
            zorder=6,
        )
        ax.text(
            comp["delta_mae"] + 0.36,
            i,
            f"{comp['delta_mae']:+.2f}",
            va="center",
            ha="left",
            fontsize=7.2,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.6),
            zorder=8,
        )
    ax.axvline(0, color=COL["black"], linewidth=0.9)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([SOURCE_LABEL[s] for s in ["FEP", MD_CONTACT_Q_SOURCE]])
    ax.invert_yaxis()
    ax.set_xlabel("error change vs Tm labels only (deg C)")
    ax.set_xlim(-9, 9)
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[1, 0]
    core = encoder_core_rows()
    core_sources = ["Tm_only", "FEP", MD_CONTACT_Q_SOURCE]
    ypos = np.arange(len(core_sources))
    y_offsets = {"frozen": -0.13, "hot": 0.13}
    markers = {"frozen": "s", "hot": "o"}
    encoder_labels = {"frozen": "frozen encoder", "hot": "hot encoder"}
    for encoder in ["frozen", "hot"]:
        subset = core[core["encoder"] == encoder].set_index("source")
        for i, source in enumerate(core_sources):
            row = subset.loc[source]
            horizontal_interval(
                ax,
                i + y_offsets[encoder],
                float(row["test_mae"]),
                float(row["ci_lo"]),
                float(row["ci_hi"]),
                SOURCE_COLOR[source],
                marker=markers[encoder],
            )
    ax.set_yticks(ypos)
    ax.set_yticklabels(["Tm labels\nonly", "FEP mutation\nfree energy", "MD Q-value"])
    ax.invert_yaxis()
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(5.95, 7.70)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="s", color=COL["black"], linestyle="none", markersize=5, label=encoder_labels["frozen"]),
            Line2D([0], [0], marker="o", color=COL["black"], linestyle="none", markersize=5, label=encoder_labels["hot"]),
        ],
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.55, 1.01),
        ncol=2,
        borderaxespad=0.0,
    )
    polish(ax, "x")
    panel_label(ax, "C")

    ax = axes[1, 1]
    descriptor_rows = descriptor_control_rows()
    y = np.arange(len(descriptor_rows))
    for i, row in descriptor_rows.iterrows():
        horizontal_interval(
            ax,
            i,
            row["mae"],
            row["ci_lo"],
            row["ci_hi"],
            row["color"],
            marker=row["marker"],
        )
        ax.text(row["ci_hi"] + 0.025, i, f"{row['mae']:.2f}", va="center", fontsize=6.8)
    ax.axvline(float(row_lookup.loc["FEP", "test_mae"]), color=COL["fep"], linewidth=1.0, linestyle="--")
    ax.text(
        float(row_lookup.loc["FEP", "test_mae"]) + 0.015,
        -0.52,
        "FEP",
        color=COL["fep"],
        fontsize=6.8,
        ha="left",
        va="center",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(descriptor_rows["label"])
    ax.invert_yaxis()
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(6.0, 7.45)
    polish(ax, "x")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline03_design_bridge")


def fig04_boundary_mdq(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.4, 5.35),
        constrained_layout=True,
        gridspec_kw={"height_ratios": [1.0, 0.68]},
    )
    row_lookup = rows.set_index(rows["source"].astype(str))
    design_sources = ["Tm_only", "FEP", "rosetta_esm", "thermoMPNN", "rosetta_random", "rosetta"]

    ax = axes[0, 0]
    ordered = row_lookup.loc[design_sources].reset_index(drop=True)
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
        ax.text(row["ci_hi"] + 0.030, i, f"{row['test_mae']:.2f}", va="center", fontsize=7.3)
    ax.set_yticks(y)
    ax.set_yticklabels(ordered["label_plot"])
    ax.invert_yaxis()
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(5.72, 7.05)
    polish(ax, "x")
    panel_label(ax, "A")

    ax = axes[0, 1]
    delta_sources = [s for s in design_sources if s != "Tm_only"]
    y = np.arange(len(delta_sources))
    for i, source in enumerate(delta_sources):
        comp = paired[paired_key(source)]
        horizontal_interval(ax, i, comp["delta_mae"], comp["delta_ci_lo"], comp["delta_ci_hi"], SOURCE_COLOR[source], zorder=6)
        ax.text(comp["delta_ci_hi"] + 0.016, i, f"{comp['delta_mae']:+.2f}", va="center", fontsize=7.2)
    ax.axvline(0, color=COL["black"], linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([SOURCE_LABEL[s] for s in delta_sources])
    ax.invert_yaxis()
    ax.set_xlabel("MAE change vs Tm labels only (deg C)")
    ax.set_xlim(-0.55, 0.15)
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[1, 0]
    random_abs = np.asarray(row_lookup.loc["rosetta_random", "abs_errors"], dtype=float)
    esm_abs = np.asarray(row_lookup.loc["rosetta_esm", "abs_errors"], dtype=float)
    mean, lo, hi = paired_delta_ci(random_abs, esm_abs)
    horizontal_interval(ax, 0, mean, lo, hi, COL["design"], zorder=4)
    ax.axvline(0, color=COL["black"], linewidth=0.9)
    ax.set_yticks([0])
    ax.set_yticklabels(["ESM2-proposed\nminus random"])
    ax.set_xlabel("ESM2-proposed minus random MAE (deg C)")
    ax.set_xlim(-0.30, 0.20)
    ax.set_ylim(-0.55, 0.55)
    ax.text(mean, -0.22, f"{mean:+.2f}", ha="center", va="top", fontsize=7.3, color=COL["design"])
    ax.text(
        0.02,
        0.88,
        "negative values favor\nESM2-proposed variants",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.2,
        color=COL["gray"],
    )
    polish(ax, "x")
    panel_label(ax, "C")

    ax = axes[1, 1]
    hide_axes(ax)
    box(ax, (0.05, 0.60), (0.25, 0.18), "sequence\nproposal", fc=COL["soft_blue"], ec=COL["design"], weight="bold", fontsize=7.2)
    box(ax, (0.375, 0.60), (0.25, 0.18), "physics-based\nscoring", fc=COL["soft_orange"], ec=COL["rosetta"], weight="bold", fontsize=7.2)
    box(ax, (0.70, 0.60), (0.25, 0.18), "Tm\npredictor", fc=COL["soft_gray"], ec=COL["baseline"], weight="bold", fontsize=7.2)
    box(ax, (0.375, 0.24), (0.25, 0.18), "future\nexperimental\nfeedback", fc="white", ec=COL["black"], fontsize=7.0)
    arrow(ax, (0.30, 0.69), (0.375, 0.69), color=COL["design"])
    arrow(ax, (0.625, 0.69), (0.70, 0.69), color=COL["rosetta"])
    arrow(ax, (0.82, 0.60), (0.54, 0.42), color=COL["baseline"])
    arrow(ax, (0.40, 0.33), (0.18, 0.60), color=COL["black"], style="--")
    ax.text(0.50, 0.08, "current study tests the supervised-scoring step,\nnot a closed-loop reinforcement-learning experiment",
            ha="center", va="center", fontsize=7.0, color=COL["gray"])
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
