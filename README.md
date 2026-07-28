# sim2real

**Transfer learning from computed stability data for nanobody
melting-temperature prediction**

A research repository that asks which computed labels help predict nanobody
melting temperature (Tm) when experimental data are scarce. Using an ESM-2
encoder, we train on experimental Tm together with one computed auxiliary label
at a time: mutation free energies from FEP, MD native-contact Q from either a
local mutation scan or a heterogeneous panel of nanobodies, Rosetta
`ddg_monomer` scores, FoldX predictions, and Rosetta scores for random or
ESM2-proposed variants.

Whether the computed labels lower the Tm error depends on how the data are built
and which quantity is computed, not on how many labels there are. Among the
computed quantities, FEP gave the lowest held-out test MAE and was the only source
significant with both a frozen and a fine-tuned encoder; FoldX also helped with a
frozen encoder and outperformed Rosetta, while MD native-contact Q and Rosetta
gave little or no improvement. Among two ways of choosing MD variants that share
one Q definition and differ only in the sequences they cover, a sequence-diverse
heterogeneous panel lowered Tm error after fine-tuning, whereas a local mutation
scan of two fixed structures did not. Results are reported separately for frozen
and fine-tuned encoders.

| Encoder | Tm labels only | + FEP | + FoldX |
|---|---:|---:|---:|
| Frozen | 7.27 °C | 7.03 °C (−0.245) | 7.09 °C (−0.181) |
| Fine-tuned | 6.72 °C | 6.35 °C (−0.368) | 6.60 °C (−0.120) |

Values in parentheses are the change in held-out test MAE relative to the Tm-only
model with the same encoder. Conditions are in
`results/fig3_*_{frozen,hot}/scaling.json` (physical-observable comparison) and
`results/design_aligned_*_{frozen,hot}/design.json` (data-design comparison).

## Experimental Tm split

We reassign the public NbBench `ZYMScott/thermo-tm` split for a low-data setting:

| Local file | Published split | Purpose | n |
|---|---|---|---:|
| `data/nbbench/train.csv` | validation | training | 57 |
| `data/nbbench/val.csv` | test | model selection | 114 |
| `data/nbbench/test.csv` | train | final held-out evaluation | 396 |

`data/nbbench/download.py` reproduces this mapping. The final test set is never
used to select candidate settings.

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/matsunagalab/sim2real.git
cd sim2real
uv sync
```

Install the extra dependencies only if you need the notebooks:

```bash
uv sync --extra notebooks
```

## Reproduce the current manuscript

Check, read-only, that the fixed inputs and the results, figures, and PDFs the
manuscript refers to are present:

```bash
uv run python scripts/reproduce_paper_results.py --check-only
```

Rebuild the compact summaries from the existing final results:

```bash
uv run python scripts/reproduce_paper_results.py --stage summaries --force
```

Rebuild Fig. 2 and Fig. 3, the supplementary figure and tables, and the main and
supplementary PDFs (the author-edited Fig. 1 is left unchanged):

```bash
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

Building the PDFs needs `pdflatex` and `bibtex` (or `tectonic`); set
`TECTONIC=/path/to/tectonic` to point at a specific Tectonic binary.

To retrain the 14 selected final configurations (Tm-only and six computed-label
conditions, each frozen and fine-tuned) from the fixed CSVs and then rebuild the
summaries, figures, and PDFs:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force
```

This is a long GPU run that executes the selected configurations in sequence.
Use `--gpus` to pick a different device and add `--dry-run` to print the commands
without running them.

This compact workflow retrains only the settings adopted in the manuscript; it
does not repeat the full candidate search. The candidates and the selected
settings are in `paper/analysis/supplementary/tables/candidate_validation.tsv`
and `selected_settings.tsv`.

The raw MD, FEP, Rosetta, and FoldX calculations are not run here; their
processed CSVs are fixed inputs. The steps are defined in
`reproduce/manuscript_results.yaml` and driven by
`scripts/reproduce_paper_results.py`; see `REPRODUCE.md` for details.

## Run one selected configuration

For example, the final fine-tuned-encoder condition with FEP labels is:

```bash
DETACH_AUX_ENCODER=true CUDA_VISIBLE_DEVICES=0 uv run python prepare.py \
  --train-mode mtl --selection-scope tm --final-eval-split test \
  --encoder-mode hot --ddg-source FEP --n-ddg-list 20,80,160,320 \
  --model-arch shared --ddg-head-mode separate --encoder-lr 3e-5 \
  --dropout-rate 0.15 --weight-decay 0.1 --n-runs 5 \
  --exp-name final_fep_hot
```

Run `uv run python prepare.py --help` for the available arguments. Older named
experiments are kept in `EXPERIMENTS.md` and `experiments.yaml`, but they should
be distinguished from the current manuscript results.

## Repository layout

```text
prepare.py                         data loading, training driver, evaluation
train.py                           ESM-2 multitask model and training loop
data/nbbench/                      fixed 57/114/396 experimental Tm split
data/source_labels/                processed mutation-label tables
data/md/                           processed MD-derived quantities
results/final_*/scaling.json       selected held-out test results
results/tuned_rep/                 compact summaries used by main figures
plot/                              manuscript figure and table builders
paper/tex/                         main and supplementary LaTeX sources
reproduce/manuscript_results.yaml  current reproduction steps
```

## Manuscript

Authors: Taihei Murakami, Kentaro Sasaki, Soichiro Oda, Kazuma Okada, and Yasuhiro Matsunaga.

The public repository is <https://github.com/matsunagalab/sim2real>. The
large-data deposit is described in `zenodo/README.md`; its DOI is intentionally
left as a placeholder until the record is created.

## License

MIT License
