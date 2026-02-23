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

各ディレクトリ（例: `multi/scail-FEP/10/`）に移動して学習を実行します。

#### インタラクティブ実行（GPU マシン上で直接）

```bash
cd multi/scail-FEP/10/
python ESM.py 1          # seed=1 で 1 回実行
```

複数 seed をまとめて流す場合:

```bash
for seed in $(seq 1 5); do
  python ESM.py $seed
done
```

#### SLURM 経由

```bash
cd multi/scail-FEP/10/
sbatch --gres=gpu:a6000:1 -w floyd run-SFT.sh
```

- `run-SFT.sh` 内の `#SBATCH --array=n-m%7` で seed の範囲と同時実行数を指定します
  - 例: `--array=1-100%7` → seed 1〜100 を最大 7 並列で実行

いずれの方法でも、各 seed で `supervised/mtl_run<seed>/` にモデルが保存されます

### 3. 評価

学習完了後、同じディレクトリで評価スクリプトを実行します。

```bash
python3 pLM523.py
```

- `pLM523.py` 内の `for i in range(n)` の `n` を実行した seed 数に合わせてください
- 出力:
  - `mtl_eval_summary523.txt` — 各指標の平均値と 90% ブートストラップ信頼区間
  - `mtl_eval_per_run_523.csv` — seed ごとの評価指標（MSE, RMSE, R2, MAE, Spearman, Pearson）

### 4. 可視化

`plot/simscail.ipynb` でスケーリング解析の結果をプロットします。

## ディレクトリの構成

各ディレクトリ（`single/Tm10per/`, `multi/scail-FEP/10/` など）は同じ構成を持ちます:

| ファイル | 説明 |
|---------|------|
| `ESM.py` | 学習プログラム。seed をコマンドライン引数で受け取る |
| `pLM523.py` | テストデータ 523 件での評価プログラム |
| `pLM.py` | テストデータ 12 件での評価プログラム（存在する場合） |
| `run-SFT.sh` | SLURM ジョブ投入用バッチスクリプト |
| `mtl_eval_summary523.txt` | 評価結果サマリー（存在する場合） |
| `mtl_eval_per_run_523.csv` | seed ごとの評価結果（存在する場合） |

`multi/scail-*/` 以下の数字ディレクトリ名（10, 15, 23, ...）は、マルチタスク学習に使用する ddG データのサンプル数を表します。

## ライセンス

MIT License
