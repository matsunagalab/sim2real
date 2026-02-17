# MPNN データ

このフォルダには、Message Passing Neural Network（MPNN）系モデルを用いたタンパク質安定性予測（ΔΔG）のデータが格納されています。

---

## ThermoMPNN 出力ファイル（Google Colab 由来）

以下の CSV は、**Google Colab** 上のノートブックで生成した出力ファイルです。

| ファイル | 説明 |
|----------|------|
| `1mel_thermompnn_data.csv` | 1MEL 用 ThermoMPNN の予測結果 |
| `4idl_thermompnn_data.csv` | 4IDL 用 ThermoMPNN の予測結果 |

**Colab ノートブック**  
[https://colab.research.google.com/drive/1OcT4eYwzxUFNlHNPk9_5uvxGNMVg3CFA](https://colab.research.google.com/drive/1OcT4eYwzxUFNlHNPk9_5uvxGNMVg3CFA)

### ThermoMPNN データの形式

- **列**: `Mutation`（変異表記）, `ddG (kcal/mol)`, `pos`, `wtAA`, `mutAA`
- 各変異ごとに 1 行で、ΔΔG（kcal/mol）が含まれます。

---

## MPNN2 系ファイル

配列単位で ΔΔG をまとめたデータです。

| ファイル | 説明 |
|----------|------|
| `1melMPNN2.csv` | 1MEL 配列と ddg |
| `4idlMPNN2.csv` | 4IDL 配列と ddg |
| `*_processed.csv` | 上記の処理版 |
| `*_processed_rand.csv` | 処理版＋`ddg_neg`, `ddg_scaled01` など追加列 |

### MPNN2 系の形式

- **\*MPNN2.csv**: `seq`（アミノ酸配列）, `ddg`
- **\*_processed_rand.csv**: `seq`, `ddg`, `ddg_neg`, `ddg_scaled01`
