#!/usr/bin/env bash
# Wait for short-trajectory Q extraction, then sweep MAE vs trajectory length.
# frozen sweep on GPU1, hot sweep on GPU2 (in parallel). n_md fixed at 640.
set -u
cd /home/yasu/tmp/sim2real

# 1) wait for extraction to finish
until [ -f /tmp/extract_q_short.flag ]; do sleep 30; done
echo "extraction done; starting length sweep at $(date)"

LENGTHS="5 10 17 30 50 100"
NMD=640
NRUNS=10

run_sweep () {  # $1=encoder $2=gpu
  local enc=$1 gpu=$2
  export CUDA_VISIBLE_DEVICES=$gpu
  for t in $LENGTHS; do
    local exp="short_${enc}_t${t}"
    mkdir -p results/$exp
    uv run python prepare.py \
      --md-source MD_Q_HPHIL_400K_T${t} --n-md-list $NMD --n-runs $NRUNS \
      --ddg-source none --encoder-mode $enc \
      --exp-name $exp --result-dir results/$exp \
      > /tmp/${exp}.log 2>&1
  done
}

run_sweep frozen 1 &
P1=$!
run_sweep hot 2 &
P2=$!
wait $P1 $P2
echo "SHORT SWEEP DONE" > /tmp/short_sweep.flag
echo "all done at $(date)"
