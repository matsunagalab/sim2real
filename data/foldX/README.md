# FoldX の使い方

## FoldX のインストール

FoldX はインストール不要のポータブル実行ファイルです。

1. **ダウンロード**
   - [FoldX Suite](https://foldxsuite.crg.eu/) にアクセスし、利用規約に同意してアカデミックライセンス情報ページ（[academic-license-info](https://foldxsuite.crg.eu/academic-license-info)）からダウンロード用のリンクを取得する。

2. **展開と配置**
   - ダウンロードしたアーカイブを解凍する。
   - FoldX 4 では **rotabase.txt** は必須。

---

## 解析の手順

### 1. RepairPDB で入力構造を直す

RepairPDB は必須ではありませんが、結果を安定させるために最初に実行しておくのが推奨です。

```bash
foldx --command=RepairPDB --pdb=yourfile.pdb
```

**RepairPDB 後に出る主なファイル**

| ファイル | 説明 |
|----------|------|
| 修復済み PDB | `<元名>_Repair.pdb`（例: 1mel.pdb → 1mel_Repair.pdb） |
| ログ/エネルギー | RepairPDB.fxout |

### 2. individual_list.txt を作る

#### make_individual_list.py の使い方

指定した PDB・配列・鎖に対して**全単変異**を列挙するスクリプトです。変異先として「野生型と同じアミノ酸」と「Cys」は自動で除外します（各位置あたり最大 18 種類）。PDB の残基番号が配列の 1 番目と一致しない場合は `--start-residue` で先頭残基番号を指定します。

**コマンドライン**

```bash
python make_individual_list.py --pdb-id <PDB ID> --sequence <アミノ酸配列> --chain <鎖ID> [--output <出力ファイル>] [--group-by-position] [--start-residue N]
```

| オプション | 短縮 | 必須 | 説明 |
|------------|------|------|------|
| `--pdb-id` | - | ○ | PDB ID（例: 1MEL） |
| `--sequence` | `-s` | ○ | アミノ酸配列（1文字表記） |
| `--chain` | `-c` | ○ | 鎖 ID（1文字、例: A） |
| `--output` | `-o` | - | 出力ファイルパス（既定: `individual_list.txt`） |
| `--group-by-position` | - | - | 同一残基の変異を 1 行にカンマ区切りでまとめる |
| `--start-residue` | - | - | 配列の先頭に対応する PDB 上の残基番号（既定: 1） |

**実行例**

```bash
# 1変異1行で出力（BuildModel の入力にそのまま使える）
python make_individual_list.py --pdb-id 1MEL --sequence MKTAYIAKQRQ... --chain A --output individual_list.txt

# PDB の残基番号が 50 から始まる場合
python make_individual_list.py --pdb-id 1MEL -s MKTAYIAK... -c A -o individual_list.txt --start-residue 50
```

**Python から呼び出す**

```python
from make_individual_list import make_individual_list

# 戻り値は出力した変異の総数
n = make_individual_list("1MEL", "MKTAYIAK...", "A", "individual_list.txt")
# 同一残基で1行にまとめる場合
n = make_individual_list("1MEL", "MKTAYIAK...", "A", "individual_list.txt", one_per_line=False)
# PDB の残基番号が 50 から始まる場合
n = make_individual_list("1MEL", "MKTAYIAK...", "A", "individual_list.txt", start_residue=50)
```

**出力形式**

- 各エントリは `[元アミノ酸][鎖][残基番号][変異先アミノ酸]`（例: `VA2D` = 鎖A 2番目 Val→Asp）。残基番号は `--start-residue` で揃えられます。
- 既定は 1 行 1 変異・行末 `;`。`--group-by-position` 時は同一残基の変異がカンマ区切りで 1 行になります。

手動で書く場合の形式:

```
AA3G,AC3G,AE3G,AG3G;
YA6A,YC6A,YE6A,YG6A;
```

- `,` = 複数チェーン同時に入れる場合の変異の区切り
- `;` = その 1 セットの終わり
- `AA3G` = 「Ala(元) / chain A / 残基3 / Gly(変異先)」

### 3. BuildModel を実行

```bash
foldx --command=BuildModel --pdb=yourfile_Repair.pdb --mutant-file=individual_list.txt --output-dir=results
```

**BuildModel 後に出る主なファイル（1mel_Repair.pdb の例）**

| ファイル | 説明 |
|----------|------|
| Dif_1mel_Repair.fxout | 変異体と WT のエネルギー差（ddG） |
| 1mel_Repair_1.pdb など | 変異体の PDB（_1, _2… は individual_list.txt の行番号に対応） |
| WT_1mel_Repair_1.pdb など | 比較用 WT 構造 |
| Average_1mel_Repair.fxout | ラン平均（numberOfRuns=1 なら Dif とほぼ同じ） |
| Raw_1mel_Repair.fxout | WT/変異体それぞれの生データ |
| PdbList_1mel_Repair.fxout | 生成 PDB の名前一覧 |
| 1mel_Repair_0_ST.fxout | 入力構造のエネルギー情報 |

### 4. foldx_to_csv.py で変異体配列・ddG の CSV を出力

**foldx_to_csv.py** は、`individual_list` と `Dif_*_Repair.fxout` および**入力配列（野生型）**から、変異体ごとの配列と FoldX の ddG を 1 行にまとめた CSV を出力します。`make_individual_list.py` で individual_list を作成したときと同じ配列と `--start-residue` を指定してください。

**コマンドライン**

```bash
python foldx_to_csv.py --individual-list <individual_list> --fxout <Dif_*_Repair.fxout> --sequence "<アミノ酸配列>" [--output <CSV>] [--start-residue N]
```

| オプション | 短縮 | 必須 | 説明 |
|------------|------|------|------|
| `--individual-list` | `-i` | ○ | individual_list ファイル（例: individual_list_1mel_all.txt） |
| `--fxout` | `-f` | ○ | FoldX の Dif_*_Repair.fxout ファイル |
| `--sequence` | `-s` | ○ | 野生型アミノ酸配列（individual_list 作成時と同じもの） |
| `--output` | `-o` | - | 出力 CSV パス（既定: foldx_ddg.csv） |
| `--start-residue` | - | - | 配列の先頭の PDB 残基番号（make_individual_list と同一、既定: 1） |

**出力 CSV の列**

| 列 | 説明 |
|----|------|
| position | PDB 残基番号（1-based） |
| wt_aa | 野生型アミノ酸 |
| mut_aa | 変異先アミノ酸 |
| mutation | 変異ラベル（例: V2A） |
| variant_sequence | 変異体のアミノ酸配列 |
| ddG | FoldX の total energy（変異の安定性変化） |

**実行例（1MEL 全単変異）**

```bash
python foldx_to_csv.py \
  --individual-list individual_list_1mel_all.txt \
  --fxout Dif_1MEL-all_Repair.fxout \
  --sequence "VQLQASGGGSVQAGGSLRLSCAASG..." \
  --output 1mel_all_foldx_ddg.csv \
  --start-residue 2
```

`--start-residue` は、その配列で individual_list を作ったときに `make_individual_list.py` に渡した値と揃えてください。
