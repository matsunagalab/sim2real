ESM.pyがマルチタスク学習を行うプログラム
Tm,ΔΔG(1mel),ΔΔG(4dil)の3つのheadを1/2,1/4,1/4の割合で学習している

訓練データは
DATA_PATH_TM = "/data2/ssk/ESM2/splitdata/Tm10/splitdata/train2-"+ str(seed)+".csv"      # TmデータCSV
DATA_PATH_DDG_1mel = "/data2/ssk/DATA/1mel/dataset_st_yj.csv"   #ΔΔGデータCSV
DATA_PATH_DDG_4idl = "/data2/ssk/DATA/4idl/dataset_st_yj.csv"   #ΔΔGデータCSV
で読み込み既に前処理したcsvファイルがあるものとする

run-SFTはバッチファイルであり
#SBATCH --array=n-m%7
で流すrunの数とseed値を決める
seed1-100を流す場合#SBATCH --array=1-100%7