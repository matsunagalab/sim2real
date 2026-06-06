#!/usr/bin/env bash
# Sweep nanobody-specific features (300K, frozen).
# 7 features × 4 scaling × 10 runs = 280 trainings.
set -u
cd "$(dirname "$0")/.."

FEATURES=(MD_Q_CDR3 MD_Q_FRAMEWORK MD_RMSF_CDR3 MD_RMSF_FRAMEWORK MD_SS_DIST_MEAN MD_SS_DIST_STD MD_CDR3_LEN)
T0=$(date +%s)
for src in "${FEATURES[@]}"; do
    name=$(echo "$src" | tr '[:upper:]' '[:lower:]' | sed 's/md_/frozen_/')
    echo "[$(date +%H:%M:%S)] >>> $name (frozen, $src)"
    CUDA_VISIBLE_DEVICES=1 uv run python prepare.py --ddg-source none \
        --md-source "$src" --encoder-mode frozen \
        --n-md-list 10,40,160,640 --n-runs 10 --exp-name "$name" 2>&1 \
        > "logs/$name.log" || true
done
echo "[$(date +%H:%M:%S)] <<< nb autoresearch done in $(( ($(date +%s) - T0)/60 )) min"
