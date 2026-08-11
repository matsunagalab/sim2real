# Reproduction Files

`manuscript_results.yaml` lists the fixed inputs, expected outputs, and commands
for the current paper. `scripts/reproduce_paper_results.py` reads this file and
runs the requested steps.

The three steps are:

- `physical-observable`: rerun the 14 selected configurations behind Fig. 3 (the
  two Tm-only baselines and the six computed observables, each frozen and
  fine-tuned, as 24-model ensembles) through `prepare.py`;
- `data-design`: rerun the 6 configurations behind Fig. 2 (the two Tm-only
  baselines and the two data designs, each frozen and fine-tuned) through
  `scripts/run_design_comparison.py`;
- `figures`: rebuild Figs. 2 and 3, Supplementary Figs. S1 and S2, and both
  PDFs. The author-edited Fig. 1 is left unchanged.

Useful commands from the repository root are:

```bash
uv run python scripts/reproduce_paper_results.py --check-only
uv run python scripts/reproduce_paper_results.py --stage figures --force
uv run python scripts/reproduce_paper_results.py --stage physical-observable --gpus 0 --force
uv run python scripts/reproduce_paper_results.py --stage data-design --gpus 0 --force
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0 --force
```

The training stages require a GPU. They do not repeat the raw MD, FEP, Rosetta,
or FoldX calculations, and they do not repeat the earlier model searches.

`results/final_*`, `results/tuned_rep/*`, and the ThermoMPNN label condition
belong to an earlier version of this study and are deliberately outside this
workflow. See `../REPRODUCE.md` for the full explanation.
