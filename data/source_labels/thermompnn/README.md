# ThermoMPNN / MPNN Source Labels

This directory contains ThermoMPNN-derived mutation-effect labels and processed
tables used as computational source labels.

---

## Files Used By The Current Training Code

`prepare.py` maps `--ddg-source thermoMPNN` to:

| Structure | Processed CSV | Parent CSV | Rows used |
| --- | --- | --- | --- |
| 1MEL | `1melMPNN2_processed.csv` | `1melMPNN2.csv` | 435 |
| 4IDL | `4idlMPNN2_processed.csv` | `4idlMPNN2.csv` | 409 |

The loader uses only `seq` and `ddg_scaled01`. The larger Colab output files
below are provenance/raw-output files and are not read directly by
`prepare.py`.

---

## ThermoMPNN Output Files From Google Colab

The following CSV files were generated with a Google Colab notebook.

| ファイル | 説明 |
|----------|------|
| `1mel_thermompnn_data.csv` | 1MEL 用 ThermoMPNN の予測結果 |
| `4idl_thermompnn_data.csv` | 4IDL 用 ThermoMPNN の予測結果 |

**Colab notebook**
[https://colab.research.google.com/drive/1OcT4eYwzxUFNlHNPk9_5uvxGNMVg3CFA](https://colab.research.google.com/drive/1OcT4eYwzxUFNlHNPk9_5uvxGNMVg3CFA)

### ThermoMPNN raw-output format

- Columns: `Mutation`, `ddG (kcal/mol)`, `pos`, `wtAA`, `mutAA`
- Each row is one mutation-level ThermoMPNN prediction.

---

## MPNN2 Processed Tables

These files are sequence-level tables derived for the current training loader.

| ファイル | 説明 |
|----------|------|
| `1melMPNN2.csv` | 1MEL 配列と ddg |
| `4idlMPNN2.csv` | 4IDL 配列と ddg |
| `*_processed.csv` | 上記の処理版 |
| `*_processed_rand.csv` | 処理版＋`ddg_neg`, `ddg_scaled01` など追加列 |

### MPNN2 format

- `*MPNN2.csv`: `seq`, `ddg`
- `*_processed.csv`: `seq`, `ddg`, `ddg_neg`, `ddg_scaled01`
- `*_processed_rand.csv`: related randomized/diagnostic processed tables

See `data/source_labels/MANIFEST.tsv` for the cross-source catalog used to
check manuscript reproducibility.
