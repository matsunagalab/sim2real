# Supplementary Analysis Files

This folder is intended to make follow-up analyses easy to
extend.

## Files

- `tables/*.tsv`: numerical source data and retained result tables. The selected
  display items are Supplementary Figs. S1--S2.
- `figures/*.pdf` and `figures/*.png`: rendered supplementary figures.
- `MANIFEST.tsv`: panel-level index of figures, source tables, upstream result
  summaries, generator functions, and the question each panel answers.
- `../../tex/figures/supp_fig*.pdf`: LaTeX-ready figure copies.
- `../../../plot/make_supplementary_figures.py`: table and figure generator.

## Panel manifest

Use `MANIFEST.tsv` as the first stop when extending or checking the
supplementary analysis. Each row corresponds to one figure panel and records:

- the rendered figure file and LaTeX-ready copy;
- the compact TSV table used for the panel;
- the generator script;
- the question addressed by the panel.

## Saved result summaries

The supplementary figure generator reads the final per-source runs under
`results/final_*`, the staged Tm-validation searches under `results/tune_*`, the
available ESM2-size controls, and tracked processed label tables. The compact
`candidate_validation.tsv` table is also retained so the figures can be rebuilt
when the full staged-search directories are not present.

These JSON files record the results used by the current manuscript figures.
Write a new result directory and summary JSON for a new analysis instead of
overwriting them.

## Adding a new analysis

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
- Final comparisons use the reserved experimental Tm test split.
- Single-condition intervals are nonparametric bootstrap intervals over test
  examples.
- Paired comparisons use paired bootstrap resampling of the same test examples.
- Figure labels should use manuscript-facing names such as `fine-tuned ESM2`,
  `frozen ESM2`, `FEP mutation free energy`, and `MD native contact`.

## External MD source files

The raw MD trajectories are not stored in the paper tree. The tracked processed
Q-value tables and generated TSV files contain the values needed by the current
supplementary figures.
