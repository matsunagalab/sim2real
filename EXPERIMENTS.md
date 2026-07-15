# Experiments

Named-experiment registry for reproducing every Tm-prediction run in this project.
The entries are defined in `experiments.yaml`. Run any entry with:

```bash
uv run python scripts/run_experiment.py <name>
```

Outputs:
- `logs/<name>.log` — full stdout/stderr
- `results/<name>/scaling.json` — per-scaling MAE / CI / paired-bootstrap ΔMAE / hparams
- appended row in `results.tsv`

`--list` prints all names. `--dry-run` prints the command without executing.
`--check` (after a run) compares `best_mae` against `expected.best_mae` (tolerance ±0.05°C).

---

## Data prerequisites

Before running any MD experiment, populate `data/md/` from the upstream MD pipeline at
`/home/yasu/tmp/mdclaw/job_nano_*/`:

```bash
uv run python scripts/extract_all_features.py
```

This runs four extractors and produces:

| CSV | Source |
|-----|--------|
| `nanobody_qvalue_hphil.csv` | `extract_q_values.py` (all-atom MD trajectory.dcd) |
| `nanobody_rmsf.csv`         | `extract_rmsf.py` |
| `feat_q_highflex.csv`       | `extract_features_pilot.py` (CDR-proxy Q) |
| `feat_q_lowflex.csv`        | `extract_features_pilot.py` (framework Q) |
| `feat_saltbridge.csv`       | `extract_features_pilot.py` (native salt-bridge persistence) |
| `rosetta_qvalue_hphil.csv`  | `extract_rosetta_qvalues.py` (needs `data/md/rosetta_traj/` from `run_rosetta_backrub.py`) |

DDG experiments don't need these — those datasets are already checked into `data/{fep,foldX,rosetta,mpnn,rosetta_esm1000,rosetta_random1000}/`.

---

## Headline results

| Setup | base | encoder | aux task(s) | best n_md | best MAE | best CI |
|-------|------|---------|-------------|-----------|----------|---------|
| Frozen baseline | ESM-2 8M | frozen | Q_HPHIL | 640 | 7.32 | 0.90 |
| Best frozen | ESM-2 8M | frozen | Q_LOWFLEX + Q_HIGHFLEX | 640 | 7.22 | 0.90 |
| **Overall best** | **ESM-2 8M** | **hot** | **Q_LOWFLEX** | **640** | **6.76** | **0.86** |
| 650M LoRA | ESM-2 650M | lora | Q_LOWFLEX | 640 | 7.04 | 0.89 |
| 650M Hot | ESM-2 650M | hot | Q_LOWFLEX | 640 | 6.78 | 0.89 |
| Rosetta MC | ESM-2 8M | frozen | ROSETTA_Q_HPHIL | 160 | 7.32 | 0.90 |

Hot encoder fine-tuning of the 8M base is the decisive change. 650M brings no further improvement.

---

## Experiments by family

### 1. Frozen 8M baseline
- `frozen_q_hphil_full` — current full-data Q baseline (10→640, 10 runs) → 7.32
- `frozen_q_lowflex_full` — framework Q (best floor with fewer samples) → 7.32
- `frozen_q_highflex_full` — CDR-proxy Q → 7.33
- `frozen_saltbridge_full` — native salt-bridge persistence → 7.39
- `rosetta_full` — Rosetta backrub Q-value, 10→960 → 7.32

### 2. Frozen combinations (primary + aux)
- `combo_lowflex_highflex_frozen` — best frozen 7.22 (only beneficial combo)
- `combo_lowflex_saltbridge_frozen` — combo hurts → 7.42
- `combo_qhphil_rmsf_frozen` — RMSF as aux to Q hurts
- `rmsf_only_frozen` — RMSF alone, comparable to Q

### 3. Hot encoder (8M)
- `hot_lowflex_sweep` — overall best 6.76 (10→640, 10 runs)
- `hot_lowflex_alone_640` — single-point 5-run check → 6.80
- `hot_qhphil_alone_640` — Q_HPHIL with hot → 6.93
- `hot_lowflex_highflex_combo_640` — combo with hot is worse than alone → 6.94

### 4. ESM-2 650M
- `lora_650m_lowflex_640` — LoRA on 650M → 7.04
- `hot_650m_lowflex_640` — full FT on 650M → 6.78 (≈ 8M hot, 80× the params)

### 5. MD-weight grid (fixed-weight MTL scan, n=320)
- `md_weight_w0.5` / `w1.0` / `w2.0` / `w4.0` / `w8.0`
- `w=1.0` matches the learnable-uncertainty result; `w=8.0` collapses Tm.

### 6. DDG sources (no MD)
- `ddg_FEP_full` / `ddg_FoldX_full` / `ddg_rosetta_full` / `ddg_thermoMPNN_full`
- `ddg_rosetta_esm_full` / `ddg_rosetta_random_full`

---

## How to add a new experiment

1. Add an entry to `experiments.yaml` under `experiments:`
2. Fill `args` (kebab-case, mirrors `prepare.py --foo-bar`), `env` (env vars), `expected` (optional MAE/CI for verification)
3. `uv run python scripts/run_experiment.py <new_name>`

---

## Backward compatibility

The pre-refactor invocation still works:

```bash
ENCODER_MODE=hot CUDA_VISIBLE_DEVICES=1 uv run python prepare.py \
  --ddg-source none --md-source MD_Q_LOWFLEX --n-md-list 640 --n-runs 10
```

Existing `results.tsv` rows (without `encoder_mode`/`base_model`/etc. columns) are preserved;
new rows append the extended schema after the historical columns.
