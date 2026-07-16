# Planned Zenodo data deposit

Supporting data for **“Transfer learning with simulated variants and calculated quantities for nanobody melting-temperature prediction.”**

- Code and processed tables: <https://github.com/matsunagalab/sim2real>

This directory is a local staging area, not a completed public record. File counts, checksums, archive names, and the total size must be regenerated immediately before upload.

The consolidated backbone-only deposit prepared from this staging area is in
`sim2real_deposit/`. Use `sim2real_deposit/README.md`, its manifests, and its
checksums as the source of truth for the assembled bundle. The component
directories described below are preparation inputs and should not be uploaded
in addition to that bundle.

## What is currently staged

| Directory | Present contents | Approximate staged size |
|---|---|---:|
| `md_trajectories_300K/` | Reduced protein-only trajectories from the heterogeneous SAbDab nanobody panel at 300 K | 8.1 GB |
| `md_trajectories_400K/` | Reduced protein-only trajectories from the heterogeneous SAbDab nanobody panel at 400 K | 8.1 GB |
| `rosetta_backrub_trajectories/` | Thinned Rosetta backrub ensembles | 4.5 GB |
| `rosetta_ddg_scans/` | Rosetta mutation-scan inputs, code, and processed score tables | 0.25 GB |
| `fep/` | Processed FEP mutation labels and representative setup material | 0.16 GB |
| `thermompnn/` | Processed ThermoMPNN labels, input structures, and the generating notebook | 4 MB |

The present staging snapshot is about 21 GB. The large solvated MD trajectories, raw FEP trajectories, FEP energy-output files, Rosetta silent decoys, and model checkpoints are not staged.

## Important missing data

The main manuscript result uses an **FEP-matched 1MEL/4IDL mutation scan** and defines each MD native-contact label from the first 40 ns of the corresponding 400 K trajectory. Those matched mutation trajectories are not in the currently staged `md_trajectories_300K/` or `md_trajectories_400K/` directories; those directories contain the earlier heterogeneous SAbDab panel.

The processed matched labels are available in the GitHub repository:

- `data/source_labels/md_fep400k/1mel_mdq_processed.csv`
- `data/source_labels/md_fep400k/4idl_mdq_processed.csv`
- `data/md/study_qvalue_fep400k_1mel.csv`
- `data/md/study_qvalue_fep400k_4idl.csv`

The current manuscript follows the second option below. Before public release,
either keep that wording or add enough files to use the first option:

1. Add the reduced first-40-ns matched trajectories, topologies, native reference frames, variant-to-file mapping, extraction settings, and checksums needed to recalculate those labels; or
2. Limit the manuscript data-availability statement to the processed matched
   labels and state clearly that the matched raw trajectories are available
   from the corresponding author. This is the wording now used in the paper.

Do not claim that the current staging area alone can reproduce the manuscript’s matched MD labels.

## Reduction choices for the present components

- The heterogeneous 300 K and 400 K MD files are protein-only, with solvent and ions removed, and contain reduced trajectory windows rather than the full simulations.
- Rosetta backrub ensembles are thinned to a subset of models.
- The FEP component keeps processed mutation labels and representative setup material, not the multi-terabyte raw trajectories or energy-output files.
- The ThermoMPNN component keeps processed outputs and generation material, not training checkpoints.
- The Rosetta mutation-scan component omits regenerable silent decoys and run logs.

These reductions must be described independently of the first-40-ns matched MD definition used by the main paper.

## Before creating the Zenodo record

- Add the matched MD material or revise the data-availability wording as described above.
- Rebuild every component `MANIFEST.tsv` and `CHECKSUMS.sha256` from the files that will actually be uploaded.
- Create one archive per component and test extraction and checksum verification on a clean machine.
- Record archive names, compressed sizes, file counts, software versions, and license information.
- Verify that the repository tag named in the record reproduces both `paper/tex/main.pdf` and `paper/tex/supplementary_main.pdf`.

Scripts used to prepare the existing staged components include `scripts/strip_md_solvent.py`, `scripts/thin_rosetta_traj.py`, `scripts/build_zenodo_manifest.py`, `scripts/build_fep_labels.py`, and `scripts/build_fep_inputs.py`. The matched MD label extraction is performed by `scripts/extract_study_qvalue.py` and must be documented with the exact deposited inputs if option 1 is chosen.
