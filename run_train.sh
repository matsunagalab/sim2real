#!/bin/bash
#SBATCH -p all
#SBATCH -J sim2real_train         # job name
#SBATCH -n 1                     # total MPI processes
#SBATCH -c 1                     # threads per MPI process
#SBATCH --mail-type=ALL
#SBATCH -o run_%A_%a.log   # RESULT_DIR が指定されていればその下に保存
#SBATCH --array=1-5%5            # タスクID 1～5, 同時最大5ジョブ

# sim2real 直下の ESM.py を実行するため、作業ディレクトリを設定する。
# sbatch 投入時はスクリプトがスプールにコピーされるため、BASH_SOURCE の dirname では
# ESM.py のあるディレクトリを得られない。SLURM_SUBMIT_DIR（投入したディレクトリ）を使う。
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
  SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
cd "$SCRIPT_DIR"

# 結果を保存するディレクトリ（未指定時は sim2real 直下 = SCRIPT_DIR）
# 指定する場合: RESULT_DIR=/path/to/output sbatch run_train.sh
export RESULT_DIR="${RESULT_DIR:-$SCRIPT_DIR}"

# DDGデータソース（FEP, FoldX, rosetta, thermoMPNN, none）。デフォルト: FoldX
# 指定する場合: DDG_SOURCE=FEP sbatch run_train.sh
DDG_SOURCE="${DDG_SOURCE:-FoldX}"

# 訓練に使うddgデータ数（1mel/4idlそれぞれ）。未指定時は全件使用
# 指定する場合: N_DDG=10 sbatch run_train.sh
N_DDG="${N_DDG:-}"

# GPU を使う場合は export を削除。CPU のみの場合は空にする
export CUDA_VISIBLE_DEVICES=""

# 実行例:
#   cd sim2real && sbatch run_train.sh
#   cd sim2real && DDG_SOURCE=FEP N_DDG=10 RESULT_DIR=/path/to/results sbatch run_train.sh
#   cd sim2real && DDG_SOURCE=none RESULT_DIR=/path/to/single sbatch run_train.sh  # single-task
#   cd sim2real && sbatch --gres=gpu:a6000:1 -w floyd run_train.sh
# スケーリング実験の一括投入:
#   for n in 10 15 23 35 53 80 121 184 279; do
#     DDG_SOURCE=FEP N_DDG=$n RESULT_DIR=results/FEP/$n sbatch run_train.sh
#   done
#   DDG_SOURCE=FEP RESULT_DIR=results/FEP/all sbatch run_train.sh  # 全件

python ESM.py ${SLURM_ARRAY_TASK_ID} --ddg-source "$DDG_SOURCE" ${N_DDG:+--n-ddg $N_DDG}
