# Computational Source-Label Catalog

This directory is the canonical store for computational mutation-label datasets
used by the manuscript analysis. The actual CSV files live here, organized
by source:

- `fep/`
- `thermompnn/`
- `rosetta/measured/`
- `rosetta/random1000/`
- `rosetta/esm1000/`

`MANIFEST.tsv` records the processed CSV files used by `prepare.py` for the
computational mutation-label tasks. `prepare.py` reads this file directly, so
new manuscript source-label datasets should be added here rather than hard-coded
in Python. The manifest answers three questions before a model rerun:

1. Which `--ddg-source` argument selects this table?
2. Which processed CSVs are the fixed source labels?
3. Which raw or parent files document where the processed table came from?

## How the labels are used

For mutation-label source tasks, `prepare.py` loads two files per source: one
for the 1MEL-derived variant set and one for the 4IDL-derived variant set. It
uses:

- `seq` as the input sequence;
- `ddg_scaled01` as the auxiliary regression label;
- task id 1 for the 1MEL source table;
- task id 2 for the 4IDL source table.

For each random seed, source rows are sampled after loading when `--n-ddg-list`
or `--fixed-n-ddg` is specified. The sampled source rows are then split into an
internal source-label train/validation split. The experimental Tm validation set
is still used to select models for the manuscript comparisons.

## Included Source Types

| `--ddg-source` | Meaning |
| --- | --- |
| `FEP` | Free-energy perturbation mutation labels for the measured 1MEL and 4IDL variant sets. |
| `rosetta` | Rosetta mutation-effect labels for the measured variant sets. |
| `thermoMPNN` | ThermoMPNN-derived mutation-effect labels stored as MPNN2 processed tables. |
| `rosetta_random` | Uniformly random two-mutation variants scored by Rosetta. |
| `rosetta_esm` | Two-mutation variants proposed by ESM2, filtered by model likelihood, then scored by Rosetta. |

`thermompnn/*_thermompnn_data.csv` are the larger Google Colab ThermoMPNN
outputs. The current manuscript training code does not read those files
directly; it reads `thermompnn/1melMPNN2_processed.csv` and
`thermompnn/4idlMPNN2_processed.csv`.
