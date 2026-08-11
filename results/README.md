# Results directory

This directory contains compact tracked results and many local training runs. Manuscript numbers should come from the tracked files listed here, not from an arbitrary scratch directory.

## Selected current results

The paper has two comparisons, produced by two different harnesses. Both are
reported separately for a frozen and a fine-tuned (`hot`) ESM-2 encoder.

### Fig. 3, physical observable (`prepare.py`, 24-model ensembles)

Six computed observables on the identical 1MEL/4IDL variant set, against a shared
Tm-only baseline. Held-out test MAE at the representative 320-label point:

| Condition | Frozen result | MAE | Fine-tuned result | MAE |
|---|---|---:|---|---:|
| Tm labels only | `n24_tm_frozen_shared/scaling.json` | 7.272 °C | `n24_tm_hot_shared/scaling.json` | 6.718 °C |
| FEP mutation free energy | `fig3_FEP_frozen/scaling.json` | 7.027 °C | `fig3_FEP_hot/scaling.json` | 6.350 °C |
| MD native-contact Q | `fig3_MD_frozen/scaling.json` | 7.161 °C | `fig3_MD_hot/scaling.json` | 6.728 °C |
| Rosetta mutation score | `fig3_ROS_frozen/scaling.json` | 7.226 °C | `fig3_ROS_hot/scaling.json` | 6.756 °C |
| FoldX ddG | `fig3_FOLDX_frozen/scaling.json` | 7.091 °C | `fig3_FOLDX_hot/scaling.json` | 6.598 °C |
| ESM2-proposed variants + Rosetta | `fig3_ROSESM_frozen/scaling.json` | 7.328 °C | `fig3_ROSESM_hot/scaling.json` | 6.603 °C |
| random variants + Rosetta | `fig3_ROSRND_frozen/scaling.json` | 7.246 °C | `fig3_ROSRND_hot/scaling.json` | 6.557 °C |

Each file records the command arguments, resolved hyperparameters, held-out MAE
and interval, and the 396 per-example absolute errors, so the paired bootstrap of
`plot/fig3_matched.py` can be recomputed from the files alone.

### Fig. 2, data design (`scripts/run_design_comparison.py`)

One pre-specified protocol shared by both designs, 8 subset draws x 3
model-initialization seeds. Held-out test MAE at 320 labels:

| Condition | Frozen result | MAE | Fine-tuned result | MAE |
|---|---|---:|---|---:|
| Tm labels only | `design_tmonly_frozen/design.json` | 7.274 °C | `design_tmonly_hot/design.json` | 7.066 °C |
| single mutation scan | `design_aligned_scan_pool_frozen/design.json` | 7.283 °C | `design_aligned_scan_pool_hot/design.json` | 7.075 °C |
| heterogeneous panel | `design_aligned_hetero_frozen/design.json` | 7.184 °C | `design_aligned_hetero_hot/design.json` | 6.763 °C |

The two comparisons have different Tm-only baselines because Fig. 2 fixes one
protocol for both sources instead of tuning per source; never compare a Fig. 2
number with a Fig. 3 baseline. Each `design.json` also records the label pool it
read, in its `pool_dir` and `pool_files` fields.

### Earlier result families

`final_*`, `tuned_rep/*`, and the ThermoMPNN condition (`fig3_TMPNN_*`) come from
an earlier version of this study, in which the architecture was still being
selected and the ensembles were smaller. They are kept for history, are outside
the reproduction workflow, and must not be quoted as current results.

## Tracked comparison inputs

The figures also use compact results from earlier, clearly labelled controls:

- `source_screen/final_source_screen_summary.json` and `source_screen/final_frozen_core_summary.json`: heterogeneous-nanobody source comparison.
- `tm_ref_hot_mtl_tmselect/scaling.json`, `fep_hot_tmselect_enc3e-5/scaling.json`, and `final_residual_q_hphil_400k/scaling.json`: references from the earlier heterogeneous MD comparison.
- `size35_*` and `size650_*`: exploratory fixed-configuration model-size controls.

These controls are retained so the figures can be rebuilt. The availability check confirms that they exist, but the current retraining step does not rerun them.

## Candidate selection records

Candidate runs may exist as untracked `tune_*` directories. The paper-facing records are the tracked tables:

- `paper/analysis/supplementary/tables/candidate_validation.tsv`
- `paper/analysis/supplementary/tables/selected_settings.tsv`

The validation split is used for selecting settings. The held-out test split is used only for the final result files.

## Rebuild

```bash
uv run python scripts/reproduce_paper_results.py --check-only
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

See `REPRODUCE.md` for the GPU-intensive retraining command, the inputs kept fixed, and the calculations that are repeated.

## Adding a result

For a new paper-facing result, preserve the source table, encoder mode, model settings, seeds, selection split, final evaluation split, and per-example errors. Reduce the run to a compact tracked `scaling.json` or summary table before citing it in text or a figure.
