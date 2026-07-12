#!/usr/bin/env python3
"""Rebuild FEP source labels from ALL raw 1mel/4idl scans (Ala/Asp/Gln/Ile/Phe).

The current repo labels (fep1mel_435, fep4idl_409) only use 4 scans and a partial Asp set.
This rebuilds the full set from the raw per-scan ddG.csv, reconstructing each mutant sequence
from the FEP input PDB (VHH chain) exactly as ddG.jl does (verified: reproduces the existing
repo sequences with <1% mismatch).

Robustness: raw ΔΔG for buried-charge mutations (hydrophobic→Asp, Arg→Gln) is well-converged
(BAR error <0.5) but magnitude-inflated (|ΔΔG| up to ~38 kcal/mol) because ddG.jl's unfolded
reference is a crude per-residue constant table that under-corrects the folded-state desolvation.
Protein folding stability rarely exceeds ~15 kcal/mol, so ΔΔG is **clipped to ±CLIP** before the
min-max scaling, so a handful of inflated values do not dominate the scaled labels.

Output: data/source_labels/fep/fep{sys}_full.csv (seq,ddg) and _full_processed.csv
(seq,ddg,ddg_neg,ddg_scaled01); registers source key FEP_FULL in MANIFEST (keeps original FEP).
"""
import collections
import os

import pandas as pd

CLIP = 15.0  # kcal/mol; |ΔΔG| clipped to [-CLIP, +CLIP] before scaling
AA3 = {'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C', 'GLN': 'Q', 'GLU': 'E',
       'GLY': 'G', 'HIS': 'H', 'ILE': 'I', 'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F',
       'PRO': 'P', 'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'}
PDB = {'1mel': '/data/odas/vhh_fep/1mel/1_oripdb/1mel.pdb',
       '4idl': '/data/odas/vhh_fep/4idl_aspscan/1_oripdb/4idl.pdb'}
RAW = {
    '1mel': {'A': '/data/odas/vhh_fep/1mel/ionized-FEP/ddG.csv',
             'D': '/data/odas/vhh_fep/1mel_aspscan/ionized-FEP/ddG.csv',
             'Q': '/data/odas/vhh_fep/1mel_glnscan_all/ionized-FEP/ddG.csv',
             'I': '/data/kazu/vhh_fep/1mel_ile/ionized-FEP/ddG.csv',
             'F': '/data/kazu/vhh_fep/1mel_phe/ionized-FEP/ddG.csv'},
    '4idl': {'A': '/data/yasu/vhh_fep/4idl/ionized-FEP/ddG.csv',
             'D': '/data/odas/vhh_fep/4idl_aspscan/ionized-FEP/ddG.csv',
             'Q': '/data/odas/vhh_fep/4idl_glnscan_all/ionized-FEP/ddG.csv',
             'I': '/data/kazu/vhh_fep/4idl_ile/ionized-FEP/ddG.csv',
             'F': '/data/kazu/vhh_fep/4idl_phe/ionized-FEP/ddG.csv'},
}
MANIFEST = "data/source_labels/MANIFEST.tsv"


def vhh_ca(path, want_seq):
    """Ordered [(res_id, 1-letter)] of the CA chain whose sequence == want_seq (VHH)."""
    chains = collections.defaultdict(list)
    for l in open(path):
        if l.startswith("ATOM") and l[12:16].strip() == "CA":
            rn = l[17:20].strip()
            if rn in AA3:
                chains[l[21]].append((int(l[22:26]), AA3[rn]))
    for ca in chains.values():
        if "".join(x[1] for x in ca) == want_seq:
            return ca
    # fallback: first chain of matching length
    for ca in chains.values():
        if len(ca) == len(want_seq):
            return ca
    raise RuntimeError(f"no VHH chain matching WT in {path}")


def consensus_wt(system):
    f = f"data/source_labels/fep/fep{system}_{'435' if system=='1mel' else '409'}.csv"
    seqs = pd.read_csv(f)["seq"].tolist()
    L = len(seqs[0])
    return "".join(collections.Counter(s[i] for s in seqs).most_common(1)[0][0] for i in range(L))


def build_system(system):
    wt = consensus_wt(system)
    ca = vhh_ca(PDB[system], wt)
    resid = [r for r, _ in ca]
    rows = {}   # seq -> dict
    stats = collections.Counter()
    for mut, path in RAW[system].items():
        for l in open(path):
            c = l.strip().split(",")
            if len(c) < 4:
                continue
            try:
                rid, w, m, dd = int(c[0]), c[1].strip().upper(), c[2].strip().upper(), float(c[3])
            except ValueError:
                continue
            if rid not in resid:
                stats["skip_resid"] += 1
                continue
            j = resid.index(rid)
            if ca[j][1] != w:
                stats["skip_wtmismatch"] += 1
                continue
            seq = wt[:j] + m + wt[j + 1:]
            rows[seq] = dict(seq=seq, ddg=dd, scan=m, wt=w, pos=j + 1)  # last wins on dup seq
            stats[f"scan_{m}"] += 1
    df = pd.DataFrame(rows.values())
    return df, wt, stats


def main():
    man = pd.read_csv(MANIFEST, sep="\t", dtype=str)
    summary = []
    for system in ("1mel", "4idl"):
        df, wt, stats = build_system(system)
        n_clip = int((df["ddg"].abs() > CLIP).sum())
        df["ddg_clip"] = df["ddg"].clip(-CLIP, CLIP)
        lo, hi = df["ddg_clip"].min(), df["ddg_clip"].max()
        df["ddg_neg"] = -df["ddg_clip"]
        df["ddg_scaled01"] = (df["ddg_clip"] - lo) / (hi - lo)
        outdir = "data/source_labels/fep"
        parent = f"{outdir}/fep{system}_full.csv"
        proc = f"{outdir}/fep{system}_full_processed.csv"
        df[["seq", "ddg"]].rename(columns={"ddg": "ddg"}).to_csv(parent, index=False)
        df[["seq", "ddg_clip", "ddg_neg", "ddg_scaled01"]].rename(
            columns={"ddg_clip": "ddg"}).to_csv(proc, index=False)
        by = {k[5:]: v for k, v in stats.items() if k.startswith("scan_")}
        print(f"[{system}] n={len(df)} (scans {by})  clipped(|ddg|>{CLIP}): {n_clip}  "
              f"skips: resid={stats['skip_resid']} wt={stats['skip_wtmismatch']}")
        struct = system.upper()
        row = {"source_key": "FEP_FULL",
               "label_family": "FEP mutation free energy (all raw scans, clipped)",
               "structure": struct, "variant_set": "Ala/Asp/Gln/Ile/Phe scan, full raw",
               "scorer_or_generator": "NAMD FEP + ddG.jl (scripts/build_fep_full.py)",
               "processed_csv": proc, "parent_csv": parent, "n_rows": str(len(df)),
               "prepare_argument": "--ddg-source FEP_FULL", "used_in_current_manuscript": "yes",
               "notes": f"Full raw 1mel/4idl FEP (5 scans); ddG clipped to +/-{CLIP} kcal/mol "
                        "(buried-charge inflation). Original FEP source kept separately."}
        man = man[~((man.source_key == "FEP_FULL") & (man.structure == struct))]
        man = pd.concat([man, pd.DataFrame([row])[man.columns]], ignore_index=True)
        summary.append((system, len(df), n_clip))
    man.to_csv(MANIFEST, sep="\t", index=False)
    print(f"\nregistered FEP_FULL in {MANIFEST}. total={sum(s[1] for s in summary)} labels "
          f"(clipped {sum(s[2] for s in summary)}).")


if __name__ == "__main__":
    main()
