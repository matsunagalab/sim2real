# sim2real

**Sim2Real Transfer Learning for Nanobody Thermal Stability Prediction**

ナノボディの熱安定性（Tm）予測を改善するために、シミュレーション由来の補助タスク（ddG, MD-derived structural features）をマルチタスク学習で活用する研究プロジェクトです。タンパク質言語モデル ESM-2 を NbBench thermo-tm データで fine-tuning する際に、計算科学ツール（FEP / FoldX / Rosetta / ThermoMPNN）の ddG や、all-atom MD trajectory から計算した Q-value, RMSF, 塩橋持続率を補助タスクとして同時に学習させます。

最良構成 (`hot_lowflex_sweep`): **MAE = 6.76°C, 90% CI 幅 = 0.86** (frozen ベースライン 7.32 から **-0.56°C 改善**)。

## 手法の概要

- **ベースモデル**: ESM-2 8M (`facebook/esm2_t6_8M_UR50D`、デフォルト) / 35M / 650M を切替可
- **エンコーダーモード**: `frozen` (head のみ学習・最速) / `lora` (PEFT) / `hot` (フル fine-tuning、ベスト)
- **タスク**:
  - Primary: Tm 回帰 (NbBench thermo-tm)
  - Auxiliary 1-2: ddG (1MEL / 4IDL のペア)
  - Auxiliary 3-4: MD-derived scalar feature (Q-value 各種、RMSF、塩橋)
- **損失重み**: Kendall et al. 2018 の learnable uncertainty weighting (デフォルト) / 固定重み
- **アンサンブル評価**: 複数 seed の予測を平均してから MAE / 90% bootstrap CI を算出

## セットアップ

[uv](https://docs.astral.sh/uv/) で依存関係を管理しています。

```bash
uv sync                # 仮想環境作成 + 依存関係インストール
uv sync --extra plot   # 可視化用 (matplotlib, seaborn, jupyter) も含める
```

GPU は CUDA 12.4 系を想定。pyproject.toml の `[[tool.uv.index]]` で PyTorch cu124 を指定済み。

## クイックスタート

### 1. データ準備（MD 系を使う場合のみ）

NbBench/DDG データはリポジトリに同梱済み。MD-derived 特徴量は MD trajectory から抽出する必要あり：

```bash
# 上流の MD パイプライン (/home/yasu/tmp/mdclaw/job_nano_*) から特徴量を一括抽出
uv run python scripts/extract_all_features.py
```

これで `data/md/` 以下に以下が生成されます：

| CSV | 内容 | 抽出元 |
|-----|------|-------|
| `nanobody_qvalue_hphil.csv` | hphil-all Q-value (Best-Hummer, β=50, λ=1.8) | `extract_q_values.py` |
| `nanobody_rmsf.csv` | mean Cα RMSF | `extract_rmsf.py` |
| `feat_q_highflex.csv` | top 30% RMSF 残基のみで計算した hphil-Q (CDR proxy) | `extract_features_pilot.py` |
| `feat_q_lowflex.csv` | bottom 70% RMSF 残基のみで計算した hphil-Q (framework proxy) | 同上 |
| `feat_saltbridge.csv` | native 塩橋の persistence | 同上 |
| `rosetta_qvalue_hphil.csv` | Rosetta backrub MC trajectory の Q-value | `extract_rosetta_qvalues.py` |

Rosetta 系は別途 `scripts/run_rosetta_backrub.py` で trajectory を作成してから抽出。

### 2. 名前付き実験を再現する

すべての過去実験は `experiments.yaml` に登録されており、1 コマンドで再現可能：

```bash
# 登録実験を一覧
uv run python scripts/run_experiment.py --list

# ベスト構成 (8M Hot + Q_LOWFLEX) を再現
CUDA_VISIBLE_DEVICES=1 uv run python scripts/run_experiment.py hot_lowflex_sweep

# 期待値と比較しつつ実行
uv run python scripts/run_experiment.py hot_lowflex_sweep --check

# 既存の結果を verify するだけ (再実行しない)
uv run python scripts/run_experiment.py hot_lowflex_sweep --check-only

# コマンドだけ表示 (実行しない)
uv run python scripts/run_experiment.py hot_lowflex_sweep --dry-run
```

出力：
- `logs/<name>.log` — stdout/stderr 全文
- `results/<name>/scaling.json` — args / env / hparams / per-scaling MAE+CI / paired bootstrap ΔMAE
- `results.tsv` — 拡張スキーマで 1 行追記

主な実験名（詳細は `EXPERIMENTS.md`）：

| name | 概要 | best MAE |
|------|------|----------|
| `frozen_q_hphil_full` | Frozen ESM-2 8M ベースライン | 7.32 |
| `combo_lowflex_highflex_frozen` | Framework Q + CDR Q 並列 (frozen) | 7.22 |
| **`hot_lowflex_sweep`** | **8M Hot + Q_LOWFLEX (overall best)** | **6.76** |
| `hot_650m_lowflex_640` | 650M Hot + Q_LOWFLEX | 6.78 |
| `lora_650m_lowflex_640` | 650M LoRA + Q_LOWFLEX | 7.04 |
| `rosetta_full` | Rosetta backrub Q (ROSETTA_Q_HPHIL) | 7.32 |

### 3. 直接 prepare.py を呼ぶ（旧式・互換維持）

`run_experiment.py` を介さず prepare.py を直接起動することも可能：

```bash
# Frozen baseline
uv run python prepare.py --ddg-source none --md-source MD_Q_HPHIL \
  --n-md-list 10,20,40,80,160,320,640 --n-runs 10

# Hot encoder + Q_LOWFLEX (ベスト)
uv run python prepare.py --encoder-mode hot --ddg-source none \
  --md-source MD_Q_LOWFLEX --n-md-list 10,40,160,640 --n-runs 10

# 650M Hot
uv run python prepare.py --encoder-mode hot --base-model facebook/esm2_t33_650M_UR50D \
  --ddg-source none --md-source MD_Q_LOWFLEX --n-md-list 640 --n-runs 5

# DDG ベースライン (Tm + 1MEL/4IDL ペア)
uv run python prepare.py --ddg-source FEP --n-ddg-list 10,20,40,80,160,320 --n-runs 10
```

CLI 引数（`--encoder-mode` など）は環境変数 (`ENCODER_MODE` など) より優先。env var 経由の旧呼び出しも依然動作：

```bash
ENCODER_MODE=hot CUDA_VISIBLE_DEVICES=1 uv run python prepare.py \
  --ddg-source none --md-source MD_Q_LOWFLEX --n-md-list 640 --n-runs 5
```

## CLI 引数リファレンス（prepare.py）

| flag | 既定 | 説明 |
|------|------|------|
| `--ddg-source` | FEP | `FEP` / `FoldX` / `rosetta` / `thermoMPNN` / `rosetta_esm` / `rosetta_random` / `none` |
| `--n-ddg-list` | "20,80,280" | DDG スケーリングのサンプル数（カンマ区切り） |
| `--md-source` | none | `MD_Q` / `MD_Q_HPHIL` / `ROSETTA_Q_HPHIL` / `MD_RMSF` / `MD_Q_HIGHFLEX` / `MD_Q_LOWFLEX` / `MD_SALTBRIDGE` |
| `--md-aux-source` | none | 並列の 2 番目の MD task (task_id=4) |
| `--n-md-list` | "" | MD スケーリングのサンプル数（指定時は MD axis） |
| `--n-runs` | 3 | アンサンブルする seed 数 |
| `--encoder-mode` | env / frozen | `frozen` / `lora` / `hot` |
| `--base-model` | env / esm2_t6_8M_UR50D | HF model id |
| `--mtl-weight-mode` | env / uncertainty | `uncertainty` / `fixed` |
| `--md-weight` | env / 1.0 | `mtl-weight-mode=fixed` 時の MD タスク重み |
| `--exp-name` | None | 出力 dir 名 / results.tsv ラベル |
| `--result-dir` | tempdir | チェックポイント保存先 |

## リポジトリ構成

```
sim2real/
├── prepare.py             # データ読込・評価・スケーリング解析（CLI ドライバ）
├── train.py               # MultiTaskModel + 学習ループ（HPARAMS）
├── experiments.yaml       # 名前付き実験レジストリ
├── EXPERIMENTS.md         # 実験一覧（人間用）
├── results.tsv            # 全実験のサマリログ（拡張スキーマ）
│
├── scripts/
│   ├── run_experiment.py          # experiments.yaml から実験を起動
│   ├── extract_all_features.py    # 全 MD 抽出スクリプトの wrapper
│   ├── extract_q_values.py        # MD trajectory → Q-value (hphil-all)
│   ├── extract_rmsf.py            # MD trajectory → mean Cα RMSF
│   ├── extract_features_pilot.py  # → q_highflex / q_lowflex / saltbridge
│   ├── extract_rosetta_qvalues.py # Rosetta MC trajectory → Q-value
│   ├── run_rosetta_backrub.py     # Rosetta backrub の並列実行
│   └── mlm_finetune.py            # ESM-2 を VHH NGS で MLM fine-tuning
│
├── data/
│   ├── nbbench/                # NbBench thermo-tm (train 396 / val 57 / test 114)
│   ├── md/                     # MD-derived 特徴量 CSV (上記スクリプトで生成)
│   ├── fep/ foldX/ rosetta/    # ddG データ (1MEL + 4IDL ペア)
│   ├── mpnn/ rosetta_esm1000/ rosetta_random1000/
│   └── Tm/                     # 旧 Tm データ（NbBench 切替前のレガシー）
│
├── results/<exp-name>/scaling.json   # 構造化された実験結果
├── logs/<exp-name>.log               # run_experiment.py 経由のログ
├── logs/archive/                     # リファクタ前の古いログ群（96 件）
├── plot/                             # 可視化ノートブック
└── paper/                            # 論文（LaTeX）
```

## アーキテクチャ詳細

`MultiTaskModel` (`train.py`):
- **Encoder**: ESM-2 (frozen / LoRA / hot)
- **Shared layers**: `Linear(hs, 256) → ReLU → Dropout → Linear(256, 128) → ReLU → Dropout → Linear(128, 32) → ReLU`
- **Heads** (32 → 1):
  - `tm_head` (task_id=0): Tm 回帰
  - `ddg_head` (task_id=1): 1MEL ddG
  - `ddg_head2` (task_id=2): 4IDL ddG
  - `md_head` (task_id=3): primary MD scalar
  - `md_head2` (task_id=4): aux MD scalar
- **Loss**: HuberLoss(δ=1.0) per task、uncertainty weighting (`log_sigma_*`)
- **Early stopping**: patience=15 (HPARAMS で調整可)

Hot mode 時は encoder と head で別 LR (encoder=1e-4, head=3e-4) を `HotModeTrainer.create_optimizer` で適用。

## 結果の構造

`results/<exp-name>/scaling.json`:

```json
{
  "exp_name": "hot_lowflex_sweep",
  "git_commit": "abc1234",
  "args": {...},
  "env": {"ENCODER_MODE": "hot", ...},
  "resolved_encoder_mode": "hot",
  "hparams": {...},
  "scaling": [
    {"n": 10, "mae": 6.94, "ci_lo": 6.52, "ci_hi": 7.35, "ci_width": 0.84},
    ...
  ],
  "best": {"n": 640, "mae": 6.76, "ci_width": 0.86},
  "summary": {"slope": -0.43, "ci_width_avg": 0.86, "mae_avg": 6.83},
  "paired_bootstrap": {
    "ref_n": 10,
    "per_n": [{"n": 40, "delta_mae": -0.10, ...}, ...],
    "full_range": {"from": 10, "to": 640, "delta_mae": -0.17, "p_positive": 0.014}
  }
}
```

## 新しい実験の追加

1. `experiments.yaml` に entry を追加（`args` / `env` / `expected`）
2. 抽出 CSV が必要なら `scripts/extract_*.py` を実行
3. `uv run python scripts/run_experiment.py <new_name>`

## ライセンス

MIT License
