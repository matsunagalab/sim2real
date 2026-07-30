# Third-party notices

The MIT license in `LICENSE` covers the code and derived data written for this
study. It does not cover the third-party material listed here, which keeps the
license and the attribution requirements of its own source.

## Experimental melting temperatures

`data/nbbench/` and `data/Tm/` hold nanobody melting temperatures taken from the
NbBench `thermo-tm` dataset, released under **CC BY 4.0**.

- Dataset: <https://huggingface.co/datasets/ZYMScott/thermo-tm>
- Cite: Zhang et al., NbBench.

`data/nbbench/download.py` reproduces the local files from the published
dataset, including the deliberate reassignment of the split names described in
`README.md`. The reassignment changes which sequences are used for training,
selection, and testing; it does not change any measured value.

## Protein structures

The starting structures are Protein Data Bank entries **1MEL** (anti-lysozyme
VHH) and **4IDL** (anti-cholera-toxin VHH), distributed by the RCSB PDB under
its terms of use, which place the coordinate data in the public domain.

Files named `*_Repair.pdb` and the structures under
`data/source_labels/rosetta/` are these entries after processing by FoldX or
Rosetta. They are derived coordinates, not redistributions of those programs.

## Sequence model

The encoder is Meta AI's **ESM-2** (`facebook/esm2_t6_8M_UR50D`), released under
the **MIT license**. `models/esm2_t6_8M_vhh/` contains configuration files only;
model weights are not redistributed here.

## Simulation and modelling software

FoldX, Rosetta, NAMD, CHARMM force-field parameters, OpenMM, and Amber
force-field parameters are **not** included in this repository. The scripts under
`data/source_labels/rosetta/` and `data/foldX/` record how those programs were
invoked and what they returned, and expect a separately obtained, separately
licensed installation. FoldX and Rosetta in particular require their own
licenses, which this repository neither grants nor extends.

## Journal manuscript template

`paper/tex/bppb.cls`, `paper/tex/bppb.bst`, and `paper/tex/bppb-logo.pdf` are the
LaTeX template of *Biophysics and Physicobiology*, the journal of the Biophysical
Society of Japan, written by Motoaki Sato (ULS and Company). They are included so
that the manuscript builds as submitted, and are the property of the journal.

- Template source: <https://www.biophys.jp/dl/biophysics_and_physicobiology/BPPB_LaTeX_Template_8may2025.zip>

The journal logo is the society's mark and is not licensed for reuse outside a
manuscript prepared for that journal.
