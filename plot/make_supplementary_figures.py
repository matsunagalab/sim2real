#!/usr/bin/env python3
"""Build the supplementary figure for the current paper.

The Supplementary Materials contain a single figure: FEP minus Tm-only test MAE
across ESM2 encoder sizes (Supplementary Fig. S1). The 8M anchor is the 24-model,
matched-variant result used in the main physical-observable comparison; the 35M
and 650M points are exploratory fixed-configuration checks. The script reads only
tracked held-out result JSONs and never launches training.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

os.environ.setdefault("XDG_CACHE_HOME", "/tmp/codex-cache")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache-codex")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
PAPER = REPO / "paper"
ANALYSIS = PAPER / "analysis" / "supplementary"
TABLES = ANALYSIS / "tables"
ANALYSIS_FIGS = ANALYSIS / "figures"
TEX_FIGS = PAPER / "tex" / "figures"

COL = {"black": "#222222", "grid": "#E8E8E8", "fep": "#009E73"}


def configure_style() -> None:
    plt.rcParams.update({
        "figure.dpi": 160, "savefig.dpi": 600, "savefig.facecolor": "white",
        "pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "DejaVu Sans",
        "font.size": 10.3, "axes.titlesize": 10.5, "axes.labelsize": 10.0,
        "xtick.labelsize": 9.4, "ytick.labelsize": 9.4, "legend.fontsize": 9.1,
        "axes.linewidth": 0.95, "axes.spines.top": True, "axes.spines.right": True,
        "lines.linewidth": 1.7, "lines.markersize": 6.5,
    })


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def representative(run: dict) -> dict:
    points = run["scaling"]
    return points[0] if len(points) == 1 else max(points, key=lambda x: int(x["n"]))


def paired_delta(reference, candidate, level: float = 0.95, seed: int = 42) -> tuple[float, float, float]:
    a, b = np.asarray(reference, float), np.asarray(candidate, float)
    if len(a) != len(b):
        raise ValueError("paired comparisons require equal-length error vectors")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(10000, len(a)))
    boot = (b[idx] - a[idx]).mean(axis=1)
    q = (1.0 - level) * 50.0
    lo, hi = np.percentile(boot, [q, 100.0 - q])
    return float((b - a).mean()), float(lo), float(hi)


def polish(ax, axis: str = "both") -> None:
    ax.set_axisbelow(True)
    ax.grid(True, axis=axis, color=COL["grid"], linewidth=0.7)
    ax.tick_params(width=0.9, length=3.5)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.9)
        spine.set_color(COL["black"])


def save_table(df: pd.DataFrame, name: str) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / name, sep="\t", index=False)


def save_figure(fig, stem: str) -> None:
    ANALYSIS_FIGS.mkdir(parents=True, exist_ok=True)
    TEX_FIGS.mkdir(parents=True, exist_ok=True)
    for suffix, kwargs in (("pdf", {}), ("png", {"dpi": 600})):
        source = ANALYSIS_FIGS / f"{stem}.{suffix}"
        target = TEX_FIGS / f"{stem}.{suffix}"
        fig.savefig(source, bbox_inches="tight", **kwargs)
        shutil.copyfile(source, target)
    plt.close(fig)
    print(f"wrote {TEX_FIGS / (stem + '.pdf')}")


def size_controls() -> pd.DataFrame:
    """FEP minus Tm-only across ESM2 encoder sizes."""
    specs = [
        ("8M", RESULTS / "n24_tm_hot_shared/scaling.json",
         RESULTS / "fig3_FEP_hot/scaling.json", "matched, 24-model"),
        ("35M", RESULTS / "size35_tm_shared_drop005/scaling.json",
         RESULTS / "size35_ddg_fep_enc3e-5/scaling.json", "exploratory fixed configuration"),
        ("650M", RESULTS / "size650_tm_shared_drop005/scaling.json",
         RESULTS / "size650_ddg_fep_enc3e-5/scaling.json", "exploratory fixed configuration"),
    ]
    rows = []
    for size, tm_path, fep_path, design in specs:
        tm_run, fep_run = read_json(tm_path), read_json(fep_path)
        tm_point, fep_point = representative(tm_run), representative(fep_run)
        delta, lo, hi = paired_delta(tm_point["abs_errors"], fep_point["abs_errors"])
        rows.append({"size": size, "design": design,
                     "tm_test_mae": tm_point["mae"], "fep_test_mae": fep_point["mae"],
                     "fep_minus_tm": delta, "ci_lo": lo, "ci_hi": hi,
                     "n_seeds": fep_run.get("args", {}).get("n_runs"),
                     "tm_source": str(tm_path.relative_to(REPO)),
                     "fep_source": str(fep_path.relative_to(REPO))})
    return pd.DataFrame(rows)


def fig_s2_controls(sizes: pd.DataFrame) -> None:
    """Supplementary Fig. S1: the FEP result across ESM2 encoder sizes."""
    fig, ax = plt.subplots(figsize=(5.2, 3.1), constrained_layout=True)
    order = ["8M", "35M", "650M"]
    d = sizes.set_index("size").loc[order]
    y = np.arange(len(order))
    mid = d["fep_minus_tm"].to_numpy(float)
    lo = d["ci_lo"].to_numpy(float)
    hi = d["ci_hi"].to_numpy(float)
    ax.axvline(0, color=COL["black"], linewidth=1.0, linestyle="--")
    for i in range(len(order)):
        face = COL["fep"] if i == 0 else "white"
        ax.errorbar(mid[i], y[i], xerr=[[mid[i] - lo[i]], [hi[i] - mid[i]]],
                    fmt="o", color=COL["fep"], markerfacecolor=face,
                    markeredgecolor=COL["fep"], markeredgewidth=1.3,
                    markersize=7.8, capsize=4.0, elinewidth=1.6, zorder=3)
        ax.text(hi[i] + 0.008, y[i], f"{mid[i]:+.2f}", ha="left", va="center",
                fontsize=9.0, fontweight="bold", color=COL["fep"])
    ax.set_yticks(y, order)
    ax.set_ylim(-0.8, len(order) - 1 + 0.8)
    ax.invert_yaxis()
    ax.set_xlim(min(-0.38, float(lo.min()) - 0.03), 0.09)
    ax.set_xlabel(r"FEP $-$ Tm-only, $\Delta$MAE (°C)")
    ax.set_ylabel("ESM2 encoder size")
    polish(ax, "x")
    save_figure(fig, "supp_fig02_transfer_controls")


def write_manifest() -> None:
    rows = [{"figure": "Supplementary Fig. S1", "panel": "-",
             "figure_file": "figures/supp_fig02_transfer_controls.pdf",
             "tex_figure_file": "../../tex/figures/supp_fig02_transfer_controls.pdf",
             "source_tables": "tables/model_size_controls.tsv",
             "generator": "plot/make_supplementary_figures.py",
             "question": "FEP effect across ESM2 sizes"}]
    pd.DataFrame(rows).to_csv(ANALYSIS / "MANIFEST.tsv", sep="\t", index=False)


def main() -> None:
    configure_style()
    sizes = size_controls()
    save_table(sizes, "model_size_controls.tsv")
    fig_s2_controls(sizes)
    write_manifest()
    print("supplementary figure build complete")


if __name__ == "__main__":
    main()
