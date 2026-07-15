# Reproduction Files

`manuscript_results.yaml` lists the fixed inputs, expected outputs, and commands
for the current paper. `scripts/reproduce_paper_results.py` reads this file and
runs the requested steps.

The three steps are:

- `reported-results`: rerun the 14 selected frozen and fine-tuned model
  configurations;
- `summaries`: rebuild compact result summaries from their `scaling.json`
  files;
- `figures`: rebuild Figs. 2 and 3, Supplementary Figs. S1 and S2, and both
  PDFs. The author-edited Fig. 1 is left unchanged.

Useful commands from the repository root are:

```bash
uv run python scripts/reproduce_paper_results.py --check-only
uv run python scripts/reproduce_paper_results.py --stage summaries --force
uv run python scripts/reproduce_paper_results.py --stage figures --force
uv run python scripts/reproduce_paper_results.py --stage all --gpus 0 --force
```

The last command requires a GPU and reruns the selected configurations. It does
not repeat the raw MD, FEP, Rosetta, or ThermoMPNN calculations, and it does not
repeat the earlier model searches. See `../REPRODUCE.md` for the full explanation.
