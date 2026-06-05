# Results Directory Handoff

This directory contains training outputs and compact result summaries. The
manuscript and supplementary figures should be regenerated from tracked summary
JSON files, not by scanning arbitrary run directories.

For a downstream rerun from fixed source-label CSV files, use
`scripts/reproduce_paper_results.py`. See `REPRODUCE.md` for the full workflow.

## Current Manuscript Inputs

The current manuscript-facing figure generators read these summaries directly:

- `results/source_screen/final_source_screen_summary.json`
- `results/source_screen/final_frozen_core_summary.json`
- `results/source_screen/hpo_summary.json`
- `results/source_screen/hpo_frozen_core_summary.json`
- `results/ddg_head_search/final_ddg_head_summary.json`
- `results/ddg_head_search/frozen/final_ddg_head_summary.json`
- `results/ddg_head_search/hpo_summary.json`
- `results/abcd_search/final_abcd_with_dq_summary.json`
- `results/arch_search/final_summary.json`
- `results/arch_search/feature_summary.json`
- `results/hparam_search/per_nmd_test_summary.json`
- `results/tm_ref_hot_mtl_tmselect/scaling.json`
- `results/fep_hot_tmselect_enc3e-5/scaling.json`
- `results/hot_q_400k_tmselect/scaling.json`
- `results/size35_tm_shared_drop005/scaling.json`
- `results/size35_ddg_fep_enc3e-5/scaling.json`
- `results/size650_tm_shared_drop005/scaling.json`
- `results/size650_ddg_fep_enc3e-5/scaling.json`
- `results/short_hot_t*/scaling.json`
- `results/short_frozen_t*/scaling.json`

The exact panel mapping is recorded in
`paper/analysis/supplementary/MANIFEST.tsv`.

## Legacy And Diagnostic Summaries

These tracked summaries are retained because older summaries or diagnostics
refer to them, but the current manuscript figures do not use them as primary
inputs:

- `results/hot_q_400k/scaling.json`
- `results/frozen_q_400k/scaling.json`
- `results/hparam_search/summary.json`

Historical filenames may contain short internal labels. Manuscript text and
figure labels should use reader-facing descriptions such as `hot encoder`,
`frozen encoder`, `FEP mutation free energy`, and `MD Q-value`.

## Scratch Run Directories

Many untracked subdirectories under `results/` are full training runs produced
during source-label, encoder, architecture, model-size, and trajectory-window
searches. Treat them as scratch run outputs unless they have been reduced to a
tracked summary JSON and listed above.

Do not make a manuscript claim from an untracked run directory alone. First
write a compact summary JSON with resolved settings, validation metrics, final
test metrics, bootstrap intervals, and seed-level or example-level records when
available.

## Derived Analyses

Some quantities are computed directly from the tracked scaling summaries, with no
new training. `plot/equivalent_sample_size.py` estimates the equivalent sample
size (computational labels worth one experimental Tm label; Minami et al. 2025)
from `tm_ref_hot_mtl_tmselect/scaling.json`,
`fep_hot_tmselect_enc3e-5/scaling.json`, and `hot_q_400k_tmselect/scaling.json`,
writing `results/equivalent_sample_size.json` and
`results/equivalent_sample_size.md`.

## Adding New Analysis Results

1. Write new jobs under a new directory, for example
   `results/<analysis_name>/<run_name>/`.
2. Preserve the command-line arguments, git commit, random seed, selected split,
   source-label file, encoder mode, loss weights, and checkpoint-selection
   criterion.
3. Select candidate settings using only the experimental Tm validation split.
4. Report final numbers on the held-out experimental Tm test split.
5. Store a compact summary JSON in the analysis directory.
6. Add a table builder and manifest row in
   `plot/make_supplementary_figures.py`.
7. Regenerate the supplementary analysis with
   `uv run python plot/make_supplementary_figures.py`.

This convention keeps the paper outputs reproducible while allowing additional
analyses to be added without overwriting the current result
set.
