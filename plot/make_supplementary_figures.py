#!/usr/bin/env python3
"""Assemble supplementary figure panels and their numerical source tables.

The script keeps the reviewer-round handoff simple:

  1. read stable result summaries from results/
  2. write compact TSV tables to paper/analysis/supplementary/tables/
  3. render publication figures to paper/analysis/supplementary/figures/
     and paper/tex/figures/

It does not launch model training or move any result directories.
"""

from __future__ import annotations

import json
import os
import re
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


REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
DATA = REPO / "data"
PAPER = REPO / "paper"
ANALYSIS = PAPER / "analysis" / "supplementary"
TABLES = ANALYSIS / "tables"
ANALYSIS_FIGS = ANALYSIS / "figures"
TEX_FIGS = PAPER / "tex" / "figures"

MD_CONTACT_Q_SOURCE = "MD_Q_" + "H" + "PHIL_400K"

COL = {
    "black": "#222222",
    "gray": "#707070",
    "light_gray": "#D7D7D7",
    "grid": "#E8E8E8",
    "tm": "#4D4D4D",
    "fep": "#009E73",
    "rosetta": "#E69F00",
    "design": "#0072B2",
    "thermo": "#CC79A7",
    "mdq": "#D55E00",
    "rmsf": "#56B4E9",
    "other": "#999999",
}

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
    "rosetta": "Rosetta\nmutation score",
    "thermoMPNN": "ThermoMPNN\nstability score",
    "rosetta_random": "random variants\nscored by Rosetta",
    "rosetta_esm": "ESM2 variants\nscored by Rosetta",
    MD_CONTACT_Q_SOURCE: "MD Q-value",
}

SOURCE_SHORT = {
    "Tm_only": "Tm only",
    "FEP": "FEP",
    "rosetta": "Rosetta",
    "thermoMPNN": "ThermoMPNN",
    "rosetta_random": "random/Rosetta",
    "rosetta_esm": "ESM2/Rosetta",
    MD_CONTACT_Q_SOURCE: "MD Q-value",
}

SOURCE_TICK = {
    "Tm_only": "Tm only",
    "FEP": "FEP",
    "rosetta": "Rosetta",
    "thermoMPNN": "ThermoMPNN",
    "rosetta_random": "random/\nRosetta",
    "rosetta_esm": "ESM2/\nRosetta",
    MD_CONTACT_Q_SOURCE: "MD\nQ-value",
}

SOURCE_COLOR = {
    "Tm_only": COL["tm"],
    "FEP": COL["fep"],
    "rosetta": "#B9770E",
    "thermoMPNN": COL["thermo"],
    "rosetta_random": COL["rosetta"],
    "rosetta_esm": COL["design"],
    MD_CONTACT_Q_SOURCE: COL["mdq"],
}

MD_FEATURE_LABEL = {
    "MD_Q_HPHIL_400K": "Q-value, 400 K",
    "MD_Q_HPHIL_400K_SHUF": "Q-value, shuffled labels",
    "MD_RMSF": "mean residue fluctuation",
    "MD_RMSF_MAX": "maximum residue fluctuation",
    "MD_RG_STD": "radius-of-gyration fluctuation",
    "MD_SALTBRIDGE": "salt-bridge persistence",
    "MD_Q_MIN_400K": "minimum Q-value, 400 K",
    "MD_Q_STD_400K": "Q-value fluctuation, 400 K",
    "MD_Q_SLOPE_400K": "Q-value slope, 400 K",
    "MD_RMSF_MAX_400K": "maximum residue fluctuation, 400 K",
    "MD_RG_STD_400K": "radius-of-gyration fluctuation, 400 K",
    "MD_Q_CDR3": "CDR3 Q-value",
    "MD_Q_FRAMEWORK": "framework Q-value",
    "MD_RMSF_CDR3": "CDR3 residue fluctuation",
    "MD_RMSF_FRAMEWORK": "framework residue fluctuation",
    "MD_SS_DIST_MEAN": "disulfide distance",
    "MD_SS_DIST_STD": "disulfide-distance fluctuation",
    "MD_CDR3_LEN": "CDR3 length",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.family": "DejaVu Sans",
            "font.size": 8.2,
            "axes.titlesize": 8.8,
            "axes.labelsize": 8.2,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 7.2,
            "ytick.labelsize": 7.2,
            "legend.fontsize": 7.0,
            "lines.linewidth": 1.55,
            "lines.markersize": 4.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def ensure_dirs() -> None:
    for path in (TABLES, ANALYSIS_FIGS, TEX_FIGS):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict | list:
    return json.loads(path.read_text())


def resolve_path(raw: str | Path) -> Path:
    path = Path(raw)
    if path.exists():
        return path
    text = str(raw)
    if "/results/" in text:
        return RESULTS / text.split("/results/", 1)[1]
    return path


def scaling_point(path: str | Path, index: int = 0) -> dict:
    data = read_json(resolve_path(path))
    return data["scaling"][index]


def all_scaling_points(path: str | Path) -> list[dict]:
    return read_json(resolve_path(path))["scaling"]


def interval_from_row(row: pd.Series | dict) -> tuple[float, float]:
    mae = float(row["mae"] if "mae" in row else row["test_mae"])
    if "ci_lo" in row and pd.notna(row["ci_lo"]):
        return float(row["ci_lo"]), float(row["ci_hi"])
    width = float(row.get("ci_width", 0.0))
    return mae - width / 2.0, mae + width / 2.0


def panel_label(ax, label: str) -> None:
    ax.text(
        -0.10,
        1.05,
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


def horizontal_interval(ax, y, mid, lo, hi, color, marker="o", alpha=1.0, zorder=3):
    ax.plot([lo, hi], [y, y], color=color, linewidth=1.8, solid_capstyle="round", alpha=alpha, zorder=zorder)
    ax.scatter([mid], [y], s=32, color=color, edgecolor="white", linewidth=0.6, marker=marker, alpha=alpha, zorder=zorder + 1)


def save_figure(fig, stem: str) -> None:
    for out_dir in (ANALYSIS_FIGS, TEX_FIGS):
        for ext in ("pdf", "png"):
            path = out_dir / f"{stem}.{ext}"
            if ext == "png":
                fig.savefig(path, bbox_inches="tight", dpi=600)
            else:
                fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {ANALYSIS_FIGS / (stem + '.pdf')}")


def write_table(df: pd.DataFrame, name: str) -> Path:
    path = TABLES / name
    df.to_csv(path, sep="\t", index=False)
    return path


def source_screen_final() -> pd.DataFrame:
    rows = pd.DataFrame(read_json(RESULTS / "source_screen" / "final_source_screen_summary.json")["rows"])
    records = []
    for _, row in rows.iterrows():
        point = scaling_point(row["scaling_json"])
        records.append(
            {
                "source": row["source"],
                "label": SOURCE_SHORT.get(row["source"], row["source"]),
                "architecture": row["arch"],
                "selected_setting": row["label"],
                "n_ddg": int(row.get("n_ddg", 0)),
                "n_md": int(row.get("n_md", 0)),
                "validation_mae_deg_c": float(row["val_mae"]),
                "test_mae_deg_c": float(row["test_mae"]),
                "ci_lo_deg_c": float(point["ci_lo"]),
                "ci_hi_deg_c": float(point["ci_hi"]),
                "scaling_json": str(resolve_path(row["scaling_json"]).relative_to(REPO)),
            }
        )
    out = pd.DataFrame(records)
    out["source"] = pd.Categorical(out["source"], SOURCE_ORDER, ordered=True)
    return out.sort_values("source").reset_index(drop=True)


def source_screen_hunt(path: Path) -> pd.DataFrame:
    rows = pd.DataFrame(read_json(path))
    rows = rows[rows.get("rc", 0).eq(0) if "rc" in rows.columns else np.ones(len(rows), dtype=bool)].copy()
    rows["source_label"] = rows["source"].map(SOURCE_SHORT)
    rows["source"] = pd.Categorical(rows["source"], SOURCE_ORDER, ordered=True)
    keep = ["condition", "source", "source_label", "arch", "label", "n_ddg", "n_md", "val_mae", "ci_width", "exp"]
    return rows[[c for c in keep if c in rows.columns]].sort_values(["source", "arch", "label"]).reset_index(drop=True)


def frozen_final() -> pd.DataFrame:
    rows = pd.DataFrame(read_json(RESULTS / "source_screen" / "final_frozen_core_summary.json")["rows"])
    records = []
    for _, row in rows.iterrows():
        point = scaling_point(row["scaling_json"])
        records.append(
            {
                "encoder": "frozen encoder",
                "source": row["source"],
                "label": SOURCE_SHORT.get(row["source"], row["source"]),
                "test_mae_deg_c": float(row["test_mae"]),
                "ci_lo_deg_c": float(point["ci_lo"]),
                "ci_hi_deg_c": float(point["ci_hi"]),
                "validation_mae_deg_c": float(row["val_mae"]),
                "scaling_json": str(resolve_path(row["scaling_json"]).relative_to(REPO)),
            }
        )
    return pd.DataFrame(records)


def encoder_controls(final_sources: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    fine = final_sources[final_sources["source"].isin(["Tm_only", "FEP", "rosetta", MD_CONTACT_Q_SOURCE])].copy()
    fine["encoder"] = "fine-tuned encoder"
    fine = fine.rename(
        columns={
            "test_mae_deg_c": "test_mae_deg_c",
            "ci_lo_deg_c": "ci_lo_deg_c",
            "ci_hi_deg_c": "ci_hi_deg_c",
        }
    )
    fine = fine[["encoder", "source", "label", "test_mae_deg_c", "ci_lo_deg_c", "ci_hi_deg_c", "validation_mae_deg_c", "scaling_json"]]
    out = pd.concat([fine, frozen], ignore_index=True)
    out["source"] = pd.Categorical(out["source"], ["Tm_only", "FEP", "rosetta", MD_CONTACT_Q_SOURCE], ordered=True)
    out["encoder"] = pd.Categorical(out["encoder"], ["frozen encoder", "fine-tuned encoder"], ordered=True)
    return out.sort_values(["source", "encoder"]).reset_index(drop=True)


def data_sources_table() -> pd.DataFrame:
    rows = [
        ("Experimental Tm", "target train", 57),
        ("Experimental Tm", "target validation", 114),
        ("Experimental Tm", "target test", 396),
        ("FEP mutation free energy", "source", 435 + 409),
        ("Rosetta mutation score", "source", 435 + 409),
        ("ThermoMPNN stability score", "source", 435 + 409),
        ("random variants scored by Rosetta", "source", 1000 + 1000),
        ("ESM2 variants scored by Rosetta", "source", 1000 + 1000),
    ]
    q = pd.read_csv(DATA / "md" / "nanobody_qvalue_hphil_400K.csv")
    rows.append(("MD Q-value", "source", len(q)))
    return pd.DataFrame(rows, columns=["data_set", "role", "processed_rows"])


def md_q_summary_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q = pd.read_csv(DATA / "md" / "nanobody_qvalue_hphil_400K.csv")
    q_keep = q[["pdb_id", "q_value_raw", "n_frames_used", "n_contacts", "seq_len", "ddg_scaled01"]].copy()
    stats = []
    for col in ["q_value_raw", "n_frames_used", "n_contacts", "seq_len", "ddg_scaled01"]:
        s = q_keep[col]
        stats.append(
            {
                "variable": col,
                "n": int(s.notna().sum()),
                "min": float(s.min()),
                "median": float(s.median()),
                "max": float(s.max()),
            }
        )

    mdclaw = Path("/home/yasu/tmp/mdclaw")
    method_rows = []
    manifest_path = mdclaw / "nano_manifest_400K.json"
    sabdab_path = mdclaw / "sabdab_nano_summary_all.tsv"
    if manifest_path.exists() and sabdab_path.exists():
        manifest = read_json(manifest_path)
        sabdab = pd.read_csv(sabdab_path, sep="\t")
        selected = []
        for entry in manifest:
            idx = int(entry["tsv_row"]) - 1
            if 0 <= idx < len(sabdab):
                selected.append(sabdab.iloc[idx])
        selected_df = pd.DataFrame(selected)
        for method, count in selected_df["method"].value_counts(dropna=False).items():
            method_rows.append({"method": str(method), "structures": int(count)})
    else:
        method_rows = [
            {"method": "X-RAY DIFFRACTION", "structures": 798},
            {"method": "ELECTRON MICROSCOPY", "structures": 345},
            {"method": "SOLUTION NMR", "structures": 3},
        ]
    methods = pd.DataFrame(method_rows).sort_values("structures", ascending=False).reset_index(drop=True)
    return q_keep, pd.DataFrame(stats), methods


def scaling_table() -> pd.DataFrame:
    specs = [
        ("experimental Tm labels", RESULTS / "tm_ref_hot_mtl_tmselect" / "scaling.json", "target labels", COL["tm"]),
        ("FEP mutation free-energy labels", RESULTS / "fep_hot_tmselect_enc3e-5" / "scaling.json", "source labels", COL["fep"]),
        ("MD Q-value labels", RESULTS / "hot_q_400k_tmselect" / "scaling.json", "source labels", COL["mdq"]),
    ]
    rows = []
    for label, path, x_kind, color in specs:
        for point in all_scaling_points(path):
            rows.append(
                {
                    "curve": label,
                    "label_kind": x_kind,
                    "n_labels": int(point["n"]),
                    "mae_deg_c": float(point["mae"]),
                    "ci_lo_deg_c": float(point["ci_lo"]),
                    "ci_hi_deg_c": float(point["ci_hi"]),
                    "color": color,
                    "source_json": str(path.relative_to(REPO)),
                }
            )
    return pd.DataFrame(rows)


def source_count_selected_table() -> pd.DataFrame:
    rows = []
    for row in read_json(RESULTS / "hparam_search" / "per_nmd_test_summary.json"):
        lo, hi = interval_from_row({"test_mae": row["test_mae"], "ci_width": row["ci_width"]})
        rows.append(
            {
                "n_md_labels": int(row["n_md"]),
                "selected_setting": row["label"],
                "selected_validation_mae_deg_c": float(row["selected_val_mae"]),
                "test_mae_deg_c": float(row["test_mae"]),
                "ci_lo_approx_deg_c": float(lo),
                "ci_hi_approx_deg_c": float(hi),
                "ci_width_deg_c": float(row["ci_width"]),
                "exp": row["exp"],
            }
        )
    return pd.DataFrame(rows).sort_values("n_md_labels").reset_index(drop=True)


def model_size_table(final_sources: pd.DataFrame) -> pd.DataFrame:
    lookup = final_sources.set_index("source")
    rows = [
        ("8M", "Tm labels only", lookup.loc["Tm_only", "test_mae_deg_c"], lookup.loc["Tm_only", "ci_lo_deg_c"], lookup.loc["Tm_only", "ci_hi_deg_c"]),
        ("8M", "FEP mutation free energy", lookup.loc["FEP", "test_mae_deg_c"], lookup.loc["FEP", "ci_lo_deg_c"], lookup.loc["FEP", "ci_hi_deg_c"]),
    ]
    for size, condition, path in [
        ("35M", "Tm labels only", RESULTS / "size35_tm_shared_drop005" / "scaling.json"),
        ("35M", "FEP mutation free energy", RESULTS / "size35_ddg_fep_enc3e-5" / "scaling.json"),
        ("650M", "Tm labels only", RESULTS / "size650_tm_shared_drop005" / "scaling.json"),
        ("650M", "FEP mutation free energy", RESULTS / "size650_ddg_fep_enc3e-5" / "scaling.json"),
    ]:
        point = all_scaling_points(path)[0]
        rows.append((size, condition, point["mae"], point["ci_lo"], point["ci_hi"]))
    out = pd.DataFrame(rows, columns=["esm2_size", "condition", "test_mae_deg_c", "ci_lo_deg_c", "ci_hi_deg_c"])
    out["esm2_size"] = pd.Categorical(out["esm2_size"], ["8M", "35M", "650M"], ordered=True)
    out["condition"] = pd.Categorical(out["condition"], ["Tm labels only", "FEP mutation free energy"], ordered=True)
    return out.sort_values(["esm2_size", "condition"]).reset_index(drop=True)


def head_controls_table(path: Path, encoder: str) -> pd.DataFrame:
    rows = []
    for row in read_json(path)["rows"]:
        point = scaling_point(row["scaling_json"])
        rows.append(
            {
                "encoder": encoder,
                "source_head": {
                    "separate": "template-specific",
                    "shared": "shared",
                    "context": "conditioned",
                    "calibrated": "calibrated",
                }.get(row["ddg_head_mode"], row["ddg_head_mode"]),
                "test_mae_deg_c": float(row["test_mae"]),
                "ci_lo_deg_c": float(point["ci_lo"]),
                "ci_hi_deg_c": float(point["ci_hi"]),
                "validation_mae_deg_c": float(row["val_mae"]),
                "selected_setting": row["label"],
                "exp": row["exp"],
            }
        )
    return pd.DataFrame(rows)


def abcd_table() -> pd.DataFrame:
    label = {
        "A_Tm": "Tm only",
        "B_ddG": "FEP only",
        "C_MD": "MD Q only",
        "D_ddG_MD_validation_selected": "FEP + selected MD",
        "D_ddG_MD_extra_q_hphil": "FEP + MD Q-value",
    }
    rows = []
    for row in read_json(RESULTS / "abcd_search" / "final_abcd_with_dq_summary.json")["rows"]:
        lo, hi = interval_from_row({"test_mae": row["test_mae"], "ci_width": row["ci_width"]})
        rows.append(
            {
                "condition": row["condition"],
                "label": label.get(row["condition"], row["condition"]),
                "architecture": row.get("arch", ""),
                "test_mae_deg_c": float(row["test_mae"]),
                "ci_lo_approx_deg_c": float(lo),
                "ci_hi_approx_deg_c": float(hi),
                "ci_width_deg_c": float(row["ci_width"]),
            }
        )
    return pd.DataFrame(rows)


def md_feature_table() -> pd.DataFrame:
    rows = []
    for row in read_json(RESULTS / "arch_search" / "feature_summary.json"):
        rows.append(
            {
                "feature": row["condition"],
                "label": MD_FEATURE_LABEL.get(row["condition"], row["condition"]),
                "validation_mae_deg_c": float(row["val_mae"]),
                "ci_width_deg_c": float(row["ci_width"]),
                "architecture": row["arch"],
                "exp": row["exp"],
            }
        )
    out = pd.DataFrame(rows).sort_values("validation_mae_deg_c").reset_index(drop=True)
    return out


def architecture_controls_table() -> pd.DataFrame:
    label = {
        "tm_latent_drop0.30": "Tm only, latent-control architecture",
        "tm_residual_enc3e-4": "Tm only, residual-control architecture",
        "residual_q_hphil_400k": "MD Q-value, residual-control architecture",
        "residual_q_hphil_400k_shuf": "MD Q-value, shuffled labels",
        "residual_cdr3_len": "CDR3 length",
        "residual_rmsf_cdr3": "CDR3 residue fluctuation",
        "residual_ss_dist_std": "disulfide-distance fluctuation",
        "residual_rmsf_max": "maximum residue fluctuation",
    }
    rows = []
    for row in read_json(RESULTS / "arch_search" / "final_summary.json"):
        lo, hi = interval_from_row({"test_mae": row["test_mae"], "ci_width": row["ci_width"]})
        rows.append(
            {
                "condition": row["condition"],
                "label": label.get(row["condition"], row["condition"]),
                "architecture": row["arch"],
                "n_md": int(row["n_md"]),
                "test_mae_deg_c": float(row["test_mae"]),
                "ci_lo_approx_deg_c": float(lo),
                "ci_hi_approx_deg_c": float(hi),
                "ci_width_deg_c": float(row["ci_width"]),
                "exp": row["exp"],
            }
        )
    return pd.DataFrame(rows)


def trajectory_length_table() -> pd.DataFrame:
    rows = []
    for path in sorted(RESULTS.glob("short_*")):
        scaling = path / "scaling.json"
        if not scaling.exists():
            continue
        data = read_json(scaling)
        args = data.get("args", {})
        source = args.get("md_source", "")
        match = re.search(r"_T(\d+)$", source)
        if not match:
            continue
        point = data.get("best", data["scaling"][-1])
        rows.append(
            {
                "encoder": "fine-tuned encoder" if "short_hot" in path.name else "frozen encoder",
                "trajectory_ns": int(match.group(1)),
                "test_mae_deg_c": float(point["mae"]),
                "ci_width_deg_c": float(point.get("ci_width", np.nan)),
                "exp": path.name,
            }
        )
    out = pd.DataFrame(rows)
    out["encoder"] = pd.Categorical(out["encoder"], ["frozen encoder", "fine-tuned encoder"], ordered=True)
    return out.sort_values(["encoder", "trajectory_ns"]).reset_index(drop=True)


def md_label_distribution_table() -> pd.DataFrame:
    specs = [
        ("Q-value, 400 K", DATA / "md" / "nanobody_qvalue_hphil_400K.csv", "q_value_raw"),
        ("minimum Q-value, 400 K", DATA / "md" / "feat_q_min_400K.csv", "q_min"),
        ("Q-value fluctuation, 400 K", DATA / "md" / "feat_q_std_400K.csv", "q_std"),
        ("maximum residue fluctuation", DATA / "md" / "feat_rmsf_max.csv", "rmsf_max"),
        ("salt-bridge persistence", DATA / "md" / "feat_saltbridge.csv", "saltbridge"),
    ]
    rows = []
    for label, path, preferred in specs:
        df = pd.read_csv(path)
        col = preferred if preferred in df.columns else "ddg_scaled01"
        for val in df[col].dropna().to_numpy(dtype=float):
            rows.append({"label": label, "value": float(val), "source_file": str(path.relative_to(REPO))})
    return pd.DataFrame(rows)


def candidate_label(row: pd.Series) -> str:
    label = str(row.get("label", "default"))
    if label == "default":
        return "default"
    if label == "fixed":
        return "fixed source weight"
    if label.startswith("fixed_w"):
        return "fixed source weight " + label.split("fixed_w", 1)[1]
    if label.startswith("drop"):
        return "dropout " + label.replace("drop", "")
    if label.startswith("enc"):
        return "encoder LR " + label.replace("enc", "")
    if label.startswith("lr"):
        return "lower trunk LR"
    return label


def fig_s1_data_and_md(q: pd.DataFrame, methods: pd.DataFrame, sources: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.0), constrained_layout=True)

    ax = axes[0, 0]
    source_counts = sources.copy()
    source_counts["plot_label"] = [
        "Tm train",
        "Tm validation",
        "Tm test",
        "FEP",
        "Rosetta",
        "ThermoMPNN",
        "random/Rosetta",
        "ESM2/Rosetta",
        "MD Q-value",
    ]
    source_counts = source_counts.iloc[::-1].reset_index(drop=True)
    ypos = np.arange(len(source_counts))
    colors = [
        COL["tm"] if r == "target train" else COL["light_gray"] if r.startswith("target") else COL["mdq"] if "MD" in d else COL["fep"]
        for d, r in zip(source_counts["data_set"], source_counts["role"])
    ]
    ax.barh(ypos, source_counts["processed_rows"], color=colors, edgecolor="white", linewidth=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("processed rows")
    ax.set_yticks(ypos)
    ax.set_yticklabels(source_counts["plot_label"])
    ax.invert_yaxis()
    polish(ax, "x")
    panel_label(ax, "A")

    ax = axes[0, 1]
    ax.hist(q["q_value_raw"], bins=32, color=COL["mdq"], alpha=0.82, edgecolor="white", linewidth=0.4)
    ax.axvline(q["q_value_raw"].median(), color=COL["black"], linewidth=1.1)
    ax.set_xlabel("raw MD Q-value")
    ax.set_ylabel("structures")
    polish(ax, "y")
    panel_label(ax, "B")

    ax = axes[1, 0]
    ax.scatter(q["seq_len"], q["q_value_raw"], s=10, color=COL["mdq"], alpha=0.42, edgecolor="none")
    ax.set_xlabel("sequence length")
    ax.set_ylabel("raw MD Q-value")
    ax.set_xlim(45, max(470, q["seq_len"].max() + 10))
    ax.set_ylim(0.0, 1.02)
    polish(ax, "both")
    panel_label(ax, "C")

    ax = axes[1, 1]
    method_labels = methods["method"].str.replace("X-RAY DIFFRACTION", "X-ray", regex=False)
    method_labels = method_labels.str.replace("ELECTRON MICROSCOPY", "EM", regex=False)
    method_labels = method_labels.str.replace("SOLUTION NMR", "NMR", regex=False)
    ypos = np.arange(len(methods))
    ax.barh(ypos, methods["structures"], color=[COL["design"], COL["rosetta"], COL["gray"]][: len(methods)], edgecolor="white")
    ax.set_yticks(ypos)
    ax.set_yticklabels(method_labels)
    ax.invert_yaxis()
    ax.set_xlabel("selected SAbDab structures")
    polish(ax, "x")
    panel_label(ax, "D")

    save_figure(fig, "supp_fig01_data_and_md_label")


def fig_s2_candidate_settings(hunt: pd.DataFrame, frozen_hunt: pd.DataFrame, head_hunt: pd.DataFrame, final_sources: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2), constrained_layout=True)

    ax = axes[0, 0]
    plot_order = SOURCE_ORDER
    for i, source in enumerate(plot_order):
        vals = hunt.loc[hunt["source"].astype(str) == source, "val_mae"].dropna().to_numpy(float)
        if len(vals) == 0:
            continue
        x = np.full(len(vals), i) + np.linspace(-0.18, 0.18, len(vals))
        ax.scatter(x, vals, s=18, color=SOURCE_COLOR[source], alpha=0.55, edgecolor="white", linewidth=0.3)
        best = vals.min()
        ax.scatter([i], [best], s=44, color=SOURCE_COLOR[source], marker="D", edgecolor="white", linewidth=0.6, zorder=5)
    ax.set_xticks(np.arange(len(plot_order)))
    ax.set_xticklabels([SOURCE_TICK[s] for s in plot_order])
    ax.set_ylabel("experimental validation MAE (deg C)")
    ax.set_ylim(5.55, 7.25)
    polish(ax, "y")
    panel_label(ax, "A")

    ax = axes[0, 1]
    frozen_order = ["Tm_only", "FEP", "rosetta", MD_CONTACT_Q_SOURCE]
    for i, source in enumerate(frozen_order):
        vals = frozen_hunt.loc[frozen_hunt["source"].astype(str) == source, "val_mae"].dropna().to_numpy(float)
        x = np.full(len(vals), i) + np.linspace(-0.17, 0.17, max(len(vals), 1))[: len(vals)]
        ax.scatter(x, vals, s=18, color=SOURCE_COLOR[source], alpha=0.55, edgecolor="white", linewidth=0.3)
        if len(vals):
            ax.scatter([i], [vals.min()], s=44, color=SOURCE_COLOR[source], marker="D", edgecolor="white", linewidth=0.6, zorder=5)
    ax.set_xticks(np.arange(len(frozen_order)))
    ax.set_xticklabels([SOURCE_TICK[s] for s in frozen_order])
    ax.set_ylabel("experimental validation MAE (deg C)")
    ax.set_ylim(6.3, 7.6)
    polish(ax, "y")
    panel_label(ax, "B")

    ax = axes[1, 0]
    head_order = ["separate", "shared", "context", "calibrated"]
    head_names = {
        "separate": "template-\nspecific",
        "shared": "shared",
        "context": "conditioned",
        "calibrated": "calibrated",
    }
    for i, mode in enumerate(head_order):
        vals = head_hunt.loc[head_hunt["ddg_head_mode"] == mode, "val_mae"].dropna().to_numpy(float)
        x = np.full(len(vals), i) + np.linspace(-0.18, 0.18, len(vals))
        ax.scatter(x, vals, s=18, color=COL["fep"], alpha=0.55, edgecolor="white", linewidth=0.3)
        if len(vals):
            ax.scatter([i], [vals.min()], s=44, color=COL["fep"], marker="D", edgecolor="white", linewidth=0.6, zorder=5)
    ax.set_xticks(np.arange(len(head_order)))
    ax.set_xticklabels([head_names[h] for h in head_order])
    ax.set_ylabel("experimental validation MAE (deg C)")
    ax.set_ylim(5.55, 7.35)
    polish(ax, "y")
    panel_label(ax, "C")

    ax = axes[1, 1]
    for _, row in final_sources.iterrows():
        source = str(row["source"])
        ax.scatter(
            row["validation_mae_deg_c"],
            row["test_mae_deg_c"],
            s=46,
            color=SOURCE_COLOR[source],
            edgecolor="white",
            linewidth=0.6,
            zorder=3,
        )
        if source in ["Tm_only", "FEP", MD_CONTACT_Q_SOURCE]:
            ax.annotate(
                SOURCE_SHORT[source],
                xy=(row["validation_mae_deg_c"], row["test_mae_deg_c"]),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=6.8,
                arrowprops=dict(arrowstyle="-", lw=0.45, color=COL["gray"]),
            )
    ax.set_xlabel("selected validation MAE (deg C)")
    ax.set_ylabel("held-out test MAE (deg C)")
    ax.set_xlim(5.68, 6.28)
    ax.set_ylim(6.15, 6.85)
    polish(ax, "both")
    panel_label(ax, "D")

    save_figure(fig, "supp_fig02_candidate_setting_search")


def fig_s3_controls(encoders: pd.DataFrame, heads_hot: pd.DataFrame, heads_frozen: pd.DataFrame, abcd: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.1), constrained_layout=True)

    ax = axes[0, 0]
    sources = ["Tm_only", "FEP", "rosetta", MD_CONTACT_Q_SOURCE]
    offsets = {"frozen encoder": -0.13, "fine-tuned encoder": 0.13}
    markers = {"frozen encoder": "s", "fine-tuned encoder": "o"}
    for encoder in ["frozen encoder", "fine-tuned encoder"]:
        subset = encoders[encoders["encoder"] == encoder].set_index("source")
        for i, source in enumerate(sources):
            row = subset.loc[source]
            horizontal_interval(
                ax,
                i + offsets[encoder],
                row["test_mae_deg_c"],
                row["ci_lo_deg_c"],
                row["ci_hi_deg_c"],
                SOURCE_COLOR[source],
                marker=markers[encoder],
            )
    ax.set_yticks(np.arange(len(sources)))
    ax.set_yticklabels([SOURCE_LABEL[s] for s in sources])
    ax.invert_yaxis()
    ax.set_xlabel("held-out test MAE (deg C)")
    ax.set_xlim(5.95, 7.70)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="s", color=COL["black"], linestyle="none", label="frozen encoder", markersize=5),
            Line2D([0], [0], marker="o", color=COL["black"], linestyle="none", label="fine-tuned encoder", markersize=5),
        ],
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.55, 1.01),
        ncol=2,
    )
    polish(ax, "x")
    panel_label(ax, "A")

    for ax, df, letter, xlim in [
        (axes[0, 1], heads_hot, "B", (5.95, 6.78)),
        (axes[1, 0], heads_frozen, "C", (7.05, 7.34)),
    ]:
        ordered = df.sort_values("test_mae_deg_c")
        y = np.arange(len(ordered))
        for i, (_, row) in enumerate(ordered.iterrows()):
            horizontal_interval(ax, i, row["test_mae_deg_c"], row["ci_lo_deg_c"], row["ci_hi_deg_c"], COL["fep"])
            ax.text(xlim[1] - 0.015, i, f"{row['test_mae_deg_c']:.2f}", va="center", ha="right", fontsize=6.8)
        ax.set_yticks(y)
        ax.set_yticklabels(ordered["source_head"])
        ax.invert_yaxis()
        ax.set_xlabel("held-out test MAE (deg C)")
        ax.set_xlim(*xlim)
        polish(ax, "x")
        panel_label(ax, letter)

    ax = axes[1, 1]
    order = [
        "Tm only",
        "FEP only",
        "MD Q only",
        "FEP + MD Q-value",
        "FEP + selected MD",
    ]
    plot = abcd.set_index("label").loc[order].reset_index()
    y = np.arange(len(plot))
    colors = [COL["tm"], COL["fep"], COL["mdq"], COL["mdq"], COL["rmsf"]]
    for i, (_, row) in enumerate(plot.iterrows()):
        horizontal_interval(
            ax,
            i,
            row["test_mae_deg_c"],
            row["ci_lo_approx_deg_c"],
            row["ci_hi_approx_deg_c"],
            colors[i],
            alpha=0.94,
        )
        ax.text(6.93, i, f"{row['test_mae_deg_c']:.2f}", va="center", ha="right", fontsize=6.8)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["label"])
    ax.invert_yaxis()
    ax.set_xlabel("held-out test MAE (deg C)")
    ax.set_xlim(6.15, 6.95)
    polish(ax, "x")
    panel_label(ax, "D")

    save_figure(fig, "supp_fig03_model_controls")


def fig_s4_scaling(scaling: pd.DataFrame, selected_md: pd.DataFrame, model_sizes: pd.DataFrame, traj: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.9), constrained_layout=True)

    ax = axes[0, 0]
    for curve, color in [
        ("experimental Tm labels", COL["tm"]),
        ("FEP mutation free-energy labels", COL["fep"]),
        ("MD Q-value labels", COL["mdq"]),
    ]:
        subset = scaling[scaling["curve"] == curve]
        ax.fill_between(subset["n_labels"], subset["ci_lo_deg_c"], subset["ci_hi_deg_c"], color=color, alpha=0.10, lw=0)
        ax.plot(subset["n_labels"], subset["mae_deg_c"], marker="o", color=color, label=curve)
    ax.set_xscale("log")
    ax.set_xlabel("labels used")
    ax.set_ylabel("held-out test MAE (deg C)")
    ax.set_ylim(6.05, 7.90)
    ax.legend(frameon=False, loc="upper right")
    polish(ax, "both")
    panel_label(ax, "A")

    ax = axes[0, 1]
    baseline = selected_md.loc[selected_md["n_md_labels"] == 0, "test_mae_deg_c"].iloc[0]
    ax.axhline(baseline, color=COL["tm"], linestyle="--", linewidth=1.1, label="selected Tm-only reference")
    ax.plot(selected_md["n_md_labels"].replace(0, 1), selected_md["test_mae_deg_c"], marker="o", color=COL["mdq"])
    ax.fill_between(
        selected_md["n_md_labels"].replace(0, 1),
        selected_md["ci_lo_approx_deg_c"],
        selected_md["ci_hi_approx_deg_c"],
        color=COL["mdq"],
        alpha=0.08,
        lw=0,
    )
    ax.set_xscale("log")
    ax.set_xticks([1, 10, 40, 80, 160, 320, 640])
    ax.set_xticklabels(["0", "10", "40", "80", "160", "320", "640"])
    ax.set_xlabel("MD Q-value labels used")
    ax.set_ylabel("held-out test MAE (deg C)")
    ax.set_ylim(6.40, 6.95)
    polish(ax, "both")
    panel_label(ax, "B")

    ax = axes[1, 0]
    sizes = ["8M", "35M", "650M"]
    xpos = np.arange(len(sizes))
    offsets = {"Tm labels only": -0.10, "FEP mutation free energy": 0.10}
    colors = {"Tm labels only": COL["tm"], "FEP mutation free energy": COL["fep"]}
    markers = {"Tm labels only": "s", "FEP mutation free energy": "o"}
    for condition in ["Tm labels only", "FEP mutation free energy"]:
        subset = model_sizes[model_sizes["condition"] == condition].set_index("esm2_size")
        vals = np.array([subset.loc[s, "test_mae_deg_c"] for s in sizes], dtype=float)
        lo = vals - np.array([subset.loc[s, "ci_lo_deg_c"] for s in sizes], dtype=float)
        hi = np.array([subset.loc[s, "ci_hi_deg_c"] for s in sizes], dtype=float) - vals
        ax.errorbar(
            xpos + offsets[condition],
            vals,
            yerr=[lo, hi],
            color=colors[condition],
            marker=markers[condition],
            capsize=2.5,
            linewidth=1.0,
            label=condition,
        )
    ax.set_xticks(xpos)
    ax.set_xticklabels(sizes)
    ax.set_xlabel("ESM2 encoder size")
    ax.set_ylabel("held-out test MAE (deg C)")
    ax.set_ylim(6.00, 7.32)
    ax.legend(frameon=False, loc="upper left")
    polish(ax, "y")
    panel_label(ax, "C")

    ax = axes[1, 1]
    for encoder, color, marker in [("frozen encoder", COL["gray"], "s"), ("fine-tuned encoder", COL["mdq"], "o")]:
        subset = traj[traj["encoder"] == encoder]
        ax.plot(subset["trajectory_ns"], subset["test_mae_deg_c"], marker=marker, color=color, label=encoder)
    ax.set_xscale("log")
    ax.set_xticks([5, 10, 17, 30, 50, 100])
    ax.set_xticklabels(["5", "10", "17", "30", "50", "100"])
    ax.set_xlabel("terminal MD window used for Q-value (ns)")
    ax.set_ylabel("held-out test MAE (deg C)")
    ax.set_ylim(6.55, 7.45)
    ax.legend(frameon=False, loc="upper right")
    polish(ax, "both")
    panel_label(ax, "D")

    save_figure(fig, "supp_fig04_scaling_and_size_controls")


def fig_s5_md_features(features: pd.DataFrame, arch: pd.DataFrame, md_dist: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 7.0), constrained_layout=True)

    ax = axes[0, 0]
    top = features.sort_values("validation_mae_deg_c").reset_index(drop=True)
    y = np.arange(len(top))
    colors = [COL["mdq"] if "Q-value" in label else COL["rmsf"] if "fluctuation" in label or "residue" in label else COL["other"] for label in top["label"]]
    ax.barh(y, top["validation_mae_deg_c"], color=colors, edgecolor="white", linewidth=0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(top["label"])
    ax.invert_yaxis()
    ax.set_xlabel("experimental validation MAE (deg C)")
    ax.set_xlim(5.65, 6.35)
    polish(ax, "x")
    panel_label(ax, "A")

    ax = axes[0, 1]
    order = [
        "Tm only, latent-control architecture",
        "MD Q-value, residual-control architecture",
        "MD Q-value, shuffled labels",
        "maximum residue fluctuation",
        "disulfide-distance fluctuation",
    ]
    plot = arch.set_index("label").loc[order].reset_index()
    y = np.arange(len(plot))
    for i, (_, row) in enumerate(plot.iterrows()):
        color = COL["tm"] if "Tm only" in row["label"] else COL["mdq"] if "Q-value" in row["label"] else COL["rmsf"]
        horizontal_interval(ax, i, row["test_mae_deg_c"], row["ci_lo_approx_deg_c"], row["ci_hi_approx_deg_c"], color)
        ax.text(row["ci_hi_approx_deg_c"] + 0.015, i, f"{row['test_mae_deg_c']:.2f}", va="center", fontsize=6.8)
    ax.set_yticks(y)
    ax.set_yticklabels(plot["label"])
    ax.invert_yaxis()
    ax.set_xlabel("held-out test MAE (deg C)")
    ax.set_xlim(6.20, 7.05)
    polish(ax, "x")
    panel_label(ax, "B")

    ax = axes[1, 0]
    keep = ["Q-value, 400 K", "minimum Q-value, 400 K", "Q-value fluctuation, 400 K", "maximum residue fluctuation", "salt-bridge persistence"]
    data = [md_dist.loc[md_dist["label"] == k, "value"].to_numpy(float) for k in keep]
    bp = ax.boxplot(data, patch_artist=True, showfliers=False, widths=0.58)
    for patch, color in zip(bp["boxes"], [COL["mdq"], COL["mdq"], COL["mdq"], COL["rmsf"], COL["other"]]):
        patch.set_facecolor(color)
        patch.set_alpha(0.65)
        patch.set_edgecolor("white")
    for element in ["whiskers", "caps", "medians"]:
        for artist in bp[element]:
            artist.set_color(COL["black"])
            artist.set_linewidth(0.8)
    ax.set_xticks(np.arange(1, len(keep) + 1))
    ax.set_xticklabels(keep, rotation=30, ha="right")
    ax.set_ylabel("raw or scaled feature value")
    polish(ax, "y")
    panel_label(ax, "C")

    ax = axes[1, 1]
    q = md_dist[md_dist["label"].isin(["Q-value, 400 K", "maximum residue fluctuation", "salt-bridge persistence"])].copy()
    summary = q.groupby("label")["value"].agg(["median", "mean", "std"]).reset_index()
    y = np.arange(len(summary))
    ax.barh(y - 0.12, summary["median"], height=0.22, color=COL["black"], alpha=0.85, label="median")
    ax.barh(y + 0.12, summary["std"], height=0.22, color=COL["light_gray"], edgecolor=COL["gray"], label="standard deviation")
    ax.set_yticks(y)
    ax.set_yticklabels(summary["label"])
    ax.invert_yaxis()
    ax.set_xlabel("summary statistic")
    ax.legend(frameon=False, loc="lower right")
    polish(ax, "x")
    panel_label(ax, "D")

    save_figure(fig, "supp_fig05_md_feature_controls")


def build_all_tables() -> dict[str, pd.DataFrame]:
    final_sources = source_screen_final()
    frozen = frozen_final()
    tables = {
        "data_sources": data_sources_table(),
        "final_source_screen": final_sources,
        "source_candidate_settings": source_screen_hunt(RESULTS / "source_screen" / "hpo_summary.json"),
        "frozen_candidate_settings": source_screen_hunt(RESULTS / "source_screen" / "hpo_frozen_core_summary.json"),
        "encoder_controls": encoder_controls(final_sources, frozen),
        "scaling_curves": scaling_table(),
        "candidate_selected_md_q_scaling": source_count_selected_table(),
        "model_size_controls": model_size_table(final_sources),
        "fep_head_controls_fine_tuned": head_controls_table(RESULTS / "ddg_head_search" / "final_ddg_head_summary.json", "fine-tuned encoder"),
        "fep_head_controls_frozen": head_controls_table(RESULTS / "ddg_head_search" / "frozen" / "final_ddg_head_summary.json", "frozen encoder"),
        "fep_head_candidate_settings": pd.DataFrame(read_json(RESULTS / "ddg_head_search" / "hpo_summary.json")),
        "source_combination_controls": abcd_table(),
        "md_feature_survey": md_feature_table(),
        "architecture_controls": architecture_controls_table(),
        "trajectory_length_controls": trajectory_length_table(),
        "md_label_distributions": md_label_distribution_table(),
    }
    q, q_stats, methods = md_q_summary_tables()
    tables["md_qvalue_rows"] = q
    tables["md_qvalue_summary"] = q_stats
    tables["md_structure_methods"] = methods
    return tables


def write_all_tables(tables: dict[str, pd.DataFrame]) -> None:
    for name, df in tables.items():
        write_table(df, f"{name}.tsv")


def write_manifest() -> None:
    """Write a panel-level map from figures to tables and upstream sources."""
    rows = [
        {
            "figure": "Supplementary Fig. 1",
            "panel": "A",
            "figure_file": "figures/supp_fig01_data_and_md_label.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig01_data_and_md_label.pdf",
            "source_tables": "tables/data_sources.tsv",
            "upstream_sources": "data/nbbench/train.csv; data/nbbench/val.csv; data/nbbench/test.csv; data/md/nanobody_qvalue_hphil_400K.csv",
            "table_builder": "data_sources_table",
            "panel_builder": "fig_s1_data_and_md",
            "reviewer_question": "What target and source-label data sizes are used?",
            "notes": "Processed row counts used by the reported comparisons.",
        },
        {
            "figure": "Supplementary Fig. 1",
            "panel": "B",
            "figure_file": "figures/supp_fig01_data_and_md_label.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig01_data_and_md_label.pdf",
            "source_tables": "tables/md_qvalue_rows.tsv; tables/md_qvalue_summary.tsv",
            "upstream_sources": "data/md/nanobody_qvalue_hphil_400K.csv",
            "table_builder": "md_q_summary_tables",
            "panel_builder": "fig_s1_data_and_md",
            "reviewer_question": "What is the raw distribution of the MD Q-value source label?",
            "notes": "Raw Q-values before min-max scaling.",
        },
        {
            "figure": "Supplementary Fig. 1",
            "panel": "C",
            "figure_file": "figures/supp_fig01_data_and_md_label.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig01_data_and_md_label.pdf",
            "source_tables": "tables/md_qvalue_rows.tsv",
            "upstream_sources": "data/md/nanobody_qvalue_hphil_400K.csv",
            "table_builder": "md_q_summary_tables",
            "panel_builder": "fig_s1_data_and_md",
            "reviewer_question": "Does MD Q-value mainly reflect sequence length?",
            "notes": "Scatter of raw Q-value against sequence length.",
        },
        {
            "figure": "Supplementary Fig. 1",
            "panel": "D",
            "figure_file": "figures/supp_fig01_data_and_md_label.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig01_data_and_md_label.pdf",
            "source_tables": "tables/md_structure_methods.tsv",
            "upstream_sources": "/home/yasu/tmp/mdclaw/nano_manifest_400K.json; /home/yasu/tmp/mdclaw/sabdab_nano_summary_all.tsv",
            "table_builder": "md_q_summary_tables",
            "panel_builder": "fig_s1_data_and_md",
            "reviewer_question": "What experimental structure methods support the MD panel?",
            "notes": "Falls back to stored counts if local MDClaw metadata are unavailable.",
        },
        {
            "figure": "Supplementary Fig. 2",
            "panel": "A",
            "figure_file": "figures/supp_fig02_candidate_setting_search.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig02_candidate_setting_search.pdf",
            "source_tables": "tables/source_candidate_settings.tsv",
            "upstream_sources": "results/source_screen/hpo_summary.json",
            "table_builder": "source_screen_hunt",
            "panel_builder": "fig_s2_candidate_settings",
            "reviewer_question": "Which candidate settings were screened for fine-tuned-encoder source comparisons?",
            "notes": "Diamonds mark the lowest experimental validation MAE per source.",
        },
        {
            "figure": "Supplementary Fig. 2",
            "panel": "B",
            "figure_file": "figures/supp_fig02_candidate_setting_search.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig02_candidate_setting_search.pdf",
            "source_tables": "tables/frozen_candidate_settings.tsv",
            "upstream_sources": "results/source_screen/hpo_frozen_core_summary.json",
            "table_builder": "source_screen_hunt",
            "panel_builder": "fig_s2_candidate_settings",
            "reviewer_question": "Which candidate settings were screened for frozen-encoder controls?",
            "notes": "Frozen-encoder validation search for core source labels.",
        },
        {
            "figure": "Supplementary Fig. 2",
            "panel": "C",
            "figure_file": "figures/supp_fig02_candidate_setting_search.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig02_candidate_setting_search.pdf",
            "source_tables": "tables/fep_head_candidate_settings.tsv",
            "upstream_sources": "results/ddg_head_search/hpo_summary.json",
            "table_builder": "read_json",
            "panel_builder": "fig_s2_candidate_settings",
            "reviewer_question": "Which FEP source-head designs were screened?",
            "notes": "Candidate source-head design search for FEP labels.",
        },
        {
            "figure": "Supplementary Fig. 2",
            "panel": "D",
            "figure_file": "figures/supp_fig02_candidate_setting_search.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig02_candidate_setting_search.pdf",
            "source_tables": "tables/final_source_screen.tsv",
            "upstream_sources": "results/source_screen/final_source_screen_summary.json",
            "table_builder": "source_screen_final",
            "panel_builder": "fig_s2_candidate_settings",
            "reviewer_question": "How do selected validation and final test errors relate?",
            "notes": "Target-validation selection is compared with held-out test performance.",
        },
        {
            "figure": "Supplementary Fig. 3",
            "panel": "A",
            "figure_file": "figures/supp_fig03_model_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig03_model_controls.pdf",
            "source_tables": "tables/encoder_controls.tsv",
            "upstream_sources": "results/source_screen/final_source_screen_summary.json; results/source_screen/final_frozen_core_summary.json",
            "table_builder": "encoder_controls",
            "panel_builder": "fig_s3_controls",
            "reviewer_question": "Does the source-label effect depend on fine-tuning the encoder?",
            "notes": "Fine-tuned and frozen encoder final test comparisons.",
        },
        {
            "figure": "Supplementary Fig. 3",
            "panel": "B",
            "figure_file": "figures/supp_fig03_model_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig03_model_controls.pdf",
            "source_tables": "tables/fep_head_controls_fine_tuned.tsv",
            "upstream_sources": "results/ddg_head_search/final_ddg_head_summary.json",
            "table_builder": "head_controls_table",
            "panel_builder": "fig_s3_controls",
            "reviewer_question": "Which FEP source-head design is best with a fine-tuned encoder?",
            "notes": "Final test evaluation of selected source-head designs.",
        },
        {
            "figure": "Supplementary Fig. 3",
            "panel": "C",
            "figure_file": "figures/supp_fig03_model_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig03_model_controls.pdf",
            "source_tables": "tables/fep_head_controls_frozen.tsv",
            "upstream_sources": "results/ddg_head_search/frozen/final_ddg_head_summary.json",
            "table_builder": "head_controls_table",
            "panel_builder": "fig_s3_controls",
            "reviewer_question": "Which FEP source-head design is best with a frozen encoder?",
            "notes": "Frozen-encoder source-head final test controls.",
        },
        {
            "figure": "Supplementary Fig. 3",
            "panel": "D",
            "figure_file": "figures/supp_fig03_model_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig03_model_controls.pdf",
            "source_tables": "tables/source_combination_controls.tsv",
            "upstream_sources": "results/abcd_search/final_abcd_with_dq_summary.json",
            "table_builder": "abcd_table",
            "panel_builder": "fig_s3_controls",
            "reviewer_question": "Do source combinations improve beyond FEP alone?",
            "notes": "Tm-only, FEP-only, MD-only, and combined-source controls.",
        },
        {
            "figure": "Supplementary Fig. 4",
            "panel": "A",
            "figure_file": "figures/supp_fig04_scaling_and_size_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig04_scaling_and_size_controls.pdf",
            "source_tables": "tables/scaling_curves.tsv",
            "upstream_sources": "results/tm_ref_hot_mtl_tmselect/scaling.json; results/fep_hot_tmselect_enc3e-5/scaling.json; results/hot_q_400k_tmselect/scaling.json",
            "table_builder": "scaling_table",
            "panel_builder": "fig_s4_scaling",
            "reviewer_question": "How does label-count scaling differ across target, FEP, and MD Q-value labels?",
            "notes": "Main label-count curves collected in one table.",
        },
        {
            "figure": "Supplementary Fig. 4",
            "panel": "B",
            "figure_file": "figures/supp_fig04_scaling_and_size_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig04_scaling_and_size_controls.pdf",
            "source_tables": "tables/candidate_selected_md_q_scaling.tsv",
            "upstream_sources": "results/hparam_search/per_nmd_test_summary.json",
            "table_builder": "source_count_selected_table",
            "panel_builder": "fig_s4_scaling",
            "reviewer_question": "Does MD Q-value scaling improve when candidate settings are selected separately for each label count?",
            "notes": "Validation-selected MD Q-value controls by source-label count.",
        },
        {
            "figure": "Supplementary Fig. 4",
            "panel": "C",
            "figure_file": "figures/supp_fig04_scaling_and_size_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig04_scaling_and_size_controls.pdf",
            "source_tables": "tables/model_size_controls.tsv",
            "upstream_sources": "results/source_screen/final_source_screen_summary.json; results/size35_tm_shared_drop005/scaling.json; results/size35_ddg_fep_enc3e-5/scaling.json; results/size650_tm_shared_drop005/scaling.json; results/size650_ddg_fep_enc3e-5/scaling.json",
            "table_builder": "model_size_table",
            "panel_builder": "fig_s4_scaling",
            "reviewer_question": "Is the FEP gain explained by ESM2 encoder size?",
            "notes": "8M, 35M, and 650M encoder controls.",
        },
        {
            "figure": "Supplementary Fig. 4",
            "panel": "D",
            "figure_file": "figures/supp_fig04_scaling_and_size_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig04_scaling_and_size_controls.pdf",
            "source_tables": "tables/trajectory_length_controls.tsv",
            "upstream_sources": "results/short_*/*scaling.json",
            "table_builder": "trajectory_length_table",
            "panel_builder": "fig_s4_scaling",
            "reviewer_question": "Does the MD Q-value result depend on the terminal trajectory window?",
            "notes": "Fine-tuned and frozen encoder trajectory-window controls.",
        },
        {
            "figure": "Supplementary Fig. 5",
            "panel": "A",
            "figure_file": "figures/supp_fig05_md_feature_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig05_md_feature_controls.pdf",
            "source_tables": "tables/md_feature_survey.tsv",
            "upstream_sources": "results/arch_search/feature_summary.json",
            "table_builder": "md_feature_table",
            "panel_builder": "fig_s5_md_features",
            "reviewer_question": "Which alternative MD-derived features were screened?",
            "notes": "Experimental validation MAE values for MD-feature candidates.",
        },
        {
            "figure": "Supplementary Fig. 5",
            "panel": "B",
            "figure_file": "figures/supp_fig05_md_feature_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig05_md_feature_controls.pdf",
            "source_tables": "tables/architecture_controls.tsv",
            "upstream_sources": "results/arch_search/final_summary.json",
            "table_builder": "architecture_controls_table",
            "panel_builder": "fig_s5_md_features",
            "reviewer_question": "Do architecture controls rescue MD-derived labels?",
            "notes": "Held-out test controls for selected architecture and shuffled-label settings.",
        },
        {
            "figure": "Supplementary Fig. 5",
            "panel": "C",
            "figure_file": "figures/supp_fig05_md_feature_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig05_md_feature_controls.pdf",
            "source_tables": "tables/md_label_distributions.tsv",
            "upstream_sources": "data/md/nanobody_qvalue_hphil_400K.csv; data/md/feat_q_min_400K.csv; data/md/feat_q_std_400K.csv; data/md/feat_rmsf_max.csv; data/md/feat_saltbridge.csv",
            "table_builder": "md_label_distribution_table",
            "panel_builder": "fig_s5_md_features",
            "reviewer_question": "What are the distributions of representative MD-derived features?",
            "notes": "Boxplots of raw or scaled MD-derived feature values.",
        },
        {
            "figure": "Supplementary Fig. 5",
            "panel": "D",
            "figure_file": "figures/supp_fig05_md_feature_controls.pdf",
            "tex_figure_file": "../../tex/figures/supp_fig05_md_feature_controls.pdf",
            "source_tables": "tables/md_label_distributions.tsv",
            "upstream_sources": "data/md/nanobody_qvalue_hphil_400K.csv; data/md/feat_rmsf_max.csv; data/md/feat_saltbridge.csv",
            "table_builder": "md_label_distribution_table",
            "panel_builder": "fig_s5_md_features",
            "reviewer_question": "How do summary statistics compare for representative MD-derived features?",
            "notes": "Median, mean, and standard deviation are computed from the same long-form table.",
        },
    ]
    path = ANALYSIS / "MANIFEST.tsv"
    pd.DataFrame(rows).to_csv(path, sep="\t", index=False)
    print(f"wrote {path}")


def build_figures(tables: dict[str, pd.DataFrame]) -> None:
    fig_s1_data_and_md(tables["md_qvalue_rows"], tables["md_structure_methods"], tables["data_sources"])
    fig_s2_candidate_settings(
        tables["source_candidate_settings"],
        tables["frozen_candidate_settings"],
        tables["fep_head_candidate_settings"],
        tables["final_source_screen"],
    )
    fig_s3_controls(
        tables["encoder_controls"],
        tables["fep_head_controls_fine_tuned"],
        tables["fep_head_controls_frozen"],
        tables["source_combination_controls"],
    )
    fig_s4_scaling(
        tables["scaling_curves"],
        tables["candidate_selected_md_q_scaling"],
        tables["model_size_controls"],
        tables["trajectory_length_controls"],
    )
    fig_s5_md_features(
        tables["md_feature_survey"],
        tables["architecture_controls"],
        tables["md_label_distributions"],
    )


def main() -> None:
    configure_style()
    ensure_dirs()
    tables = build_all_tables()
    write_all_tables(tables)
    write_manifest()
    build_figures(tables)
    print(f"wrote tables to {TABLES}")


if __name__ == "__main__":
    main()
