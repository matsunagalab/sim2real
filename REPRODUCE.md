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

## Rebuild figures and PDFs

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

The two comparisons of the paper are produced by two different harnesses and have their own stages.

The `physical-observable` stage reruns Fig. 3: the two Tm-only baselines and the six computed observables (FEP, MD native contacts, Rosetta, FoldX, and the two Rosetta proposal-design controls), each with a frozen and a fine-tuned encoder, as 24-model ensembles:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage physical-observable --gpus 0 --force
```

The `data-design` stage reruns Fig. 2: the two Tm-only baselines and the single mutation scan and heterogeneous designs, each with a frozen and a fine-tuned encoder, as 8 subset draws x 3 model-initialization seeds under one pre-specified protocol shared by both designs:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage data-design --gpus 0 --force
```

Every result uses the 114-example validation set for selection and the 396-example test set for final evaluation. The conditions run sequentially on the first GPU ID supplied to `--gpus`. To use another device, replace `0` with its ID. To inspect the planned commands without running them:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force --dry-run
```

To run training and the paper outputs in one command:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force
```

## What is and is not repeated

These steps repeat the selected final configurations. They do not repeat every architecture and hyperparameter candidate that preceded selection. Candidate records and the selected settings are preserved in:

- `paper/analysis/supplementary/tables/candidate_validation.tsv`
- `paper/analysis/supplementary/tables/selected_settings.tsv`

The 35M/650M model-size controls of the supplementary material are checked for availability but are not retrained by these steps.

`results/final_*`, `results/tuned_rep/*`, and the ThermoMPNN label condition come from an earlier version of this study. They are kept for history and are deliberately not part of this workflow; rerunning them does not reproduce the current paper.

Raw simulation data are not needed to rebuild model summaries, figures, or PDFs. They are needed only to regenerate processed computational labels. The trajectories, calculation inputs, and processed labels are deposited at <https://doi.org/10.5281/zenodo.21637705>, which carries its own README describing the deposited files and how to recompute a label from them.

## Outputs used by the paper

- Fig. 3 results: `results/fig3_*_{frozen,hot}/scaling.json`, with the baseline in `results/n24_tm_{frozen,hot}_shared/scaling.json`
- Fig. 2 results: `results/design_aligned_*_{frozen,hot}/design.json`, with the baseline in `results/design_tmonly_{frozen,hot}/design.json`
- Main figures: `paper/tex/figures/fig_outline*.{pdf,png,svg}`
- Supplementary tables and figures: `paper/analysis/supplementary/`
- Main and supplementary PDFs: `paper/tex/main.pdf`, `paper/tex/supplementary_main.pdf`

See `results/README.md` for the exact current result families and the distinction between tracked manuscript inputs and scratch runs.
