# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sim2Real Transfer Learning for Nanobody Thermal Stability Prediction. A protein language model (ESM-2) is fine-tuned on experimental Tm data while simultaneously training on simulation-derived ddG data (FEP, FoldX, Rosetta, ThermoMPNN) as auxiliary tasks.

## autoresearch Structure

This repo follows the [karpathy/autoresearch](https://github.com/karpathy/autoresearch) pattern:

| File | Owner | Role |
|------|-------|------|
| `train.py` | Agent | Model architecture, hyperparameters, training loop. **Freely editable.** |
| `prepare.py` | Human | Data loading, evaluation, scaling metrics. **Do not modify.** |
| `program.md` | Human | Research goals and constraints. **Do not modify.** |
| `results.tsv` | Auto | Experiment log (auto-appended by prepare.py) |

## Running an Experiment

```bash
uv sync                                                                    # install deps
uv run python prepare.py --ddg-source FEP --n-ddg-list 20,80,280 --n-runs 3  # full run
uv run python prepare.py --ddg-source FEP --n-ddg-list 20 --n-runs 1         # quick test
```

Output ends with a machine-readable line:
```
RESULT: slope=-0.234000 ci_width=1.450000 mae_mean=7.120000
```

## Research Loop

1. Edit `train.py` (HPARAMS, MultiTaskModel architecture, etc.)
2. `git commit`
3. Run `uv run python prepare.py ...` → read RESULT line
4. If improved: keep. If not: `git revert HEAD`
5. Repeat

## Optimization Targets

- **slope**: Power law exponent `b` in `MAE(n) = a*(n/1000)^b + c`. More negative = better scaling.
- **ci_width**: Average 90% bootstrap CI width across scaling points. Smaller = more stable.

## Model Architecture

`MultiTaskModel` in `train.py`:
- **Encoder**: Frozen ESM-2 (`facebook/esm2_t6_8M_UR50D`, 8M params)
- **Shared layers**: Linear→ReLU→Dropout (configurable in train.py)
- **Task heads**: `tm_head` (task_id=0), `ddg_head` (task_id=1), `ddg_head2` (task_id=2)
- **Loss weights**: Configurable via `HPARAMS["loss_weights"]`
- **Early stopping**: Enabled (patience configurable)

## Repository Structure

- `train.py` / `prepare.py` / `program.md` — autoresearch core
- `data/` — input datasets: `Tm/Tm10per/`, `fep/`, `foldX/`, `rosetta/`, `mpnn/`
- `results/` — historical evaluation results
- `results.tsv` — experiment log
- `plot/simscail.ipynb` — scaling analysis visualization
- `paper/` — LaTeX paper (has its own `CLAUDE.md`)
