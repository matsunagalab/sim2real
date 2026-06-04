# Data Directory

This directory contains the fixed input tables used by the manuscript
reproduction workflow. The downstream training code treats the processed CSV
files as fixed source labels; raw MD, FEP, Rosetta, and ThermoMPNN calculations
are not rerun by `scripts/reproduce_paper_results.py`.

## Main Subdirectories

| Directory | Contents | Used directly by training |
| --- | --- | --- |
| `nbbench/` | Fixed experimental Tm train/validation/test splits. | Yes |
| `md/` | Processed MD-derived source-label tables. | Yes, via `--md-source ...` |
| `source_labels/` | FEP, Rosetta, ThermoMPNN, random Rosetta, and ESM2-generated Rosetta source-label datasets plus their manifest. | Yes, via `--ddg-source ...` |

## Canonical Source-Label Tables

The current training loader is `prepare.py`. For computational mutation labels,
it reads `data/source_labels/MANIFEST.tsv` and uses only two columns from each
processed CSV:

- `seq`: amino-acid sequence;
- `ddg_scaled01`: normalized source label used as the auxiliary regression
  target.

The processed mutation-label tables are catalogued in
`data/source_labels/MANIFEST.tsv`. Use that manifest when checking which file is
used for FEP, Rosetta, ThermoMPNN, random Rosetta variants, and ESM2-generated
Rosetta variants.

The processed CSVs generally also contain:

- `ddg`: source value before the shared post-processing step;
- `ddg_neg`: sign-reversed source value;
- `ddg_scaled01`: transformed and min-max scaled source value.

The historical conversion notebook is `data/convert_yj.ipynb`. It applies a
RobustScaler, Yeo-Johnson power transform, and min-max scaling to produce the
`*_processed.csv` files. For manuscript reproduction, the processed CSVs are the
fixed inputs; the notebook is provenance, not part of the automated rerun.

## Reproduction Boundary

Rerun downstream manuscript calculations with:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0,1,2,3,4,5,6 --force
```

This command starts from the fixed CSV files in this directory. It does not
recompute FEP, Rosetta, ThermoMPNN, or raw MD outputs.
