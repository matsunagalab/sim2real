#!/usr/bin/env python3
"""Build the selected supplementary figures for the current two-axis paper.

The script reads final held-out results, staged-validation runs, and tracked
processed label tables. It writes compact TSV audit tables and two figures to
paper/analysis/supplementary/ and paper/tex/figures/. It never launches training.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("XDG_CACHE_HOME", "/tmp/codex-cache")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache-codex")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import yeojohnson


REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
DATA = REPO / "data"
PAPER = REPO / "paper"
ANALYSIS = PAPER / "analysis" / "supplementary"
TABLES = ANALYSIS / "tables"
ANALYSIS_FIGS = ANALYSIS / "figures"
TEX_FIGS = PAPER / "tex" / "figures"

COL = {
    "black": "#222222", "gray": "#6F6F6F", "light": "#D9D9D9",
    "grid": "#E8E8E8", "fep": "#009E73", "md": "#D55E00",
    "design": "#0072B2",
}

SOURCES = ["Tm_only", "FEP", "MD_FEP400K", "thermoMPNN", "rosetta", "rosetta_random", "rosetta_esm"]
STEMS = {"Tm_only": "tm", "FEP": "fep", "MD_FEP400K": "mdq", "thermoMPNN": "tmpnn",
         "rosetta": "ros", "rosetta_random": "rosrnd", "rosetta_esm": "rosesm"}
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


def final_run(source: str, regime: str) -> dict:
    return read_json(RESULTS / f"final_{STEMS[source]}_{regime}" / "scaling.json")


def representative(run: dict) -> dict:
    points = run["scaling"]
    return points[0] if len(points) == 1 else max(points, key=lambda x: int(x["n"]))


def paired_delta(reference, candidate, level: float = 0.90, seed: int = 42) -> tuple[float, float, float]:
    a, b = np.asarray(reference, float), np.asarray(candidate, float)
    if len(a) != len(b):
        raise ValueError("paired comparisons require equal-length error vectors")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), size=(10000, len(a)))
    boot = (b[idx] - a[idx]).mean(axis=1)
    q = (1.0 - level) * 50.0
    lo, hi = np.percentile(boot, [q, 100.0 - q])
    return float((b - a).mean()), float(lo), float(hi)


def panel_label(ax, letter: str) -> None:
    ax.text(-0.22, 1.10, f"({letter})", transform=ax.transAxes, fontsize=12.0,
            fontweight="bold", ha="left", va="top", clip_on=False)


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
    for directory in (ANALYSIS_FIGS, TEX_FIGS):
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(directory / f"{stem}.pdf", bbox_inches="tight")
        fig.savefig(directory / f"{stem}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {TEX_FIGS / (stem + '.pdf')}")


def data_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source_specs = [
        ("Tm train", [DATA / "nbbench/train.csv"]), ("Tm validation", [DATA / "nbbench/val.csv"]),
        ("Tm test", [DATA / "nbbench/test.csv"]),
        ("FEP", [DATA / "source_labels/fep/fep1mel_435_processed.csv", DATA / "source_labels/fep/fep4idl_409_processed.csv"]),
        ("matched MD", [DATA / "source_labels/md_fep400k/1mel_mdq_processed.csv", DATA / "source_labels/md_fep400k/4idl_mdq_processed.csv"]),
        ("Rosetta", [DATA / "source_labels/rosetta/measured/1mel_rosettaddg_processed.csv", DATA / "source_labels/rosetta/measured/4idl_rosettaddg_processed.csv"]),
        ("ThermoMPNN", [DATA / "source_labels/thermompnn/1melMPNN2_processed.csv", DATA / "source_labels/thermompnn/4idlMPNN2_processed.csv"]),
        ("random/Rosetta", [DATA / "source_labels/rosetta/random1000/random_2mut_1mel_1000_with_ddg_processed.csv", DATA / "source_labels/rosetta/random1000/random_2mut_4idl_1000_with_ddg_processed.csv"]),
        ("ESM2/Rosetta", [DATA / "source_labels/rosetta/esm1000/esm2_650M_2muts_1mel_100000_top1pct_with_ddg_processed.csv", DATA / "source_labels/rosetta/esm1000/esm2_650M_2muts_4idl_100000_top1pct_with_ddg_processed.csv"]),
        ("heterogeneous MD", [DATA / "md/nanobody_qvalue_400K.csv"]),
    ]
    counts = []
    for label, paths in source_specs:
        frames = [pd.read_csv(p) for p in paths]
        part = [len(frame) for frame in frames]
        sequences = []
        for frame in frames:
            column = "text" if "text" in frame.columns else "seq" if "seq" in frame.columns else None
            if column is not None:
                sequences.extend(frame[column].dropna().astype(str).tolist())
        counts.append({"data_set": label, "rows": sum(part),
                       "unique_sequences": len(set(sequences)) if sequences else np.nan,
                       "table_rows": "+".join(map(str, part))})

    diverse = pd.read_csv(DATA / "md/nanobody_qvalue_400K.csv")
    qrows = [pd.DataFrame({"design": "heterogeneous panel", "system": "SAbDab",
                           "sequence": diverse["seq"], "length": diverse["seq_len"],
                           "raw_q": diverse["q_value_raw"]})]
    for system in ("1mel", "4idl"):
        d = pd.read_csv(DATA / f"md/study_qvalue_fep400k_{system}.csv")
        qrows.append(pd.DataFrame({"design": "matched mutation scan", "system": system.upper(),
                                   "sequence": d["seq"], "length": d["seq"].str.len(), "raw_q": d["q_value"]}))
    qvalues = pd.concat(qrows, ignore_index=True)

    split_sets = {s: set(pd.read_csv(DATA / f"nbbench/{s}.csv")["text"]) for s in ("train", "val", "test")}
    overlap = []
    for design, group in qvalues.groupby("design"):
        seqs = set(group["sequence"])
        for split, targets in split_sets.items():
            overlap.append({"design": design, "split": split, "exact_matches": len(seqs & targets)})
    return pd.DataFrame(counts), qvalues, pd.DataFrame(overlap)


def fig_s1(qvalues: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.65), constrained_layout=True)
    div = qvalues[qvalues["design"] == "heterogeneous panel"]
    density = ax.hexbin(div["length"], div["raw_q"], gridsize=(34, 22), mincnt=1,
                        cmap="Blues", linewidths=0.25, edgecolors="white", alpha=0.95)
    for system, color in [("1MEL", COL["md"]), ("4IDL", COL["fep"])]:
        d = qvalues[(qvalues["design"] == "matched mutation scan") & (qvalues["system"] == system)]
        length = float(d["length"].iloc[0])
        ax.axvline(length, color=color, linestyle="--", linewidth=1.7,
                   label=f"{system} matched scan ({int(length)} aa)")
    r = np.corrcoef(div["length"], div["raw_q"])[0, 1]
    ax.text(0.97, 0.94, f"heterogeneous panel\nr = {r:+.2f}; n = {len(div):,}",
            transform=ax.transAxes, ha="right", va="top", fontsize=10.0,
            bbox={"facecolor": "white", "edgecolor": COL["light"], "alpha": 0.9, "pad": 4})
    ax.set_xlim(45, 475); ax.set_ylim(0, 1.02)
    ax.set_xlabel("Sequence length (residues)")
    ax.set_ylabel("Raw native-contact Q")
    ax.legend(frameon=False, loc="lower right", fontsize=9.1)
    cbar = fig.colorbar(density, ax=ax, pad=0.02, aspect=25)
    cbar.set_label("Rows per hexagon")
    polish(ax)
    save_figure(fig, "supp_fig01_data_and_design")


def candidate_table() -> pd.DataFrame:
    records = []
    for regime in ("frozen", "hot"):
        for source in SOURCES:
            stem = STEMS[source]
            prefix = "tune_s2" if source in ("Tm_only", "FEP", "MD_FEP400K") else "tune_c2"
            for path in RESULTS.glob(f"{prefix}_{stem}_{regime}_*/scaling.json"):
                run = read_json(path); args = run.get("args", {})
                if args.get("final_eval_split") != "val": continue
                point = run["scaling"][0]; hp = run.get("hparams", {})
                records.append({"regime": regime, "source": source, "validation_mae": float(point["mae"]),
                                "architecture": args.get("model_arch"),
                                "head": "-" if source == "Tm_only" else args.get("ddg_head_mode"),
                                "learning_rate": hp.get("learning_rate"), "encoder_lr": hp.get("encoder_lr"),
                                "dropout": hp.get("dropout_rate"), "weight_decay": hp.get("weight_decay"),
                                "run": str(path.relative_to(REPO))})
    if not records:
        saved = TABLES / "candidate_validation.tsv"
        if saved.exists(): return pd.read_csv(saved, sep="\t")
        raise FileNotFoundError("staged validation runs and candidate_validation.tsv are both missing")
    return pd.DataFrame(records).sort_values(["regime", "source", "validation_mae"]).reset_index(drop=True)


def selected_table(candidates: pd.DataFrame) -> pd.DataFrame:
    records = []
    for regime in ("frozen", "hot"):
        for source in SOURCES:
            selected = candidates[(candidates["regime"] == regime) & (candidates["source"] == source)].nsmallest(1, "validation_mae").iloc[0]
            run = final_run(source, regime); args, hp = run["args"], run["hparams"]
            point = representative(run)
            expected = (args.get("model_arch"), "-" if source == "Tm_only" else args.get("ddg_head_mode"),
                        hp.get("learning_rate"), hp.get("encoder_lr"), hp.get("dropout_rate"), hp.get("weight_decay"))
            observed = (selected["architecture"], selected["head"], selected["learning_rate"], selected["encoder_lr"], selected["dropout"], selected["weight_decay"])
            if expected != observed:
                raise ValueError(f"selected validation setting does not match final run: {source} {regime}\n{expected}\n{observed}")
            records.append({"regime": regime, "source": source, "validation_mae": selected["validation_mae"],
                            "test_mae": point["mae"], "ci_lo": point["ci_lo"], "ci_hi": point["ci_hi"],
                            "architecture": expected[0], "head": expected[1], "learning_rate": expected[2],
                            "encoder_lr": expected[3], "dropout": expected[4], "weight_decay": expected[5],
                            "validation_run": selected["run"],
                            "final_run": str((RESULTS / f"final_{STEMS[source]}_{regime}/scaling.json").relative_to(REPO))})
    return pd.DataFrame(records)


def effect_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    effects = []
    for regime in ("frozen", "hot"):
        base = representative(final_run("Tm_only", regime))["abs_errors"]
        for source in SOURCES:
            point = representative(final_run(source, regime))
            if source == "Tm_only": delta, lo, hi = 0.0, 0.0, 0.0
            else: delta, lo, hi = paired_delta(base, point["abs_errors"])
            effects.append({"regime": regime, "source": source, "test_mae": point["mae"],
                            "ci_lo": point["ci_lo"], "ci_hi": point["ci_hi"],
                            "delta_mae": delta, "delta_ci_lo": lo, "delta_ci_hi": hi})
    direct = []
    for regime in ("frozen", "hot"):
        fep = {int(p["n"]): p for p in final_run("FEP", regime)["scaling"]}
        md = {int(p["n"]): p for p in final_run("MD_FEP400K", regime)["scaling"]}
        for n in sorted(fep.keys() & md.keys()):
            d, lo, hi = paired_delta(md[n]["abs_errors"], fep[n]["abs_errors"])
            direct.append({"regime": regime, "n": n, "fep_minus_md": d, "ci_lo": lo, "ci_hi": hi})
    sizes = []
    specs = [
        ("8M", RESULTS / "final_tm_hot/scaling.json", RESULTS / "final_fep_hot/scaling.json", "staged-selected"),
        ("35M", RESULTS / "size35_tm_shared_drop005/scaling.json",
         RESULTS / "size35_ddg_fep_enc3e-5/scaling.json", "exploratory fixed configuration"),
        ("650M", RESULTS / "size650_tm_shared_drop005/scaling.json",
         RESULTS / "size650_ddg_fep_enc3e-5/scaling.json", "exploratory fixed configuration"),
    ]
    for size, tm_path, fep_path, design in specs:
        tm_run, fep_run = read_json(tm_path), read_json(fep_path)
        tm_point, fep_point = representative(tm_run), representative(fep_run)
        delta, lo, hi = paired_delta(tm_point["abs_errors"], fep_point["abs_errors"])
        sizes.append({"size": size, "design": design,
                      "tm_test_mae": tm_point["mae"], "fep_test_mae": fep_point["mae"],
                      "fep_minus_tm": delta, "ci_lo": lo, "ci_hi": hi,
                      "n_seeds": fep_run.get("args", {}).get("n_runs"),
                      "tm_source": str(tm_path.relative_to(REPO)),
                      "fep_source": str(fep_path.relative_to(REPO))})
    return pd.DataFrame(effects), pd.DataFrame(direct), pd.DataFrame(sizes)


def fep_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prov = pd.read_csv(DATA / "source_labels/fep/PROVENANCE.tsv", sep="\t")
    prov = prov[prov["pos"] > 0].copy()
    composition = prov.groupby(["system", "mut"], as_index=False).size().rename(columns={"size": "rows"})
    def scale(values) -> np.ndarray:
        """Robust -> Yeo-Johnson -> standardize -> min-max, matching convert_yj.ipynb."""
        x = np.asarray(values, float)
        iqr = np.percentile(x, 75) - np.percentile(x, 25)
        x = (x - np.median(x)) / iqr
        x, _ = yeojohnson(x)
        x = (x - x.mean()) / x.std()
        return (x - x.min()) / (x.max() - x.min())
    sensitivity = []
    corrected_rows = []
    for name, amount in [("periodicity eps=97", 0.069), ("periodicity eps=78", 0.086),
                         ("sensitivity 0.5", 0.5), ("sensitivity 1.5", 1.5)]:
        all_u, all_c = [], []
        for system, g in prov.groupby("system"):
            raw = -g["ddg"].to_numpy()
            corrected = -(g["ddg"] + amount * g["dq"]**2).to_numpy()
            u, c = scale(raw), scale(corrected)
            all_u.extend(u); all_c.extend(c)
            if name == "periodicity eps=78":
                corrected_rows.extend({"system": system, "dq": int(dq),
                                       "unadjusted": a, "corrected": b}
                                      for a, b, dq in zip(u, c, g["dq"]))
        u, c = np.asarray(all_u), np.asarray(all_c)
        sensitivity.append({"correction": name, "kcal_per_dq2": amount, "label_correlation": np.corrcoef(u, c)[0, 1],
                            "max_abs_scaled_shift": np.max(np.abs(u-c)), "rows_shifted_gt_0.02": int(np.sum(np.abs(u-c) > .02))})
    return composition, pd.DataFrame(sensitivity), pd.DataFrame(corrected_rows), prov


def fig_s2_controls(sizes: pd.DataFrame, corrected: pd.DataFrame) -> None:
    """Plot only the two robustness checks used in the manuscript."""
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.45), constrained_layout=True)

    ax = axes[0]
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
        ax.text(hi[i] + 0.006, y[i], f"{mid[i]:+.2f}", ha="left", va="center",
                fontsize=9.0, fontweight="bold", color=COL["fep"])
    ax.set_yticks(y, order); ax.invert_yaxis()
    ax.set_xlim(min(-0.38, float(lo.min()) - 0.03), 0.04)
    ax.set_xlabel("FEP − Tm-only, paired ΔMAE (°C)")
    ax.set_ylabel("ESM2 encoder size")
    ax.set_title("FEP effect across encoder sizes", loc="left", fontweight="bold")
    polish(ax, "x"); panel_label(ax, "a")

    ax = axes[1]
    d = corrected.copy()
    d["shift"] = d["corrected"] - d["unadjusted"]
    neutral = d["dq"] == 0
    ax.scatter(d.loc[neutral, "unadjusted"], d.loc[neutral, "shift"],
               s=13, alpha=0.30, color=COL["gray"], edgecolor="none", label="Δq = 0")
    ax.scatter(d.loc[~neutral, "unadjusted"], d.loc[~neutral, "shift"],
               s=16, alpha=0.48, color=COL["md"], edgecolor="none", label="Δq ≠ 0")
    ax.axhline(0, color=COL["black"], linewidth=1.0, linestyle="--")
    corr = np.corrcoef(d["unadjusted"], d["corrected"])[0, 1]
    shift = float(np.max(np.abs(d["shift"])))
    limit = max(0.009, shift * 1.16)
    ax.set_ylim(-limit, limit)
    ax.text(0.04, 0.94, f"284/844 charge-changing\nr = {corr:.5f}\nmax |shift| = {shift:.3f}",
            transform=ax.transAxes, va="top", fontsize=8.8,
            bbox={"facecolor": "white", "edgecolor": COL["light"], "alpha": 0.9, "pad": 3})
    ax.set_xlabel("Unadjusted scaled FEP label")
    ax.set_ylabel("Corrected − unadjusted label")
    ax.set_title("Net-charge correction", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="lower left", ncol=2, fontsize=8.2)
    polish(ax); panel_label(ax, "b")

    save_figure(fig, "supp_fig02_transfer_controls")


def write_manifest() -> None:
    rows = []
    specs = {
        "Supplementary Fig. S1": ("supp_fig01_data_and_design.pdf", ["data_design_qvalues.tsv"],
                                   ["Q versus sequence length"]),
        "Supplementary Fig. S2": ("supp_fig02_transfer_controls.pdf",
                                   ["model_size_controls.tsv", "fep_charge_corrected_labels.tsv"],
                                   ["paired FEP effect across ESM2 sizes", "per-label periodicity shift"]),
    }
    for figure, (file, tables, questions) in specs.items():
        for i, question in enumerate(questions):
            panel = "-" if len(questions) == 1 else chr(65+i)
            rows.append({"figure": figure, "panel": panel, "figure_file": f"figures/{file}",
                         "tex_figure_file": f"../../tex/figures/{file}", "source_tables": ";".join(f"tables/{t}" for t in tables),
                         "generator": "plot/make_supplementary_figures.py", "question": question})
    pd.DataFrame(rows).to_csv(ANALYSIS / "MANIFEST.tsv", sep="\t", index=False)


def main() -> None:
    configure_style()
    counts, qvalues, overlap = data_tables()
    candidates = candidate_table(); selected = selected_table(candidates)
    effects, direct, sizes = effect_tables()
    composition, sensitivity, corrected, provenance = fep_tables()
    for df, name in [(counts, "data_sources.tsv"), (qvalues, "data_design_qvalues.tsv"), (overlap, "sequence_overlap.tsv"),
                     (candidates, "candidate_validation.tsv"), (selected, "selected_settings.tsv"),
                     (effects, "final_source_effects.tsv"), (direct, "fep_md_direct.tsv"), (sizes, "model_size_controls.tsv"),
                     (composition, "fep_scan_composition.tsv"), (sensitivity, "fep_charge_sensitivity.tsv"),
                     (corrected, "fep_charge_corrected_labels.tsv")]:
        save_table(df, name)
    fig_s1(qvalues)
    fig_s2_controls(sizes, corrected)
    write_manifest()
    print("supplementary figure build complete")


if __name__ == "__main__":
    main()
