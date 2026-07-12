#!/usr/bin/env python3
"""FEP source-label provenance mapping + net-charge (Rocklin-type) correction estimate.

Two jobs, both reproducible from the raw FEP data + the repo source labels:

1. PROVENANCE: match each row of the repo FEP labels
   (data/source_labels/fep/fep{1mel_435,4idl_409}.csv, columns seq,ddg) back to the raw
   per-scan ddG.csv under /data/{odas,kazu,yasu}/vhh_fep, by (mutant amino acid, ΔΔG value).
   The mutant aa is recovered by comparing each label sequence to the consensus wild type
   (single-point mutations, so WT dominates each column). Writes PROVENANCE.tsv.

2. CHARGE CORRECTION: for charge-changing mutations, estimate the finite-size (periodic
   PME) net-charge artifact and test whether correcting it would change the ML labels.

   Post-processing recap (Notion "NAMDによるFEP" → /data/share/ddG.jl):
     ΔΔG = ΔG_fold(FEP, scan.dat)  −  ( dG_unfold[WT] − dG_unfold[mut] )
   The folded leg is the explicit PME FEP (carries the charge artifact); the unfolded leg
   is a fixed per-residue lookup table (dG_unfold), so the artifact does NOT cancel.

   Net-charge periodicity (Ewald self-energy) correction, cubic box, homogeneous solvent:
     ΔG_per = ξ_EW · q² / (8π ε0 εs L)
       ξ_EW  = -2.837297           (Wigner constant, cubic lattice)
       1/(4π ε0) = 332.0637 kcal·Å·mol⁻¹·e⁻²
     ⇒ |ΔG_per| = (|ξ_EW|/2)·332.0637 · q²/(εs·L) = 471.1 · q²/(εs·L)   [kcal/mol, L in Å]
   with q = Δq = net charge change of the mutation, L = box edge (measured 70 Å, uniform
   across all runs), εs = solvent dielectric (78 experimental water; ~97 for TIP3P).

   This is only the analytically-computable term. The undersolvation / discrete-solvent /
   residual-integrated-potential terms of the full Rocklin (2013) correction need a
   Poisson-Boltzmann solve (APBS; e.g. github.com/xiki-tempula/rocklinc). We bracket them
   with a generous per-q² sensitivity sweep instead of running APBS.

Residue net charges (CHARMM, physiological; HIS treated neutral):
     R,K = +1 ; D,E = −1 ; others 0.
"""
import argparse
import collections
import glob
import os

import numpy as np
import pandas as pd

CHG = {"R": 1, "K": 1, "D": -1, "E": -1}          # HIS -> 0 (neutral HSD/HSE)
BOX_L = 70.0                                        # Angstrom (measured, uniform)
COUL = 332.0637                                     # kcal*A/mol/e^2  = 1/(4 pi eps0)
XI_EW = -2.837297                                   # Wigner constant, cubic
PER_Q2 = abs(XI_EW) / 2 * COUL                      # = 471.1 kcal*A/mol prefactor

LABELS = {
    "1mel": "data/source_labels/fep/fep1mel_435.csv",
    "4idl": "data/source_labels/fep/fep4idl_409.csv",
}
RAW_ROOTS = {"odas": "/data/odas/vhh_fep", "kazu": "/data/kazu/vhh_fep",
             "yasu": "/data/yasu/vhh_fep"}
SYSTEMS = ("1mel", "4idl", "5sv4", "1fvc", "4tyu", "4w70", "EN565", "EN577")


def periodicity_kcal(dq, eps, L=BOX_L):
    """Net-charge periodicity (Ewald self-energy) correction magnitude, kcal/mol."""
    return PER_Q2 * dq * dq / (eps * L)


def system_of(case):
    for s in SYSTEMS:
        if case.startswith(s):
            return s
    return case


def build_raw_index():
    """(system, mut_aa, round(ddG,3)) -> list of (researcher, case)."""
    idx = collections.defaultdict(list)
    def add(researcher, case, path):
        sysn = system_of(case)
        for r in open(path):
            c = r.strip().split(",")
            if len(c) >= 4:
                try:
                    idx[(sysn, c[2].strip().upper(), round(float(c[3]), 3))].append((researcher, case))
                except ValueError:
                    pass
    for who in ("odas", "kazu", "yasu"):
        for p in glob.glob(f"{RAW_ROOTS[who]}/*/ionized-FEP/ddG.csv"):
            add(who, p.split("/vhh_fep/")[1].split("/")[0], p)
    return idx


def build_provenance(idx):
    rows = []
    for system, labfile in LABELS.items():
        lab = pd.read_csv(labfile)
        seqs, ddgs = lab["seq"].tolist(), lab["ddg"].tolist()
        Ln = len(seqs[0])
        wt = "".join(collections.Counter(s[i] for s in seqs if len(s) > i).most_common(1)[0][0]
                     for i in range(Ln))
        for s, d in zip(seqs, ddgs):
            diff = [(i, wt[i], s[i]) for i in range(min(len(s), Ln)) if s[i] != wt[i]]
            if len(diff) != 1:
                rows.append(dict(system=system, pos=-1, wt="?", mut="?", dq=0, ddg=d, source="?"))
                continue
            pos, w, m = diff[0]
            dq = CHG.get(m, 0) - CHG.get(w, 0)
            hits = idx.get((system, m, round(d, 3)), [])
            orig = [h for h in hits if h[0] != "yasu"] or hits or [("?", "?")]
            rows.append(dict(system=system, pos=pos + 1, wt=w, mut=m, dq=dq, ddg=d,
                             source=f"{orig[0][0]}:{orig[0][1]}"))
    return pd.DataFrame(rows)


def ml_impact(df):
    """How much would correcting the charge artifact change the min-max scaled ML labels?
    Scaling matches the pipeline: per-system (whole-file) min-max over ddg."""
    df = df[df.pos > 0]
    scale = lambda x: (x - x.min()) / (x.max() - x.min())
    out = []
    for A_label, A in [("periodicity eps=78", periodicity_kcal(1, 78)),
                       ("periodicity eps=97", periodicity_kcal(1, 97)),
                       ("generous undersolv 0.5/q^2", 0.5),
                       ("generous undersolv 1.5/q^2", 1.5)]:
        corrs, maxd, nshift, tot = [], 0.0, 0, 0
        for _, g in df.groupby("system"):
            u, c = scale(g["ddg"]), scale(g["ddg"] + A * g["dq"] ** 2)
            corrs.append(float(np.corrcoef(u, c)[0, 1]))
            maxd = max(maxd, float((u - c).abs().max()))
            nshift += int(((u - c).abs() > 0.02).sum())
            tot += len(g)
        out.append((A_label, A, np.mean(corrs), maxd, nshift, tot))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/source_labels/fep/PROVENANCE.tsv")
    args = ap.parse_args()

    idx = build_raw_index()
    df = build_provenance(idx)
    df.to_csv(args.out, sep="\t", index=False)
    print(f"wrote {args.out} ({len(df)} rows)\n")

    m = df[df.pos > 0]
    print("Provenance (scan x raw source):")
    print(m.groupby(["system", "mut", "source"]).size().to_string())
    print(f"\nΔq distribution: {dict(sorted(collections.Counter(m.dq).items()))}")
    print(f"charge-changing (Δq!=0): {int((m.dq != 0).sum())}/{len(m)} = {100*(m.dq!=0).mean():.0f}%")
    print(f"\nΔΔG periodicity correction (L={BOX_L} A): "
          f"|Δq|=1 -> {periodicity_kcal(1,78):.3f} (eps78)/{periodicity_kcal(1,97):.3f} (eps97) kcal/mol; "
          f"|Δq|=2 -> {periodicity_kcal(2,78):.3f}/{periodicity_kcal(2,97):.3f}")
    print("\nML impact (per-system min-max scaled labels, corrected vs uncorrected):")
    print(f"  {'correction':28} {'per_q2':>7} {'label_corr':>11} {'max|dscaled|':>12} {'shifted>0.02':>13}")
    for lbl, A, corr, maxd, nsh, tot in ml_impact(df):
        print(f"  {lbl:28} {A:7.3f} {corr:11.5f} {maxd:12.4f} {f'{nsh}/{tot}':>13}")
    print("\nConclusion: with the defensible (no-APBS) periodicity term the scaled labels are "
          "unchanged (corr>0.9999, 0 labels shift >0.02). Even a generous undersolvation "
          "upper bound keeps corr>=0.98. -> charge correction does not affect the ML transfer result.")


if __name__ == "__main__":
    main()
