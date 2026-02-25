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

# 訓練に使うddgデータ数（1mel/4idlそれぞれ）。未指定時は全件使用
# 指定する場合: N_DDG=10 sbatch run_train.sh
N_DDG="${N_DDG:-}"

# GPU を使う場合は export を削除。CPU のみの場合は空にする
export CUDA_VISIBLE_DEVICES=""

# 実行例（sim2real から）:
#   cd sim2real && sbatch run_train.sh
# 結果・ログを別ディレクトリに保存（RESULT_DIR は存在するパスを指定すること）:
#   cd sim2real && RESULT_DIR=/path/to/results sbatch run_train.sh
# ddgデータ数を指定（1mel/4idlそれぞれの件数）:
#   cd sim2real && N_DDG=10 sbatch run_train.sh
# GPU 指定時:
#   cd sim2real && sbatch --gres=gpu:a6000:1 -w floyd run_train.sh

if [ -n "$N_DDG" ]; then
  python ESM.py ${SLURM_ARRAY_TASK_ID} "$N_DDG"
else
  python ESM.py ${SLURM_ARRAY_TASK_ID}
fi

