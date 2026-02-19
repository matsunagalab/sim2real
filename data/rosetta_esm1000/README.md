# rosetta_esm1000

ESM-2（Protein Language Model）で生成した変異バリアントを、Rosetta の ddG 計算で評価するためのワークフローです。  
約 10 万バリアントを生成し、PLL（Pseudolog-Likelihood）で上位 1% を選んだ約 1000 バリアントに対して Rosetta ddG を実行します。

## 概要

1. **変異生成**: ESM-2 (650M) の確率分布に基づき、WT 配列から多変異バリアントをサンプリング
2. **PLL フィルタ**: 各バリアントの PLL を計算し、上位 1% のみを出力
3. **Rosetta 入力変換**: CSV を Rosetta 形式の変異リスト（`muts.txt` 等）に変換
4. **Rosetta ddG**: ddG 計算で各変異の安定性変化を評価

## ディレクトリ構成

```
rosetta_esm1000/
├── README.md
├── generate_mutation_plm.ipynb   # ESM-2 で変異生成・PLL 計算
├── csv_to_rosetta_mutations.py   # CSV → Rosetta 変異リスト変換
├── run.sh                         # PDB クリーン + 変異リスト生成（SLURM 用）
├── run_rosetta.sh                 # Rosetta ddG 実行（SLURM 用）
├── 1MEL.pdb, 4IDL.pdb             # 入力 PDB
├── esm2_650M_large_scale_variants_*_top1pct.csv   # 上位 1% 変異 CSV
└── esm2_650M_2muts_*_with_ddg*.csv                # ddG 付き結果（処理済み含む）
```

## 前提環境

- **Python**: `torch`, `transformers`, `pandas`, `numpy`, `tqdm`
- **ESM-2**: `facebook/esm2_t33_650M_UR50D`
- **Rosetta**: インストール済み（`run.sh` / `run_rosetta.sh` 内のパスを環境に合わせて変更）

## 使い方

### 1. 変異生成と PLL フィルタ（Notebook）

`generate_mutation_plm.ipynb` を上から実行します。

- **設定例**:
  - `seq_name`: 配列名（例: `1mel`, `4idl`）
  - `wt_sequence`: 抗体の WT アミノ酸配列
  - `num_variants`: 生成するバリアント数（例: 100000）
  - `mutation_counts`: 1 バリアントあたりの変異数（例: `[2]`）
  - `top_pll_percent`: PLL 上位何 % を残すか（例: 1）

- **出力**:  
  `esm2_650M_large_scale_variants_<seq_name>_<num_variants>_top1pct.csv`  
  列: `sequence`, `num_mutations`, `mutations`, `pll`

### 2. CSV → Rosetta 変異リスト

```bash
python3 csv_to_rosetta_mutations.py \
  --csv_file esm2_650M_large_scale_variants_1mel_100000_top1pct.csv \
  --output_file muts.txt \
  --num_files 20
```

- `--num_files 20`: 出力を 20 ファイルに分割（`muts_1.txt` … `muts_20.txt`）
- 各ファイルは Rosetta の `-ddg::mut_file` で指定する形式

### 3. PDB の準備と変異リスト生成（オプション）

`run.sh` では以下を行います。

- Rosetta の `clean_pdb.py` で鎖の抽出（例: 1MEL 鎖 A）
- 上記と同様に `csv_to_rosetta_mutations.py` で `muts.txt`（および分割時は `muts_1.txt` 等）を生成

PDB 名・鎖は `run.sh` 内の `PDB_ID`, `CHAIN_ID` を編集してください。

### 4. Rosetta ddG の実行

`run_rosetta.sh` を参照して ddG を実行します。

- 入力: `1MEL_A.pdb`（または `4IDL_A.pdb` 等）、`muts_1.txt` など
- `-ddg::mut_file muts_${id}.txt` でファイル番号を指定
- 出力は silent 形式等、スクリプト内のオプションに従います

SLURM で投入する場合は、ジョブ名やパーティションを環境に合わせて変更してください。

## 入力 CSV 形式

`generate_mutation_plm.ipynb` が出力する CSV は以下の列を持ちます。

| 列名 | 説明 |
|------|------|
| sequence | 変異後のアミノ酸配列 |
| num_mutations | 変異数 |
| mutations | JSON 配列。各要素は `position`, `original_aa`, `mutated_aa` |
| pll | Pseudolog-Likelihood（高いほどモデルが「自然」と評価） |

`csv_to_rosetta_mutations.py` はこの `mutations` を読み、Rosetta の変異リスト形式（`original_aa position mutated_aa` の行）に変換します。

## 注意事項

- Rosetta のパス（`ROSETTA_ROOT`, `ROSETTA_BIN`, `ROSETTA_DB` 等）は実行環境に合わせて変更してください。
- `run.sh` では `clean_pdb.py` 実行後に `*_${CHAIN_ID}.pdb` ができるため、`run_rosetta.sh` の `-in:file:s` はそのファイル名と一致させる必要があります。
- 大量バリアントを扱う場合は、`--num_files` で分割し、ジョブ配列などで並列に ddG を回すと効率的です。
