# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sim2Real Transfer Learning for Nanobody Thermal Stability Prediction. This project uses multi-task learning to improve nanobody thermal stability (Tm) prediction by co-training with simulation-derived ddG data from various computational tools (FEP, FoldX, Rosetta, ThermoMPNN).

The core idea: a protein language model (ESM-2) is fine-tuned on Tm data (real) while simultaneously training on ddG data (simulation) as auxiliary tasks, investigating whether simulation data improves real-world prediction (sim-to-real transfer).

## Language and Key Dependencies

- Python 3 with PyTorch, Hugging Face Transformers, datasets, pandas, scikit-learn, scipy
- Base model: `facebook/esm2_t6_8M_UR50D` (ESM-2 8M parameter protein language model)
- Computational tools: Rosetta (ddg_monomer), FoldX, ThermoMPNN (external, not in repo)
- Jobs run on SLURM cluster with GPU (A6000)

## Running Training

Training jobs are submitted via SLURM:
```bash
sbatch --gres=gpu:a6000:1 -w floyd run-SFT.sh
```

Each `run-SFT.sh` calls `python ESM.py ${SLURM_ARRAY_TASK_ID}` where the array task ID is used as the random seed. To change the number of runs, edit the `#SBATCH --array=n-m%7` line (e.g., `1-100%7` for 100 runs with max 7 concurrent).

## Running Evaluation

After training, run the evaluation script from the same directory:
```bash
python3 pLM523.py
```
Adjust the `for i in range(n)` loop count to match the number of training runs. Outputs `mtl_eval_summary523.txt` (bootstrap CI summary) and `mtl_eval_per_run_523.csv`.

## Repository Architecture

### `data/` - Input datasets and data preparation tools

Contains ddG prediction data from multiple simulation tools, plus the Tm experimental data:
- `Tm/` - Nanobody thermal stability data (Tm). `Tm10per/` has train/test splits using 10% of 567 Tm data points
- `fep/` - Free Energy Perturbation ddG data for 1MEL (435 variants) and 4IDL (409 variants)
- `foldX/` - FoldX ddG predictions with scripts (`make_individual_list.py`, `foldx_to_csv.py`)
- `rosetta/` - Rosetta ddg_monomer results with scripts (`sequence_to_rosetta_mutations.py`)
- `mpnn/` - ThermoMPNN ddG predictions
- `rosetta_esm1000/` - ESM-2 generated variants evaluated by Rosetta (PLM-guided mutation)
- `rosetta_random1000/` - Random variants evaluated by Rosetta (baseline comparison)
- `convert_yj.ipynb` - Converts raw CSV to processed format (adds `ddg_neg`, `ddg_scaled01` columns)

Data columns convention: processed CSVs use `seq` (amino acid sequence) and `ddg_scaled01` (0-1 scaled ddG). Training CSVs use `text` (sequence) and `label` (target value).

### `single/` - Single-task learning experiments (Tm only, baseline)

- `test/` - Template for single-task experiments
- `Tm10per/` - Single-task training with 10% Tm data (44 train, 12 test, 523 full test)

### `multi/` - Multi-task learning experiments (Tm + ddG)

- `test/` - Template for multi-task experiments
- `scail-FEP/` - Scaling experiments with FEP ddG data (subdirs: 10, 15, 23, 35, 53, 80, 121, 184, 279, 435_409 = number of ddG samples)
- `scail-FoldX/` - Scaling experiments with FoldX ddG data
- `scail-rosetta/` - Scaling experiments with Rosetta ddG data
- `scail-thermoMPNN/` - Scaling experiments with ThermoMPNN ddG data

Each numbered subdirectory under `scail-*` represents an experiment with that many ddG training samples, allowing analysis of how ddG data quantity affects Tm prediction.

### `plot/` - Visualization

- `simscail.ipynb` - Plots for scaling analysis results

### `paper/` - LaTeX paper with AI-assisted writing workflow

Has its own `CLAUDE.md` with detailed instructions. Build with:
```bash
cd paper/tex && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Model Architecture

`MultiTaskModel` in `ESM.py`:
- **Encoder**: Frozen ESM-2 backbone (parameters not updated during fine-tuning)
- **Shared layers**: Linear(hidden_size, 256) -> ReLU -> Dropout -> Linear(256, 128) -> ReLU -> Dropout -> Linear(128, 32) -> ReLU
- **Task heads**: Separate `nn.Linear(32, 1)` for each task
  - Single-task: `tm_head` only
  - Multi-task: `tm_head` (task_id=0), `ddg_head` for 1MEL (task_id=1), `ddg_head2` for 4IDL (task_id=2)
- **Loss weighting**: Tm: 1/2, ddG(1MEL): 1/4, ddG(4IDL): 1/4
- Pooling: CLS token (first position)

## Key Patterns

- Each experiment directory is self-contained with `ESM.py` (training), `pLM523.py` (evaluation), `run-SFT.sh` (SLURM submission)
- The `ESM.py` scripts have hardcoded data paths pointing to `/data2/ssk/...` on the cluster
- Seed is passed as command-line argument; `--array=1-100%7` runs seeds 1-100
- `supervised/mtl_run{seed}/` stores model checkpoints (model.safetensors)
- `435_409` directories use a slightly different ESM.py because 1MEL has 435 and 4IDL has 409 variants (different ddG counts per target)
