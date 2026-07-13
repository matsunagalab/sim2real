#!/usr/bin/env python3
"""Build the selected supplementary figures for the current two-axis paper.

The script reads final held-out results, staged-validation runs, and tracked
processed label tables. It writes compact TSV audit tables and four figures to
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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
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
    "grid": "#E8E8E8", "tm": "#4D4D4D", "fep": "#009E73",
    "md": "#D55E00", "rosetta": "#E69F00", "thermo": "#CC79A7",
    "design": "#0072B2", "soft_blue": "#E7F0F7", "soft_green": "#E6F4EF",
    "soft_orange": "#FAF0DC", "soft_red": "#F8E7DF", "soft_gray": "#F3F3F3",
}

SOURCES = ["Tm_only", "FEP", "MD_FEP400K", "thermoMPNN", "rosetta", "rosetta_random", "rosetta_esm"]
STEMS = {"Tm_only": "tm", "FEP": "fep", "MD_FEP400K": "mdq", "thermoMPNN": "tmpnn",
         "rosetta": "ros", "rosetta_random": "rosrnd", "rosetta_esm": "rosesm"}
LABEL = {"Tm_only": "Tm labels only", "FEP": "FEP mutation\nfree energy",
         "MD_FEP400K": "MD native contact\n(matched scan)", "thermoMPNN": "ThermoMPNN",
         "rosetta": "Rosetta mutation\nscore", "rosetta_random": "random variants\n+ Rosetta",
         "rosetta_esm": "ESM2-proposed\nvariants + Rosetta"}
SHORT = {"Tm_only": "Tm only", "FEP": "FEP", "MD_FEP400K": "matched MD",
         "thermoMPNN": "ThermoMPNN", "rosetta": "Rosetta",
         "rosetta_random": "random/Rosetta", "rosetta_esm": "ESM2/Rosetta"}
COLOR = {"Tm_only": COL["tm"], "FEP": COL["fep"], "MD_FEP400K": COL["md"],
         "thermoMPNN": COL["thermo"], "rosetta": "#B9770E",
         "rosetta_random": COL["rosetta"], "rosetta_esm": COL["design"]}


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


def interval(ax, y, mid, lo, hi, color, marker="o", label=None) -> None:
    ax.errorbar(mid, y, xerr=[[mid - lo], [hi - mid]], fmt=marker, color=color,
                ecolor=color, elinewidth=1.5, capsize=3.8, markersize=7,
                markeredgecolor="white", markeredgewidth=0.7, label=label, zorder=3)


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


def ecdf(values) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(np.asarray(values, float))
    return x, np.arange(1, len(x) + 1) / len(x)


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


def fig_s1(counts: pd.DataFrame, qvalues: pd.DataFrame, overlap: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 6.35), constrained_layout=True)
    ax = axes[0, 0]
    shown = counts.iloc[::-1]
    colors = []
    for name in shown["data_set"]:
        if name.startswith("Tm"):
            colors.append(COL["tm"])
        elif name == "FEP":
            colors.append(COL["fep"])
        elif name == "matched MD":
            colors.append(COL["md"])
        elif name == "heterogeneous MD":
            colors.append(COL["design"])
        else:
            colors.append(COL["gray"])
    display_names = {"Tm train": "Tm train", "Tm validation": "Tm validation",
                     "Tm test": "Tm test", "FEP": "FEP", "matched MD": "matched MD",
                     "Rosetta": "Rosetta", "ThermoMPNN": "ThermoMPNN",
                     "random/Rosetta": "random/Rosetta", "ESM2/Rosetta": "ESM2/Rosetta",
                     "heterogeneous MD": "heterog. MD"}
    ax.barh([display_names[x] for x in shown["data_set"]], shown["rows"], color=colors, alpha=0.9)
    ax.set_xscale("log"); ax.set_xlabel("Processed rows (log scale)")
    for y, (_, r) in enumerate(shown.iterrows()):
        if r["data_set"] == "heterogeneous MD":
            label = f"{int(r['rows']):,}; {int(r['unique_sequences']):,} unique"
        elif "+" in str(r["table_rows"]):
            label = f"{int(r['rows']):,}"
        else:
            label = f"{int(r['rows']):,}"
        if r["rows"] >= 1000:
            ax.text(r["rows"] * 0.96, y, label, va="center", ha="right",
                    fontsize=7.8, color="white", fontweight="bold", clip_on=True)
        else:
            ax.text(r["rows"] * 1.08, y, label, va="center", fontsize=8.2, clip_on=True)
    ax.set_xlim(35, 4500)
    ax.set_title("Label counts", loc="left", fontweight="bold")
    polish(ax, "x"); panel_label(ax, "a")

    ax = axes[0, 1]
    specs = [("heterogeneous panel", None, COL["design"], "-"),
             ("matched mutation scan", "1MEL", COL["md"], "-"),
             ("matched mutation scan", "4IDL", COL["md"], "--")]
    for design, system, color, ls in specs:
        d = qvalues[qvalues["design"] == design]
        if system is not None: d = d[d["system"] == system]
        x, y = ecdf(np.maximum(1.0 - d["raw_q"].to_numpy(float), 1e-5))
        label = "heterogeneous" if system is None else system
        ax.plot(x, y, color=color, linestyle=ls, linewidth=1.8, label=label)
    ax.set_xscale("log")
    ax.set_xlabel(r"Native-contact loss, $1-Q$")
    ax.set_ylabel("Cumulative fraction")
    ax.set_title("Native-contact loss", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left", handlelength=2.0, fontsize=8.3)
    polish(ax); panel_label(ax, "b")

    ax = axes[1, 0]
    div = qvalues[qvalues["design"] == "heterogeneous panel"]
    ax.hexbin(div["length"], div["raw_q"], gridsize=(25, 18), mincnt=1,
              cmap="Blues", linewidths=0.25, edgecolors="white", alpha=0.92)
    handles = [Patch(facecolor=COL["design"], edgecolor="none", label="heterogeneous")]
    for system, color in [("1MEL", COL["md"]), ("4IDL", COL["md"])]:
        d = qvalues[(qvalues["design"] == "matched mutation scan") & (qvalues["system"] == system)]
        parts = ax.violinplot([d["raw_q"].to_numpy(float)],
                             positions=[float(d["length"].iloc[0])], widths=15,
                             showmeans=False, showextrema=False, showmedians=True)
        for body in parts["bodies"]:
            body.set_facecolor(color); body.set_edgecolor("white"); body.set_alpha(0.55)
        parts["cmedians"].set_color(COL["black"]); parts["cmedians"].set_linewidth(1.5)
        handles.append(Line2D([], [], color=color, linewidth=7, alpha=0.55, label=system))
    r = np.corrcoef(div["length"], div["raw_q"])[0, 1]
    ax.text(0.97, 0.94, f"heterogeneous r = {r:+.2f}", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.8,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1})
    ax.set_xlabel("Sequence length (residues)"); ax.set_ylabel("Raw native-contact Q")
    ax.set_title("Length and Q", loc="left", fontweight="bold")
    ax.legend(handles=handles, frameon=False, loc="lower right", fontsize=8.1)
    polish(ax); panel_label(ax, "c")

    ax = axes[1, 1]
    order = ["train", "val", "test"]
    designs = [("heterogeneous panel", COL["soft_blue"]),
               ("matched mutation scan", COL["soft_orange"])]
    ax.set_xlim(-0.5, 2.5); ax.set_ylim(1.5, -0.5)
    for y, (design, face) in enumerate(designs):
        d = overlap[overlap["design"] == design].set_index("split").loc[order]
        for x, value in enumerate(d["exact_matches"]):
            ax.add_patch(Rectangle((x - 0.46, y - 0.40), 0.92, 0.80,
                                   facecolor=face, edgecolor="white", linewidth=1.2))
            ax.text(x, y, str(int(value)), ha="center", va="center", fontsize=12,
                    fontweight="bold", color=COL["black"])
    ax.set_xticks(range(3), ["Train", "Val.", "Test"])
    ax.set_xlabel("NbBench split")
    ax.set_yticks(range(2), ["heterogeneous", "matched scans"])
    ax.set_title("Exact overlap", loc="left", fontweight="bold")
    ax.grid(False); panel_label(ax, "d")
    fig.align_ylabels()
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


def fig_s2(candidates: pd.DataFrame, selected: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 6.65), constrained_layout=True)
    rng = np.random.default_rng(13)
    candidate_gaps = candidates.copy()
    best_map = candidate_gaps.groupby(["regime", "source"])["validation_mae"].transform("min")
    candidate_gaps["gap"] = candidate_gaps["validation_mae"] - best_map
    common_max = float(candidate_gaps["gap"].quantile(0.995) * 1.12)
    for ax, regime, letter in [(axes[0, 0], "frozen", "a"), (axes[0, 1], "hot", "b")]:
        for y, source in enumerate(SOURCES):
            d = candidate_gaps[(candidate_gaps["regime"] == regime) & (candidate_gaps["source"] == source)]
            jitter = rng.uniform(-0.12, 0.12, len(d))
            ax.scatter(d["gap"], y + jitter, s=18, color=COL["light"], alpha=0.75,
                       edgecolor=COL["gray"], linewidth=0.25)
            ax.scatter(0, y, s=62, marker="D", color=COLOR[source],
                       edgecolor="white", linewidth=0.9, zorder=4)
            ax.text(common_max * 0.98, y, f"n={len(d)}", ha="right", va="center",
                    fontsize=8.0, color=COL["gray"])
        ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES]); ax.invert_yaxis()
        ax.set_xlim(-0.03 * common_max, common_max)
        ax.set_xlabel("Candidate MAE − selected MAE (°C)")
        ax.set_title("Frozen ESM2" if regime == "frozen" else "Fine-tuned ESM2",
                     loc="left", fontweight="bold")
        polish(ax, "x"); panel_label(ax, letter)

    ax = axes[1, 0]
    columns = [("frozen", "architecture", "frozen\narch."), ("frozen", "head", "frozen\nhead"),
               ("hot", "architecture", "fine-tuned\narch."), ("hot", "head", "fine-tuned\nhead")]
    ax.set_xlim(-.5, 3.5); ax.set_ylim(len(SOURCES)-.5, -.5)
    ax.set_xticks(range(4), ["Arch.", "Head", "Arch.", "Head"])
    ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES])
    fill = {"shared": "#EAF4EA", "residual": "#F7EDDE", "latent": "#E7F0F7",
            "separate": "#EEF2F5", "context": "#E2E7EB", "-": COL["soft_gray"]}
    for y, source in enumerate(SOURCES):
        for x, (regime, field, _) in enumerate(columns):
            value = selected[(selected["regime"] == regime) & (selected["source"] == source)].iloc[0][field]
            ax.add_patch(plt.Rectangle((x-.48, y-.46), .96, .92, facecolor=fill.get(value, "white"), edgecolor="white"))
            shown_value = {"residual": "resid.", "separate": "sep.",
                           "context": "ctx.", "-": "—"}.get(value, value)
            ax.text(x, y, shown_value, ha="center", va="center", fontsize=8.3)
    ax.text(0.25, 1.07, "Frozen", transform=ax.transAxes, ha="center", va="bottom", fontweight="bold")
    ax.text(0.75, 1.07, "Fine-tuned", transform=ax.transAxes, ha="center", va="bottom", fontweight="bold")
    ax.axvline(1.5, color="white", linewidth=3)
    ax.set_title("Selected model form", loc="left", fontweight="bold", pad=28)
    ax.grid(False); panel_label(ax, "c")

    ax = axes[1, 1]
    for y, source in enumerate(SOURCES):
        for regime, marker, offset in [("frozen", "s", -0.16), ("hot", "o", 0.16)]:
            r = selected[(selected["regime"] == regime) & (selected["source"] == source)].iloc[0]
            gap = r["test_mae"] - r["validation_mae"]
            ax.scatter(gap, y + offset, s=58, marker=marker, color=COLOR[source],
                       edgecolor="white", linewidth=0.8, zorder=3)
    ax.axvline(0, color=COL["black"], linestyle="--", linewidth=1.0)
    ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES]); ax.invert_yaxis()
    ax.set_xlabel("Test MAE − validation MAE (°C)")
    ax.set_title("Held-out generalization gap", loc="left", fontweight="bold")
    handles = [Line2D([], [], marker="s", color="none", markerfacecolor=COL["gray"], label="frozen"),
               Line2D([], [], marker="o", color="none", markerfacecolor=COL["gray"], label="fine-tuned")]
    ax.legend(handles=handles, frameon=False, loc="upper left")
    polish(ax, "x"); panel_label(ax, "d")
    fig.align_ylabels()
    save_figure(fig, "supp_fig02_model_selection")


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


def fig_s3(effects: pd.DataFrame, direct: pd.DataFrame, sizes: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 6.55), constrained_layout=True)
    x_lo = float(effects["ci_lo"].min() - 0.08)
    x_hi = float(effects["ci_hi"].max() + 0.08)
    for ax, regime, letter in [(axes[0, 0], "frozen", "a"), (axes[0, 1], "hot", "b")]:
        d = effects[effects["regime"] == regime].set_index("source").loc[SOURCES]
        for y, (source, r) in enumerate(d.iterrows()): interval(ax, y, r.test_mae, r.ci_lo, r.ci_hi, COLOR[source])
        baseline = float(d.loc["Tm_only", "test_mae"])
        ax.axvline(baseline, color=COL["tm"], linestyle="--", linewidth=1.0)
        ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES]); ax.invert_yaxis()
        ax.set_xlim(x_lo, x_hi)
        ax.set_xlabel("Held-out Tm test MAE (°C)")
        ax.set_title("Frozen ESM2" if regime == "frozen" else "Fine-tuned ESM2",
                     loc="left", fontweight="bold")
        polish(ax, "x"); panel_label(ax, letter)

    ax = axes[1, 0]
    for regime, marker, face, label in [("frozen", "s", COL["gray"], "frozen"),
                                         ("hot", "o", "white", "fine-tuned")]:
        d = direct[direct["regime"] == regime].sort_values("n")
        y = d["fep_minus_md"].to_numpy(); yerr = np.vstack([y-d["ci_lo"], d["ci_hi"]-y])
        ax.errorbar(d["n"], y, yerr=yerr, color=COL["gray"], marker=marker, capsize=3.8,
                    label=label, markerfacecolor=face, markeredgecolor=COL["gray"],
                    markeredgewidth=1.2, elinewidth=1.4)
    ax.axhline(0, color=COL["black"], linewidth=1.0)
    ax.set_xscale("log", base=2); ax.set_xlim(16, 430)
    ax.set_xticks([20, 80, 160, 320], [20, 80, 160, 320])
    ax.set_xlabel("Labels per scaffold, n")
    ax.set_ylabel("FEP − matched MD, paired ΔMAE (°C)")
    ax.set_title("Direct label comparison", loc="left", fontweight="bold")
    ax.text(.03, .95, "negative = lower FEP error", transform=ax.transAxes,
            fontsize=8.6, va="top")
    ax.legend(frameon=False, loc="lower right"); polish(ax); panel_label(ax, "c")

    ax = axes[1, 1]
    order = ["8M", "35M", "650M"]
    d = sizes.set_index("size").loc[order]
    x = np.arange(3); y = d["fep_minus_tm"].to_numpy(float)
    yerr = np.vstack([y-d["ci_lo"].to_numpy(float), d["ci_hi"].to_numpy(float)-y])
    ax.axhline(0, color=COL["black"], linewidth=1.0, linestyle="--")
    ax.errorbar(x[0], y[0], yerr=yerr[:, [0]], fmt="o", color=COL["fep"],
                markerfacecolor=COL["fep"], markeredgecolor="white", markeredgewidth=0.8,
                markersize=7.5, capsize=3.8, elinewidth=1.5)
    ax.errorbar(x[1:], y[1:], yerr=yerr[:, 1:], fmt="o", color=COL["fep"],
                markerfacecolor="white", markeredgecolor=COL["fep"], markeredgewidth=1.4,
                markersize=7.5, capsize=3.8, elinewidth=1.5, linestyle="none")
    for xi, yi in zip(x, y):
        ax.text(xi, yi - 0.018, f"{yi:+.2f}", ha="center", va="top", fontsize=8.6,
                fontweight="bold", color=COL["fep"])
    ax.set_xticks(x, order); ax.set_xlabel("ESM2 encoder size")
    ax.set_ylabel("FEP − Tm-only, paired ΔMAE (°C)")
    ax.set_title("FEP benefit across encoder sizes", loc="left", fontweight="bold")
    ax.text(0.97, 0.95, "filled: selected\nopen: exploratory",
            transform=ax.transAxes, fontsize=8.2, ha="right", va="top")
    polish(ax, "y"); panel_label(ax, "d")
    fig.align_ylabels()
    save_figure(fig, "supp_fig03_transfer_controls")


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


def fig_s4(composition, sensitivity, corrected, prov) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(6.4, 6.25), constrained_layout=True)
    ax = axes[0, 0]
    pivot = composition.pivot(index="mut", columns="system", values="rows").fillna(0).loc[["A", "D", "I", "Q"]]
    x = np.arange(len(pivot)); width = 0.36
    for offset, system, color in [(-width/2, "1mel", COL["fep"]),
                                   (width/2, "4idl", "#64B89E")]:
        bars = ax.bar(x + offset, pivot[system], width=width, color=color, label=system.upper())
        ax.bar_label(bars, fontsize=8.3, padding=2)
    ax.set_xticks(x, ["Ala", "Asp", "Ile", "Gln"]); ax.set_ylabel("Retained FEP rows")
    ax.set_ylim(0, float(pivot.to_numpy().max()) * 1.25)
    ax.set_title("Retained mutation scans", loc="left", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="upper center"); polish(ax, "y"); panel_label(ax, "a")

    ax = axes[0, 1]
    q = prov["dq"].value_counts().sort_index()
    q_colors = [COL["gray"] if int(v) == 0 else COL["md"] for v in q.index]
    bars = ax.bar([str(int(v)) for v in q.index], q.values, color=q_colors)
    ax.bar_label(bars, fontsize=8.8, padding=3); ax.set_xlabel("Mutation charge change, Δq")
    ax.set_ylabel("FEP rows"); ax.set_ylim(0, float(q.max()) * 1.18)
    changing = int(q[q.index != 0].sum())
    ax.text(0.03, 0.78, f"{changing}/{int(q.sum())} charge-changing",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.7)
    ax.set_title("Formal charge changes", loc="left", fontweight="bold")
    polish(ax, "y"); panel_label(ax, "b")

    ax = axes[1, 0]
    corrected = corrected.copy()
    corrected["shift"] = corrected["corrected"] - corrected["unadjusted"]
    neutral = corrected["dq"] == 0
    ax.scatter(corrected.loc[neutral, "unadjusted"], corrected.loc[neutral, "shift"],
               s=12, alpha=.28, color=COL["gray"], edgecolor="none", label="Δq = 0")
    ax.scatter(corrected.loc[~neutral, "unadjusted"], corrected.loc[~neutral, "shift"],
               s=14, alpha=.45, color=COL["md"], edgecolor="none", label="Δq ≠ 0")
    ax.axhline(0, color=COL["black"], linewidth=1.0, linestyle="--")
    corr = np.corrcoef(corrected["unadjusted"], corrected["corrected"])[0, 1]
    shift = np.max(np.abs(corrected["shift"]))
    limit = max(0.009, float(np.max(np.abs(corrected["shift"]))) * 1.15)
    ax.set_ylim(-limit, limit)
    ax.text(.04, .94, f"r = {corr:.5f}\nmax |shift| = {shift:.3f}",
            transform=ax.transAxes, va="top", fontsize=8.7,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": .8, "pad": 1})
    ax.set_xlabel("Unadjusted scaled FEP label")
    ax.set_ylabel("Corrected − unadjusted label")
    ax.set_title("Effect of ε=78 correction", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="lower left", ncol=2, fontsize=8.3)
    polish(ax); panel_label(ax, "c")

    ax = axes[1, 1]
    x = np.arange(len(sensitivity))
    bars = ax.bar(x, sensitivity["max_abs_scaled_shift"],
                  color=["#76B7A4", COL["fep"], "#E7B45D", COL["md"]])
    ax.axhline(.02, color=COL["black"], linestyle="--", linewidth=.9, label="0.02 scaled-label shift")
    ax.axvline(1.5, color=COL["light"], linewidth=1.2)
    ax.set_xticks(x, ["ε=97", "ε=78", "0.5", "1.5"])
    ax.set_ylabel("Maximum absolute scaled-label shift")
    for i, r in sensitivity.reset_index(drop=True).iterrows():
        ax.text(i, r.max_abs_scaled_shift + .004,
                f"{r.max_abs_scaled_shift:.3f}\nr={r.label_correlation:.3f}",
                ha="center", va="bottom", fontsize=8.2)
    ax.legend(frameon=False, loc="upper left")
    ax.set_ylim(0, max(.13, sensitivity["max_abs_scaled_shift"].max()+.045))
    ax.set_title("Correction sensitivity", loc="left", fontweight="bold")
    polish(ax, "y"); panel_label(ax, "d")
    fig.align_ylabels()
    save_figure(fig, "supp_fig04_fep_checks")


def write_manifest() -> None:
    rows = []
    specs = {
        "Supplementary Fig. 1": ("supp_fig01_data_and_design.pdf", ["data_sources.tsv", "data_design_qvalues.tsv", "sequence_overlap.tsv"],
                                  ["processed row and unique-sequence counts", "native-contact loss distributions", "Q versus sequence length", "unique exact-sequence overlap"]),
        "Supplementary Fig. 2": ("supp_fig02_model_selection.pdf", ["candidate_validation.tsv", "selected_settings.tsv"],
                                  ["frozen completed validation candidates", "fine-tuned completed validation candidates", "selected model forms", "held-out generalization gap"]),
        "Supplementary Fig. 3": ("supp_fig03_transfer_controls.pdf", ["final_source_effects.tsv", "fep_md_direct.tsv", "model_size_controls.tsv"],
                                  ["frozen absolute MAE", "fine-tuned absolute MAE", "direct FEP-minus-MD count sweep", "paired FEP effect across ESM2 sizes"]),
        "Supplementary Fig. 4": ("supp_fig04_fep_checks.pdf", ["fep_scan_composition.tsv", "fep_charge_sensitivity.tsv", "fep_charge_corrected_labels.tsv"],
                                  ["scan composition", "charge-change counts", "per-label periodicity shift", "correction sensitivity"]),
    }
    for figure, (file, tables, questions) in specs.items():
        for i, question in enumerate(questions):
            rows.append({"figure": figure, "panel": chr(65+i), "figure_file": f"figures/{file}",
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
    fig_s1(counts, qvalues, overlap); fig_s2(candidates, selected); fig_s3(effects, direct, sizes)
    fig_s4(composition, sensitivity, corrected, provenance); write_manifest()
    print("supplementary figure build complete")


if __name__ == "__main__":
    main()
