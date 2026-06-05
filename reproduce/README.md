# Reproduction Directory

This directory contains the manifest for rerunning manuscript-facing results
downstream of fixed source-label CSV files.

## Layout

```text
reproduce/
  README.md
  manuscript_results.yaml

scripts/
  reproduce_paper_results.py
```

`manuscript_results.yaml` is the source of truth for the reproducible workflow.
It records:

- fixed input files under `data/`;
- expected manuscript-facing output files;
- the ordered stages for a full downstream rerun;
- the exact commands for each stage.

`scripts/reproduce_paper_results.py` is intentionally a thin runner. It reads
the manifest, expands matrix jobs such as trajectory-window controls, and runs
the requested stage. Add new calculations to the YAML manifest
instead of burying them in Python code.

## What Is Fixed Upstream

The workflow does not rerun raw MD simulations, FEP calculations, Rosetta
calculations, or ThermoMPNN scoring. Their processed CSV outputs under `data/`
are fixed inputs. The script checks that those inputs exist before doing any
downstream work.

## Main Commands

Check fixed inputs:

```bash
uv run python scripts/reproduce_paper_results.py --stage preflight
```

Print the complete full-rerun command plan:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --force --dry-run
```

Run the full downstream rerun:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0,1,2,3,4,5,6 --force
```

Check fixed inputs and expected manuscript-facing outputs without writing:

```bash
uv run python scripts/reproduce_paper_results.py --check-only
```

Regenerate summaries from existing `results/*/scaling.json` files where the
underlying stage supports collection:

```bash
uv run python scripts/reproduce_paper_results.py --stage all --collect-only
```

Regenerate figures and the manuscript PDF from existing summaries:

```bash
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

## Adding A New Calculation

1. Add any new mutation-label dataset under `data/source_labels/` and register
   active `--ddg-source` inputs in `data/source_labels/MANIFEST.tsv`.
2. Add any other new fixed source-label CSV to `fixed_inputs` if it is required.
3. Add a new stage or action under `stages`.
4. Add the final summary or figure input to `expected_outputs`.
5. Run with `--dry-run` to check the command expansion.
6. Run the stage with `--force`.
7. Regenerate `figures` if the manuscript or supplementary figure set changes.

Use `type: prepare` for a direct `prepare.py` call, `type: script` for an
existing orchestration script, `type: command` for figure or PDF commands, and
`type: prepare_matrix` when one command pattern should be expanded over several
conditions.
