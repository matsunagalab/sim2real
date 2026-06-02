# Supplementary Analysis Handoff

This folder is intended to make reviewer-round follow-up analyses easy to
extend.

## Files

- `tables/*.tsv`: numerical source data for Supplementary Figs. 1-5.
- `figures/*.pdf` and `figures/*.png`: rendered supplementary figures.
- `../../tex/figures/supp_fig*.pdf`: LaTeX-ready figure copies.
- `../../../plot/make_supplementary_figures.py`: table and figure generator.

## Source-of-truth result summaries

The supplementary figure generator reads these result summaries:

- `results/source_screen/final_source_screen_summary.json`
- `results/source_screen/final_frozen_core_summary.json`
- `results/source_screen/hpo_summary.json`
- `results/source_screen/hpo_frozen_core_summary.json`
- `results/ddg_head_search/final_ddg_head_summary.json`
- `results/ddg_head_search/frozen/final_ddg_head_summary.json`
- `results/abcd_search/final_abcd_with_dq_summary.json`
- `results/arch_search/final_summary.json`
- `results/arch_search/feature_summary.json`
- `results/hparam_search/per_nmd_test_summary.json`

These JSON files should be treated as immutable summaries for the current
manuscript figures. New reviewer-round calculations should write new result
directories and new summary JSON files rather than overwriting these summaries.

## Adding a reviewer-round analysis

1. Run the new training or evaluation job under `results/<analysis_name>/`.
2. Save a compact summary JSON with resolved command-line arguments, selected
   settings, test metrics, bootstrap intervals, and per-example absolute errors
   when available.
3. Add a table builder to `plot/make_supplementary_figures.py`.
4. Add a panel or a new supplementary figure using the generated TSV table.
5. Regenerate with `uv run python plot/make_supplementary_figures.py`.
6. Update `paper/tex/sections/supplementary.tex` if the figure set changes.

## Reporting conventions

- Candidate settings are selected on the experimental Tm validation split.
- Final claims use the held-out experimental Tm test split.
- Single-condition intervals are nonparametric bootstrap intervals over test
  examples.
- Paired comparisons use paired bootstrap resampling of the same test examples.
- Figure labels should use manuscript-facing names such as `fine-tuned encoder`,
  `frozen encoder`, `FEP mutation free energy`, and `MD Q-value`.

## External MD source files

The MD structure manifests and raw MDClaw outputs are stored outside the paper
tree under `/home/yasu/tmp/mdclaw/`. The generated TSV tables in this directory
capture the SAbDab method counts and processed Q-value summaries needed by the
current manuscript.

