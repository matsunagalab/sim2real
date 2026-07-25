# MD data-design comparison — result (valid-minimal)

**Date:** 2026-07-26
**Question:** holding the Q definition, auxiliary channel, architecture, loss
weighting, and the number of model-visible label pairs fixed, does a matched
single-mutation scan (1MEL/4IDL) or a heterogeneous nanobody panel transfer
better to NbBench melting-temperature prediction?

**Protocol** (`scripts/run_design_comparison.py`; design in
`md_data_design_review.md`): both sources on the MD head (`task_id=3`), shared
architecture, fixed MD loss weight, raw Q as `ddg_scaled01`; nested prefix
subsets (scan stratified 50:50 across the two scaffolds); **no auxiliary
hold-out** (every sampled label trains); checkpoint selection on the
experimental Tm validation set only; per (source, n): **8 subset draws × 3
model-init seeds = 24 fits**, the 3 seeds of one subset ensembled and the 8
subset ensembles kept as independent replicates; two-way (subset × test-protein)
bootstrap of `Δdesign = MAE_scan − MAE_hetero`. Isolated from `prepare.py`
(whose default ensembling averages across different subsets and would defeat the
label-budget match).

**Pools** (`data/source_labels/md_design/`, own_frame0 backbone Q, exact NbBench
matches removed): scan_pool 762 (1MEL 403 + 4IDL 359), heterogeneous 686
(len 50–158, no X, deduplicated to one structure per canonical sequence).

## Primary endpoint (n = 320)

`Δdesign = MAE_scan − MAE_hetero` (°C); positive favours heterogeneous.

| contrast | frozen | hot |
|---|---|---|
| pool vs heterogeneous | **+0.156** [+0.046, +0.274] | **+0.263** [+0.053, +0.477] |
| 1MEL (anchored) vs heterogeneous | +0.136 [+0.031, +0.240] | +0.171 [−0.017, +0.364] |
| 4IDL (no anchor) vs heterogeneous | +0.262 [+0.107, +0.422] | +0.201 [+0.014, +0.399] |

Heterogeneous is better in every contrast; all are significant except hot
1MEL-vs-heterogeneous (P(heterogeneous better)=0.96).

## Scaling (MAE mean over 8 subsets, °C)

| source | frozen n=20→320 | hot n=20→320 |
|---|---|---|
| heterogeneous | 7.331 → **7.122** | 7.114 → **6.710** |
| scan pool | 7.310 → 7.278 | 7.103 → 6.973 |
| scan 1MEL | 7.260 → 7.259 | 7.118 → 6.881 |
| scan 4IDL | 7.316 → 7.385 | 7.086 → 6.911 |

Heterogeneous MAE decreases monotonically with n; the mutation scans saturate
and, for 4IDL frozen, worsen from n=160 to n=320.

## Interpretation

Under a controlled comparison, the **heterogeneous nanobody panel transfers
better than the matched single-mutation scan**, in both encoder regimes and for
each scaffold individually. The effect is not an artefact of the 1MEL anchor
(1MEL is ~99% identical to a NbBench training sequence): the anchored 1MEL scan
still loses, and the unanchored 4IDL scan loses by more. Diverse-sequence labels
keep improving with n while single-fold mutation labels saturate.

**Supported claim (narrow):** for the same Q definition, channel, architecture,
and number of trained label pairs, this two-scaffold matched mutation-scan pool
does **not** transfer better than this deduplicated heterogeneous nanobody pool;
heterogeneous is significantly better at n=320.

**Not supported:** that single-mutation scanning is universally worse, or that
the difference is purely local mutation structure. Concentrating compute on one
or two folds did not help here.

## Deferred (sensitivity, Codex §7–§8)

Tm-only baseline in this harness (to separate "heterogeneous helps" from "scan
hurts"), production absolute-time / frame-cadence alignment, raw-Q vs
rank-normalisation, fixed vs uncertainty loss weight, equal-budget separate HPO,
full-n (762 vs 686), `latent`/`residual` architectures. None is expected to flip
the sign given the size and consistency of the n=320 effect.
