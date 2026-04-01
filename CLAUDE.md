# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sim2Real Transfer Learning for Nanobody Thermal Stability Prediction. A protein language model (ESM-2) is fine-tuned on experimental Tm data while simultaneously training on simulation-derived ddG data (FEP, FoldX, Rosetta, ThermoMPNN) as auxiliary tasks, investigating whether simulation data improves real-world thermal stability prediction.

## Language and Key Dependencies

- Python 3 with PyTorch, Hugging Face Transformers, datasets, pandas, scikit-learn, scipy, safetensors
- Base model: `facebook/esm2_t6_8M_UR50D` (ESM-2 8M parameter protein language model)
- Jobs run on SLURM cluster with GPU (A6000)

## Running Training

```bash
# Multi-task (Tm + ddG): DDG_SOURCE で計算ツールを選択
DDG_SOURCE=FEP python ESM.py 1                       # seed=1, FEP, 全件
DDG_SOURCE=FEP python ESM.py 1 --n-ddg 10            # seed=1, FEP, 10サンプル
DDG_SOURCE=rosetta RESULT_DIR=/path/to/out python ESM.py 1

# Single-task (Tm のみ)
DDG_SOURCE=none python ESM.py 1

# SLURM 経由
DDG_SOURCE=FEP N_DDG=10 RESULT_DIR=/path/to/out sbatch run_train.sh
DDG_SOURCE=FEP N_DDG=10 RESULT_DIR=/path/to/out sbatch --gres=gpu:a6000:1 -w floyd run_train.sh

# スケーリング実験の一括投入
for n in 10 15 23 35 53 80 121 184 279; do
  DDG_SOURCE=FEP N_DDG=$n RESULT_DIR=results/FEP/$n sbatch run_train.sh
done
DDG_SOURCE=FEP RESULT_DIR=results/FEP/all sbatch run_train.sh  # 全件
```

**DDG_SOURCE**: `FEP`, `FoldX`, `rosetta`, `thermoMPNN`, `none` (single-task)

Edit `#SBATCH --array=1-5%5` in `run_train.sh` to control seed range and concurrency.

Models save to `{RESULT_DIR}/supervised/mtl_run{seed}/`.

## Running Evaluation

```bash
# 自動検出 (supervised/mtl_run* の数を自動カウント)
python pLM523.py --model-dir /path/to/output

# run数を明示
python pLM523.py --n-runs 100 --model-dir /path/to/output

# SLURM 経由
EVAL_DIR=/path/to/output N_RUNS=100 sbatch run_eval.sh
```

Outputs: `mtl_eval_summary523.txt` (bootstrap CI) and `mtl_eval_per_run_523.csv` (per-seed metrics: MSE, RMSE, R2, MAE, Spearman, Pearson).

## Model Architecture

`MultiTaskModel` in `ESM.py`:
- **Encoder**: Frozen ESM-2 backbone (no gradient updates)
- **Shared layers**: Linear(hidden_size, 256) → ReLU → Dropout → Linear(256, 128) → ReLU → Dropout → Linear(128, 32) → ReLU
- **Task heads**: `tm_head` (task_id=0), `ddg_head`/1MEL (task_id=1), `ddg_head2`/4IDL (task_id=2)
- **Loss weighting**: Multi-task: Tm 1/2, ddG(1MEL) 1/4, ddG(4IDL) 1/4. Single-task: Tm 1.0
- **Pooling**: CLS token (first position)
- Embeddings are precomputed once (frozen encoder) before the training loop for speed

## Repository Structure

- `ESM.py` — training script (multi-task and single-task via `--ddg-source`)
- `pLM523.py` — evaluation script (imports `MultiTaskModel` from `ESM.py`)
- `run_train.sh` / `run_eval.sh` — SLURM job scripts
- `data/` — input datasets: `Tm/Tm10per/` (experimental Tm), `fep/`, `foldX/`, `rosetta/`, `mpnn/` (ddG data)
- `results/` — committed evaluation results, organized as `results/multi/scail-{tool}/{n}/`
- `plot/simscail.ipynb` — scaling analysis visualization
- `paper/` — LaTeX paper (has its own `CLAUDE.md`)

## Key Patterns

- **Data paths are repo-relative**: `ESM.py` resolves paths via `REPO_ROOT = os.path.dirname(os.path.abspath(__file__))`. No hardcoded cluster paths.
- **Data column conventions**: raw CSVs use `seq` + `ddg_scaled01`; training CSVs use `text` + `label`.
- **pLM523.py imports from ESM.py**: model class is defined once. Loads with `strict=False` to handle single-task checkpoints missing ddG heads.
- **Inverse scaling in evaluation**: `pLM523.py` fits RobustScaler → MinMaxScaler on training labels, then inverse-transforms predictions back to original Tm scale.

## paper/ subdirectory

Has its own `CLAUDE.md` with detailed instructions. Build with:
```bash
cd paper/tex && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```
