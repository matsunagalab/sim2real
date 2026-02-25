#!/bin/bash
# pLM523.py で評価を行う。評価対象は EVAL_DIR 配下の supervised/mtl_run* とする。
# 使い方: sim2real から実行すること。
#   cd sim2real && sbatch run_eval.sh                    # EVAL_DIR 未指定時は sim2real 直下を評価
#   cd sim2real && EVAL_DIR=/path/to/results sbatch run_eval.sh

#SBATCH -p all
#SBATCH -J sim2real_eval
#SBATCH -n 1
#SBATCH -c 1
#SBATCH --mail-type=ALL
#SBATCH -o eval_%j.log

# sim2real の場所（sbatch 投入時は SLURM_SUBMIT_DIR）
if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
  SCRIPT_DIR="$SLURM_SUBMIT_DIR"
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# 評価対象ディレクトリ（supervised/mtl_run* が存在するディレクトリ）。未指定時は SCRIPT_DIR
export EVAL_DIR="${EVAL_DIR:-$SCRIPT_DIR}"

# 評価ディレクトリに移動してから sim2real の pLM523.py を実行（pLM523.py は cwd の supervised/ を参照）
cd "$EVAL_DIR" || exit 1
python "${SCRIPT_DIR}/pLM523.py"
