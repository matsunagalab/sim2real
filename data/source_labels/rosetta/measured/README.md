# Rosetta データ

このフォルダには、Rosetta の **ddg_monomer** を用いたタンパク質安定性予測（ΔΔG）の入力・出力データおよび実行用スクリプトが格納されています。

---

## ファイル構成

### 入力構造（PDB）

| ファイル | 説明 |
|----------|------|
| `1MEL.pdb` | 1MEL の PDB 構造 |
| `4IDL.pdb` | 4IDL の PDB 構造 |

`run.sh` 実行時に Rosetta の `clean_pdb.py` で鎖を抽出した `1MEL_A.pdb` / `4IDL_A.pdb` が生成され、`run_rosetta.sh` の入力として使われます。

### 変異リスト用入力 CSV

| ファイル | 説明 |
|----------|------|
| `1mel_all-var_ddg_v2.csv` | 1MEL 用の変異一覧（変異配列など。`run.sh` では `sequence_to_rosetta_mutations.py` の入力として参照） |
| `4idl_all-var_ddg.csv` | 4IDL 用の変異一覧（`mutant_sequence` などの列を含む） |

これらを元に、Rosetta 用の変異リスト（`muts.txt` や `muts_1.txt` …）を生成して ddG 計算に使います。

### スクリプト

| ファイル | 説明 |
|----------|------|
| `run.sh` | **Step 1**: PDB のクリーニング（鎖抽出）と、`sequence_to_rosetta_mutations.py` による変異リストの生成。SLURM ジョブ用。 |
| `run_rosetta.sh` | **Step 2**: `ddg_monomer` による Rosetta ddG 計算。入力は `*_A.pdb` と `muts_<id>.txt`。SLURM ジョブ用。 |
| `sequence_to_rosetta_mutations.py` | 変異体配列の列を持つ CSV を読み、野生型との差分から変異を求め、Rosetta 形式の変異リスト（`muts.txt` または `muts_1.txt` …）を出力。複数ファイルへの分割（`--num_files`）に対応。 |

### Rosetta ddG 出力 CSV

| ファイル | 説明 |
|----------|------|
| `1mel_rosettaddg.csv` | 1MEL の Rosetta ddG 結果（変異ごと 1 行） |
| `4idl_rosettaddg.csv` | 4IDL の Rosetta ddG 結果 |
| `1mel_rosettaddg_processed.csv` | 1MEL の処理版（後述の追加列あり） |
| `4idl_rosettaddg_processed.csv` | 4IDL の処理版 |

---

## データ形式

### `*_rosettaddg.csv` の主な列

| 列名 | 説明 |
|------|------|
| `position` | 変異位置（残基番号） |
| `original_aa` | 野生型アミノ酸（1 文字） |
| `mutant_aa` | 変異後アミノ酸（1 文字） |
| `ddG` | Rosetta で計算した ΔΔG（kcal/mol） |
| `seq` / `mutant_sequence` | 変異体のアミノ酸配列 |
| `source_file` | 元データのファイル名 |
| `ddg` | 実験値など参照用の ddG（存在する場合） |

### `*_rosettaddg_processed.csv` の追加列

処理版では、学習用などに次の列が追加されています。

| 列名 | 説明 |
|------|------|
| `ddg_neg` | 参照 ddG の符号反転（`-ddg`） |
| `ddg_scaled01` | 参照 ddG を 0–1 にスケーリングした値 |

---

## run.sh / run_rosetta.sh の設定

**PDB_ID と CHAIN_ID は、計算対象の構造に応じて必ず書き換えてください。** スクリプト内の既定値（1MEL / A）は 1MEL 用の例です。

| 計算対象 | PDB_ID | CHAIN_ID | 補足 |
|----------|--------|----------|------|
| 1MEL     | `1MEL` | `A`      | `run.sh` の CSV は `1mel_all-var_ddg_v2.csv`、野生型配列を `--wildtype` に指定 |
| 4IDL     | `4IDL` | `A`      | `run.sh` の CSV は `4idl_all-var_ddg.csv`、4IDL の野生型配列を `--wildtype` に指定 |

- **run.sh**: 先頭で `PDB_ID` と `CHAIN_ID` を設定するほか、`clean_pdb.py` の入力になる `${PDB_ID}.pdb` がカレントにあること、および後続の `sequence_to_rosetta_mutations.py` に渡す `--csv_file` と `--wildtype` をその PDB 用のものに合わせて編集してください。
- **run_rosetta.sh**: 同じく `PDB_ID` と `CHAIN_ID` を設定し、`ddg_monomer` が読み込む `${PDB_ID}_${CHAIN_ID}.pdb`（run.sh で生成されたクリーニング済み PDB）と、`muts_<id>.txt` の `id` が対応するようにしてください。

Rosetta のパス（`ROSETTA_ROOT` 等）も、環境に合わせて `run.sh` および `run_rosetta.sh` 内で変更してください。

---

## sequence_to_rosetta_mutations.py の使い方

`run.sh` から呼ばれる **sequence_to_rosetta_mutations.py** は、変異体配列が入った CSV を読み、野生型との差分から変異を求め、Rosetta の ddg_monomer 用の変異リスト（`muts.txt` または `muts_1.txt` …）を出力するスクリプトです。本フォルダに格納されています。

### コマンドライン

```bash
python3 sequence_to_rosetta_mutations.py \
  --csv_file <入力CSV> \
  --wildtype <野生型アミノ酸配列（1文字）> \
  --variant_column <変異体配列の列名> \
  [--output_file <出力ファイル>] \
  [--num_files <分割数>]
```

### 主なオプション

| オプション | 必須 | 説明 |
|------------|------|------|
| `--csv_file` | ○ | 変異体配列（および必要に応じて他の列）を含む CSV のパス。例: `1mel_all-var_ddg_v2.csv`, `4idl_all-var_ddg.csv` |
| `--wildtype` | ○ | 野生型のアミノ酸配列（1 文字表記）。これと変異体配列を比較して変異位置・残基を求めます。 |
| `--variant_column` | ○ | 変異体配列が入っている列の名前。例: `mutant_sequence` |
| `--output_file` | - | 出力する変異リストのパス（既定は `muts.txt`）。`--num_files` > 1 のときは `muts_1.txt`, `muts_2.txt`, … のように連番が付きます。 |
| `--num_files` | - | 変異リストを何個のファイルに分割するか（既定: 1）。ジョブ並列用に複数に分ける場合に指定。 |

### 入力 CSV の想定

- ヘッダーに `--variant_column` で指定した列名（例: `mutant_sequence`）が含まれること。
- その列に、野生型と比較可能な長さのアミノ酸配列（1 文字）が各行に 1 本ずつ入っていること。
- 野生型配列 `--wildtype` は、その PDB/鎖の実際の野生型と一致している必要があります（1MEL 用と 4IDL 用で異なります）。

### 実行例（1MEL）

```bash
python3 sequence_to_rosetta_mutations.py \
  --csv_file 1mel_all-var_ddg_v2.csv \
  --wildtype "VQLQASGGGSVQAGGSLRLSCAASGYTIGPYCMGWFRQAPGKEREGVAAINMGGGITYYADSVKGRFTISQDNAKNTVYLLMNSLEPEDTAIYYCAADSTIYASYYECGHGLSTGGYGYDSWGQGTQVTVSS" \
  --variant_column "mutant_sequence" \
  --output_file muts.txt \
  --num_files 20
```

4IDL を計算する場合は、`--csv_file` に `4idl_all-var_ddg.csv`、`--wildtype` に 4IDL の野生型配列を指定し、`run.sh` の `PDB_ID`/`CHAIN_ID` を `4IDL`/`A` に合わせてください。

---

## 実行フロー概要

1. **変異リストの準備**  
   - `run.sh`: `clean_pdb.py` で PDB を整え、`sequence_to_rosetta_mutations.py` で `1mel_all-var_ddg_v2.csv` 等から `muts.txt`（または複数ファイル）を生成。

2. **Rosetta ddG 計算**  
   - `run_rosetta.sh`: `ddg_monomer` に `*_A.pdb` と `muts_<id>.txt` を渡して ddG を計算。結果は後処理で `*_rosettaddg.csv` などにまとめます。
