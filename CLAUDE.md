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
| `scripts/run_design_comparison.py` | The Fig. 2 data-design harness; does not go through `prepare.py`. |
| `results/fig3_*_{frozen,hot}/scaling.json` | Fig. 3 results, with the baseline in `results/n24_tm_{frozen,hot}_shared/`. |
| `results/design_{aligned_*,tmonly_*}/design.json` | Fig. 2 results. |
| `plot/fig3_matched.py`, `plot/fig2_data_design_aligned.py` | Build Fig. 3 and Fig. 2; each owns its output file. |
| `plot/make_supplementary_figures.py` | Builds supplementary figures and tables. |
| `reproduce/manuscript_results.yaml` | Lists the current reproduction steps. |

`results/final_*`, `results/tuned_rep/*`, `plot/build_tuned_summaries.py`, `plot/make_outline_figures.py`, and the ThermoMPNN label condition belong to an earlier version of this study. They are retained for history, are outside the reproduction workflow, and must not be presented as current results. The same applies to the named experiments in `experiments.yaml` and `EXPERIMENTS.md`.

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

This reruns the 14 selected configurations of Fig. 3 (`physical-observable` stage) and the 6 of Fig. 2 (`data-design` stage). It does not repeat every candidate search or regenerate raw MD, FEP, Rosetta, or FoldX calculations.

The Fig. 2 harness reads its label pools from `data/source_labels/md_design_aligned/`. `DESIGN_DATA_DIR` overrides that directory; the older `data/source_labels/md_design/` holds files with the same names but different variants and Q values, so an accidental override shifts the MAEs silently. `design.json` files written from August 2026 record the pool in `pool_dir` and `pool_files`; the tracked ones predate that and identify their pool by subset size (421 + 389 and 763).

## Reporting rules

- Select settings with the 114-example validation set; never select on the 396-example test set.
- Compare computational-label conditions with the Tm-only result from the same encoder regime.
- Keep the heterogeneous nanobody MD panel separate from the single mutation scan. Never call either design "matched" in figures or text.
- Base manuscript numbers on tracked `scaling.json` files and generated supplementary tables, not an untracked scratch directory.
- Record the source label, encoder mode, selected settings, seeds, and evaluation split for new results.
