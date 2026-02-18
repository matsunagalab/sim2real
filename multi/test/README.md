とりあえずsbatch --gres=gpu:a6000:1 -w floyd run.shで流れます
seedを変えて流す回数はrun-SFT.shの#SBATCH --array=n-m%7を変更してください
seed1-100を流す場合#SBATCH --array=1-100%7
デフォルトは1-5にしました

ESM.pyがマルチタスク学習を行うプログラム
Tm,ΔΔG(1mel),ΔΔG(4dil)の3つのheadを1/2,1/4,1/4の割合で学習している

訓練データは
DATA_PATH_TM = "/data2/ssk/githubtest/sim2real/data/Tm/Tm10per/train2-"+ str(seed)+".csv"      # TmデータCSV
DATA_PATH_DDG_1mel = ""   #ΔΔGデータCSV
DATA_PATH_DDG_4idl = ""   #ΔΔGデータCSV
で指定
読み込み既に前処理したcsvファイルがあるものとする
デフォルトはfoldx

ESM_sabunum_x.py
スケーリング確認のために用いたΔΔGのデータ数を指定して学習させるプログラム
変数　n_ddg = 10　で指定

run-SFTはバッチファイルであり
#SBATCH --array=n-m%7
で流すrunの数とseed値を決める
seed1-100を流す場合#SBATCH --array=1-100%7


test.pyについて
同じフォルダにあればそのままpython3 test.pyで使える
mtl_eval_summary523.txtを出力する
例
=== Mean & 90% Bootstrap CI (percentile) ===
MSE        mean =  89.917847   90% CI = [ 87.952350,  91.874792]
RMSE       mean =  9.462153   90% CI = [ 9.359312,  9.563333]
R2         mean =  0.107345   90% CI = [ 0.088262,  0.126451]
MAE        mean =  7.612354   90% CI = [ 7.522341,  7.699484]
Spearman   mean =  0.391996   90% CI = [ 0.367323,  0.415478]
Pearson    mean =  0.400309   90% CI = [ 0.376768,  0.422634]

=== Sample Std (across runs) ===
MSE        std  =  12.037384
RMSE       std  =  0.624026
R2         std  =  0.117059
MAE        std  =  0.541000
Spearman   std  =  0.144406
Pearson    std  =  0.138009
