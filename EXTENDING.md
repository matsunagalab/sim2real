# Extending the Analysis

This guide is for anyone adding new calculations to the released analysis without
breaking the published manuscript result set. To reproduce the existing results
first, start with `REPRODUCE.md` and `scripts/reproduce_paper_results.py`.

## Non-Negotiable Protocol

- Keep the NbBench train, validation, and test definitions fixed.
- Select candidate settings and early-stopped checkpoints using only the
  experimental Tm validation split.
- Use the held-out experimental Tm test split only for final reported
  performance.
- Use paired bootstrap resampling when comparing two models on the same test
  examples.
- Do not overwrite tracked summary JSON files. Write new result directories and
  new compact summaries.
- Keep manuscript-facing terminology readable. Internal filenames can be
  historical, but figures and manuscript text should use names such as
  `hot encoder`, `frozen encoder`, `FEP mutation free energy`, and
  `MD Q-value`.

## Directory Pattern

Use a new top-level directory for each new analysis:

```text
results/<analysis_name>/
  README.md
  candidate_search/
  final_eval/
  summary.json
```

The local `README.md` should state the scientific question, source data, command
template, planned seeds, and expected summary fields.

## Step 1: Define The Source Data

For an auxiliary source label, keep a table with at least:

- `seq`: amino-acid sequence.
- one numeric source-label column, for example a scaled mutation free energy or
  a Q-value-derived quantity.
- optional metadata columns such as template, mutation identifier, structure
  source, simulation temperature window, or score type.

For mutation-effect source labels used through `--ddg-source`, place the data
under `data/source_labels/` and add the two active processed CSVs to
`data/source_labels/MANIFEST.tsv`. `prepare.py` reads that manifest directly;
do not add new source-label paths by hard-coding them in Python.

For target Tm data, keep the existing NbBench split files under
`data/nbbench/`. Do not reshuffle these splits.

## Step 2: Candidate-Setting Search

Run a compact validation search before final evaluation. The summary should
record:

- source-label name and path;
- number of target labels and source labels;
- encoder mode;
- architecture/head type;
- learning rates, dropout, loss weights, batch size, and epoch count;
- random seeds;
- best epoch by validation MAE for each seed;
- mean validation MAE used to select the candidate setting.

The selected setting must be chosen by experimental Tm validation MAE, not by
source-label validation loss.

## Step 3: Final Evaluation

After selecting the candidate setting, rerun the final evaluation with the
planned seed count. The final summary should include:

- resolved settings copied from the candidate search;
- seed-level validation and test MAE;
- mean held-out test MAE;
- bootstrap confidence interval for each condition;
- paired bootstrap interval versus the appropriate Tm-only reference;
- per-example absolute errors when possible.

Do not inspect the held-out test results to choose a different setting. If a new
setting is needed, document it as a new candidate search.

## Step 4: Add To The Figure Pipeline

1. Add a table builder to `plot/make_supplementary_figures.py`.
2. Write the compact table under `paper/analysis/supplementary/tables/`.
3. Add or update a plotting panel in the same script.
4. Add a row to the `write_manifest()` output so each panel has a clear source
   table, upstream summary, and the question it answers.
5. Regenerate outputs:

```bash
uv run python plot/make_supplementary_figures.py
```

6. If the manuscript figure set changes, update
   `paper/tex/sections/supplementary.tex` and typeset the PDF.

## Derived Analyses Without Retraining

Some quantities are computed directly from the tracked scaling summaries and need
no new training. For example, the equivalent sample size -- how many computational
labels are worth one experimental Tm label, following the marginal-rate-of
-substitution definition of Minami et al. (2025) -- is computed by:

```bash
python plot/equivalent_sample_size.py
```

- Inputs: `results/tm_ref_hot_mtl_tmselect/scaling.json`,
  `results/fep_hot_tmselect_enc3e-5/scaling.json`,
  `results/hot_q_400k_tmselect/scaling.json`.
- Outputs: `results/equivalent_sample_size.json` and
  `results/equivalent_sample_size.md`.

## Useful Entry Points

- `paper/analysis/supplementary/MANIFEST.tsv`: panel-to-source map.
- `paper/analysis/supplementary/tables/`: compact numerical tables.
- `plot/make_supplementary_figures.py`: supplementary table and figure builder.
- `plot/make_outline_figures.py`: main figure builder.
- `plot/equivalent_sample_size.py`: equivalent-sample-size estimate from the
  scaling curves.
- `results/README.md`: current source-of-truth summary list.
- `paper/tex/sections/methods.tex`: main Methods description.
- `paper/tex/sections/supplementary.tex`: detailed supplementary Methods and
  controls.

## Before Committing

Regenerate the supplementary outputs from the repository root:

```bash
uv run python plot/make_supplementary_figures.py
```

Then typeset from `paper/tex/` with a standard TeX installation:

```bash
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

Commit only the compact summary JSON files, generated paper tables/figures, and
manuscript changes needed for the new analysis. Leave large scratch run
directories untracked unless the team explicitly decides to archive them.
