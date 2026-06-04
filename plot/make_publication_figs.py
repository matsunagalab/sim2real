#!/usr/bin/env python3
"""Build publication-quality multi-panel figures from all sim2real results.

The script reads every results/*/scaling.json file, including one known
leniently-parseable file with an extra trailing brace, and writes both PDF
vector figures and high-resolution PNG copies to:

  plot/
  paper/tex/figures/

It also writes plot/publication_results_summary.tsv, which is the numerical
table used by the figure panels.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
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
from scipy.optimize import curve_fit


REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
PLOT = REPO / "plot"
PAPER_FIGS = REPO / "paper" / "tex" / "figures"

OKABE_ITO = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "black": "#000000",
    "gray": "#7A7A7A",
    "light_gray": "#D9D9D9",
}

FAMILY_COLORS = {
    "Tm reference": OKABE_ITO["red"],
    "Physics ddG": OKABE_ITO["green"],
    "MD Q": OKABE_ITO["blue"],
    "Short MD Q": OKABE_ITO["sky"],
    "MD flexibility": OKABE_ITO["orange"],
    "MD structure": OKABE_ITO["purple"],
    "Rosetta MC Q": OKABE_ITO["yellow"],
    "Other": OKABE_ITO["gray"],
}

ENC_MARKERS = {"frozen": "o", "hot": "s", "lora": "^", None: "o"}


@dataclass
class Curve:
    exp: str
    path: Path
    data: dict
    axis: str
    encoder: str | None
    source: str
    source_label: str
    family: str
    n: np.ndarray
    x: np.ndarray
    mae: np.ndarray
    ci_lo: np.ndarray
    ci_hi: np.ndarray
    best_n: float
    best_x: float
    best_mae: float
    best_ci_width: float
    slope: float | None
    avg_mae: float | None
    p_value: float | None


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 400,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.0,
            "lines.linewidth": 1.7,
            "lines.markersize": 4.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
        }
    )


def read_json_lenient(path: Path) -> dict:
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        obj, idx = decoder.raw_decode(text)
        trailing = text[idx:].strip()
        if trailing and set(trailing) <= {"}"}:
            return obj
        raise


def infer_axis(args: dict) -> str:
    if str(args.get("n_tm_list") or "").strip():
        return "n_tm"
    if str(args.get("n_md_list") or "").strip():
        return "n_md"
    return "n_ddg"


def actual_x(axis: str, n: np.ndarray, args: dict) -> np.ndarray:
    ddg = args.get("ddg_source")
    if axis == "n_ddg" and ddg and ddg != "none":
        return n * 2.0
    return n.astype(float)


def clean_model_name(model: str | None) -> str:
    if not model:
        return ""
    if "esm2_t6_8M" in model:
        return "ESM-2 8M"
    if "esm2_t12_35M" in model:
        return "ESM-2 35M"
    if "esm2_t33_650M" in model:
        return "ESM-2 650M"
    return model.split("/")[-1]


def humanize_source(args: dict, exp: str) -> tuple[str, str, str, str]:
    ddg = args.get("ddg_source")
    md = args.get("md_source")
    axis = infer_axis(args)

    if axis == "n_tm":
        return "Tm only", "Tm only", "Tm reference", "Tm reference"
    if ddg and ddg != "none":
        label = {
            "FEP": "FEP ddG",
            "FoldX": "FoldX ddG",
            "rosetta": "Rosetta ddG",
            "thermoMPNN": "ThermoMPNN ddG",
            "rosetta_esm": "Rosetta ddG (ESM)",
            "rosetta_random": "Rosetta ddG (random)",
        }.get(ddg, f"{ddg} ddG")
        return ddg, label, "Physics ddG", label
    if not md or md == "none":
        return "none", "Tm only", "Tm reference", "Tm only"

    labels = {
        "MD_Q": "Q all contacts",
        "MD_Q_HPHIL": "Q HPHIL 300K",
        "MD_Q_HPHIL_400K": "Q HPHIL 400K",
        "MD_Q_HPHIL_400K_SHUF": "Q HPHIL 400K shuffled",
        "MD_Q_MIN": "Q min 300K",
        "MD_Q_STD": "Q std 300K",
        "MD_Q_SLOPE": "Q slope 300K",
        "MD_Q_MIN_400K": "Q min 400K",
        "MD_Q_STD_400K": "Q std 400K",
        "MD_Q_SLOPE_400K": "Q slope 400K",
        "MD_Q_HIGHFLEX": "Q high-flex 300K",
        "MD_Q_LOWFLEX": "Q low-flex 300K",
        "MD_Q_CDR3": "Q CDR3 300K",
        "MD_Q_FRAMEWORK": "Q framework 300K",
        "ROSETTA_Q_HPHIL": "Rosetta MC Q",
        "MD_RMSF": "RMSF mean",
        "MD_RMSF_MAX": "RMSF max 300K",
        "MD_RMSF_MAX_400K": "RMSF max 400K",
        "MD_RMSF_CDR3": "RMSF CDR3 300K",
        "MD_RMSF_FRAMEWORK": "RMSF framework 300K",
        "MD_RG_STD": "Rg std 300K",
        "MD_RG_STD_400K": "Rg std 400K",
        "MD_SS_DIST_MEAN": "SS distance mean",
        "MD_SS_DIST_STD": "SS distance std",
        "MD_CDR3_LEN": "CDR3 length",
        "MD_SALTBRIDGE": "salt-bridge persistence",
    }

    short = re.match(r"MD_Q_HPHIL_400K_T(\d+)", md or "")
    if short:
        label = f"Q HPHIL 400K, {short.group(1)} ns"
        return md, label, "Short MD Q", label

    label = labels.get(md, md.replace("MD_", "").replace("_", " "))
    if md == "ROSETTA_Q_HPHIL":
        family = "Rosetta MC Q"
    elif "Q" in md:
        family = "MD Q"
    elif "RMSF" in md or "RG" in md:
        family = "MD flexibility"
    elif "SS" in md or "CDR3" in md or "SALT" in md:
        family = "MD structure"
    else:
        family = "Other"
    return md, label, family, label


def load_curves() -> list[Curve]:
    curves: list[Curve] = []
    for path in sorted(RESULTS.glob("*/scaling.json")):
        data = read_json_lenient(path)
        args = data.get("args", {})
        pts = data.get("scaling", [])
        if not pts:
            continue

        n = np.array([float(p["n"]) for p in pts], dtype=float)
        mae = np.array([float(p["mae"]) for p in pts], dtype=float)
        ci_lo = np.array([float(p.get("ci_lo", p["mae"])) for p in pts], dtype=float)
        ci_hi = np.array([float(p.get("ci_hi", p["mae"])) for p in pts], dtype=float)
        order = np.argsort(n)
        n, mae, ci_lo, ci_hi = n[order], mae[order], ci_lo[order], ci_hi[order]

        axis = infer_axis(args)
        x = actual_x(axis, n, args)
        best_idx = int(np.argmin(mae))
        best = data.get("best") or {}
        summary = data.get("summary") or {}
        full = (data.get("paired_bootstrap") or {}).get("full_range") or {}
        source, source_label, family, _ = humanize_source(args, data.get("exp_name") or path.parent.name)
        encoder = data.get("resolved_encoder_mode") or args.get("encoder_mode") or (data.get("env") or {}).get("ENCODER_MODE")

        curves.append(
            Curve(
                exp=data.get("exp_name") or path.parent.name,
                path=path,
                data=data,
                axis=axis,
                encoder=encoder,
                source=source,
                source_label=source_label,
                family=family,
                n=n,
                x=x,
                mae=mae,
                ci_lo=ci_lo,
                ci_hi=ci_hi,
                best_n=float(best.get("n", n[best_idx])),
                best_x=float(actual_x(axis, np.array([best.get("n", n[best_idx])], dtype=float), args)[0]),
                best_mae=float(best.get("mae", mae[best_idx])),
                best_ci_width=float(best.get("ci_width", ci_hi[best_idx] - ci_lo[best_idx])),
                slope=float(summary["slope"]) if summary.get("slope") is not None else None,
                avg_mae=float(summary["mae_avg"]) if summary.get("mae_avg") is not None else None,
                p_value=float(full["p_positive"]) if full.get("p_positive") is not None else None,
            )
        )
    return curves


def as_summary_frame(curves: list[Curve]) -> pd.DataFrame:
    rows = []
    for c in curves:
        args = c.data.get("args", {})
        hp = c.data.get("hparams", {})
        rows.append(
            {
                "exp": c.exp,
                "timestamp": c.data.get("timestamp", ""),
                "encoder": c.encoder or "",
                "base_model": clean_model_name(hp.get("base_model_name") or args.get("base_model")),
                "axis": c.axis,
                "source": c.source,
                "source_label": c.source_label,
                "family": c.family,
                "n_points": len(c.n),
                "min_n": c.n.min(),
                "max_n": c.n.max(),
                "best_n": c.best_n,
                "best_x_actual": c.best_x,
                "best_mae": c.best_mae,
                "best_ci_width": c.best_ci_width,
                "mae_avg": c.avg_mae,
                "slope": c.slope,
                "full_range_p_positive": c.p_value,
                "path": str(c.path.relative_to(REPO)),
            }
        )
    df = pd.DataFrame(rows).sort_values(["best_mae", "exp"]).reset_index(drop=True)
    return df


def read_history() -> pd.DataFrame:
    path = REPO / "results.tsv"
    cols = [
        "timestamp",
        "commit",
        "slope",
        "ci_width",
        "mae_mean",
        "n_ddg_list",
        "n_runs",
        "ddg_source",
        "time_s",
        "md_source",
        "n_md_list",
        "encoder_mode",
        "base_model",
        "md_aux_source",
        "mtl_weight_mode",
        "md_weight",
        "exp_name",
    ]
    if not path.exists():
        return pd.DataFrame(columns=cols)
    # The file started with a 9-column header and later gained 17-column rows.
    # Skip the historical header and impose the expanded schema explicitly.
    df = pd.read_csv(path, sep="\t", names=cols, header=None, skiprows=1, engine="python")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["slope", "ci_width", "mae_mean", "n_runs", "time_s", "md_weight"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["encoder_mode"] = df["encoder_mode"].fillna("frozen")
    df["exp_name"] = df["exp_name"].fillna("")
    return df.dropna(subset=["timestamp", "mae_mean"]).sort_values("timestamp")


def curve_by_exp(curves: list[Curve]) -> dict[str, Curve]:
    return {c.exp: c for c in curves}


def panel(ax, label: str) -> None:
    ax.text(
        -0.12,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
    )


def polish(ax) -> None:
    ax.grid(True, which="major", color="#E5E5E5", linewidth=0.65)
    ax.grid(True, which="minor", color="#F0F0F0", linewidth=0.45, alpha=0.8)
    ax.tick_params(width=0.8, length=3.0)


def plot_curve(ax, c: Curve, color: str, label: str, marker: str = "o", linestyle: str = "-") -> None:
    ax.fill_between(c.x, c.ci_lo, c.ci_hi, color=color, alpha=0.15, lw=0)
    ax.plot(c.x, c.mae, marker=marker, linestyle=linestyle, color=color, label=label)


def power_law(x, a, b, c):
    return a * (x / 1000.0) ** b + c


def fit_power(c: Curve):
    if len(c.x) < 3:
        return None
    x, y = c.x.astype(float), c.mae.astype(float)
    c0 = float(np.min(y) - 0.02)
    a0 = float(max(np.max(y) - c0, 1e-3))
    try:
        popt, _ = curve_fit(
            power_law,
            x,
            y,
            p0=[a0, -0.2, c0],
            bounds=((1e-6, -3.0, min(y) - 1.0), (1e3, -1e-4, max(y) + 1.0)),
            maxfev=40000,
        )
        return popt
    except Exception:
        return None


def plot_fit(ax, c: Curve, color: str) -> None:
    popt = fit_power(c)
    if popt is None:
        return
    xs = np.geomspace(max(min(c.x), 1), max(c.x), 150)
    ax.plot(xs, power_law(xs, *popt), color=color, linestyle=":", linewidth=1.3, alpha=0.9)


def save_figure(fig, stem: str) -> None:
    PLOT.mkdir(exist_ok=True)
    PAPER_FIGS.mkdir(parents=True, exist_ok=True)
    for out_dir in [PLOT, PAPER_FIGS]:
        pdf = out_dir / f"{stem}.pdf"
        png = out_dir / f"{stem}.png"
        fig.savefig(pdf, bbox_inches="tight")
        fig.savefig(png, bbox_inches="tight", dpi=400)
    plt.close(fig)
    print(f"wrote {PLOT / (stem + '.pdf')}")


def baseline_at_full(curves: dict[str, Curve], enc: str) -> float | None:
    c = curves.get(f"tm_ref_{enc}")
    if not c:
        return None
    return float(c.mae[np.argmax(c.n)])


def draw_baseline(ax, curves: dict[str, Curve], enc: str) -> None:
    b = baseline_at_full(curves, enc)
    if b is None:
        return
    ax.axhline(b, color=OKABE_ITO["red"], linestyle="--", linewidth=1.2, label=f"Tm only ({b:.2f})")


def fig01_main_scaling(curves_list: list[Curve]) -> None:
    curves = curve_by_exp(curves_list)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.2), constrained_layout=True)

    ax = axes[0, 0]
    for enc, color, marker in [("frozen", OKABE_ITO["purple"], "o"), ("hot", OKABE_ITO["orange"], "s")]:
        c = curves.get(f"tm_ref_{enc}")
        if c:
            plot_curve(ax, c, color, enc, marker=marker)
            plot_fit(ax, c, color)
    ax.set_xlabel("experimental Tm training labels")
    ax.set_ylabel("MAE (deg C)")
    ax.set_title("Tm-only reference scaling")
    ax.legend(frameon=False)
    polish(ax)
    panel(ax, "A")

    ax = axes[0, 1]
    draw_baseline(ax, curves, "frozen")
    for exp, label, color, marker in [
        ("fep_frozen", "FEP ddG", OKABE_ITO["green"], "s"),
        ("frozen_q_400k", "MD-Q HPHIL 400K", OKABE_ITO["blue"], "o"),
        ("frozen_q_hphil_full", "MD-Q HPHIL 300K", OKABE_ITO["sky"], "^"),
        ("rosetta_full", "Rosetta MC Q", OKABE_ITO["yellow"], "D"),
    ]:
        c = curves.get(exp)
        if c:
            plot_curve(ax, c, color, label, marker=marker)
            plot_fit(ax, c, color)
    ax.set_xscale("log")
    ax.set_xlabel("auxiliary labels")
    ax.set_ylabel("MAE (deg C)")
    ax.set_title("Frozen encoder")
    ax.legend(frameon=False, ncol=1)
    polish(ax)
    panel(ax, "B")

    ax = axes[1, 0]
    draw_baseline(ax, curves, "hot")
    for exp, label, color, marker in [
        ("fep_hot", "FEP ddG", OKABE_ITO["green"], "s"),
        ("hot_q_400k", "MD-Q HPHIL 400K", OKABE_ITO["blue"], "o"),
        ("hot_q_slope_400k", "MD-Q slope 400K", OKABE_ITO["sky"], "^"),
        ("hot_lowflex_sweep", "MD-Q low-flex 300K", OKABE_ITO["orange"], "D"),
    ]:
        c = curves.get(exp)
        if c:
            plot_curve(ax, c, color, label, marker=marker)
            plot_fit(ax, c, color)
    ax.set_xscale("log")
    ax.set_xlabel("auxiliary labels")
    ax.set_ylabel("MAE (deg C)")
    ax.set_title("Hot encoder")
    ax.legend(frameon=False, ncol=1)
    polish(ax)
    panel(ax, "C")

    ax = axes[1, 1]
    bars = []
    labels = []
    colors = []
    for enc, prefix in [("frozen", "Frozen"), ("hot", "Hot")]:
        for exp, name, color in [
            (f"tm_ref_{enc}", "Tm only", OKABE_ITO["red"]),
            (f"fep_{enc}", "FEP", OKABE_ITO["green"]),
            (f"{'frozen_q_400k' if enc == 'frozen' else 'hot_q_400k'}", "MD-Q", OKABE_ITO["blue"]),
        ]:
            c = curves.get(exp)
            if not c:
                continue
            value = baseline_at_full(curves, enc) if "tm_ref" in exp else c.best_mae
            bars.append(value)
            labels.append(f"{prefix}\n{name}")
            colors.append(color)
    xpos = np.arange(len(bars))
    ax.bar(xpos, bars, color=colors, width=0.72)
    for x, y in zip(xpos, bars):
        ax.text(x, y + 0.015, f"{y:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels)
    ax.set_ylabel("best MAE (deg C)")
    ax.set_ylim(6.35, 7.55)
    ax.set_title("Best performance by condition")
    polish(ax)
    panel(ax, "D")

    save_figure(fig, "fig_pub01_main_scaling")


FEATURE_PAIRS = [
    ("Q HPHIL 400K", "frozen_q_400k", "hot_q_400k"),
    ("Q HPHIL 300K", "frozen_q_hphil_full", "hot_qhphil_alone_640"),
    ("Q min", "frozen_q_min", "hot_q_min"),
    ("Q std", "frozen_q_std", "hot_q_std"),
    ("Q slope", "frozen_q_slope", "hot_q_slope"),
    ("Q low-flex", "frozen_q_lowflex_full", "hot_lowflex_sweep"),
    ("Q framework", "frozen_q_framework", "hot_q_framework"),
    ("RMSF max", "frozen_rmsf_max", "hot_rmsf_max"),
    ("Rg std", "frozen_rg_std", "hot_rg_std"),
    ("SS dist mean", "frozen_ss_dist_mean", "hot_ss_dist_mean"),
    ("SS dist std", "frozen_ss_dist_std", None),
    ("CDR3 length", "frozen_cdr3_len", "hot_cdr3_len"),
]


def feature_color(name: str) -> str:
    if name.startswith("Q"):
        return OKABE_ITO["blue"]
    if "RMSF" in name or "Rg" in name:
        return OKABE_ITO["orange"]
    return OKABE_ITO["purple"]


def fig02_md_feature_survey(curves_list: list[Curve]) -> None:
    curves = curve_by_exp(curves_list)
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.0), constrained_layout=True)

    for ax, enc, col_idx, letter in [
        (axes[0, 0], "frozen", 1, "A"),
        (axes[0, 1], "hot", 2, "B"),
    ]:
        rows = []
        for name, fz, ht in FEATURE_PAIRS:
            exp = fz if enc == "frozen" else ht
            if exp and curves.get(exp):
                rows.append((name, curves[exp].best_mae, curves[exp].best_ci_width))
        rows.sort(key=lambda x: x[1])
        y = np.arange(len(rows))
        vals = [r[1] for r in rows]
        ax.barh(y, vals, color=[feature_color(r[0]) for r in rows], height=0.68)
        for yi, value in zip(y, vals):
            ax.text(value + 0.015, yi, f"{value:.2f}", va="center", fontsize=6.5)
        b = baseline_at_full(curves, enc)
        if b:
            ax.axvline(b, color=OKABE_ITO["red"], linestyle="--", linewidth=1.2, label=f"Tm only {b:.2f}")
        ax.set_yticks(y)
        ax.set_yticklabels([r[0] for r in rows])
        ax.invert_yaxis()
        ax.set_xlabel("best MAE (deg C)")
        ax.set_title(f"{enc.capitalize()} MD-feature ranking")
        ax.set_xlim(min(vals) - 0.08, max(max(vals), b or max(vals)) + 0.25)
        ax.legend(frameon=False, loc="upper right")
        polish(ax)
        panel(ax, letter)

    ax = axes[1, 0]
    for exp, label, color, marker, ls in [
        ("frozen_q_hphil_full", "HPHIL 300K frozen", OKABE_ITO["sky"], "o", "--"),
        ("frozen_q_400k", "HPHIL 400K frozen", OKABE_ITO["blue"], "o", "-"),
        ("hot_q_slope", "slope 300K hot", OKABE_ITO["orange"], "s", "--"),
        ("hot_q_slope_400k", "slope 400K hot", OKABE_ITO["red"], "s", "-"),
    ]:
        c = curves.get(exp)
        if c:
            plot_curve(ax, c, color, label, marker=marker, linestyle=ls)
    ax.set_xscale("log")
    ax.set_xlabel("MD labels")
    ax.set_ylabel("MAE (deg C)")
    ax.set_title("Temperature and feature trajectory effects")
    ax.legend(frameon=False, ncol=1)
    polish(ax)
    panel(ax, "C")

    ax = axes[1, 1]
    xs, ys, labels, colors = [], [], [], []
    for name, fz, ht in FEATURE_PAIRS:
        if ht and curves.get(fz) and curves.get(ht):
            xs.append(curves[fz].best_mae)
            ys.append(curves[ht].best_mae)
            labels.append(name)
            colors.append(feature_color(name))
    ax.scatter(xs, ys, s=42, c=colors, edgecolor="white", linewidth=0.5, zorder=3)
    offsets = {
        "Q HPHIL 400K": (5, -9),
        "Q HPHIL 300K": (5, 4),
        "Q min": (6, -13),
        "Q std": (5, -8),
        "Q slope": (5, 3),
        "Q low-flex": (5, 4),
        "Q framework": (5, 4),
        "RMSF max": (5, 12),
        "Rg std": (5, -6),
        "SS dist mean": (5, -8),
        "CDR3 length": (5, 4),
    }
    for x, yv, label in zip(xs, ys, labels):
        dx, dy = offsets.get(label, (4, 3))
        ax.annotate(
            label,
            (x, yv),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=5.8,
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.72),
        )
    bf, bh = baseline_at_full(curves, "frozen"), baseline_at_full(curves, "hot")
    if bf and bh:
        ax.scatter([bf], [bh], marker="*", s=95, color=OKABE_ITO["red"], edgecolor="white", zorder=4, label="Tm only")
    ax.set_xlabel("frozen best MAE (deg C)")
    ax.set_ylabel("hot best MAE (deg C)")
    ax.set_title("Encoder effect by feature")
    ax.legend(frameon=False, loc="lower right")
    polish(ax)
    panel(ax, "D")

    save_figure(fig, "fig_pub02_md_feature_survey")


def short_curves(curves: dict[str, Curve], enc: str) -> list[tuple[int, Curve]]:
    out = []
    for exp, c in curves.items():
        match = re.match(rf"short_{enc}_t(\d+)$", exp)
        if match:
            out.append((int(match.group(1)), c))
    return sorted(out)


def fig03_trajectory_cost(curves_list: list[Curve]) -> None:
    curves = curve_by_exp(curves_list)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.4), constrained_layout=True)

    for ax, enc, letter in [(axes[0, 0], "frozen", "A"), (axes[0, 1], "hot", "B")]:
        rows = short_curves(curves, enc)
        if rows:
            x = np.array([r[0] for r in rows], dtype=float)
            mae = np.array([r[1].best_mae for r in rows])
            lo = np.array([r[1].ci_lo[0] for r in rows])
            hi = np.array([r[1].ci_hi[0] for r in rows])
            ax.fill_between(x, lo, hi, color=OKABE_ITO["sky"], alpha=0.18, lw=0)
            ax.plot(x, mae, marker="o", color=OKABE_ITO["blue"], label="short MD-Q")
        b = baseline_at_full(curves, enc)
        if b:
            ax.axhline(b, color=OKABE_ITO["red"], linestyle="--", linewidth=1.2, label=f"Tm only {b:.2f}")
        fep = curves.get(f"fep_{enc}")
        if fep:
            ax.axhline(fep.best_mae, color=OKABE_ITO["green"], linestyle=":", linewidth=1.4, label=f"FEP best {fep.best_mae:.2f}")
        ax.set_xscale("log")
        ax.set_xticks([5, 10, 17, 30, 50, 100])
        ax.set_xticklabels(["5", "10", "17", "30", "50", "100"])
        ax.set_xlabel("trajectory length (ns)")
        ax.set_ylabel("MAE (deg C)")
        ax.set_title(f"{enc.capitalize()} short-trajectory sweep")
        ax.legend(frameon=False)
        polish(ax)
        panel(ax, letter)

    ax = axes[1, 0]
    q_rows = []
    for ns in [5, 10, 17, 30, 50, 100]:
        path = REPO / "data" / "md" / f"feat_q_hphil_400K_t{ns}ns.csv"
        if path.exists():
            df = pd.read_csv(path)
            q = df["q_value_raw"].to_numpy()
            q_rows.append((ns, np.nanpercentile(q, 10), np.nanmedian(q), np.nanpercentile(q, 90)))
    if q_rows:
        x = np.array([r[0] for r in q_rows], dtype=float)
        q10 = np.array([r[1] for r in q_rows])
        q50 = np.array([r[2] for r in q_rows])
        q90 = np.array([r[3] for r in q_rows])
        ax.fill_between(x, q10, q90, color=OKABE_ITO["gray"], alpha=0.22, label="10-90 percentile")
        ax.plot(x, q50, marker="o", color=OKABE_ITO["black"], label="median")
    ax.set_xscale("log")
    ax.set_xticks([5, 10, 17, 30, 50, 100])
    ax.set_xticklabels(["5", "10", "17", "30", "50", "100"])
    ax.set_xlabel("trajectory length (ns)")
    ax.set_ylabel("raw Q value")
    ax.set_title("Q-value distribution widens with trajectory length")
    ax.legend(frameon=False)
    polish(ax)
    panel(ax, "C")

    ax = axes[1, 1]
    labels, values, colors = [], [], []
    for enc, color in [("frozen", OKABE_ITO["purple"]), ("hot", OKABE_ITO["orange"])]:
        b = baseline_at_full(curves, enc)
        if b is None:
            continue
        for ns, c in short_curves(curves, enc):
            labels.append(f"{enc[0].upper()} {ns}")
            values.append(c.best_mae - b)
            colors.append(color)
    order = np.argsort(values)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    colors = [colors[i] for i in order]
    x = np.arange(len(values))
    ax.bar(x, values, color=colors, width=0.72)
    ax.axhline(0, color=OKABE_ITO["black"], linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("MAE minus Tm-only baseline (deg C)")
    ax.set_title("Accuracy gain from short MD-Q")
    handles = [
        plt.Line2D([0], [0], color=OKABE_ITO["purple"], lw=6, label="Frozen"),
        plt.Line2D([0], [0], color=OKABE_ITO["orange"], lw=6, label="Hot"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left")
    polish(ax)
    panel(ax, "D")

    save_figure(fig, "fig_pub03_trajectory_cost")


def source_family_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["family", "encoder"], dropna=False)
        .agg(best_mae=("best_mae", "min"), n=("exp", "count"))
        .reset_index()
    )
    return grouped.sort_values("best_mae")


def fig04_all_results_landscape(curves_list: list[Curve], summary: pd.DataFrame, history: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 7.2), constrained_layout=True)

    ax = axes[0, 0]
    top = summary.sort_values("best_mae").head(28).iloc[::-1]
    y = np.arange(len(top))
    ax.barh(y, top["best_mae"], color=[FAMILY_COLORS.get(f, OKABE_ITO["gray"]) for f in top["family"]], height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(top["exp"], fontsize=5.8)
    ax.set_xlabel("best MAE (deg C)")
    ax.set_title("Top structured results")
    ax.set_xlim(6.45, max(7.95, top["best_mae"].max() + 0.1))
    polish(ax)
    panel(ax, "A")

    ax = axes[0, 1]
    df = summary.dropna(subset=["slope"]).copy()
    df = df[np.isfinite(df["slope"])]
    for family, sub in df.groupby("family"):
        color = FAMILY_COLORS.get(family, OKABE_ITO["gray"])
        for enc, sub2 in sub.groupby("encoder"):
            ax.scatter(
                sub2["slope"],
                sub2["best_mae"],
                s=38,
                c=color,
                marker=ENC_MARKERS.get(enc, "o"),
                edgecolor="white",
                linewidth=0.45,
                label=family if enc == list(sub.groupby("encoder").groups.keys())[0] else None,
                alpha=0.9,
            )
    ax.set_xlabel("power-law slope b")
    ax.set_ylabel("best MAE (deg C)")
    ax.set_title("Scaling slope versus accuracy")
    ax.legend(frameon=False, fontsize=6.2, loc="upper right")
    polish(ax)
    panel(ax, "B")

    ax = axes[0, 2]
    for family, sub in summary.groupby("family"):
        ax.scatter(
            sub["best_ci_width"],
            sub["best_mae"],
            s=42,
            c=FAMILY_COLORS.get(family, OKABE_ITO["gray"]),
            edgecolor="white",
            linewidth=0.45,
            label=family,
            alpha=0.9,
        )
    ax.set_xlabel("90% bootstrap CI width (deg C)")
    ax.set_ylabel("best MAE (deg C)")
    ax.set_title("Uncertainty versus accuracy")
    polish(ax)
    panel(ax, "C")

    ax = axes[1, 0]
    group = source_family_summary(summary)
    group = group[group["encoder"].isin(["frozen", "hot", "lora"])]
    labels = [f"{r.family} ({r.encoder})" for r in group.itertuples()]
    group = group.iloc[::-1]
    labels = labels[::-1]
    y = np.arange(len(group))
    ax.barh(y, group["best_mae"], color=[FAMILY_COLORS.get(f, OKABE_ITO["gray"]) for f in group["family"]], height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6.3)
    ax.set_xlabel("best MAE (deg C)")
    ax.set_title("Best result by source family")
    ax.set_xlim(6.45, max(8.1, group["best_mae"].max() + 0.1))
    polish(ax)
    panel(ax, "D")

    ax = axes[1, 1]
    selected = [
        "hot_lowflex_sweep",
        "hot_650m_lowflex_640",
        "lora_650m_lowflex_640",
        "hot_qhphil_alone_640",
        "md_weight_w1.0",
        "md_weight_w8.0",
    ]
    rows = summary[summary["exp"].isin(selected)].copy()
    rows["label"] = rows["exp"].replace(
        {
            "hot_lowflex_sweep": "8M hot\nQ low-flex",
            "hot_650m_lowflex_640": "650M hot\nQ low-flex",
            "lora_650m_lowflex_640": "650M LoRA\nQ low-flex",
            "hot_qhphil_alone_640": "8M hot\nQ HPHIL",
            "md_weight_w1.0": "fixed w=1",
            "md_weight_w8.0": "fixed w=8",
        }
    )
    rows = rows.sort_values("best_mae")
    x = np.arange(len(rows))
    ax.bar(x, rows["best_mae"], color=[FAMILY_COLORS.get(f, OKABE_ITO["gray"]) for f in rows["family"]])
    for xi, yi in zip(x, rows["best_mae"]):
        ax.text(xi, yi + 0.015, f"{yi:.2f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(x)
    ax.set_xticklabels(rows["label"], rotation=35, ha="right")
    ax.set_ylabel("best MAE (deg C)")
    ax.set_title("Architecture and weighting checks")
    ax.set_ylim(6.55, 7.65)
    polish(ax)
    panel(ax, "E")

    ax = axes[1, 2]
    if not history.empty:
        colors = []
        for _, row in history.iterrows():
            if isinstance(row.get("md_source"), str) and row["md_source"] and row["md_source"] != "none":
                colors.append(FAMILY_COLORS["MD Q"] if "Q" in row["md_source"] else FAMILY_COLORS["MD structure"])
            elif isinstance(row.get("ddg_source"), str) and row["ddg_source"] and row["ddg_source"] != "none":
                colors.append(FAMILY_COLORS["Physics ddG"])
            else:
                colors.append(FAMILY_COLORS["Tm reference"])
        ax.scatter(history["timestamp"], history["mae_mean"], s=14, c=colors, alpha=0.55, linewidth=0)
        running = history["mae_mean"].cummin()
        ax.plot(history["timestamp"], running, color=OKABE_ITO["black"], linewidth=1.3, label="running best")
    ax.set_ylabel("mean MAE (deg C)")
    ax.set_title("Experiment log trajectory")
    ax.tick_params(axis="x", rotation=35)
    ax.legend(frameon=False)
    polish(ax)
    panel(ax, "F")

    save_figure(fig, "fig_pub04_all_results_landscape")


def main() -> None:
    configure_style()
    curves = load_curves()
    summary = as_summary_frame(curves)
    history = read_history()
    summary_path = PLOT / "publication_results_summary.tsv"
    summary.to_csv(summary_path, sep="\t", index=False)
    print(f"loaded {len(curves)} structured results")
    print(f"wrote {summary_path}")

    fig01_main_scaling(curves)
    fig02_md_feature_survey(curves)
    fig03_trajectory_cost(curves)
    fig04_all_results_landscape(curves, summary, history)


if __name__ == "__main__":
    main()
