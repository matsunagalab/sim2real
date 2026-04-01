# sim2real

**Sim2Real Transfer Learning for Nanobody Thermal Stability Prediction**

ナノボディの熱安定性（Tm）予測を改善するために、シミュレーション由来の ddG データをマルチタスク学習で活用する研究プロジェクトです。タンパク質言語モデル ESM-2 を Tm 実験データで fine-tuning する際に、計算科学ツール（FEP, FoldX, Rosetta, ThermoMPNN）で得た ddG データを補助タスクとして同時に学習させ、シミュレーションから現実への転移学習（sim-to-real）の効果を検証します。

## 手法の概要

- **ベースモデル**: ESM-2 (`facebook/esm2_t6_8M_UR50D`, 8M パラメータ)。エンコーダの重みは凍結し、共有全結合層 + タスク別ヘッドを学習
- **シングルタスク学習**: Tm データのみで学習（ベースライン）
- **マルチタスク学習**: Tm + ddG（1MEL） + ddG（4IDL）の 3 タスクを同時学習。損失の重みは Tm: 1/2, ddG(1MEL): 1/4, ddG(4IDL): 1/4
- **スケーリング解析**: ddG データの量（10〜435 サンプル）を変化させ、補助データ量が Tm 予測に与える影響を分析

## セットアップ

[uv](https://docs.astral.sh/uv/) で依存関係を管理しています。

```bash
uv sync                # 仮想環境の作成と依存関係のインストール
uv sync --extra plot   # 可視化用パッケージ（matplotlib, seaborn, jupyter）も含める
```

GPU（SLURM クラスタ上で A6000 を想定）を使う場合は、環境に合わせて PyTorch の CUDA 版を別途インストールしてください。

## リポジトリ構成

```
sim2real/
├── ESM.py                  # 学習スクリプト（マルチタスク / シングルタスク）
├── pLM523.py               # 評価スクリプト（523 件テストデータ）
├── run_train.sh            # SLURM 用学習ジョブ投入スクリプト
├── run_eval.sh             # SLURM 用評価ジョブ投入スクリプト
│
├── data/                   # 入力データとデータ準備ツール
│   ├── Tm/                 #   Tm 実験データ（Tm10per: 10% 分割）
│   ├── fep/                #   FEP ddG データ（1MEL: 435, 4IDL: 409 バリアント）
│   ├── foldX/              #   FoldX ddG データ + 変換スクリプト
│   ├── rosetta/            #   Rosetta ddg_monomer ddG データ + 変換スクリプト
│   ├── mpnn/               #   ThermoMPNN ddG データ
│   ├── rosetta_esm1000/    #   ESM-2 で生成した変異の Rosetta 評価
│   ├── rosetta_random1000/ #   ランダム変異の Rosetta 評価（ベースライン）
│   └── convert_yj.ipynb    #   生データ → 学習用フォーマットへの変換
│
├── results/                # 評価結果
│   ├── multi/scail-FEP/    #   FEP データでのスケーリング検証結果
│   ├── multi/scail-FoldX/  #   FoldX データでのスケーリング検証結果
│   ├── multi/scail-rosetta/#   Rosetta データでのスケーリング検証結果
│   ├── multi/scail-thermoMPNN/ # ThermoMPNN データでのスケーリング検証結果
│   └── single/Tm10per/     #   シングルタスク学習の評価結果
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

`ESM.py` は `--ddg-source` で計算ツールを、`--n-ddg` でサンプル数を指定します。`RESULT_DIR` 環境変数で結果の保存先を指定します。

**インタラクティブ実行:**

```bash
cd sim2real

# マルチタスク（Tm + ddG）
DDG_SOURCE=FEP uv run python ESM.py 1                       # seed=1, FEP全件
DDG_SOURCE=FEP uv run python ESM.py 1 --n-ddg 10            # seed=1, FEP 10サンプル
DDG_SOURCE=rosetta RESULT_DIR=/path/to/out uv run python ESM.py 1

# シングルタスク（Tm のみ）
DDG_SOURCE=none uv run python ESM.py 1

# 複数 seed
export DDG_SOURCE=FEP RESULT_DIR=/path/to/out
for seed in $(seq 1 5); do uv run python ESM.py $seed; done
```

**SLURM 経由:**

```bash
cd sim2real

# 基本
DDG_SOURCE=FEP RESULT_DIR=/path/to/out sbatch run_train.sh

# GPU 指定
DDG_SOURCE=FEP RESULT_DIR=/path/to/out sbatch --gres=gpu:a6000:1 -w floyd run_train.sh

# スケーリング実験の一括投入
for n in 10 15 23 35 53 80 121 184 279; do
  DDG_SOURCE=FEP N_DDG=$n RESULT_DIR=results/FEP/$n sbatch run_train.sh
done
DDG_SOURCE=FEP RESULT_DIR=results/FEP/all sbatch run_train.sh  # 全件
```

**DDG_SOURCE の選択肢**: `FEP`, `FoldX`, `rosetta`, `thermoMPNN`, `none`（シングルタスク）

`run_train.sh` 内の `#SBATCH --array=1-5%5` で seed の範囲と同時実行数を変更できます。

モデルは `{RESULT_DIR}/supervised/mtl_run<seed>/` に保存されます。

### 3. 評価

学習完了後、モデルが保存されたディレクトリを `--model-dir` で指定して評価します。

```bash
cd sim2real

# 自動検出（supervised/mtl_run* の数を自動カウント）
uv run python pLM523.py --model-dir /path/to/out

# run 数を明示
uv run python pLM523.py --n-runs 100 --model-dir /path/to/out

# SLURM 経由
EVAL_DIR=/path/to/out N_RUNS=100 sbatch run_eval.sh
```

出力:
- `mtl_eval_summary523.txt` — 各指標の平均値と 90% ブートストラップ信頼区間
- `mtl_eval_per_run_523.csv` — seed ごとの評価指標（MSE, RMSE, R2, MAE, Spearman, Pearson）

### 4. 可視化

`plot/simscail.ipynb` でスケーリング解析の結果をプロットします。

## ライセンス

MIT License
