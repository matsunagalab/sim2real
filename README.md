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

Dependencies are managed with [uv](https://docs.astral.sh/uv/), which creates the
virtual environment and installs the exact versions in `uv.lock`. Python 3.10 or
newer is required.

```bash
git clone https://github.com/matsunagalab/sim2real.git
cd sim2real
uv sync
```

Then prefix commands with `uv run`, for example
`uv run python scripts/reproduce_paper_results.py --check-only`. There is no need
to activate the environment by hand.

Install the extra dependencies only if you need the notebooks:

```bash
uv sync --extra notebooks
```

On Linux x86-64, `uv sync` installs a CUDA 12.4 build of PyTorch from the index
declared in `pyproject.toml`; the environment used for the manuscript was
Python 3.11 with torch 2.6.0+cu124, transformers 5.4.0, and MDAnalysis 2.10.0.
Training needs a GPU, but checking the results, rebuilding the figures, and
building the PDFs run on CPU. Confirm the installation with:

```bash
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
uv run python scripts/reproduce_paper_results.py --check-only
```

The second command is read-only and should report that the fixed source-label
inputs and the manuscript-facing outputs are present.

Building the PDFs additionally needs a LaTeX installation providing `pdflatex`
and `bibtex`, or Tectonic (`TECTONIC=/path/to/tectonic`). It is not installed by
`uv sync`.

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

To retrain the selected final configurations (the Tm-only baseline and the
computed-label conditions of the physical-observable and data-design comparisons,
each frozen and fine-tuned) from the fixed CSVs and then rebuild the summaries,
figures, and PDFs:

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force
```

This is a long GPU run that executes the selected configurations in sequence.
Use `--gpus` to pick a different device and add `--dry-run` to print the commands
without running them.

This compact workflow retrains only the settings adopted in the manuscript; it
does not repeat the full candidate search. The selected settings for each
condition are recorded in the `config` block of the corresponding
`results/*/scaling.json`.

The raw MD, FEP, Rosetta, and FoldX calculations are not run here; their
processed CSVs are fixed inputs. The steps are defined in
`reproduce/manuscript_results.yaml` and driven by
`scripts/reproduce_paper_results.py`; see `REPRODUCE.md` for details.

## Where each manuscript number comes from

Every number in the paper is read from a tracked JSON file, so a claim can be
checked without retraining anything.

| Manuscript item | File |
|---|---|
| Fig. 2, data-design comparison | `results/design_aligned_{scan_pool,hetero}_{frozen,hot}/design.json` |
| Fig. 2 baseline | `results/design_tmonly_{frozen,hot}/design.json` |
| Fig. 3, physical-observable comparison | `results/fig3_{FEP,MD,ROS,FOLDX,ROSESM,ROSRND}_{frozen,hot}/scaling.json` |
| Fig. 3 baseline | `results/n24_tm_{frozen,hot}_shared/scaling.json` |
| Supp. Fig. S1, encoder-size control | `results/size{35,650}_tm_shared_drop005/` and `results/size{35,650}_ddg_fep_enc3e-5/` |
| Selected hyperparameters of any run | the `config` block inside that run's JSON |

Each `scaling.json` stores the 396 per-protein absolute errors, so a paired
bootstrap can be recomputed from the files alone. `plot/fig3_matched.py` and
`plot/fig2_data_design_aligned.py` do exactly that and write the figures.

## Next round: recalculating and answering reviewers

Read `EXTENDING.md` before adding a calculation; it states the protocol that
keeps a new result comparable with the published ones. The points that most often
go wrong here:

- **Match the ensemble size of the published conditions.** Fig. 3 uses
  `--n-runs 24`; Fig. 2 uses 8 subset draws x 3 model-initialization seeds. A
  smaller ensemble gives a noisier estimate that is not comparable with the
  reported values.
- **Compare against the Tm-only baseline of the same comparison and the same
  encoder.** The two comparisons have different baselines (7.27/6.72 °C for
  Fig. 3, 7.27/7.07 °C for Fig. 2) because Fig. 2 fixes one pre-specified
  protocol for both sources instead of tuning per source.
- **Never select on `data/nbbench/test.csv`.** Model selection uses
  `val.csv` (114) only.
- **Fig. 1 is drawn by hand**, not generated. `paper/tex/figures/figure_1_concept_protocol_v2.png`
  is replaced by editing the drawing, and the reproduction pipeline leaves it
  alone.
- **Fig. 2 and Fig. 3 are owned by their own scripts.** `plot/fig2_data_design_aligned.py`
  and `plot/fig3_matched.py` write `paper/tex/figures/fig_outline0{2,3}_*` directly.
  Do not regenerate those figures from `plot/make_outline_figures.py`.

### Rerun the data-design comparison (Fig. 2)

This comparison does not go through `prepare.py`. It has its own harness, and it
reads the aligned label pools, which are selected with an environment variable:

```bash
DESIGN_DATA_DIR=data/source_labels/md_design_aligned \
uv run python scripts/run_design_comparison.py run \
  --source hetero --encoder-mode hot --exp-name design_aligned_hetero_hot
```

`--source` is one of `scan_pool`, `hetero`, or `none` (the Tm-only reference).
Defaults are the manuscript's: `--n-list 20,80,160,320 --n-subsets 8 --n-seeds 3`.
Without `DESIGN_DATA_DIR` the script falls back to the older, non-aligned pools
under `data/source_labels/md_design/` and will not reproduce the paper.

### Recompute the MD native-contact labels

If a reviewer asks about the MD protocol, the labels are regenerated from
trajectories with:

```bash
uv run python scripts/recompute_aligned_hphil_q.py \
  --source hetero --out data/md/aligned_hphil_q/hetero.csv --workers 8
```

`--source` is `hetero`, `scan_1mel`, or `scan_4idl`. Both data designs use one
protocol: hydrophilic-contact Best--Hummer Q over backbone heavy atoms, the
production window from 10 to 40 ns sampled every 100 ps (300 frames), referenced
to the parent equilibration structure. The window is selected by frame time, not
by frame index, because the source productions differ in length and sampling
interval.

The script expects the raw solvated trajectories, which are not in this
repository. Use the deposited backbone trajectories instead, as described next.

## Getting the deposited data

The trajectories, calculation inputs, and raw calculation output are deposited at
<https://doi.org/10.5281/zenodo.21637705> (CC BY 4.0, 8.7 GB in eight ZIP files).
The repository does not need them to rebuild figures or PDFs; they are needed to
recompute a computed label from the underlying calculation.

Download only the component you need:

| Archive | Size | Contents |
|---|---:|---|
| `bundle_metadata.zip` | 1.8 MB | README, file manifest, SHA-256 checksums |
| `foldx.zip` | 3.1 MB | FoldX structures, raw `Dif_*.fxout`, labels, code |
| `fep.zip` | 168 MB | FEP labels, annotated structures, calculation inputs |
| `rosetta_ddg_scans.zip` | 184 MB | Rosetta scan inputs and score tables |
| `md_mutation_scan_400K_4idl.zip` | 715 MB | 389 4IDL variant trajectories |
| `md_mutation_scan_400K_1mel.zip` | 829 MB | 421 1MEL variant trajectories |
| `md_heterogeneous_400K.zip` | 2.0 GB | 1,072 heterogeneous panel trajectories |
| `rosetta_backrub_trajectories.zip` | 4.8 GB | Thinned backrub ensembles |

Extracting every archive into one empty directory recreates the deposit tree.
Verify a download before using it:

```bash
unzip -q md_mutation_scan_400K_1mel.zip -d sim2real_deposit
unzip -q bundle_metadata.zip -d sim2real_deposit
cd sim2real_deposit && sha256sum --check --ignore-missing CHECKSUMS.sha256
```

Each MD record is a PDB and DCD pair. The PDB is the native reference (the parent
equilibration structure) and the DCD holds the 300 analysed frames. Recompute a
published Q value by averaging over **all** frames of the DCD:

```python
import MDAnalysis as mda

stem = "sim2real_deposit/md/mutation_scan_400K/1mel/trajectories/1mel_A14D_400K_backbone"
reference = mda.Universe(f"{stem}.pdb")           # native reference for the contacts
u = mda.Universe(f"{stem}.pdb", f"{stem}.dcd")    # the 300 analysed frames
print(len(u.trajectory))                          # 300
```

Do not apply a further time filter to the deposited DCD. It already is the
analysis window, and the DCD format stores its sampling interval in single
precision, so the first frame reads as 9999.9998 ps rather than 10000 ps and a
strict `t >= 10000` test would drop it. Averaging the hydrophilic-contact Q over
all 300 frames, against the companion PDB, reproduces the value in
`data/md/aligned_hphil_q/` exactly; this was checked on twelve records spanning
both mutation scans and the heterogeneous panel.

A pair whose identifier appears in a label table but has no deposited trajectory
is listed in that component's `MISSING.tsv` with the reason, rather than being
omitted silently.

## Run one selected configuration

For example, the fine-tuned-encoder FEP condition of the physical-observable
comparison (Fig. 3) is:

```bash
DETACH_AUX_ENCODER=true CUDA_VISIBLE_DEVICES=0 uv run python prepare.py \
  --train-mode mtl --selection-scope tm --final-eval-split test \
  --encoder-mode hot --ddg-source FIG3_FEP --n-ddg-list 20,80,160,320 \
  --model-arch shared --ddg-head-mode separate \
  --learning-rate 3e-4 --encoder-lr 1e-5 --dropout-rate 0.15 --weight-decay 0.1 \
  --n-runs 24 --exp-name fig3_FEP_hot
```

Run `uv run python prepare.py --help` for the available arguments. Older named
experiments are kept in `EXPERIMENTS.md` and `experiments.yaml`, but they should
be distinguished from the current manuscript results.

## Repository layout

```text
prepare.py                             data loading, training driver, evaluation
train.py                               ESM-2 multitask model and training loop
scripts/run_design_comparison.py       the Fig. 2 harness (not via prepare.py)
scripts/recompute_aligned_hphil_q.py   MD native-contact labels from trajectories
scripts/reproduce_paper_results.py     driver for the reproduction stages
data/nbbench/                          fixed 57/114/396 experimental Tm split
data/source_labels/                    processed mutation-label tables
data/source_labels/md_design_aligned/  the Fig. 2 label pools (via DESIGN_DATA_DIR)
data/source_labels/MANIFEST.tsv        provenance of every processed label table
data/md/aligned_hphil_q/               per-variant Q behind the Fig. 2 pools
results/fig3_*/scaling.json            physical-observable comparison (Fig 3)
results/design_aligned_*/design.json   data-design comparison (Fig 2)
plot/fig2_data_design_aligned.py       builds Fig. 2 and owns its output file
plot/fig3_matched.py                   builds Fig. 3 and owns its output file
paper/tex/                             main and supplementary LaTeX sources
reproduce/manuscript_results.yaml      current reproduction steps
```

Further reading: `REPRODUCE.md` for the reproduction stages in detail,
`EXTENDING.md` for the protocol a new calculation has to follow, and
`data/source_labels/MANIFEST.tsv` for where each label table came from.
`EXPERIMENTS.md` and `experiments.yaml` record older named experiments and should
not be read as current results.

## Manuscript

Authors: Taihei Murakami, Kentaro Sasaki, Soichiro Oda, Kazuma Okada, and Yasuhiro Matsunaga.

The public repository is <https://github.com/matsunagalab/sim2real>. The
trajectories, calculation inputs, and processed labels are deposited at
<https://doi.org/10.5281/zenodo.21637705>, which carries its own README
describing the deposited files.

## License

The code and derived data written for this study are released under the MIT
license (`LICENSE`).

Some files come from elsewhere and keep their own terms: the measured melting
temperatures are from the NbBench `thermo-tm` dataset (CC BY 4.0), the starting
structures are PDB entries 1MEL and 4IDL, the encoder is ESM-2 (MIT), and the
manuscript template belongs to *Biophysics and Physicobiology*. FoldX, Rosetta,
and the MD force fields are not redistributed here and require their own
licenses. See `THIRD_PARTY_NOTICES.md`.
