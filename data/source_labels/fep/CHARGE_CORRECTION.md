# FEP source labels — provenance + net-charge (Rocklin-type) correction

Reproducible record for two questions about the FEP ΔΔG source labels:
1. Which raw FEP runs do the repo labels come from? (provenance)
2. Do periodic-PME net-charge finite-size artifacts affect the ML labels? (charge correction)

**Provenance script:** `scripts/fep_charge_correction.py` (regenerates `PROVENANCE.tsv`
and the raw-energy correction check). The current scaled-label check is recomputed
by `plot/make_supplementary_figures.py` using the preprocessing steps described
below.
**Raw data:** `/data/{odas,kazu,yasu}/vhh_fep/<system>_<scan>/`. **Post-processing:** `/data/share/ddG.jl`.

---

## 1. Provenance (repo label ↔ raw data)

The repo labels `fep1mel_435.csv` and `fep4idl_409.csv` (columns `seq,ddg`) are the union of
**four scans (Ala/Asp/Gln/Ile); the Phe scan is NOT included.** Each row was matched back to its
raw `ionized-FEP/ddG.csv` by (mutant amino acid, ΔΔG value). Full per-row table: `PROVENANCE.tsv`.

| system | scan (mut) | rows | raw source (original) |
|---|---|---|---|
| **1mel** | Ala (A) | 116 | `odas:1mel` |
| | Asp (D) | 80 | `odas:1mel_aspscan` — 80 is the correct **unique** count (raw ddG.csv has 47 duplicate rows: 80 unique + 47 exact dupes = 127) |
| | Ile (I) | 119 | `kazu:1mel_ile` |
| | Gln (Q) | 120 | `odas:1mel_glnscan_all` |
| **4idl** | Ala (A) | 105 | `yasu:4idl` |
| | Asp (D) | 84 | `odas:4idl_aspscan` |
| | Ile (I) | 113 | `kazu:4idl_ile` |
| | Gln (Q) | 107 | `odas:4idl_glnscan_all` |

Notes: provenance spans **three researchers** (odas: Asp/Gln + 1mel-Ala; kazu: Ile; yasu: 4idl-Ala).
`yasu/vhh_fep/ddG/*.csv` are rounded aggregate copies of the odas/kazu originals.
**Resolved:** 1mel Asp = 80 is the *correct unique* count — the raw `1mel_aspscan/ddG.csv` has
127 rows but 47 are exact duplicates (res_id 2,3,4,… each appear twice with identical ΔΔG), so 80
unique. (Earlier "subset/assembly-artifact" guess was wrong.) Phe scans exist raw but are unused.
A full rebuild adding the Phe scan (+238) and clipping was tested (`scripts/build_fep_full.py`)
and **reverted** — see "Rebuild experiment" below. The original `fep{1mel_435,4idl_409}` are kept.

### ΔΔG post-processing (`/data/share/ddG.jl`)
```
ΔΔG = ΔG_fold(FEP, scan.dat)  −  ( dG_unfold[WT] − dG_unfold[mut] )
```
The folded leg is the explicit periodic-PME FEP; the unfolded leg is a fixed per-residue lookup
table (`dG_unfold`). Because the unfolded leg is a table, the folded-leg charge artifact **does
not cancel** in the ΔΔG. (Numbering via ANARCI aho/kabat; sequences reconstructed by applying the
single mutation to the WT.)

---

## 2. Net-charge finite-size correction

**Setup (measured):** NAMD FEP, PME on, TIP3P, cubic box **L = 70 Å** (uniform across all runs,
odas/kazu/yasu, 1mel and 4idl). WT systems neutralized with fixed (non-alchemical) Na/Cl; **no
co-alchemical counterion**, so a charge-changing mutation leaves the box net-charged during the
transformation.

**Which mutations change net charge** (residue charges: R,K=+1; D,E=−1; else 0):
- Asp scan (→D): WT-neutral → **Δq=−1** (majority); Arg/Lys→Asp → **Δq=−2**; Asp/Glu→Asp → 0.
- Ala/Ile/Gln scans (→neutral): WT-neutral → 0 (majority); charged WT → **Δq=±1**.

Δq distribution over all 844 labels: `{-2: 8, -1: 213, 0: 560, +1: 63}` → **34% are charge-changing.**

**Analytical correction used (no APBS): net-charge periodicity (Ewald self-energy), cubic box**
```
ΔG_per = ξ_EW · q² / (8π ε0 εs L)
  ξ_EW = -2.837297  (Wigner constant, cubic lattice)
  1/(4π ε0) = 332.0637 kcal·Å·mol⁻¹·e⁻²
  ⇒ |ΔG_per| = 471.1 · q²/(εs · L)   [kcal/mol, L in Å]
```
For L=70 Å: |Δq|=1 → **0.086** (εs=78) / 0.069 (εs=97) kcal/mol; |Δq|=2 → **0.345 / 0.278**.

This is only one of the four Rocklin (2013) terms; the undersolvation / discrete-solvent /
residual terms need a Poisson-Boltzmann solve (APBS; e.g. `github.com/xiki-tempula/rocklinc`).
We bracket those with a **generous per-q² sensitivity sweep** instead of running APBS.

### Effect on the ML labels

The current model-facing calculation applies the production preprocessing separately
within each structure table: robust centering/scaling, Yeo--Johnson transformation,
standardization, and min--max scaling. This differs from the older min--max-only
diagnostic retained in `scripts/fep_charge_correction.py`.

| correction (per q²) | scaled-label corr | max &#124;Δscaled&#124; | labels shifted >0.02 |
|---|---|---|---|
| **periodicity, εs=78 (0.086)** | **0.99989** | 0.0077 | **0 / 844** |
| periodicity, εs=97 (0.069) | 0.99993 | 0.0062 | 0 / 844 |
| generous sensitivity value (0.5) | 0.9968 | 0.0403 | 12 / 844 |
| very generous sensitivity value (1.5) | 0.9734 | 0.1089 | 426 / 844 |

**Conclusion:** the correction is a function of Δq² only; with uniform box it is a per-Δq-class
offset that is largely absorbed by the model-facing preprocessing. With the defensible (no-APBS)
periodicity term **no label shifts by >0.02 (correlation 0.99989)**; even the larger sensitivity
values retain correlations above 0.97. **→ The charge correction does not change the FEP transfer/scaling result;
running rocklinc/APBS is unnecessary for the ML source labels.** It would matter only for
*quantitative* ΔΔG of the few Δq=−2 (Arg/Lys→Asp) mutations.

## References
- Rocklin, Mobley, Dill, Hünenberger, *J. Chem. Phys.* **139**, 184103 (2013) — charge-change FEP corrections.
- `xiki-tempula/rocklinc` — Python/APBS implementation of the full Rocklin correction.

---

## Rebuild experiment (tested, reverted)

We rebuilt full FEP labels from all raw scans (Ala/Asp/Gln/Ile/**Phe**) with sequences
reconstructed from the FEP input PDB VHH chain (validated: reproduces the existing repo
sequences with <1% mismatch), and tested two changes vs the original FEP (844, 4 scans, no clip):
adding the **Phe** scan (+238) and **clipping** ΔΔG (the buried-charge inflated tail).

**2×2 disentanglement** (mae_mean; baselines Tm-only hot 6.648 / frozen 7.429):

| | no-clip | clip ±15 |
|---|---|---|
| no Phe (=orig FEP) | **hot 6.601 / frozen 7.253** | hot 6.937 / frozen 7.473 |
| +Phe | hot 6.825 / frozen 7.365 | hot 6.941 / frozen 7.456 |

**Clip-threshold sweep (frozen, no Phe):** ∞ 7.253 → ±30 7.383 → ±25 7.428 → ±20 7.445 → ±15 7.473
— **monotonic: any clipping hurts; no threshold beats no-clip.**

**Conclusion:** both changes hurt, clipping (≈+0.22–0.34) more than Phe (≈+0.11–0.22).
Even clipping only the 4 most-extreme values (±30) hurts. The extreme buried-charge ΔΔG — which
are experimentally **unmeasurable** (poor yield / won't fold) — carry disproportionate transfer
value: they mark the most stability-critical positions, and keeping their full min-max prominence
maximizes transfer. So **the original unclipped FEP (no Phe) is optimal**; it is retained and the
test sources/CSVs were removed. (Contradicts the earlier "clip the inflated values" suggestion —
QC intuition ≠ ML outcome.) `scripts/build_fep_full.py` is kept as the reproducible rebuild record.
