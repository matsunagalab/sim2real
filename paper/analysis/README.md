# Paper Analysis Directory

This directory contains manuscript-facing analysis outputs derived from the
training results under `results/`.

## Layout

- `supplementary/tables/`: compact TSV source tables for supplementary figures.
- `supplementary/figures/`: rendered supplementary figures for review and handoff.

The LaTeX-ready copies of rendered figures are written to
`paper/tex/figures/`.

## Regeneration

Run the figure builders from the repository root:

```bash
uv run python plot/make_outline_figures.py
uv run python plot/make_supplementary_figures.py
```

Then typeset from `paper/tex/`:

```bash
env XDG_CACHE_HOME=/tmp/tectonic-cache /tmp/sim2real-latex/bin/tectonic main.tex
```

The figure builders only read existing results and source data. They do not
launch training jobs.

