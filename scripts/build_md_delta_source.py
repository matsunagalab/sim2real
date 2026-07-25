#!/usr/bin/env python3
"""Build the MD ΔQ transfer-learning source label from the fep_md_400k study.

Input:
  data/md/common_window_q/matched_<sys>_400K_final30ns_backbone_wtref_q.csv
    (record_id, system, mutation, sequence, q_value, n_frames_used, status, ...)
    Q referenced to the shared wild-type crystal chain (reference N); see
    scripts/recompute_common_md_q.py.

ΔQ = Q(mutant) - Q(WT). A more stable mutant retains more native contacts (higher Q),
so ΔQ > 0 = stabilizing relative to WT. The ML label is min-max scaled (ddg_scaled01);
a constant WT offset is absorbed by that scaling, so scaled Q and scaled ΔQ are
identical for the transfer-learning experiment. There is no wild-type trajectory in
the scan, so the parent ΔQ is centred on the scan mean Q (a well-defined dataset
baseline); this only shifts the parent ΔQ column and never changes ddg_scaled01,
the column that feeds training.

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
FINAL_FRAMES = 3000  # final 30 ns at dt = 10 ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="1mel")
    args = ap.parse_args()
    sys = args.system

    qcsv = f"data/md/common_window_q/matched_{sys}_400K_final30ns_backbone_wtref_q.csv"
    df = pd.read_csv(qcsv)
    df = df[df.get("status", "ok").fillna("ok") == "ok"]
    # The canonical variant sequence (the join key shared with the FEP labels and
    # the ESM features) comes from study_qvalue_fep400k; the common-window PDB
    # topology resolves a few terminal residues differently, so we take q_value by
    # record_id from the WT-crystal product but seq from study_qvalue.
    seq_by_vid = pd.read_csv(f"data/md/study_qvalue_fep400k_{sys}.csv").set_index("vid")["seq"]
    df["seq"] = df["record_id"].map(seq_by_vid)
    # Keep only variants that reached the common final 30 ns window (3000 frames at
    # dt=10 ps); shorter (still-running) trajectories would make Q non-comparable.
    full = (df["n_frames_used"] >= FINAL_FRAMES).sum()
    print(f"variants at full final-30ns window: {full}/{len(df)} (dropping partial ones)")
    df = df[df["n_frames_used"] >= FINAL_FRAMES]
    df = df.dropna(subset=["seq", "q_value"]).drop_duplicates(subset="seq").reset_index(drop=True)

    wt_q = df["q_value"].mean()  # nominal baseline; cancels out of ddg_scaled01
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
    print(f"baseline mean Q={wt_q:.4f} | n={len(df)} | ddg(ΔQ) range [{lo:.4f},{hi:.4f}] mean {df['ddg'].mean():.4f}")
    print(f"wrote {parent}\nwrote {proc}")

    # upsert MANIFEST row
    man = pd.read_csv(MANIFEST, sep="\t", dtype=str)
    structure = STRUCT[sys]
    row = {
        "source_key": SOURCE_KEY,
        "label_family": "MD native-contact Q (ΔQ vs WT crystal, fep_md_400k study)",
        "structure": structure,
        "variant_set": "single-mutant variants, 400K MD, final-30ns window",
        "scorer_or_generator": "OpenMM 400K MD + backbone Best-Hummer Q, "
                               "wild-type crystal reference (scripts/recompute_common_md_q.py --reference wt_crystal)",
        "processed_csv": proc,
        "parent_csv": parent,
        "n_rows": str(len(df)),
        "prepare_argument": f"--ddg-source {SOURCE_KEY}",
        "used_in_current_manuscript": "yes",
        "notes": "Backbone Q over final 30 ns, referenced to the shared wild-type crystal "
                 "chain (reference N). ddg_scaled01 (min-max) feeds training and is invariant "
                 "to the WT baseline. Set 'used_in_current_manuscript' to 'no' to disable.",
    }
    mask = (man["source_key"] == SOURCE_KEY) & (man["structure"] == structure)
    man = man[~mask]
    man = pd.concat([man, pd.DataFrame([row])[man.columns]], ignore_index=True)
    man.to_csv(MANIFEST, sep="\t", index=False)
    print(f"updated {MANIFEST} (+{SOURCE_KEY} {structure})")


if __name__ == "__main__":
    main()
