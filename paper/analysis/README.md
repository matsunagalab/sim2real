# Paper Analysis Directory

This directory contains manuscript-facing analysis outputs derived from the
training results under `results/`.

## Layout

- `supplementary/tables/`: compact TSV source tables for supplementary figures.
- `supplementary/figures/`: rendered supplementary figures for review and handoff.
- `supplementary/MANIFEST.tsv`: panel-level map from each supplementary
  figure panel to its source table, upstream result/source file, and generator
  function.

The LaTeX-ready copies of rendered figures are written to
`paper/tex/figures/`.

## Fixed Inputs

The manuscript workflow treats raw MD, FEP, Rosetta, and ThermoMPNN
calculations as fixed upstream inputs. The processed tables used by training are
kept in the repository under:

- `data/nbbench/`: fixed experimental Tm train, validation, and test splits.
- `data/source_labels/`: FEP, Rosetta, and ThermoMPNN mutation-effect tables.
- `data/md/`: processed MD-derived Q-value and control-feature tables.

`data/source_labels/MANIFEST.tsv` is the source-label catalog read by
`prepare.py`; new mutation-effect source labels should be added to the manifest
instead of hard-coded into Python.

## Regeneration

To rebuild all manuscript-facing outputs downstream of those fixed inputs, run
from the repository root:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0,1,2,3,4,5,6
```

For figure-only regeneration after the result summaries already exist, run:

```bash
uv run python plot/make_outline_figures.py
uv run python plot/make_supplementary_figures.py
```

Then typeset from `paper/tex/`:

```bash
mamba create -y -p /tmp/sim2real-latex -c conda-forge tectonic
env XDG_CACHE_HOME=/tmp/tectonic-cache /tmp/sim2real-latex/bin/tectonic main.tex
```

The figure builders only read existing results and source data. They do not
launch training jobs.

For reviewer-round handoff, start from
`supplementary/MANIFEST.tsv` to identify which result summary or source table
feeds each panel.
