#!/bin/bash
#SBATCH -p all
#SBATCH -J fine-tuning           # job name
#SBATCH -n 1                     # total MPI processes
#SBATCH -c 1                     # threads per MPI process
#SBATCH --mail-type=ALL
#SBATCH -o run_%A_%a.log         # %A=ジョブID, %a=タスクID
#SBATCH --array=1-100%7           # タスクIDを 1～10, 同時に最大5ジョブ

# set GPU ID if needed
# export CUDA_VISIBLE_DEVICES="3"

# 実行時にマシンを決めて実行例:
# sbatch --gres=gpu:a6000:1 -w floyd run.sh
# sbatch --gres=gpu:a6000:1 -w m1 run.sh

# run_num に応じて自動で 1,2,…,10 が入る
python ESM.py ${SLURM_ARRAY_TASK_ID}

