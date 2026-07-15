# Results directory

This directory contains compact tracked results and many local training runs. Manuscript numbers should come from the tracked files listed here, not from an arbitrary scratch directory.

## Selected current results

The current paper compares seven source-label conditions under frozen and fine-tuned (`hot`) ESM-2 encoders:

| Condition | Frozen result | Fine-tuned result |
|---|---|---|
| Tm labels only | `final_tm_frozen/scaling.json` | `final_tm_hot/scaling.json` |
| FEP mutation free energy | `final_fep_frozen/scaling.json` | `final_fep_hot/scaling.json` |
| matched MD native-contact Q | `final_mdq_frozen/scaling.json` | `final_mdq_hot/scaling.json` |
| ThermoMPNN score | `final_tmpnn_frozen/scaling.json` | `final_tmpnn_hot/scaling.json` |
| Rosetta mutation score | `final_ros_frozen/scaling.json` | `final_ros_hot/scaling.json` |
| random variants + Rosetta | `final_rosrnd_frozen/scaling.json` | `final_rosrnd_hot/scaling.json` |
| ESM2-proposed variants + Rosetta | `final_rosesm_frozen/scaling.json` | `final_rosesm_hot/scaling.json` |

Each file records the command arguments, resolved hyperparameters, held-out MAE and interval, and per-example absolute errors. Computational-label conditions contain label-count curves; the paper uses the 320-label point for its representative comparison.

`plot/build_tuned_summaries.py` reduces these files to the main-figure inputs under `tuned_rep/`:

- `tuned_rep/frozen_summary.json`
- `tuned_rep/hot_summary.json`
- `tuned_rep/<source>_<encoder>/scaling.json`

The reference held-out MAEs are:

| Encoder | Tm only | FEP | matched MD Q |
|---|---:|---:|---:|
| Frozen | 7.229 °C | 7.008 °C | 7.034 °C |
| Fine-tuned | 6.548 °C | 6.395 °C | 6.577 °C |

## Tracked comparison inputs

The figures also use compact results from earlier, clearly labelled controls:

- `source_screen/final_source_screen_summary.json` and `source_screen/final_frozen_core_summary.json`: heterogeneous-nanobody source comparison.
- `tm_ref_hot_mtl_tmselect/scaling.json`, `fep_hot_tmselect_enc3e-5/scaling.json`, and `final_residual_q_hphil_400k/scaling.json`: matched references for the heterogeneous MD comparison.
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
uv run python scripts/reproduce_paper_results.py --stage summaries --force
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

See `REPRODUCE.md` for the GPU-intensive retraining command, the inputs kept fixed, and the calculations that are repeated.

## Adding a result

For a new paper-facing result, preserve the source table, encoder mode, model settings, seeds, selection split, final evaluation split, and per-example errors. Reduce the run to a compact tracked `scaling.json` or summary table before citing it in text or a figure.
