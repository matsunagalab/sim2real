# Reproducing The Manuscript Results

This repository can rerun the manuscript-facing calculations downstream of the
fixed computational source-label tables. The raw MD simulations, FEP
calculations, Rosetta calculations, and ThermoMPNN scoring are not rerun by this
workflow; their processed CSV outputs under `data/` are treated as fixed input
data.

## Scope

The reproducible downstream scope includes:

- model training with the fixed NbBench train, validation, and test splits;
- candidate-setting searches selected by experimental Tm validation MAE;
- held-out experimental Tm test evaluation;
- paired-bootstrap summaries;
- summary JSON files used by the manuscript figures;
- main and supplementary figure regeneration;
- LaTeX PDF typesetting.

The workflow entry point is:

```bash
uv sync
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0,1,2,3,4,5,6
```

By default, existing outputs are skipped. To rerun training from scratch, add
`--force`:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0,1,2,3,4,5,6 --force
```

This is the full downstream rerun path: it starts from the fixed CSV source
labels and regenerates the downstream model results. It will take a long time.

The workflow is manifest-driven. The stage definitions and expected outputs are
stored in `reproduce/manuscript_results.yaml`; the runner is
`scripts/reproduce_paper_results.py`. See `reproduce/README.md` and `EXTENDING.md`
for how to add new calculations.

The fixed computational mutation-label inputs are catalogued in
`data/source_labels/MANIFEST.tsv`. That file records which processed CSVs are
used for FEP, Rosetta, ThermoMPNN, random Rosetta variants, and ESM2-proposed
Rosetta-scored variants.

## Fast Integrity Checks

Check that fixed inputs and manuscript-facing outputs exist without writing
anything:

```bash
uv run python scripts/reproduce_paper_results.py --check-only
```

Print the full command plan without running anything:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --force --dry-run
```

Regenerate only the figures and PDF from existing summary JSON files:

```bash
uv sync
uv run python scripts/reproduce_paper_results.py --stage figures
```

Regenerate summary JSON files from existing `results/*/scaling.json` files
without launching training:

```bash
uv run python scripts/reproduce_paper_results.py --stage source-screen,ddg-head,md-candidate,abcd,architecture --collect-only
```

## Stages

- `preflight`: check fixed input CSV files.
- `core-scaling`: regenerate the main experimental Tm, FEP, and MD Q-value
  label-count curves.
- `source-screen`: rerun the source-label candidate search and final test
  comparison for hot and frozen encoders.
- `ddg-head`: rerun source-head controls for FEP labels.
- `md-candidate`: rerun the per-source-count MD Q-value candidate-setting
  search and final test evaluation.
- `abcd`: rerun Tm-only, FEP-only, MD-only, and FEP+MD controls and rebuild the
  additional Q-value summary used in the supplementary analysis.
- `architecture`: rerun MD-derived feature and architecture controls.
- `model-size`: rerun ESM2 35M and 650M controls.
- `trajectory`: rerun terminal-trajectory-window controls.
- `figures`: regenerate main figures, supplementary figures/tables, and
  `paper/tex/main.pdf`.
- `diagnostic`: regenerate a legacy diagnostic summary that is not a primary
  manuscript input.

Run one stage at a time when debugging:

```bash
uv run python scripts/reproduce_paper_results.py --stage source-screen --gpus 0,1,2,3,4,5,6 --force
```

## Practical Notes

The 650M ESM2 controls are included in `--stage model-size` and therefore in
`--stage all`. They require substantially more GPU memory than the 8M and 35M
models. If they fail because of local GPU memory constraints, keep the failed
log and report that hardware limitation explicitly rather than substituting an
old summary.

The script does not download models intentionally. If a Hugging Face model is
not already cached, the run will fail in an offline environment. Cache the
model explicitly before a full rerun.

All output claims should be made from tracked summary JSON files and the
generated tables under `paper/analysis/supplementary/tables/`, not from
untracked scratch run directories.

## Environment

`uv sync` installs the packages needed for the manuscript-facing workflow:
model training, candidate-setting searches, summary aggregation, figure
generation, and MD-feature extraction from raw trajectories. Notebook support is
optional and can be installed with:

```bash
uv sync --extra notebooks
```

The PDF typesetting step is launched through `scripts/typeset_paper.py`. It
uses `tectonic` from `PATH` or from the `TECTONIC` environment variable. If
Tectonic is unavailable, it falls back to `pdflatex` plus `bibtex`.
