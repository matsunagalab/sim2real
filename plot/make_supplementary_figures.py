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
        "font.size": 9.0, "axes.titlesize": 9.2, "axes.labelsize": 9.0,
        "xtick.labelsize": 8.3, "ytick.labelsize": 8.3, "legend.fontsize": 8.0,
        "axes.linewidth": 0.8, "axes.spines.top": True, "axes.spines.right": True,
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
    ax.text(-0.12, 1.08, f"({letter})", transform=ax.transAxes, fontsize=11,
            fontweight="bold", ha="left", va="top", clip_on=False)


def polish(ax, axis: str = "both") -> None:
    ax.set_axisbelow(True)
    ax.grid(True, axis=axis, color=COL["grid"], linewidth=0.65)
    ax.tick_params(width=0.8, length=3)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color(COL["black"])


def interval(ax, y, mid, lo, hi, color, marker="o", label=None) -> None:
    ax.errorbar(mid, y, xerr=[[mid - lo], [hi - mid]], fmt=marker, color=color,
                ecolor=color, elinewidth=1.35, capsize=3, markersize=6,
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
        part = [len(pd.read_csv(p)) for p in paths]
        counts.append({"data_set": label, "rows": sum(part), "table_rows": "+".join(map(str, part))})

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
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.0), constrained_layout=True)
    ax = axes[0, 0]
    shown = counts.iloc[::-1]
    colors = [COL["tm"] if x.startswith("Tm") else COL["md"] if "MD" in x else COL["fep"] for x in shown["data_set"]]
    ax.barh(shown["data_set"], shown["rows"], color=colors, alpha=0.9)
    ax.set_xscale("log"); ax.set_xlabel("processed rows (log scale)")
    for y, (_, r) in enumerate(shown.iterrows()):
        ax.text(r["rows"] * 1.06, y, r["table_rows"], va="center", fontsize=7.8)
    ax.set_xlim(35, 3600); polish(ax, "x"); panel_label(ax, "a")

    ax = axes[0, 1]
    specs = [("heterogeneous panel", None, COL["design"], "-"),
             ("matched mutation scan", "1MEL", COL["md"], "-"),
             ("matched mutation scan", "4IDL", COL["fep"], "--")]
    for design, system, color, ls in specs:
        d = qvalues[qvalues["design"] == design]
        if system is not None: d = d[d["system"] == system]
        x, y = ecdf(d["raw_q"])
        label = design if system is None else f"matched {system}"
        ax.plot(x, y, color=color, linestyle=ls, linewidth=1.8, label=label)
    ax.set_xlabel("raw native-contact Q"); ax.set_ylabel("cumulative fraction")
    ax.legend(frameon=False, loc="upper left"); polish(ax); panel_label(ax, "b")

    ax = axes[1, 0]
    div = qvalues[qvalues["design"] == "heterogeneous panel"]
    ax.scatter(div["length"], div["raw_q"], s=9, alpha=0.28, color=COL["design"], edgecolor="none", label="heterogeneous panel")
    for system, color, marker in [("1MEL", COL["md"], "o"), ("4IDL", COL["fep"], "D")]:
        d = qvalues[(qvalues["design"] == "matched mutation scan") & (qvalues["system"] == system)]
        ax.scatter(d["length"], d["raw_q"], s=12, alpha=0.35, color=color, marker=marker, edgecolor="none", label=f"matched {system}")
    r = np.corrcoef(div["length"], div["raw_q"])[0, 1]
    ax.text(0.03, 0.07, f"heterogeneous panel: r = {r:+.2f}", transform=ax.transAxes, ha="left", fontsize=8.2)
    ax.set_xlabel("sequence length (residues)"); ax.set_ylabel("raw native-contact Q")
    ax.legend(frameon=False, loc="upper right"); polish(ax); panel_label(ax, "c")

    ax = axes[1, 1]
    order = ["train", "val", "test"]
    x = np.arange(3); w = 0.34
    for j, (design, color, label) in enumerate([("heterogeneous panel", COL["design"], "heterogeneous panel"),
                                                ("matched mutation scan", COL["md"], "matched scans")]):
        d = overlap[overlap["design"] == design].set_index("split").loc[order]
        bars = ax.bar(x + (j - .5) * w, d["exact_matches"], width=w, color=color, label=label)
        ax.bar_label(bars, fontsize=8, padding=2)
    ax.set_xticks(x, ["Tm train", "Tm validation", "Tm test"]); ax.set_ylabel("exact sequence matches")
    ax.set_ylim(0, 9.5); ax.legend(frameon=False, loc="upper left"); polish(ax, "y"); panel_label(ax, "d")
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
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.3), constrained_layout=True)
    rng = np.random.default_rng(13)
    for ax, regime, letter in [(axes[0, 0], "frozen", "a"), (axes[0, 1], "hot", "b")]:
        for y, source in enumerate(SOURCES):
            d = candidates[(candidates["regime"] == regime) & (candidates["source"] == source)]
            jitter = rng.uniform(-0.12, 0.12, len(d))
            ax.scatter(d["validation_mae"], y + jitter, s=15, color=COLOR[source], alpha=0.38, edgecolor="none")
            best = d.nsmallest(1, "validation_mae").iloc[0]
            ax.scatter(best["validation_mae"], y, s=56, marker="D", color=COLOR[source], edgecolor="white", linewidth=0.8, zorder=4)
        ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES]); ax.invert_yaxis()
        ax.set_xlabel("Tm validation MAE (deg C)"); ax.set_title("frozen ESM2" if regime == "frozen" else "fine-tuned ESM2")
        polish(ax, "x"); panel_label(ax, letter)

    ax = axes[1, 0]
    columns = [("frozen", "architecture", "frozen\narch."), ("frozen", "head", "frozen\nhead"),
               ("hot", "architecture", "fine-tuned\narch."), ("hot", "head", "fine-tuned\nhead")]
    ax.set_xlim(-.5, 3.5); ax.set_ylim(len(SOURCES)-.5, -.5)
    ax.set_xticks(range(4), [c[2] for c in columns]); ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES])
    fill = {"shared": COL["soft_green"], "residual": COL["soft_orange"], "latent": COL["soft_blue"],
            "separate": COL["soft_green"], "context": COL["soft_blue"], "-": COL["soft_gray"]}
    for y, source in enumerate(SOURCES):
        for x, (regime, field, _) in enumerate(columns):
            value = selected[(selected["regime"] == regime) & (selected["source"] == source)].iloc[0][field]
            ax.add_patch(plt.Rectangle((x-.48, y-.46), .96, .92, facecolor=fill.get(value, "white"), edgecolor="white"))
            ax.text(x, y, value, ha="center", va="center", fontsize=7.8)
    ax.grid(False); panel_label(ax, "c")

    ax = axes[1, 1]
    for regime, marker, label in [("frozen", "s", "frozen"), ("hot", "o", "fine-tuned")]:
        d = selected[selected["regime"] == regime]
        for _, r in d.iterrows():
            ax.scatter(r["validation_mae"], r["test_mae"], s=45, marker=marker, color=COLOR[r["source"]], edgecolor="white", linewidth=.7)
            if r["source"] in {"FEP", "MD_FEP400K", "rosetta_esm"}:
                offset = {"FEP": (3, -10), "MD_FEP400K": (3, 4), "rosetta_esm": (3, 4)}[r["source"]]
                ha = "left"
                if r["source"] == "rosetta_esm" and regime == "frozen":
                    offset, ha = (-3, 4), "right"
                ax.annotate(SHORT[r["source"]], (r["validation_mae"], r["test_mae"]),
                            xytext=offset, textcoords="offset points", fontsize=6.9, ha=ha)
    ax.set_xlabel("selected validation MAE (deg C)"); ax.set_ylabel("held-out test MAE (deg C)")
    handles = [Line2D([], [], marker="s", color="none", markerfacecolor=COL["gray"], label="frozen"),
               Line2D([], [], marker="o", color="none", markerfacecolor=COL["gray"], label="fine-tuned")]
    ax.legend(handles=handles, frameon=False, loc="upper left"); polish(ax); panel_label(ax, "d")
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
    specs = [("8M", "Tm labels only", RESULTS / "final_tm_hot/scaling.json"),
             ("8M", "FEP", RESULTS / "final_fep_hot/scaling.json"),
             ("35M", "Tm labels only", RESULTS / "size35_tm_shared_drop005/scaling.json"),
             ("35M", "FEP", RESULTS / "size35_ddg_fep_enc3e-5/scaling.json"),
             ("650M", "Tm labels only", RESULTS / "size650_tm_shared_drop005/scaling.json"),
             ("650M", "FEP", RESULTS / "size650_ddg_fep_enc3e-5/scaling.json")]
    for size, condition, path in specs:
        p = representative(read_json(path)); sizes.append({"size": size, "condition": condition, "test_mae": p["mae"], "ci_lo": p["ci_lo"], "ci_hi": p["ci_hi"], "source": str(path.relative_to(REPO))})
    return pd.DataFrame(effects), pd.DataFrame(direct), pd.DataFrame(sizes)


def fig_s3(effects: pd.DataFrame, direct: pd.DataFrame, sizes: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.1), constrained_layout=True)
    for ax, regime, letter in [(axes[0, 0], "frozen", "a"), (axes[0, 1], "hot", "b")]:
        d = effects[effects["regime"] == regime].set_index("source").loc[SOURCES]
        for y, (source, r) in enumerate(d.iterrows()): interval(ax, y, r.test_mae, r.ci_lo, r.ci_hi, COLOR[source])
        ax.set_yticks(range(len(SOURCES)), [SHORT[x] for x in SOURCES]); ax.invert_yaxis()
        ax.set_xlabel("held-out Tm test MAE (deg C)"); ax.set_title("frozen ESM2" if regime == "frozen" else "fine-tuned ESM2")
        polish(ax, "x"); panel_label(ax, letter)

    ax = axes[1, 0]
    x = np.arange(4)
    for regime, offset, color, marker, label in [("frozen", -.08, COL["design"], "s", "frozen"),
                                                  ("hot", .08, COL["fep"], "o", "fine-tuned")]:
        d = direct[direct["regime"] == regime].sort_values("n")
        y = d["fep_minus_md"].to_numpy(); yerr = np.vstack([y-d["ci_lo"], d["ci_hi"]-y])
        ax.errorbar(x+offset, y, yerr=yerr, color=color, marker=marker, capsize=3, label=label, markeredgecolor="white", markeredgewidth=.7)
    ax.axhline(0, color=COL["black"], linewidth=.9); ax.set_xticks(x, [20, 80, 160, 320])
    ax.set_xlabel("computed labels sampled per structure table")
    ax.set_ylabel("paired ΔMAE: FEP - matched MD (deg C)")
    ax.text(.03, .05, "negative favors FEP", transform=ax.transAxes, fontsize=8)
    ax.legend(frameon=False); polish(ax); panel_label(ax, "c")

    ax = axes[1, 1]
    order = ["8M", "35M", "650M"]; x = np.arange(3)
    for condition, color, marker, offset in [("Tm labels only", COL["tm"], "s", -.06), ("FEP", COL["fep"], "o", .06)]:
        d = sizes[sizes["condition"] == condition].set_index("size").loc[order]
        y = d["test_mae"].to_numpy(); yerr = np.vstack([y-d["ci_lo"], d["ci_hi"]-y])
        ax.errorbar(x+offset, y, yerr=yerr, color=color, marker=marker, capsize=3, label=condition, markeredgecolor="white", markeredgewidth=.7)
    ax.set_xticks(x, order); ax.set_xlabel("ESM2 encoder size"); ax.set_ylabel("held-out Tm test MAE (deg C)")
    ax.legend(frameon=False); polish(ax); panel_label(ax, "d")
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
                corrected_rows.extend({"system": system, "unadjusted": a, "corrected": b} for a, b in zip(u, c))
        u, c = np.asarray(all_u), np.asarray(all_c)
        sensitivity.append({"correction": name, "kcal_per_dq2": amount, "label_correlation": np.corrcoef(u, c)[0, 1],
                            "max_abs_scaled_shift": np.max(np.abs(u-c)), "rows_shifted_gt_0.02": int(np.sum(np.abs(u-c) > .02))})
    return composition, pd.DataFrame(sensitivity), pd.DataFrame(corrected_rows), prov


def fig_s4(composition, sensitivity, corrected, prov) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.9), constrained_layout=True)
    ax = axes[0, 0]
    pivot = composition.pivot(index="mut", columns="system", values="rows").fillna(0).loc[["A", "D", "I", "Q"]]
    x = np.arange(len(pivot)); bottom = np.zeros(len(pivot))
    for system, color in [("1mel", COL["design"]), ("4idl", COL["md"])]:
        bars = ax.bar(x, pivot[system], bottom=bottom, color=color, label=system.upper())
        bottom += pivot[system].to_numpy()
    ax.set_xticks(x, ["Ala", "Asp", "Ile", "Gln"]); ax.set_ylabel("retained FEP rows")
    ax.legend(frameon=False); polish(ax, "y"); panel_label(ax, "a")

    ax = axes[0, 1]
    q = prov["dq"].value_counts().sort_index(); bars = ax.bar([str(int(v)) for v in q.index], q.values, color=COL["fep"])
    ax.bar_label(bars, fontsize=8, padding=2); ax.set_xlabel("mutation charge change, Δq")
    ax.set_ylabel("FEP rows"); polish(ax, "y"); panel_label(ax, "b")

    ax = axes[1, 0]
    ax.scatter(corrected["unadjusted"], corrected["corrected"], s=10, alpha=.30, color=COL["fep"], edgecolor="none")
    ax.plot([0, 1], [0, 1], color=COL["black"], linewidth=.9, linestyle="--")
    corr = np.corrcoef(corrected["unadjusted"], corrected["corrected"])[0, 1]
    shift = np.max(np.abs(corrected["unadjusted"]-corrected["corrected"]))
    ax.text(.04, .94, f"r = {corr:.5f}\nmax shift = {shift:.3f}", transform=ax.transAxes, va="top", fontsize=8.2)
    ax.set_xlabel("unadjusted scaled FEP label"); ax.set_ylabel("charge-corrected scaled FEP label")
    polish(ax); panel_label(ax, "c")

    ax = axes[1, 1]
    x = np.arange(len(sensitivity)); bars = ax.bar(x, sensitivity["max_abs_scaled_shift"], color=[COL["design"], COL["fep"], COL["rosetta"], COL["md"]])
    ax.axhline(.02, color=COL["black"], linestyle="--", linewidth=.9, label="0.02 scaled-label shift")
    ax.set_xticks(x, ["eps=97", "eps=78", "0.5", "1.5"]); ax.set_ylabel("maximum absolute scaled-label shift")
    for i, r in sensitivity.reset_index(drop=True).iterrows():
        ax.text(i, r.max_abs_scaled_shift + .004, f"r={r.label_correlation:.3f}", rotation=90, ha="center", va="bottom", fontsize=7.2)
    ax.legend(frameon=False, loc="upper left"); ax.set_ylim(0, max(.11, sensitivity["max_abs_scaled_shift"].max()+.035))
    polish(ax, "y"); panel_label(ax, "d")
    save_figure(fig, "supp_fig04_fep_checks")


def write_manifest() -> None:
    rows = []
    specs = {
        "Supplementary Fig. 1": ("supp_fig01_data_and_design.pdf", ["data_sources.tsv", "data_design_qvalues.tsv", "sequence_overlap.tsv"],
                                  ["processed row counts", "raw Q distributions", "Q versus sequence length", "exact sequence overlap"]),
        "Supplementary Fig. 2": ("supp_fig02_model_selection.pdf", ["candidate_validation.tsv", "selected_settings.tsv"],
                                  ["frozen validation search", "fine-tuned validation search", "selected model forms", "validation versus held-out test"]),
        "Supplementary Fig. 3": ("supp_fig03_transfer_controls.pdf", ["final_source_effects.tsv", "fep_md_direct.tsv", "model_size_controls.tsv"],
                                  ["frozen absolute MAE", "fine-tuned absolute MAE", "direct FEP-minus-MD count sweep", "ESM2 size control"]),
        "Supplementary Fig. 4": ("supp_fig04_fep_checks.pdf", ["fep_scan_composition.tsv", "fep_charge_sensitivity.tsv"],
                                  ["scan composition", "charge-change counts", "periodicity correction", "correction sensitivity"]),
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
                     (composition, "fep_scan_composition.tsv"), (sensitivity, "fep_charge_sensitivity.tsv")]:
        save_table(df, name)
    fig_s1(counts, qvalues, overlap); fig_s2(candidates, selected); fig_s3(effects, direct, sizes)
    fig_s4(composition, sensitivity, corrected, provenance); write_manifest()
    print("supplementary figure build complete")


if __name__ == "__main__":
    main()
