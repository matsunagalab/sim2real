# FEP Source Labels

This directory contains free-energy perturbation mutation labels and their
processed forms. The manuscript training code treats the processed CSV files as
fixed source labels and does not rerun FEP calculations.

## Files Used By The Current Training Code

`prepare.py` maps `--ddg-source FEP` to:

| Structure | Processed CSV | Parent CSV | Rows used |
| --- | --- | --- | --- |
| 1MEL | `fep1mel_435_processed.csv` | `fep1mel_435.csv` | 435 |
| 4IDL | `fep4idl_409_processed.csv` | `fep4idl_409.csv` | 409 |

The current loader uses only:

- `seq`: mutant amino-acid sequence;
- `ddg_scaled01`: normalized source label.

The processed files also contain `ddg` and `ddg_neg`. These columns are kept
for provenance and diagnostics, but `prepare.py` does not train directly on
them.

## Additional Processed FEP Tables

These files are present in the repository but are not wired into the current
manuscript training path:

| File | Rows | Current status |
| --- | ---: | --- |
| `fep1JTP_283_processed.csv` | 283 | Available, not used by `prepare.py` |
| `fep5E0Q_308_processed.csv` | 308 | Available, not used by `prepare.py` |
| `fep6LR7_192_processed.csv` | 192 | Available, not used by `prepare.py` |

Add these to `prepare.py::DDG_PATHS` and `data/source_labels/MANIFEST.tsv` if
they become part of a reviewer-round analysis.

## Provenance Notes

- `fep4idl_409_processed.csv` has no K1Q mutation.
- For 1MEL, the source in `vhh/PLM/csv` had missing sequence information, so
  `vhh/data/ddG` was used when preparing `fep1mel_435.csv`.
- For Gln-scan data, the `all` table was used rather than the `partial` table.
- The historical processing notebook is `data/convert_yj.ipynb`.

See `data/source_labels/MANIFEST.tsv` for the cross-source catalog used to
check manuscript reproducibility.
