# sim2real

**Sim2Real Transfer Learning for Nanobody Thermal Stability Prediction**

ナノボディの熱安定性（Tm）予測を改善するために、シミュレーション由来の ddG データをマルチタスク学習で活用する研究プロジェクトです。タンパク質言語モデル ESM-2 を Tm 実験データで fine-tuning する際に、計算科学ツール（FEP, FoldX, Rosetta, ThermoMPNN）で得た ddG データを補助タスクとして同時に学習させ、シミュレーションから現実への転移学習（sim-to-real）の効果を検証します。

## 手法の概要

- **ベースモデル**: ESM-2 (`facebook/esm2_t6_8M_UR50D`, 8M パラメータ)。エンコーダの重みは凍結し、共有全結合層 + タスク別ヘッドを学習
- **シングルタスク学習**: Tm データのみで学習（ベースライン）
- **マルチタスク学習**: Tm + ddG（1MEL） + ddG（4IDL）の 3 タスクを同時学習。損失の重みは Tm: 1/2, ddG(1MEL): 1/4, ddG(4IDL): 1/4
- **スケーリング解析**: ddG データの量（10〜435 サンプル）を変化させ、補助データ量が Tm 予測に与える影響を分析

## 動作環境

- Python 3
- PyTorch, Hugging Face Transformers, datasets, pandas, scikit-learn, scipy, safetensors
- GPU（SLURM クラスタ上で A6000 を想定）

## リポジトリ構成

```
sim2real/
├── ESM.py                  # 学習スクリプト（マルチタスク Tm + ddG）
├── pLM523.py               # 評価スクリプト（523 件テストデータ）
├── run_train.sh            # SLURM 用学習ジョブ投入スクリプト（直下の ESM.py を実行）
│
├── data/                   # 入力データとデータ準備ツール
│   ├── Tm/                 #   Tm 実験データ（567 件、10% 分割）
│   ├── fep/                #   FEP ddG データ（1MEL: 435, 4IDL: 409 バリアント）
│   ├── foldX/              #   FoldX ddG データ + 変換スクリプト
│   ├── rosetta/            #   Rosetta ddg_monomer ddG データ + 変換スクリプト
│   ├── mpnn/               #   ThermoMPNN ddG データ
│   ├── rosetta_esm1000/    #   ESM-2 で生成した変異の Rosetta 評価
│   ├── rosetta_random1000/ #   ランダム変異の Rosetta 評価（ベースライン）
│   └── convert_yj.ipynb    #   生データ → 学習用フォーマットへの変換
│
├── single/                 # シングルタスク学習（Tm のみ、ベースライン）
│   ├── test/               #   テンプレート
│   └── Tm10per/            #   10% Tm データでの学習結果
│
├── multi/                  # マルチタスク学習（Tm + ddG）
│   ├── test/               #   テンプレート
│   ├── scail-FEP/          #   FEP データでのスケーリング検証
│   ├── scail-FoldX/        #   FoldX データでのスケーリング検証
│   ├── scail-rosetta/      #   Rosetta データでのスケーリング検証
│   └── scail-thermoMPNN/   #   ThermoMPNN データでのスケーリング検証
│
├── plot/                   # 可視化
│   └── simscail.ipynb      #   スケーリング解析プロット
│
└── paper/                  # 論文（LaTeX）
```

## 使い方

### 1. データの前処理

生データから学習用 CSV を作成するには `data/convert_yj.ipynb` を使います。処理後の CSV には `seq`（アミノ酸配列）と `ddg_scaled01`（0-1 にスケーリングした ddG）が含まれます。

### 2. 学習の実行

#### sim2real 直下で実行（推奨）

学習スクリプト `ESM.py` と SLURM 用 `run_train.sh` は **sim2real 直下**にあります。`run_train.sh` は実行時にスクリプト自身のディレクトリ（sim2real）に移動するため、どこから投入しても **sim2real 直下の ESM.py** が実行されます。

**結果の保存先は環境変数 `RESULT_DIR` で指定することを推奨します。** 指定しないと結果は sim2real 直下の `supervised/` に保存され、どの実験の結果か分かりにくくなります。

**SLURM 経由（基本）:**

```bash
cd sim2real
# 結果を保存するディレクトリを指定して投入（推奨）
RESULT_DIR=/path/to/your_experiment sbatch run_train.sh
```

- 上記のとき、モデルなどは **`/path/to/your_experiment/supervised/mtl_run<seed>/`** に保存されます。
- GPU を使う場合: `RESULT_DIR=/path/to/your_experiment sbatch --gres=gpu:a6000:1 -w floyd run_train.sh`
- `run_train.sh` 内の `#SBATCH --array=1-5%5` で seed の範囲（1〜5）と同時実行数（5）を変更できます。
- `RESULT_DIR` を指定しない場合も動作しますが、そのときは sim2real 直下の `supervised/` に保存され、実験ごとの区別が付きにくいため非推奨です。

**インタラクティブ実行（1 seed）:**

```bash
cd sim2real
RESULT_DIR=/path/to/your_experiment python ESM.py 1    # seed=1、結果は RESULT_DIR へ
```

**インタラクティブ実行（複数 seed）:**

```bash
cd sim2real
export RESULT_DIR=/path/to/your_experiment
for seed in $(seq 1 5); do
  python ESM.py $seed
done
```

#### サブディレクトリ（multi/scail-FEP/10/ など）で実行する場合

各ディレクトリに移動して、そのディレクトリ内の `ESM.py` と `run-SFT.sh` を使う方法もあります。

```bash
cd multi/scail-FEP/10/
python ESM.py 1
# または
sbatch --gres=gpu:a6000:1 -w floyd run-SFT.sh
```

いずれの方法でも、各 seed で `supervised/mtl_run<seed>/` にモデルが保存されます（sim2real 直下で実行した場合は **sim2real/supervised/** に保存）。

### 3. 評価

学習完了後、**学習で結果を保存したディレクトリ**で評価スクリプトを実行します。`RESULT_DIR` を指定して学習した場合は、そのディレクトリに移動してから `pLM523.py` を実行してください。

```bash
cd sim2real
# 学習時に RESULT_DIR=/path/to/your_experiment で保存した場合
cd /path/to/your_experiment
python3 pLM523.py
```

**SLURM で評価する場合**（sim2real 直下の `run_eval.sh` を使用）:

```bash
cd sim2real
# 評価対象ディレクトリを EVAL_DIR で指定（supervised/mtl_run* が存在するディレクトリ）
EVAL_DIR=/path/to/your_experiment sbatch run_eval.sh
# 未指定時は sim2real 直下を評価
sbatch run_eval.sh
```

ログは `EVAL_DIR/eval_<ジョブID>.log` に出力されます。

- `pLM523.py` はカレントディレクトリの `supervised/mtl_run*/` を参照します。`pLM523.py` 内の `for i in range(n)` の `n` を実行した seed 数に合わせてください。
- 出力（実行したディレクトリに作成）:
  - `mtl_eval_summary523.txt` — 各指標の平均値と 90% ブートストラップ信頼区間
  - `mtl_eval_per_run_523.csv` — seed ごとの評価指標（MSE, RMSE, R2, MAE, Spearman, Pearson）

### 4. 可視化

`plot/simscail.ipynb` でスケーリング解析の結果をプロットします。

## ディレクトリの構成

**sim2real 直下**には次のファイルがあります:

| ファイル | 説明 |
|---------|------|
| `ESM.py` | 学習プログラム。seed をコマンドライン引数で受け取る |
| `pLM523.py` | テストデータ 523 件での評価プログラム |
| `run_train.sh` | SLURM 用学習ジョブ投入スクリプト。直下の ESM.py を実行。**結果の保存先は環境変数 `RESULT_DIR` で指定することを推奨**（未指定時は sim2real 直下の `supervised/` に保存され、実験の区別が付きにくい） |
| `run_eval.sh` | SLURM 用評価ジョブ投入スクリプト。`EVAL_DIR` で評価対象ディレクトリ（`supervised/mtl_run*` があるディレクトリ）を指定して pLM523.py を実行する。未指定時は sim2real 直下を評価 |

サブディレクトリ（`single/Tm10per/`, `multi/scail-FEP/10/` など）も同様の構成を持ちます:

| ファイル | 説明 |
|---------|------|
| `ESM.py` | 学習プログラム |
| `pLM523.py` | 評価プログラム |
| `run-SFT.sh` | SLURM ジョブ投入用バッチスクリプト |
| `mtl_eval_summary523.txt` | 評価結果サマリー（存在する場合） |
| `mtl_eval_per_run_523.csv` | seed ごとの評価結果（存在する場合） |

`multi/scail-*/` 以下の数字ディレクトリ名（10, 15, 23, ...）は、マルチタスク学習に使用する ddG データのサンプル数を表します。

## ライセンス

MIT License
