#!/usr/bin/env python3
"""Build the MD ΔQ transfer-learning source label from the fep_md_400k study.

Input:
  data/md/study_qvalue_fep400k_<sys>.csv   (vid, system, mutation, seq, q_value, ...)
  data/md/_wt_q_<sys>.txt                   (WT reference Q, one float)

ΔQ = Q(mutant) - Q(WT). A more stable mutant retains more native contacts (higher Q),
so ΔQ > 0 = stabilizing relative to WT. The ML label is min-max scaled (ddg_scaled01);
note a constant WT offset is absorbed by that scaling, so ΔQ and raw Q give identical
scaled labels for the transfer-learning experiment.

Output:
  data/source_labels/md_fep400k/<sys>_mdq.csv            parent (seq, ddg=ΔQ)
  data/source_labels/md_fep400k/<sys>_mdq_processed.csv  seq, ddg, ddg_neg, ddg_scaled01
  appends/updates a row in data/source_labels/MANIFEST.tsv for --ddg-source MD_FEP400K
"""
import argparse
import os
import pandas as pd

SOURCE_KEY = "MD_FEP400K"
MANIFEST = "data/source_labels/MANIFEST.tsv"
STRUCT = {"1mel": "1MEL", "4idl": "4IDL"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="1mel")
    args = ap.parse_args()
    sys = args.system

    qcsv = f"data/md/study_qvalue_fep400k_{sys}.csv"
    wt_path = f"data/md/_wt_q_{sys}.txt"
    df = pd.read_csv(qcsv)
    wt_q = float(open(wt_path).read().strip())
    # Keep only variants that reached the common 40 ns window (4000 frames at dt=10 ps);
    # shorter (still-running) trajectories would make Q non-comparable.
    full = (df["n_frames_used"] >= 4000).sum()
    print(f"variants at full 40ns window: {full}/{len(df)} (dropping partial ones)")
    df = df[df["n_frames_used"] >= 4000]
    df = df.dropna(subset=["seq", "q_value"]).drop_duplicates(subset="seq").reset_index(drop=True)

    df["ddg"] = df["q_value"] - wt_q                       # ΔQ vs WT
    df["ddg_neg"] = -df["ddg"]
    lo, hi = df["ddg"].min(), df["ddg"].max()
    df["ddg_scaled01"] = (df["ddg"] - lo) / (hi - lo) if hi > lo else 0.5

    outdir = "data/source_labels/md_fep400k"
    os.makedirs(outdir, exist_ok=True)
    parent = f"{outdir}/{sys}_mdq.csv"
    proc = f"{outdir}/{sys}_mdq_processed.csv"
    df[["seq", "ddg"]].to_csv(parent, index=False)
    df[["seq", "ddg", "ddg_neg", "ddg_scaled01"]].to_csv(proc, index=False)
    print(f"WT Q={wt_q:.4f} | n={len(df)} | ddg(ΔQ) range [{lo:.4f},{hi:.4f}] mean {df['ddg'].mean():.4f}")
    print(f"wrote {parent}\nwrote {proc}")

    # upsert MANIFEST row
    man = pd.read_csv(MANIFEST, sep="\t", dtype=str)
    structure = STRUCT[sys]
    row = {
        "source_key": SOURCE_KEY,
        "label_family": "MD native-contact Q (ΔQ vs WT, fep_md_400k study)",
        "structure": structure,
        "variant_set": "single-mutant variants, 400K MD, first-40ns window",
        "scorer_or_generator": "OpenMM 400K MD + Best-Hummer Q (scripts/extract_study_qvalue.py)",
        "processed_csv": proc,
        "parent_csv": parent,
        "n_rows": str(len(df)),
        "prepare_argument": f"--ddg-source {SOURCE_KEY}",
        "used_in_current_manuscript": "yes",
        "notes": "Exploratory partial-data source (study still running). ΔQ=Q(mut)-Q(WT); "
                 "WT from pilot studies/fep_md_400k. Single-system (1mel); set to 'no' to disable.",
    }
    mask = (man["source_key"] == SOURCE_KEY) & (man["structure"] == structure)
    man = man[~mask]
    man = pd.concat([man, pd.DataFrame([row])[man.columns]], ignore_index=True)
    man.to_csv(MANIFEST, sep="\t", index=False)
    print(f"updated {MANIFEST} (+{SOURCE_KEY} {structure})")


if __name__ == "__main__":
    main()
