# Reproducing the manuscript results

This repository provides a compact rerun path for the selected configurations
reported in **“Transfer learning from computed stability data for nanobody
melting-temperature prediction.”**

It starts from processed CSV tables. It does not launch the raw MD simulations, FEP calculations, Rosetta calculations, or FoldX calculations that produced those tables.

## Install

```bash
git clone https://github.com/matsunagalab/sim2real.git
cd sim2real
uv sync
```

The steps are defined in `reproduce/manuscript_results.yaml` and run by `scripts/reproduce_paper_results.py`.

## Check the repository contents

```bash
uv run python scripts/reproduce_paper_results.py --check-only
```

This command only checks whether the listed inputs and outputs exist. It does not retrain a model, rewrite a file, or confirm that numbers are numerically equal to the manuscript.

The experimental Tm split is fixed as follows:

| Local file | Source split on Hugging Face | Use | n |
|---|---|---|---:|
| `data/nbbench/train.csv` | validation | training | 57 |
| `data/nbbench/val.csv` | test | setting selection | 114 |
| `data/nbbench/test.csv` | train | held-out test | 396 |

`data/nbbench/download.py` recreates this deliberate reassignment.

## Rebuild summaries, figures, and PDFs

Rebuild compact result summaries from the tracked final `scaling.json` files:

```bash
uv run python scripts/reproduce_paper_results.py --stage summaries --force
```

This step also checks the selected representative results against the reference values stored in `plot/build_tuned_summaries.py`.

Rebuild Figs. 2 and 3, the supplementary figures and tables, and both PDFs:

```bash
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

The PDF outputs are:

- `paper/tex/main.pdf`
- `paper/tex/supplementary_main.pdf`

The command leaves the author-edited Fig. 1 unchanged and uses its current PNG
when typesetting the main paper.

Typesetting uses `tectonic` from `PATH` or from the `TECTONIC` environment variable. If Tectonic is unavailable, the script uses `pdflatex` and `bibtex` when both are installed.

## Rerun the reported model results

The `reported-results` stage reruns the selected final conditions for seven source-label settings under both frozen and fine-tuned encoders:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage reported-results --gpus 0 --force
```

Each result uses five training seeds, the 114-example validation set for setting selection, and the 396-example test set for final evaluation. The selected conditions run sequentially on the first GPU ID supplied to `--gpus`. To use another device, replace `0` with its ID. To inspect the planned commands without running them:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage reported-results --gpus 0 --force --dry-run
```

After training, rebuild summaries and paper outputs:

```bash
uv run python scripts/reproduce_paper_results.py --stage summaries,figures --force
```

To run the full sequence in one command:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force
```

## What is and is not repeated

These steps repeat the selected final configurations. They do not repeat every architecture and hyperparameter candidate that preceded selection. Candidate records and the selected settings are preserved in:

- `paper/analysis/supplementary/tables/candidate_validation.tsv`
- `paper/analysis/supplementary/tables/selected_settings.tsv`

The main figures also retain a heterogeneous-nanobody MD comparison and 35M/650M model-size controls as tracked result inputs. These older controls are checked for availability but are not retrained by these steps.

Raw simulation data are not needed to rebuild model summaries, figures, or PDFs. They are needed only to regenerate processed computational labels. The trajectories, calculation inputs, and processed labels are deposited at <https://doi.org/10.5281/zenodo.21637705>, which carries its own README describing the deposited files and how to recompute a label from them.

## Outputs used by the paper

- Selected results: `results/final_*_{frozen,hot}/scaling.json`
- Compact main-figure summaries: `results/tuned_rep/`
- Main figures: `paper/tex/figures/fig_outline*.{pdf,png,svg}`
- Supplementary tables and figures: `paper/analysis/supplementary/`
- Main and supplementary PDFs: `paper/tex/main.pdf`, `paper/tex/supplementary_main.pdf`

See `results/README.md` for the exact current result families and the distinction between tracked manuscript inputs and scratch runs.
