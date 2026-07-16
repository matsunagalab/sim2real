#!/usr/bin/env python3
"""Build the main comparison figures for the current paper.

Figure 1 can also be generated for reference, but the manuscript currently uses
an author-edited Figure 1. Pass ``--skip-fig1`` to leave that figure untouched.

Outputs are written to both ``plot/`` and ``paper/tex/figures/`` as PDF, SVG,
and high-resolution PNG files.
"""

from __future__ import annotations

import argparse
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
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Patch


REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
# Tuned two-axis summaries (built by plot/build_tuned_summaries.py from the
# final_* staged-HPO runs). HOT = encoder unfrozen; FROZEN = encoder frozen.
SUMMARY_JSON = RESULTS / "tuned_rep" / "hot_summary.json"
FROZEN_SUMMARY_JSON = RESULTS / "tuned_rep" / "frozen_summary.json"
DIVERSE_HOT_SUMMARY_JSON = RESULTS / "source_screen" / "final_source_screen_summary.json"
DIVERSE_FROZEN_SUMMARY_JSON = RESULTS / "source_screen" / "final_frozen_core_summary.json"
DATA_MD = REPO / "data" / "md"
DATA_SRC = REPO / "data" / "source_labels"
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

# Tuned MD source: FEP-matched native-contact mutation scan (source key MD_FEP400K).
INTERNAL_MD_Q_TOKEN = "h" + "p" + "h" + "i" + "l"  # kept for the diverse-screen CSVs (Fig 3)
MD_CONTACT_Q_SOURCE = "MD_FEP400K"

SOURCE_ORDER = [
    "Tm_only",
    "FEP",
    MD_CONTACT_Q_SOURCE,
    "thermoMPNN",
    "rosetta_random",
    "rosetta",
    "rosetta_esm",
]

SOURCE_LABEL = {
    "Tm_only": "Tm labels only",
    "FEP": "FEP mutation\nfree energy",
    MD_CONTACT_Q_SOURCE: "MD native-contact\n(matched scan)",
    "rosetta": "Rosetta mutation\nscore",
    "thermoMPNN": "ThermoMPNN\nstability score",
    "rosetta_random": "random variants\n+ Rosetta",
    "rosetta_esm": "ESM2-proposed\nvariants + Rosetta",
}

SOURCE_COLOR = {
    "Tm_only": COL["baseline"],
    "FEP": COL["fep"],
    MD_CONTACT_Q_SOURCE: COL["mdq"],
    "thermoMPNN": COL["thermo"],
    "rosetta_random": COL["rosetta"],
    "rosetta": "#B9770E",
    "rosetta_esm": COL["design"],
}

# Fig. 2a: tuned FROZEN computational-label count sweeps (internally consistent —
#   all frozen). Tm-only shown as its tuned frozen baseline (dashed line). In the
#   frozen regime both FEP and the FEP-matched MD label scale below the Tm-only
#   baseline, i.e. they beat training on experimental Tm labels alone.
FIG2A_TM_BASELINE = RESULTS / "tuned_rep" / "Tm_only_frozen" / "scaling.json"
FIG2A_CURVES = [
    ("FEP mutation free energy", RESULTS / "final_fep_frozen" / "scaling.json", COL["fep"], "o"),
    ("MD native-contact (matched scan)", RESULTS / "final_mdq_frozen" / "scaling.json", COL["mdq"], "D"),
]

SIZE35_TM_JSON = RESULTS / "size35_tm_shared_drop005" / "scaling.json"
SIZE35_FEP_JSON = RESULTS / "size35_ddg_fep_enc3e-5" / "scaling.json"
SIZE650_TM_JSON = RESULTS / "size650_tm_shared_drop005" / "scaling.json"
SIZE650_FEP_JSON = RESULTS / "size650_ddg_fep_enc3e-5" / "scaling.json"

# ---------------------------------------------------------------------------
# Legacy inputs retained for the simulation-design comparison and supplementary diagnostics.
# ---------------------------------------------------------------------------
# (a) Two groups on one held-out-Tm-MAE axis. The SAME MD native-contact
#     observable is null as a diverse-nanobody screen (old hot series,
#     length-confounded) but transfers as an FEP-matched mutation scan (tuned
#     frozen). Each group carries its own matched Tm-only and FEP reference,
#     because the two experimental series sit on different absolute MAE scales.
FIG3A_DIVERSE = {
    "title": "diverse nanobody screen",
    "tm": (RESULTS / "tm_ref_hot_mtl_tmselect" / "scaling.json", "max_n"),
    "fep": (RESULTS / "fep_hot_tmselect_enc3e-5" / "scaling.json", "best_mae"),
    "md": (RESULTS / "final_residual_q_hphil_400k" / "scaling.json", "single"),
    "md_label": "MD native-contact\n(diverse screen)",
}
FIG3A_MATCHED = {
    "title": "FEP-matched mutation scan",
    "tm": (RESULTS / "tuned_rep" / "Tm_only_frozen" / "scaling.json", "single"),
    "fep": (RESULTS / "tuned_rep" / "FEP_frozen" / "scaling.json", "single"),
    "md": (RESULTS / "tuned_rep" / "MD_FEP400K_frozen" / "scaling.json", "single"),
    "md_label": "MD native-contact\n(matched scan)",
}

# (b) The length confound: MD native-contact label value vs sequence length.
FIG3B_DIVERSE_CSV = DATA_MD / f"nanobody_qvalue_{INTERNAL_MD_Q_TOKEN}_400K.csv"
FIG3B_MATCHED_CSVS = [
    DATA_MD / "study_qvalue_fep400k_1mel.csv",
    DATA_MD / "study_qvalue_fep400k_4idl.csv",
]

# (c) Label-count scaling of the matched-scan MD label (FROZEN) as paired
#     ΔMAE(n) vs the tuned frozen Tm-only baseline.
FIG3C_MD_FROZEN = RESULTS / "final_mdq_frozen" / "scaling.json"
FIG3C_TM_FROZEN = RESULTS / "final_tm_frozen" / "scaling.json"

# Fine-tuned label-count curves used in the calculated-quantity figure.
FIG3_HOT_TM_BASELINE = RESULTS / "final_tm_hot" / "scaling.json"
FIG3_HOT_CURVES = [
    ("FEP mutation free energy", RESULTS / "final_fep_hot" / "scaling.json", COL["fep"], "o"),
    ("MD native-contact (matched scan)", RESULTS / "final_mdq_hot" / "scaling.json", COL["mdq"], "D"),
]

# ---------------------------------------------------------------------------
# Fig. 4 (physical-observable axis / depth).
# ---------------------------------------------------------------------------
# Sources shown grouped by frozen vs hot encoder (representative n=320 points).
FIG4_SOURCES = ["Tm_only", "FEP", MD_CONTACT_Q_SOURCE, "rosetta", "thermoMPNN"]
# (c) design-loop feasibility: ESM2-proposed vs random variants, both scored by Rosetta.
FIG4C_SOURCES = ["rosetta_esm", "rosetta_random"]


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 600,
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10.0,
            "axes.labelsize": 9.5,
            "axes.linewidth": 0.9,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "legend.fontsize": 8.8,
            "lines.linewidth": 1.8,
            "lines.markersize": 6.0,
            "axes.spines.top": True,
            "axes.spines.right": True,
        }
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def rebase_results(path_str: str) -> Path:
    """Map an absolute scaling_json path stored on another machine
    (e.g. /home/.../results/<dir>/scaling.json) onto the local results tree,
    so figures regenerate on any checkout."""
    parts = Path(path_str).parts
    if "results" in parts:
        idx = len(parts) - 1 - parts[::-1].index("results")
        return RESULTS.joinpath(*parts[idx + 1:])
    return Path(path_str)


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
        scaling = read_json(rebase_results(row["scaling_json"]))["scaling"][0]
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


def source_screen_points(summary_rows: dict) -> dict:
    """{source: (test_mae, ci_lo, ci_hi)} from a summary's rows (any regime)."""
    out = {}
    for src, row in summary_rows.items():
        scaling = read_json(rebase_results(row["scaling_json"]))["scaling"][0]
        out[src] = (float(row["test_mae"]), float(scaling["ci_lo"]), float(scaling["ci_hi"]))
    return out


def encoder_core_rows(sources: list) -> pd.DataFrame:
    """Representative held-out test MAE + CI per source, for frozen and hot."""
    records = []
    for encoder, path in [("frozen", FROZEN_SUMMARY_JSON), ("hot", SUMMARY_JSON)]:
        summary = read_json(path)
        for row in summary["rows"]:
            source = str(row["source"])
            if source not in sources:
                continue
            scaling = read_json(rebase_results(row["scaling_json"]))["scaling"][0]
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


def encoder_delta_rows(sources: list) -> pd.DataFrame:
    """Paired ΔMAE vs Tm-only per source, for frozen and fine-tuned models."""
    records = []
    for encoder, path in [("frozen", FROZEN_SUMMARY_JSON), ("hot", SUMMARY_JSON)]:
        summary = read_json(path)
        row_map = {str(row["source"]): row for row in summary["rows"]}
        reference = select_scaling_point(
            rebase_results(row_map["Tm_only"]["scaling_json"]), "single"
        )
        for source in sources:
            candidate = select_scaling_point(
                rebase_results(row_map[source]["scaling_json"]), "single"
            )
            delta, lo, hi = paired_delta_ci(
                np.asarray(reference["abs_errors"], dtype=float),
                np.asarray(candidate["abs_errors"], dtype=float),
            )
            records.append(
                {
                    "encoder": encoder,
                    "source": source,
                    "delta_mae": delta,
                    "delta_ci_lo": lo,
                    "delta_ci_hi": hi,
                }
            )
    return pd.DataFrame.from_records(records)


def design_delta_rows() -> pd.DataFrame:
    """Native-contact transfer by data design and encoder regime.

    The diverse and matched designs were tuned in independent experimental
    series, so every effect is expressed relative to that series' own Tm-only
    reference. This avoids comparing their incompatible absolute MAE scales.
    """
    specs = [
        ("heterogeneous screen", "frozen", DIVERSE_FROZEN_SUMMARY_JSON, "MD_Q_HPHIL_400K"),
        ("heterogeneous screen", "hot", DIVERSE_HOT_SUMMARY_JSON, "MD_Q_HPHIL_400K"),
        ("matched mutation scan", "frozen", FROZEN_SUMMARY_JSON, MD_CONTACT_Q_SOURCE),
        ("matched mutation scan", "hot", SUMMARY_JSON, MD_CONTACT_Q_SOURCE),
    ]
    records = []
    for design, encoder, path, source in specs:
        summary = read_json(path)
        row_map = {str(row["source"]): row for row in summary["rows"]}
        reference = select_scaling_point(rebase_results(row_map["Tm_only"]["scaling_json"]), "single")
        candidate = select_scaling_point(rebase_results(row_map[source]["scaling_json"]), "single")
        delta, lo, hi = paired_delta_ci(
            np.asarray(reference["abs_errors"], dtype=float),
            np.asarray(candidate["abs_errors"], dtype=float),
        )
        records.append(
            {
                "design": design,
                "encoder": encoder,
                "delta_mae": delta,
                "delta_ci_lo": lo,
                "delta_ci_hi": hi,
            }
        )
    return pd.DataFrame.from_records(records)


def fep_minus_md_rows() -> pd.DataFrame:
    """Direct paired FEP-minus-matched-MD contrast in each encoder regime."""
    records = []
    for encoder in ("frozen", "hot"):
        fep = select_scaling_point(RESULTS / f"final_fep_{encoder}" / "scaling.json", "max_n")
        md = select_scaling_point(RESULTS / f"final_mdq_{encoder}" / "scaling.json", "max_n")
        delta, lo, hi = paired_delta_ci(
            np.asarray(md["abs_errors"], dtype=float),
            np.asarray(fep["abs_errors"], dtype=float),
        )
        records.append(
            {
                "encoder": encoder,
                "delta_mae": delta,
                "delta_ci_lo": lo,
                "delta_ci_hi": hi,
            }
        )
    return pd.DataFrame.from_records(records)


def model_size_rows(rows: pd.DataFrame) -> pd.DataFrame:
    row_lookup = rows.set_index(rows["source"].astype(str))
    specs = [
        ("8M", "Tm labels only", None, "Tm_only"),
        ("8M", "FEP mutation free energy", None, "FEP"),
        ("35M", "Tm labels only", SIZE35_TM_JSON, None),
        ("35M", "FEP mutation free energy", SIZE35_FEP_JSON, None),
        ("650M", "Tm labels only", SIZE650_TM_JSON, None),
        ("650M", "FEP mutation free energy", SIZE650_FEP_JSON, None),
    ]
    records = []
    for size, condition, path, source in specs:
        if path is None:
            row = row_lookup.loc[source]
            point = {
                "mae": float(row["test_mae"]),
                "ci_lo": float(row["ci_lo"]),
                "ci_hi": float(row["ci_hi"]),
            }
        else:
            point = read_json(path)["scaling"][0]
        records.append(
            {
                "esm2_size": size,
                "condition": condition,
                "test_mae": float(point["mae"]),
                "ci_lo": float(point["ci_lo"]),
                "ci_hi": float(point["ci_hi"]),
            }
        )
    return pd.DataFrame.from_records(records)


def select_scaling_point(path: Path, mode: str) -> dict:
    data = read_json(path)
    split = data.get("args", {}).get("final_eval_split")
    if split != "test":
        raise ValueError(f"{path} is not a held-out test result: final_eval_split={split!r}")
    points = data["scaling"]
    if mode == "single":
        if len(points) != 1:
            raise ValueError(f"{path} expected one scaling point, found {len(points)}")
        point = points[0]
    elif mode == "max_n":
        point = max(points, key=lambda p: float(p["n"]))
    elif mode == "best_mae":
        point = min(points, key=lambda p: float(p["mae"]))
    else:
        raise ValueError(f"unknown scaling-point selection mode: {mode}")
    if len(point.get("abs_errors", [])) != 396:
        raise ValueError(f"{path} has unexpected held-out error count: {len(point.get('abs_errors', []))}")
    return point


def fig3a_group(spec: dict) -> dict:
    """Held-out Tm MAE for the Tm-only, FEP and MD points of a Fig-3a group."""
    out = {"title": spec["title"], "md_label": spec["md_label"]}
    for key in ("tm", "fep", "md"):
        path, mode = spec[key]
        point = select_scaling_point(path, mode)
        out[key] = (float(point["mae"]), float(point["ci_lo"]), float(point["ci_hi"]))
    return out


def fig3b_confound() -> tuple:
    """MD native-contact label value vs sequence length: diverse screen vs matched scan."""
    div = pd.read_csv(FIG3B_DIVERSE_CSV)
    dlen = div["seq_len"].to_numpy(float)
    dval = div["q_value_raw"].to_numpy(float)
    r = float(np.corrcoef(dlen, dval)[0, 1])
    matched = []
    for path in FIG3B_MATCHED_CSVS:
        df = pd.read_csv(path)
        mlen = df["seq"].str.len().to_numpy(float)
        mval = df["q_value"].to_numpy(float)
        matched.append((mlen, mval, path.stem.split("_")[-1]))
    return (dlen, dval, r), matched


def fig3c_delta_by_n(n_boot: int = 10000) -> pd.DataFrame:
    """Paired ΔMAE(n) of the matched MD label (frozen) vs the frozen Tm-only baseline."""
    tm = np.asarray(select_scaling_point(FIG3C_TM_FROZEN, "single")["abs_errors"], dtype=float)
    md = read_json(FIG3C_MD_FROZEN)
    records = []
    for point in md["scaling"]:
        a = np.asarray(point["abs_errors"], dtype=float)
        delta, lo, hi = paired_delta_ci(tm, a, n_boot=n_boot)
        records.append({"n": float(point["n"]), "delta_mae": delta, "delta_ci_lo": lo, "delta_ci_hi": hi})
    return pd.DataFrame.from_records(records)


def paired_delta_ci(a: np.ndarray, b: np.ndarray, n_boot: int = 10000) -> tuple[float, float, float]:
    rng = np.random.default_rng(42)
    n = len(a)
    idx = rng.integers(0, n, size=(n_boot, n))
    delta = np.mean(b[idx], axis=1) - np.mean(a[idx], axis=1)
    lo, hi = np.percentile(delta, [2.5, 97.5])
    return float(np.mean(b) - np.mean(a)), float(lo), float(hi)


def paired_key(source: str, base: str = "Tm_only") -> str:
    return f"{source}_minus_{base}"


def panel_label(ax, label: str) -> None:
    ax.text(
        -0.16,
        1.11,
        f"({label.lower()})",
        transform=ax.transAxes,
        fontsize=11.5,
        fontweight="bold",
        ha="left",
        va="top",
        clip_on=False,
    )


def polish(ax, grid_axis: str = "y", boxed: bool = True) -> None:
    ax.set_axisbelow(True)
    ax.grid(True, axis=grid_axis, color=COL["grid"], linewidth=0.7)
    ax.tick_params(width=0.9, length=3.5)
    for spine in ax.spines.values():
        spine.set_visible(boxed)
        spine.set_linewidth(0.9)
        spine.set_color(COL["black"])


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
                fig.savefig(path, dpi=600)
            else:
                fig.savefig(path)
            if ext == "svg":
                path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    plt.close(fig)
    print(f"wrote {PLOT_DIR / (stem + '.pdf')}")


def horizontal_interval(ax, y, mid, lo, hi, color, marker="o", label=None, zorder=3):
    ax.errorbar(
        [mid],
        [y],
        xerr=np.asarray([[mid - lo], [hi - mid]]),
        fmt=marker,
        color=color,
        ecolor=color,
        elinewidth=1.5,
        capsize=3.8,
        capthick=1.2,
        markersize=6.8,
        markerfacecolor=color,
        markeredgecolor="white",
        markeredgewidth=0.7,
        label=label,
        zorder=zorder,
    )


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
        elinewidth=1.1,
        capsize=3.0,
        capthick=1.0,
        alpha=0.95,
        markerfacecolor=color,
        markeredgecolor="white",
        markeredgewidth=0.5,
        label="_nolegend_",
        zorder=2,
    )
    ax.plot(data["x"], y, marker=marker, color=color, label=label, zorder=4)


def paired_scaling_rows(curve_path: Path, baseline_path: Path, n_boot: int = 10000) -> pd.DataFrame:
    """Paired MAE change at each label count relative to one Tm-only model.

    The candidate and reference absolute errors are aligned over the same 396
    held-out proteins. Negative values therefore mean lower Tm error than the
    reference model; zero means equal mean absolute error.
    """
    reference = np.asarray(select_scaling_point(baseline_path, "single")["abs_errors"], dtype=float)
    records = []
    for point in read_json(curve_path)["scaling"]:
        candidate = np.asarray(point["abs_errors"], dtype=float)
        delta, lo, hi = paired_delta_ci(reference, candidate, n_boot=n_boot)
        records.append(
            {
                "n": float(point["n"]),
                "delta_mae": delta,
                "delta_ci_lo": lo,
                "delta_ci_hi": hi,
            }
        )
    return pd.DataFrame.from_records(records)


def paired_scaling_plot(
    ax,
    data: pd.DataFrame,
    color: str,
    label: str,
    marker: str,
) -> None:
    x = data["n"].to_numpy(float)
    y = data["delta_mae"].to_numpy(float)
    yerr = np.vstack(
        [
            y - data["delta_ci_lo"].to_numpy(float),
            data["delta_ci_hi"].to_numpy(float) - y,
        ]
    )
    ax.errorbar(
        x,
        y,
        yerr=yerr,
        fmt=f"{marker}-",
        color=color,
        ecolor=color,
        elinewidth=1.4,
        capsize=3.8,
        capthick=1.2,
        markerfacecolor=color,
        markeredgecolor="white",
        markeredgewidth=0.7,
        label=label,
        zorder=3,
    )


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
    ax.text(0.50, 0.18, "All computational labels are compared on the same test examples", ha="center", fontsize=7.5, color=COL["gray"])
    panel_label(ax, "D")

    save_figure(fig, "fig_outline01_concept_protocol")


def fig02_source_screen(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), constrained_layout=True)
    x_ticks = [20, 80, 160, 320]
    core = rows.set_index(rows["source"].astype(str))

    # (a) FROZEN-regime computational-label count sweeps: FEP and the FEP-matched
    #     MD native-contact label both scale below the Tm-only frozen baseline
    #     (dashed line), i.e. they beat training on experimental Tm labels alone.
    ax = axes[0, 0]
    tm_base = load_scaling(FIG2A_TM_BASELINE)["mae"].iloc[0]
    ax.axhline(tm_base, color=COL["baseline"], linewidth=1.1, linestyle="--", zorder=1)
    ax.text(9, tm_base + 0.02, "Tm labels only (baseline)", fontsize=6.2,
            color=COL["baseline"], va="bottom")
    for label, path, color, marker in FIG2A_CURVES:
        scaling_errorbar(ax, load_scaling(path), color, label, marker=marker)
    ax.set_xscale("log")
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([str(x) for x in x_ticks])
    ax.set_xlabel("computational labels used")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(15, 400)
    ax.set_ylim(6.85, 7.45)
    ax.set_yticks([7.0, 7.2, 7.4])
    ax.legend(frameon=False, loc="upper right", handlelength=1.8, fontsize=6.4)
    ax.text(0.02, 0.03, "frozen encoder", transform=ax.transAxes, fontsize=6.4, color=COL["gray"])
    polish(ax, "both")
    panel_label(ax, "A")

    # (b) Tuned source screen at the representative n=320 point (frozen encoder):
    #     the full hierarchy of computational labels.
    ax = axes[0, 1]
    frozen = read_json(FROZEN_SUMMARY_JSON)
    frozen_rows = {str(r["source"]): r for r in frozen["rows"]}
    screen = source_screen_points(frozen_rows)
    y = np.arange(len(SOURCE_ORDER)) * 1.0
    for i, src in enumerate(SOURCE_ORDER):
        mae, lo, hi = screen[src]
        horizontal_interval(ax, y[i], mae, lo, hi, SOURCE_COLOR[src], marker="s" if src == "Tm_only" else "o")
        ax.text(hi + 0.012, y[i], f"{mae:.2f}", va="center", fontsize=6.6)
    tm_frozen = screen["Tm_only"][0]
    ax.axvline(tm_frozen, color=COL["baseline"], linewidth=0.9, linestyle="--", zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels([SOURCE_LABEL[s] for s in SOURCE_ORDER], fontsize=6.4)
    ax.set_ylim(y[-1] + 0.6, -0.6)
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(6.90, 7.45)
    ax.text(0.02, 0.03, "frozen encoder", transform=ax.transAxes, fontsize=6.4, color=COL["gray"])
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[1, 0]
    size_rows = model_size_rows(rows)
    sizes = ["8M", "35M", "650M"]
    xpos = np.arange(len(sizes))
    x_offsets = {"Tm labels only": -0.08, "FEP mutation free energy": 0.08}
    colors = {"Tm labels only": COL["baseline"], "FEP mutation free energy": COL["fep"]}
    markers = {"Tm labels only": "s", "FEP mutation free energy": "o"}
    for condition in ["Tm labels only", "FEP mutation free energy"]:
        subset = size_rows[size_rows["condition"] == condition].set_index("esm2_size").loc[sizes]
        x = xpos + x_offsets[condition]
        yvals = subset["test_mae"].to_numpy(float)
        yerr = np.vstack([yvals - subset["ci_lo"].to_numpy(float), subset["ci_hi"].to_numpy(float) - yvals])
        ax.errorbar(
            x,
            yvals,
            yerr=yerr,
            fmt=markers[condition] + "-",
            color=colors[condition],
            ecolor=colors[condition],
            elinewidth=1.0,
            capsize=0,
            label=condition,
        )
    ax.set_xticks(xpos)
    ax.set_xticklabels(sizes)
    ax.set_xlabel("ESM2 encoder size")
    ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.set_ylim(5.75, 7.35)
    ax.legend(frameon=False, loc="upper left", handlelength=1.8)
    polish(ax, "y")
    panel_label(ax, "C")

    ax = axes[1, 1]
    abs_sources = ["Tm_only", "FEP", MD_CONTACT_Q_SOURCE]
    core_rows = encoder_core_rows(abs_sources)
    ypos = np.arange(len(abs_sources)) * 1.45
    y_offsets = {"frozen": -0.18, "hot": 0.18}
    markers = {"frozen": "s", "hot": "o"}
    encoder_labels = {"frozen": "frozen encoder", "hot": "hot encoder"}
    for encoder in ["frozen", "hot"]:
        subset = core_rows[core_rows["encoder"] == encoder].set_index("source")
        for i, source in enumerate(abs_sources):
            row = subset.loc[source]
            horizontal_interval(
                ax,
                ypos[i] + y_offsets[encoder],
                row["test_mae"],
                row["ci_lo"],
                row["ci_hi"],
                SOURCE_COLOR[source],
                marker=markers[encoder],
            )
    ax.set_yticks(ypos)
    ax.set_yticklabels(["Tm labels\nonly", "FEP mutation\nfree energy", "MD native-contact\n(matched scan)"], fontsize=6.6)
    ax.set_ylim(ypos[-1] + 0.60, -0.60)
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(5.7, 8.0)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="s", color=COL["black"], linestyle="none", markersize=5, label=encoder_labels["frozen"]),
            Line2D([0], [0], marker="o", color=COL["black"], linestyle="none", markersize=5, label=encoder_labels["hot"]),
        ],
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.54, 1.01),
        ncol=2,
        borderaxespad=0.0,
    )
    polish(ax, "x")
    panel_label(ax, "D")

    save_figure(fig, "fig_outline02_source_screen")


def fig03_design_bridge(rows: pd.DataFrame, paired: dict) -> None:
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(10.6, 3.7),
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.25, 1.0, 1.0]},
    )

    # (a) The SAME MD native-contact observable, two data designs. Each group is
    #     anchored to its own Tm-only reference (different absolute MAE scales).
    ax = axes[0]
    diverse = fig3a_group(FIG3A_DIVERSE)
    matched = fig3a_group(FIG3A_MATCHED)
    groups = [(diverse, [0, 1, 2]), (matched, [4, 5, 6])]
    for grp, ys in groups:
        entries = [
            ("Tm labels only", grp["tm"], COL["baseline"], "s"),
            ("FEP mutation\nfree energy", grp["fep"], COL["fep"], "o"),
            (grp["md_label"], grp["md"], COL["mdq"], "D"),
        ]
        tm_x = grp["tm"][0]
        ax.plot([tm_x, tm_x], [ys[0] - 0.45, ys[-1] + 0.45], color=COL["baseline"],
                linestyle="--", linewidth=0.9, zorder=1)
        for y, (lab, (mae, lo, hi), color, marker) in zip(ys, entries):
            horizontal_interval(ax, y, mae, lo, hi, color, marker=marker)
            ax.text(hi + 0.03, y, f"{mae:.2f}", va="center", fontsize=6.4)
    yticks = [0, 1, 2, 4, 5, 6]
    yticklabels = [
        "Tm labels only", "FEP mutation\nfree energy", diverse["md_label"],
        "Tm labels only", "FEP mutation\nfree energy", matched["md_label"],
    ]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels, fontsize=6.2)
    ax.set_ylim(6.7, -0.7)
    ax.axhline(3.0, color=COL["grid"], linewidth=0.9)
    ax.text(5.78, 1.0, diverse["title"], rotation=90, va="center", ha="left",
            fontsize=6.8, color=COL["mdq"], fontweight="bold")
    ax.text(5.78, 5.0, matched["title"], rotation=90, va="center", ha="left",
            fontsize=6.8, color=COL["mdq"], fontweight="bold")
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(5.75, 7.55)
    polish(ax, "x")
    panel_label(ax, "A")

    # (b) The length confound: MD native-contact label value vs sequence length.
    ax = axes[1]
    (dlen, dval, r), matched_pts = fig3b_confound()
    ax.scatter(dlen, dval, s=9, color=COL["mdq"], alpha=0.35, edgecolor="none",
               label=f"diverse screen (n={len(dlen)})", zorder=2)
    mcolors = {"1mel": COL["fep"], "4idl": COL["design"]}
    for mlen, mval, tag in matched_pts:
        ax.scatter(mlen, mval, s=9, color=mcolors.get(tag, COL["design"]), alpha=0.5,
                   edgecolor="none", label=f"matched scan ({tag}, n={len(mlen)})", zorder=3)
    ax.text(0.04, 0.10, f"diverse: Pearson $r$ = {r:+.2f}\n(length spread 58-461)",
            transform=ax.transAxes, fontsize=6.4, color=COL["mdq"], va="bottom")
    ax.text(0.62, 0.42, "matched:\nconstant length", transform=ax.transAxes,
            fontsize=6.4, color=COL["design"], va="center", ha="center")
    ax.set_xlabel("sequence length (residues)")
    ax.set_ylabel("MD Q-value (fraction native contacts)")
    ax.legend(frameon=False, loc="lower right", fontsize=5.8, handlelength=1.0, markerscale=1.4)
    polish(ax, "both")
    panel_label(ax, "B")

    # (c) Label-count scaling of the matched MD label (frozen): paired ΔMAE(n).
    ax = axes[2]
    delta = fig3c_delta_by_n()
    x = delta["n"].to_numpy(float)
    y = delta["delta_mae"].to_numpy(float)
    yerr = np.vstack([y - delta["delta_ci_lo"].to_numpy(float), delta["delta_ci_hi"].to_numpy(float) - y])
    ax.axhline(0.0, color=COL["baseline"], linewidth=1.0, linestyle="--", zorder=1)
    ax.errorbar(x, y, yerr=yerr, fmt="D-", color=COL["mdq"], ecolor=COL["mdq"],
                elinewidth=1.0, capsize=2.5, markerfacecolor=COL["mdq"],
                markeredgecolor="white", markeredgewidth=0.6, zorder=3)
    ax.text(x[-1], y[-1] - 0.03, f"{y[-1]:.2f}*", ha="center", va="top", fontsize=6.8, color=COL["mdq"])
    ax.set_xscale("log")
    ax.set_xticks([20, 80, 160, 320])
    ax.set_xticklabels(["20", "80", "160", "320"])
    ax.set_xlabel("matched MD labels")
    ax.set_ylabel(r"$\Delta$MAE vs Tm-only (deg C)")
    ax.set_xlim(15, 430)
    ax.set_ylim(-0.42, 0.28)
    ax.text(0.03, 0.92, "frozen encoder", transform=ax.transAxes, fontsize=6.4, color=COL["gray"])
    polish(ax, "both")
    panel_label(ax, "C")

    save_figure(fig, "fig_outline03_design_bridge")


def fig04_boundary_mdq(rows: pd.DataFrame, paired: dict) -> None:
    fig, axd = plt.subplot_mosaic([["A", "B"], ["C", "C"]],
                                  figsize=(7.6, 6.2), constrained_layout=True)
    markers = {"frozen": "s", "hot": "o"}
    enc_handles = [
        Line2D([0], [0], marker="s", color=COL["black"], linestyle="none", markersize=5, label="frozen encoder"),
        Line2D([0], [0], marker="o", color=COL["black"], linestyle="none", markersize=5, label="hot encoder"),
    ]

    # (a) representative held-out Tm MAE, grouped by frozen vs hot encoder.
    ax = axd["A"]
    core = encoder_core_rows(FIG4_SOURCES)
    ypos = np.arange(len(FIG4_SOURCES)) * 1.4
    y_off = {"frozen": -0.20, "hot": 0.20}
    for encoder in ["frozen", "hot"]:
        subset = core[core["encoder"] == encoder].set_index("source")
        for i, src in enumerate(FIG4_SOURCES):
            row = subset.loc[src]
            horizontal_interval(ax, ypos[i] + y_off[encoder], row["test_mae"],
                                row["ci_lo"], row["ci_hi"], SOURCE_COLOR[src], marker=markers[encoder])
    ax.set_yticks(ypos)
    ax.set_yticklabels([SOURCE_LABEL[s] for s in FIG4_SOURCES], fontsize=6.4)
    ax.set_ylim(ypos[-1] + 0.7, -0.7)
    ax.set_xlabel("held-out Tm test MAE (deg C)")
    ax.set_xlim(6.20, 7.55)
    ax.legend(handles=enc_handles, frameon=False, loc="lower center",
              bbox_to_anchor=(0.54, 1.01), ncol=2, borderaxespad=0.0)
    polish(ax, "x")
    panel_label(ax, "A")

    # (b) paired ΔMAE vs Tm-only per source x encoder regime, with 95% CI.
    ax = axd["B"]
    delta_sources = ["FEP", MD_CONTACT_Q_SOURCE, "rosetta", "thermoMPNN"]
    deltas = encoder_delta_rows(delta_sources)
    ypos = np.arange(len(delta_sources)) * 1.4
    ax.axvline(0.0, color=COL["baseline"], linewidth=1.0, linestyle="--", zorder=1)
    for encoder in ["frozen", "hot"]:
        subset = deltas[deltas["encoder"] == encoder].set_index("source")
        for i, src in enumerate(delta_sources):
            row = subset.loc[src]
            horizontal_interval(ax, ypos[i] + y_off[encoder], row["delta_mae"],
                                row["delta_ci_lo"], row["delta_ci_hi"], SOURCE_COLOR[src], marker=markers[encoder])
    ax.set_yticks(ypos)
    ax.set_yticklabels([SOURCE_LABEL[s] for s in delta_sources], fontsize=6.4)
    ax.set_ylim(ypos[-1] + 0.7, -0.7)
    ax.set_xlabel(r"$\Delta$MAE vs Tm-only (deg C)")
    ax.set_xlim(-0.45, 0.35)
    ax.text(0.02, 0.02, "left of 0 = improves over Tm-only", transform=ax.transAxes,
            fontsize=6.0, color=COL["gray"])
    ax.legend(handles=enc_handles, frameon=False, loc="lower center",
              bbox_to_anchor=(0.54, 1.01), ncol=2, borderaxespad=0.0)
    polish(ax, "x")
    panel_label(ax, "B")

    # (c) interpretation schematic: depth of transfer set by the physical observable.
    ax = axd["C"]
    fig04d_schematic(ax)
    panel_label(ax, "C")

    save_figure(fig, "fig_outline04_mdq_boundary")


def fig04d_schematic(ax) -> None:
    """Deep (free energy reshapes encoder) vs shallow (native-contact Q shapes only
    the fixed trunk) shared-representation schematic."""
    hide_axes(ax)
    # top row: FEP / free-energy -> reshapes encoder (deep, hot-transferable)
    box(ax, (0.04, 0.68), (0.24, 0.20), "mutation\nfree energy\n(FEP)", fc=COL["soft_green"], ec=COL["fep"], weight="bold", fontsize=6.6)
    box(ax, (0.40, 0.70), (0.20, 0.16), "encoder", fc=COL["soft_blue"], ec=COL["design"], weight="bold", fontsize=7.0)
    box(ax, (0.70, 0.70), (0.20, 0.16), "Tm head", fc="white", ec=COL["baseline"], fontsize=7.0)
    arrow(ax, (0.28, 0.78), (0.40, 0.78), color=COL["fep"])
    arrow(ax, (0.60, 0.78), (0.70, 0.78), color=COL["design"])
    ax.text(0.50, 0.925, "deep: reshapes the encoder (transfers frozen + hot)",
            ha="center", fontsize=6.4, color=COL["fep"], fontweight="bold")

    # bottom row: MD native-contact Q -> only the fixed trunk (shallow, frozen-only)
    box(ax, (0.04, 0.22), (0.24, 0.20), "native-contact\nstability Q\n(MD)", fc=COL["soft_red"], ec=COL["mdq"], weight="bold", fontsize=6.6)
    box(ax, (0.40, 0.24), (0.20, 0.16), "frozen\nencoder", fc=COL["soft_gray"], ec=COL["gray"], fontsize=6.6)
    box(ax, (0.70, 0.24), (0.20, 0.16), "Tm head", fc="white", ec=COL["baseline"], fontsize=7.0)
    arrow(ax, (0.28, 0.32), (0.40, 0.32), color=COL["mdq"])
    arrow(ax, (0.60, 0.32), (0.70, 0.32), color=COL["baseline"])
    ax.text(0.505, 0.335, "x", ha="center", va="center", fontsize=9, color=COL["mdq"], fontweight="bold")
    ax.text(0.50, 0.05, "shallow: only refines the fixed trunk (helps frozen, not hot)",
            ha="center", fontsize=6.4, color=COL["mdq"], fontweight="bold")


def fig2_data_design(rows: pd.DataFrame, paired: dict) -> None:
    """Simulation-plan evidence at the journal's final printed width."""
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.65),
        gridspec_kw={"width_ratios": [1.12, 1.0]},
        layout="constrained",
    )

    # (a) Four directly labelled effects; every zero is the corresponding
    # independently tuned series' own Tm-only model.
    ax = axes[0]
    effects = design_delta_rows()
    rows_b = [
        ("Heterogeneous data set\nfrozen encoder", "heterogeneous screen", "frozen", COL["gray"], "s"),
        ("Heterogeneous data set\nfine-tuned encoder", "heterogeneous screen", "hot", COL["gray"], "o"),
        ("Matched mutation scan\nfrozen encoder", "matched mutation scan", "frozen", COL["design"], "s"),
        ("Matched mutation scan\nfine-tuned encoder", "matched mutation scan", "hot", COL["design"], "o"),
    ]
    ax.axvline(0.0, color=COL["baseline"], linestyle="--", linewidth=1.0, zorder=1)
    ypos = np.arange(len(rows_b), dtype=float)
    for y, (label, design, encoder, color, marker) in zip(ypos, rows_b):
        row = effects[(effects["design"] == design) & (effects["encoder"] == encoder)].iloc[0]
        horizontal_interval(
            ax,
            y,
            row["delta_mae"],
            row["delta_ci_lo"],
            row["delta_ci_hi"],
            color,
            marker=marker,
        )
        offset = -0.018 if row["delta_mae"] < 0 else 0.018
        ax.text(
            row["delta_mae"] + offset,
            y - 0.23,
            f"{row['delta_mae']:+.2f}",
            ha="right" if offset < 0 else "left",
            va="center",
            fontsize=8.6,
            color=color,
            fontweight="normal",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 0.5},
        )
    ax.axhline(1.5, color="white", linewidth=2.0, zorder=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels([r[0] for r in rows_b], fontsize=9.2)
    ax.set_ylim(len(rows_b) - 0.45, -0.55)
    ax.set_xlim(-0.38, 0.28)
    ax.set_xlabel(r"$\Delta$MAE vs own Tm-only model (°C)")
    ax.text(0.03, 0.97, "lower Tm error", transform=ax.transAxes, ha="left", va="top",
            fontsize=8.4, color=COL["design"])
    ax.text(0.97, 0.97, "higher Tm error", transform=ax.transAxes, ha="right", va="top",
            fontsize=8.4, color=COL["rosetta"])
    polish(ax, "x", boxed=True)
    panel_label(ax, "A")

    # (b) Paired changes from the frozen Tm-only model. Paired intervals make
    # the baseline and the direction of transfer explicit and avoid clipped
    # single-model confidence intervals.
    ax = axes[1]
    ax.axhline(0.0, color=COL["baseline"], linewidth=1.0, linestyle="--", zorder=1)
    frozen_curves = [
        ("FEP $\Delta\Delta G$", RESULTS / "final_fep_frozen" / "scaling.json", COL["fep"], "o"),
        ("MD native-contact $Q$", RESULTS / "final_mdq_frozen" / "scaling.json", COL["mdq"], "D"),
    ]
    frozen_endpoints = []
    for label, path, color, marker in frozen_curves:
        curve = paired_scaling_rows(path, FIG3C_TM_FROZEN)
        paired_scaling_plot(ax, curve, color, label, marker)
        frozen_endpoints.append((label, float(curve.iloc[-1]["delta_mae"]), color))
    ax.set_xscale("log", base=2)
    ax.set_xlim(16, 520)
    ax.set_xticks([20, 80, 160, 320], ["20", "80", "160", "320"])
    ax.set_xlabel("Labels per structure and model, n")
    ax.set_ylabel(r"$\Delta$MAE vs Tm-only (°C)")
    ax.set_ylim(-0.42, 0.28)
    ax.text(0.03, 0.04, "negative = lower Tm error", transform=ax.transAxes, fontsize=8.3,
            color=COL["design"], va="bottom")
    ax.text(505, 0.015, "Tm-only", ha="right", va="bottom", fontsize=8.0,
            color=COL["baseline"])
    endpoint_labels = {"FEP $\\Delta\\Delta G$": "FEP ΔΔG",
                       "MD native-contact $Q$": "MD Q"}
    for (label, value, color), dy in zip(frozen_endpoints, (-0.025, 0.035)):
        ax.text(0.97, value + dy, f"{endpoint_labels[label]}  {value:+.2f}",
                transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8.3,
                fontweight="bold", color=color,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 0.4})
    polish(ax, "both", boxed=True)
    panel_label(ax, "B")

    save_figure(fig, "fig_outline02_data_design")


def fig3_physical_observable(rows: pd.DataFrame, paired: dict) -> None:
    """Physical-observable axis with explicit difference semantics."""
    fig = plt.figure(figsize=(7.2, 5.75), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=[1.30, 1.0], width_ratios=[1.0, 1.0])
    endpoint_labels = {"FEP $\\Delta\\Delta G$": "FEP ΔΔG",
                       "MD native-contact $Q$": "MD Q"}
    encoder_style = {
        "frozen": {"offset": -0.17, "marker": "s", "face": "source"},
        "hot": {"offset": 0.17, "marker": "o", "face": "white"},
    }

    # (a) Horizontal paired effects. Marker shape/fill, not color, encodes the
    # encoder regime; color is reserved for the physical label source.
    ax = fig.add_subplot(grid[0, :])
    map_sources = ["FEP", MD_CONTACT_Q_SOURCE, "thermoMPNN", "rosetta", "rosetta_random", "rosetta_esm"]
    source_labels = [
        "FEP mutation free energy",
        "MD native-contact Q (matched)",
        "ThermoMPNN stability score",
        "Rosetta mutation score",
        "random variants + Rosetta",
        "ESM2 variants + Rosetta",
    ]
    display_color = {
        "FEP": COL["fep"],
        MD_CONTACT_Q_SOURCE: COL["mdq"],
        "thermoMPNN": COL["gray"],
        "rosetta": COL["gray"],
        "rosetta_random": COL["gray"],
        "rosetta_esm": COL["gray"],
    }
    deltas_all = encoder_delta_rows(map_sources)
    ypos = np.arange(len(map_sources), dtype=float)
    ax.axvline(0.0, color=COL["baseline"], linewidth=1.0, linestyle="--", zorder=1)
    for encoder in ("frozen", "hot"):
        style = encoder_style[encoder]
        subset = deltas_all[deltas_all["encoder"] == encoder].set_index("source")
        for i, source in enumerate(map_sources):
            row = subset.loc[source]
            y = ypos[i] + style["offset"]
            color = display_color[source]
            ax.errorbar(
                row["delta_mae"],
                y,
                xerr=np.asarray(
                    [[row["delta_mae"] - row["delta_ci_lo"]],
                     [row["delta_ci_hi"] - row["delta_mae"]]]
                ),
                fmt=style["marker"],
                markerfacecolor=color if style["face"] == "source" else "white",
                markeredgecolor=color,
                markeredgewidth=1.3,
                markersize=7.0,
                ecolor=color,
                elinewidth=1.5,
                capsize=3.8,
                capthick=1.2,
                zorder=4,
            )
            # Directly label only the comparisons that carry the main message.
            # The other intervals remain readable against the common zero line
            # without repeating every numerical value in the panel.
            label_value = source in ("FEP", MD_CONTACT_Q_SOURCE) or (
                source == "rosetta_esm" and encoder == "hot"
            )
            if label_value:
                offset = -0.018 if row["delta_mae"] < 0 else 0.018
                ax.text(
                    row["delta_mae"] + offset,
                    y,
                    f"{row['delta_mae']:+.2f}",
                    ha="right" if offset < 0 else "left",
                    va="center",
                    fontsize=8.2,
                    fontweight="normal",
                    color=COL["black"],
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.80, "pad": 0.3},
                    zorder=5,
                )
    ax.axhline(3.5, color="white", linewidth=2.0, zorder=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels(source_labels, fontsize=8.8)
    ax.set_ylim(len(map_sources) - 0.50, -0.90)
    ax.set_xlim(-0.42, 0.70)
    ax.set_xlabel(r"$\Delta$MAE vs corresponding Tm-only model (°C)")
    ax.text(0.03, 0.98, "lower Tm error", transform=ax.transAxes, ha="left", va="top",
            fontsize=8.5, color=COL["design"])
    ax.text(0.97, 0.98, "higher Tm error", transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color=COL["rosetta"])
    ax.legend(
        handles=[
            Line2D([], [], marker="s", linestyle="none", markerfacecolor=COL["gray"],
                   markeredgecolor=COL["gray"], markersize=7, label="frozen encoder"),
            Line2D([], [], marker="o", linestyle="none", markerfacecolor="white",
                   markeredgecolor=COL["gray"], markeredgewidth=1.3, markersize=7,
                   label="fine-tuned encoder"),
        ],
        frameon=False,
        loc="upper right",
        ncol=1,
        bbox_to_anchor=(0.99, 0.82),
        borderaxespad=0.2,
        handlelength=1.5,
    )
    polish(ax, "x", boxed=True)
    panel_label(ax, "A")

    # (b) Only the direct comparison remains here. Zero now has one meaning:
    # equal held-out Tm MAE for FEP and matched native-contact Q.
    ax = fig.add_subplot(grid[1, 0])
    direct = fep_minus_md_rows()
    direct_markers = {"frozen": "s", "hot": "o"}
    ax.axvline(0.0, color=COL["baseline"], linewidth=1.0, linestyle="--", zorder=1)
    for y, encoder in enumerate(("frozen", "hot")):
        row = direct[direct["encoder"] == encoder].iloc[0]
        ax.errorbar(
            row["delta_mae"], y,
            xerr=[[row["delta_mae"] - row["delta_ci_lo"]],
                  [row["delta_ci_hi"] - row["delta_mae"]]],
            fmt=direct_markers[encoder], color=COL["baseline"],
            ecolor=COL["baseline"], elinewidth=1.5, capsize=3.8, capthick=1.2,
            markersize=7.0,
            markerfacecolor=COL["baseline"] if encoder == "frozen" else "white",
            markeredgecolor=COL["baseline"], markeredgewidth=1.3, zorder=3,
        )
        ax.text(
            row["delta_mae"] - 0.014,
            y - 0.22,
            f"{row['delta_mae']:+.2f}",
            ha="right",
            va="center",
            fontsize=8.7,
            color=COL["baseline"],
            fontweight="normal",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.80, "pad": 0.4},
        )
    ax.set_yticks([0, 1], ["Frozen encoder", "Fine-tuned encoder"])
    ax.set_ylim(1.55, -0.55)
    ax.set_xlim(-0.42, 0.24)
    ax.set_xlabel("MAE(FEP) − MAE(MD Q) (°C)")
    ax.text(0.03, 0.97, "FEP lower", transform=ax.transAxes, ha="left", va="top",
            fontsize=8.5, color=COL["fep"])
    ax.text(0.97, 0.97, "MD Q lower", transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color=COL["mdq"])
    polish(ax, "x", boxed=True)
    panel_label(ax, "B")

    # (c) Fine-tuned label-count behavior as paired changes from Tm-only.
    ax = fig.add_subplot(grid[1, 1])
    ax.axhline(0.0, color=COL["baseline"], linewidth=1.0, linestyle="--", zorder=1)
    hot_curves = [
        ("FEP $\Delta\Delta G$", RESULTS / "final_fep_hot" / "scaling.json", COL["fep"], "o"),
        ("MD native-contact $Q$", RESULTS / "final_mdq_hot" / "scaling.json", COL["mdq"], "D"),
    ]
    hot_endpoints = []
    for label, path, color, marker in hot_curves:
        curve = paired_scaling_rows(path, FIG3_HOT_TM_BASELINE)
        paired_scaling_plot(ax, curve, color, label, marker)
        hot_endpoints.append((label, float(curve.iloc[-1]["delta_mae"]), color))
    ax.set_xscale("log", base=2)
    ax.set_xlim(16, 560)
    ax.set_xticks([20, 80, 160, 320], ["20", "80", "160", "320"])
    ax.set_xlabel("Labels per structure and model, n")
    ax.set_ylabel(r"$\Delta$MAE vs Tm-only (°C)")
    ax.set_ylim(-0.35, 0.70)
    ax.text(0.03, 0.04, "negative = lower Tm error", transform=ax.transAxes, fontsize=8.3,
            color=COL["design"], va="bottom")
    for (label, value, color), dy in zip(hot_endpoints, (-0.045, 0.075)):
        ax.text(0.96, value + dy, f"{endpoint_labels[label]}  {value:+.2f}",
                transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8.3,
                fontweight="bold", color=color,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 0.4})
    polish(ax, "both", boxed=True)
    panel_label(ax, "C")

    save_figure(fig, "fig_outline03_physical_observable")


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
        # val_mae is not tracked in the tuned representative files.
        if row["val_mae"] is None or tm["val_mae"] is None:
            out["val_delta_vs_tm"] = np.nan
        else:
            out["val_delta_vs_tm"] = row["val_mae"] - tm["val_mae"]
        out_rows.append(out)
    df = pd.DataFrame(out_rows)
    for out_dir in (PLOT_DIR, PAPER_FIG_DIR):
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(
            out_dir / "outline_figure_source_screen.tsv",
            sep="\t",
            index=False,
            na_rep="NA",
        )


def verify_abs_error_alignment(rows: pd.DataFrame) -> None:
    lengths = {str(row["source"]): len(row["abs_errors"]) for _, row in rows.iterrows()}
    unique = set(lengths.values())
    if unique != {396}:
        raise ValueError(f"Unexpected abs_errors lengths: {lengths}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-fig1",
        action="store_true",
        help="Generate Figs. 2 and 3 without changing the author-edited Fig. 1.",
    )
    args = parser.parse_args()

    configure_style()
    rows = source_rows()
    verify_abs_error_alignment(rows)
    paired = paired_comparisons()
    write_summary_tsv(rows, paired)
    if not args.skip_fig1:
        fig01_concept_protocol(rows)
    fig2_data_design(rows, paired)
    fig3_physical_observable(rows, paired)


if __name__ == "__main__":
    main()
