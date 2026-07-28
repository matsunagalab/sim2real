# CLAUDE.md

## Project

This repository supports the manuscript **“Transfer learning from computed
stability data for nanobody melting-temperature prediction.”** It tests whether
computational mutation labels improve nanobody Tm prediction with an ESM-2
encoder.

The current comparison includes Tm-only training and auxiliary labels from FEP, a 400 K MD native-contact mutation scan and a heterogeneous nanobody MD panel, Rosetta, FoldX, random variants scored by Rosetta, and ESM2-proposed variants scored by Rosetta. Results must be reported separately for frozen and fine-tuned encoders.

## Experimental split

The local NbBench files intentionally use a low-data reassignment:

- `data/nbbench/train.csv`: published `validation`, 57 examples
- `data/nbbench/val.csv`: published `test`, 114 examples; model selection only
- `data/nbbench/test.csv`: published `train`, 396 examples; final evaluation only

Do not restore the published split names. `data/nbbench/download.py` preserves this mapping.

## Main files

| File | Purpose |
|---|---|
| `prepare.py` | Loads data, launches training, and writes held-out metrics. |
| `train.py` | Defines the ESM-2 multitask model and training loop. |
| `data/source_labels/MANIFEST.tsv` | Lists processed computational labels and their provenance. |
| `results/final_*_{frozen,hot}/scaling.json` | Selected final results used by the current paper. |
| `plot/build_tuned_summaries.py` | Rebuilds compact summaries from the final results. |
| `plot/make_outline_figures.py` | Builds main figures. |
| `plot/make_supplementary_figures.py` | Builds supplementary figures and tables. |
| `reproduce/manuscript_results.yaml` | Lists the current reproduction steps. |

Older named experiments in `experiments.yaml` and `EXPERIMENTS.md` are retained for history. Do not describe them as the current best result without checking the final result files above.

## Reproduction

```bash
uv sync
uv run python scripts/reproduce_paper_results.py --check-only
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

The figure stage builds both `paper/tex/main.pdf` and `paper/tex/supplementary_main.pdf`. A full selected-configuration rerun is GPU-intensive:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force
```

This reruns the 14 selected final configurations. It does not repeat every candidate search or regenerate raw MD, FEP, Rosetta, or FoldX calculations.

## Reporting rules

- Select settings with the 114-example validation set; never select on the 396-example test set.
- Compare computational-label conditions with the Tm-only result from the same encoder regime.
- Keep the heterogeneous nanobody MD panel separate from the FEP-matched mutation scan.
- Base manuscript numbers on tracked `scaling.json` files and generated supplementary tables, not an untracked scratch directory.
- Record the source label, encoder mode, selected settings, seeds, and evaluation split for new results.
