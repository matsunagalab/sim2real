使用するカラムは
seqとddg_scaled01のみ
hogehoge_processed.csvとhogehoge_processed_rand.csv
だけを使う
他はrowデータ

rowデータ(hogehoge.csv)をconvert_yj.ipynbで変換を行いhogehoge_processed.csvを出力している

convert_yj.ipynbの使い方
hogehoge.csvのカラム名でseq(変異配列),ddg（ddg）を用意して
DIR_PATH   = "aheahe"       # CSVがあるディレクトリ
FILE_NAME  = "aheahe/hogehoge.csv"         # 入力CSVファイル名
COL1       = "ddg"       # 元の数値カラム名（マイナスを掛ける対象）
ここで指定すると出てくる