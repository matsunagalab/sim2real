# Reviewer-Round Analysis Workflow

This file is for the graduate student or maintainer who needs to add
reviewer-requested calculations without breaking the current manuscript result
set.

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
  `fine-tuned encoder`, `frozen encoder`, `FEP mutation free energy`, and
  `MD Q-value`.

## Directory Pattern

Use a new top-level directory for each reviewer question:

```text
results/reviewer_<short_question>/
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

For target Tm data, keep the existing NbBench split files under
`data/nbbench/`. Do not reshuffle these splits during reviewer-round analyses.

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
   table, upstream summary, and reviewer question.
5. Regenerate outputs:

```bash
uv run python plot/make_supplementary_figures.py
```

6. If the manuscript figure set changes, update
   `paper/tex/sections/supplementary.tex` and typeset the PDF.

## Useful Entry Points

- `paper/analysis/supplementary/MANIFEST.tsv`: panel-to-source map.
- `paper/analysis/supplementary/tables/`: compact numerical tables.
- `plot/make_supplementary_figures.py`: supplementary table and figure builder.
- `results/README.md`: current source-of-truth summary list.
- `paper/tex/sections/methods.tex`: main Methods description.
- `paper/tex/sections/supplementary.tex`: detailed supplementary Methods and
  controls.

## Before Committing

Run these checks from the repository root:

```bash
uv run python plot/make_supplementary_figures.py
```

Then typeset from `paper/tex/`:

```bash
env XDG_CACHE_HOME=/tmp/tectonic-cache /tmp/sim2real-latex/bin/tectonic main.tex
```

Commit only the compact summary JSON files, generated paper tables/figures, and
manuscript changes needed for the new analysis. Leave large scratch run
directories untracked unless the team explicitly decides to archive them.
