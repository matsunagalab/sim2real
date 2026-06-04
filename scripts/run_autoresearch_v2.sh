#!/usr/bin/env bash
# Autoresearch round 2: sweep 5 new MD-derived scalar features × frozen/hot.
# Time estimate: ~400 min total (5 frozen × 30min + 5 hot × 50min).
# Usage: CUDA_VISIBLE_DEVICES=1 bash scripts/run_autoresearch_v2.sh
set -u

cd "$(dirname "$0")/.."

# Run frozen first (cheaper), then hot. Ranking based on best MAE.
EXPERIMENTS=(
    # Round 1: frozen pass to filter weak features quickly
    frozen_q_min
    frozen_q_std
    frozen_q_slope
    frozen_rmsf_max
    frozen_rg_std

    # Round 2: hot for everything (no filtering — keep comprehensive)
    hot_q_min
    hot_q_std
    hot_q_slope
    hot_rmsf_max
    hot_rg_std
)

T0=$(date +%s)
for name in "${EXPERIMENTS[@]}"; do
    echo "[$(date +%H:%M:%S)] >>> $name"
    uv run python scripts/run_experiment.py "$name" || true
done
T1=$(date +%s)
echo "[$(date +%H:%M:%S)] <<< autoresearch_v2 done in $(( (T1-T0)/60 )) min"
