# Rosetta Random-Variant Source Labels

**ランダム変異**で生成した約 1000 バリアントを、Rosetta の ddG 計算で評価するためのワークフローです。
ESM-2 等のモデルを使わず、位置・アミノ酸を一様ランダムに選んで変異を入れるベースライン用です。

## 概要

1. **変異生成**: WT 配列に対して、位置と置換アミノ酸をランダムに選び、指定本数（例: 2）の変異を持つバリアントを 1000 本生成
2. **Rosetta 入力変換**: CSV を Rosetta 形式の変異リスト（`muts.txt` 等）に変換
3. **Rosetta ddG**: ddG 計算で各変異の安定性変化を評価

## ディレクトリ構成

```
data/source_labels/rosetta/random1000/
├── README.md
├── generate_mutation_random.ipynb   # ランダム変異生成
├── csv_to_rosetta_mutations.py      # CSV → Rosetta 変異リスト変換
├── run.sh                            # PDB クリーン + 変異リスト生成（SLURM 用）
├── run_rosetta.sh                    # Rosetta ddG 実行（SLURM 用）
├── 1MEL.pdb, 4IDL.pdb               # 入力 PDB
├── multi_mutations_random_*_*.csv    # 生成した変異 CSV
└── random_*_with_ddg*.csv           # ddG 付き結果（処理済み含む）
```

## 前提環境

- **Python**: `pandas`（Notebook 実行用）
- **Rosetta**: インストール済み（`run.sh` / `run_rosetta.sh` 内のパスを環境に合わせて変更）

## 使い方

### 1. 変異生成（Notebook）

`generate_mutation_random.ipynb` を上から実行します。

- **設定例**:
  - `seq_name`: 配列名（例: `1mel`, `4idl`）
  - `wt_sequence`: 抗体の WT アミノ酸配列
  - `num_sequences_to_generate`: 生成するバリアント数（例: 1000）
  - `num_mutations`: 1 バリアントあたりの変異数（例: 2）
  - `output_dir`: 出力先ディレクトリ（例: `.` または `outputs`）

- **変異ルール**:
  - 変異先アミノ酸は Cys を除く 19 種類（`ADEFGHIKLMNPQRSTVWY`）から一様ランダムに選択
  - 同じ配列は重複排除して、指定本数になるまで生成

- **出力**:
  `multi_mutations_random_<num_mutations>mut_<seq_name>_<num_sequences>.csv`
  列: `sequence`, `num_mutations`, `mutations`

### 2. CSV → Rosetta 変異リスト

```bash
python3 csv_to_rosetta_mutations.py \
  --csv_file multi_mutations_random_2mut_1mel_1000.csv \
  --output_file muts.txt \
  --num_files 20
```

- `--num_files 20`: 出力を 20 ファイルに分割（`muts_1.txt` … `muts_20.txt`）
- 各ファイルは Rosetta の `-ddg::mut_file` で指定する形式

### 3. PDB の準備と変異リスト生成（オプション）

`run.sh` では以下を行います。

- Rosetta の `clean_pdb.py` で鎖の抽出（例: 1MEL 鎖 A）
- 上記と同様に `csv_to_rosetta_mutations.py` で `muts.txt`（および分割時は `muts_1.txt` 等）を生成

PDB 名・鎖は `run.sh` 内の `PDB_ID`, `CHAIN_ID` を編集し、`--csv_file` を実際の CSV ファイル名に合わせてください。

### 4. Rosetta ddG の実行

`run_rosetta.sh` を参照して ddG を実行します。

- 入力: `1MEL_A.pdb`（または `4IDL_A.pdb` 等）、`muts_1.txt` など
- `-ddg::mut_file muts_${id}.txt` でファイル番号を指定
- 出力は silent 形式等、スクリプト内のオプションに従います

SLURM で投入する場合は、ジョブ名やパーティションを環境に合わせて変更してください。

## 入力 CSV 形式

`generate_mutation_random.ipynb` が出力する CSV は以下の列を持ちます。

| 列名 | 説明 |
|------|------|
| sequence | 変異後のアミノ酸配列 |
| num_mutations | 変異数 |
| mutations | JSON 配列。各要素は `position`, `original_aa`, `mutated_aa` |

`csv_to_rosetta_mutations.py` はこの `mutations` を読み、Rosetta の変異リスト形式（`original_aa position mutated_aa` の行）に変換します。

## ESM2-generated Rosetta variantsとの違い

| 項目 | `rosetta/random1000` | `rosetta/esm1000` |
|------|--------------------|-----------------|
| 変異の決め方 | 位置・アミノ酸を一様ランダム | ESM-2 の確率でサンプリング |
| バリアント数 | 指定数（例: 1000）をそのまま使用 | 10 万生成 → PLL 上位 1% で約 1000 本に絞る |
| PLL | なし | あり（フィルタに使用） |
| 用途 | ベースライン・対照実験 | PLM に基づく変異候補の評価 |

## 注意事項

- Rosetta のパス（`ROSETTA_ROOT`, `ROSETTA_BIN`, `ROSETTA_DB` 等）は実行環境に合わせて変更してください。
- `run.sh` では `clean_pdb.py` 実行後に `*_${CHAIN_ID}.pdb` ができるため、`run_rosetta.sh` の `-in:file:s` はそのファイル名と一致させる必要があります。
- 複数ファイルに分割する場合は、`--num_files` で分割し、ジョブ配列などで並列に ddG を回すと効率的です。
