#!/usr/bin/env bash
# Run a curated subset of experiments via run_experiment.py.
# Usage: CUDA_VISIBLE_DEVICES=1 bash scripts/run_all_experiments.sh
set -u

cd "$(dirname "$0")/.."

EXPERIMENTS=(
    # Frozen 8M baseline family
    frozen_q_hphil_full
    frozen_q_lowflex_full
    frozen_q_highflex_full
    frozen_saltbridge_full
    rosetta_full

    # Frozen combos
    combo_lowflex_highflex_frozen

    # Hot 8M
    hot_qhphil_alone_640
    hot_lowflex_sweep

    # 650M
    lora_650m_lowflex_640
    hot_650m_lowflex_640

    # MD weight extremes (sanity)
    md_weight_w1.0
    md_weight_w8.0
)

T0=$(date +%s)
for name in "${EXPERIMENTS[@]}"; do
    echo "[$(date +%H:%M:%S)] >>> $name"
    uv run python scripts/run_experiment.py "$name" --check || true
done
T1=$(date +%s)
echo "[$(date +%H:%M:%S)] <<< done all in $(( (T1-T0)/60 )) min"
