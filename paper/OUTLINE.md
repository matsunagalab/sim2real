# CSBJ Manuscript Outline

## Submission Target

- Journal: **Biophysics and Physicobiology (BPPB)** — open-access journal of the Biophysical Society of Japan (https://www.biophys.jp/biophysics_and_physicobiology.html)
- Article type: **Regular Article** (biophysics-oriented framing). Official templates exist (download the Regular Article template before final formatting).
- Strategy: concise biophysics Research Article; foreground the physical interpretation (how the physical observable maps to stability transfer).

**Confirmed BPPB format (from Instruction for Authors, biophysics_and_physicobiology03.html, Jan 2025):**
- Section order: **Introduction → Materials and Methods → Results → Discussion (or Results and discussion) → Conclusion → Conflict of interest → Author contributions → Data availability → Acknowledgements → References.** (Methods after Intro, NOT last.)
- Page 1: title, authors, affiliations, addresses, **abstract (≤250 words, no references)**, **≤5 keywords**, **Significance statement (<100 words)**.
- **Graphical abstract required** (1 figure, color or mono, 300 dpi, TIFF/PNG/JPEG, caption <100 words).
- **References: NUMBERED, brackets `[1,3,5-8]`**, Index Medicus/MEDLINE abbreviated journal titles, DOI as URL. (Change from CSBJ author–year: `\citep`→numbered `\cite`, swap bibliography style.)
- Figures: 300 dpi, TIFF/PNG/JPEG (gray/color).
- Declarations required: Conflict of interest; Author contributions; Data availability (J-STAGE Data encouraged). Funding NOT explicitly required. AI-use: describe in Acknowledgements only if substantial.
- Word/page/figure-count limits: not stated by the journal.

Format TODOs (LaTeX): switch bib to numbered style; add Significance statement + Graphical abstract; add Conclusion section; split declarations into their own sections; regenerate `paper/AUTHOR_GUIDELINES.md` from BPPB instructions; consider the official BPPB template.

SECTION_ORDER: abstract -> introduction -> methods -> results -> discussion -> conclusion -> acknowledgments
(supplementary after references; declarations = conflict_of_interest, author_contributions, data_availability as their own blocks per BPPB.)

## Author And Submission Metadata

Author order:

1. Taihei Murakami
2. Kentaro Sasaki
3. Soichiro Oda
4. Kazuma Okada
5. Yasuhiro Matsunaga

Affiliations:

- `1`: RIKEN Center for Computational Science, Kobe, Japan
- `2`: Saitama University, Saitama, Japan

Author-affiliation mapping:

- Taihei Murakami: `2`
- Kentaro Sasaki: `2`
- Soichiro Oda: `2`
- Kazuma Okada: `2`
- Yasuhiro Matsunaga: `1,2`

Equal contribution:

- Taihei Murakami and Kentaro Sasaki contributed equally to this work.

Corresponding author:

- Yasuhiro Matsunaga
- Email: `ymatsunaga@riken.jp`

ORCID:

- Yasuhiro Matsunaga: `0000-0003-2872-3908`

Student ORCID IDs are not treated as required placeholders unless the authors already have them or the submission system requires them at upload.

## Working Title Options

Preferred:

**Data design and physical observable govern the transfer of molecular simulation to nanobody thermal-stability prediction**

Alternatives:

- **When does molecular simulation transfer to experimental protein stability? Two design axes for low-data nanobody Tm prediction**
- **Matched mutation scans let molecular-dynamics stability labels transfer to nanobody melting-temperature prediction**
- **From free energies to native contacts: how the physical observable sets the depth of simulation-to-experiment transfer**

Rationale (updated story): the earlier reading was "simulation transfers only for FEP; a
molecular-dynamics native-contact label does not." The controlled experiments here overturn the
naive part: an MD native-contact stability label **does** transfer once its data design is matched to
the target (a mutation scan on the same scaffold, removing the sequence-length confound of a diverse
screen). What still differs is the **depth** of transfer, set by the physical observable — alchemical
free energy (FEP) reshapes the sequence representation and transfers even with a fine-tuned encoder,
whereas the native-contact label only helps a fixed representation. The title should foreground these
two design axes (data design + physical observable), not a single method.

## Central Message

The broad question is how simulation data should be used to improve experimental protein-property prediction when the simulated quantity is not identical to the experimental target.

This manuscript studies one concrete case of that question:

**Can simulation-derived labels be used to improve low-data nanobody Tm prediction, even when those labels measure quantities other than Tm?**

The answer developed in this case study is:

- Train Tm prediction as the target task.
- Use computational labels as source tasks sharing the sequence representation.
- Select models using the experimental validation set.
- Evaluate all claims on a held-out experimental Tm test set.
- Compare source labels by paired errors on the same test examples.

The main result is organized along **two design axes** that together govern whether and how a
simulation-derived label transfers to the experimental phenotype:

1. **Data design (does it transfer at all).** The same physical observable — a molecular-dynamics
   native-contact stability label — fails to help when computed over a *diverse* screen of different
   nanobodies (its signal is confounded with sequence length), but **does** improve held-out Tm once
   it is computed over a *mutation scan on the same scaffolds used for FEP* (single-residue
   perturbations, constant length, no length confound). So matching the source's sequence
   neighborhood to the target — the same mutation-scan design as the free-energy labels — is what
   turns a null result into a real one. This is a controlled, confound-isolated finding: it is the
   data design, not the label arithmetic (a per-mutant Q vs a WT-referenced ΔQ are equivalent after
   min-max scaling).

2. **Physical observable (how deep the transfer goes).** With a matched design, both label families
   transfer, but to different depths. Alchemical mutation free energy (FEP) reshapes the shared
   sequence representation and improves Tm even when the encoder is fine-tuned (the deeper regime).
   The native-contact stability label helps only when the representation is held fixed (frozen
   encoder); it does not have the leverage to reshape the encoder toward the Tm phenotype. So the
   physical content of the label — how directly it encodes the mutation's effect on stability — sets
   the *depth* of transfer.

Supporting comparisons show the other structure-based scores (plain Rosetta, ThermoMPNN, and Rosetta
on ESM2-proposed or random variant sets) are weak-to-null under matched tuning, and controls rule out
alternatives (encoder size does not substitute for a matched physical label; charge-change finite-size
corrections are negligible for the ML labels).

The practical message is therefore a **design rule for simulation datasets**: match the source's
sequence design to the target, and choose the physical observable for its alignment with the
phenotype (free energies reshape the representation; coarse structural summaries only refine a fixed
one). Sparse experimental Tm labels anchor the absolute stability scale, while mutation-scan
simulation labels supply local stability-change directions over sequence perturbations.

## Reader Entry And Terminology

The manuscript must be readable before the reader knows the local data names or
method abbreviations. The abstract and opening Results paragraphs should be
self-contained.

Reader-facing order:

1. Start with the experimental problem: nanobody thermal stability is important,
   Tm is the experimental readout, and experimental labels are scarce.
2. Explain the modeling problem: simulations and structure-based calculations
   can produce related labels, but those labels are not Tm measurements.
3. Introduce transfer learning as the mechanism for using those related labels.
4. Only then introduce specific tools or data names, with definitions at first
   use.

Terminology rules:

- Do not open a section with unexplained names such as NbBench, FEP, Rosetta,
  ThermoMPNN, ESM2, or MD.
- Prefer the physical meaning first: "public nanobody Tm benchmark" before
  "NbBench"; "mutation free-energy labels from alchemical free-energy
  perturbation (FEP)" before "FEP"; "structure-based scores" before
  "Rosetta"; "stability scores from ThermoMPNN" before "ThermoMPNN";
  "pretrained protein language model" before "ESM2"; "MD-derived Q-value
  summarizing native-contact persistence" before "MD Q-value".
- In figures, use reader-facing labels such as "Tm labels only", "mutation
  free energy", "Rosetta mutation score", "ThermoMPNN stability score",
  "ESM2-proposed variants scored by Rosetta", and "MD Q-value".

Main-figure story adjustment:

- Fig. 3 should not stop at raw MD Q-value failure. It should show selected
  descriptor controls on the held-out Tm test set, because this directly
  addresses how MD-derived information is turned into a useful source label.
- Supplementary figures should support this panel by showing additional
  candidate screens, validation-to-test behavior for carried-forward
  descriptors, source-label distributions, and descriptor correlations.

## CSBJ Fit

This manuscript fits CSBJ because it combines:

- computational biology;
- structure- and physics-informed modeling;
- protein engineering;
- machine learning under limited experimental data;
- interpretable comparison of simulation-derived labels.

The paper should be framed as a scientific Research Article. It should not be framed as a software article, benchmark-only report, or general-purpose method paper.

## Introduction Logic From The Materials Sim2Real Literature

The Introduction should explicitly use the argument structure of Minami et al. (npj Computational Materials, 2025) as the closest conceptual precedent, while making clear that this manuscript transfers the idea from materials informatics to biomolecular stability prediction.

Minami et al. develop the following logic:

1. Data-driven prediction can accelerate discovery, but experimental property data are scarce because physical experiments are slow, expensive, multi-step, and often not openly shared.
2. High-throughput computational experiments can generate much larger source datasets, including first-principles calculations, quantum chemistry, and molecular dynamics simulations.
3. Transfer learning or simulation-to-real learning can integrate large simulation datasets with smaller experimental datasets.
4. The source and target domains are separated by a domain gap, so it is not obvious that adding more simulation data will improve real-world prediction.
5. Scaling behavior provides a quantitative way to evaluate the usefulness of computational databases for downstream experimental tasks.
6. The observed scaling can guide data-production protocols, estimate how much simulation data is needed, and quantify when simulation data has practical value.

This manuscript should mirror that logic, but with a biological case:

1. Protein engineering also faces scarce experimental property labels.
2. Biomolecular simulations and physics-based calculations can generate many more labels than experiments.
3. Unlike many materials examples, the source labels here are often not the same property as the target. In the main case, the experimental target is Tm, while the most useful source labels are mutation free energies.
4. The paper should first ask which simulated physical quantity transfers to the experimental target, then discuss whether useful source labels show label-count behavior.
5. Nanobody Tm prediction is the concrete case study for this broader question.
6. The main result extends the Sim2Real argument: simulation data are useful when the source label encodes transferable physical content, but not every simulation-derived label helps.

The Introduction should not overclaim that this paper establishes a universal scaling law in biomolecular Sim2Real learning. The FEP label-count sweep is useful and should be shown, but the stronger claim is source-dependent transfer rather than a clean power-law.

### Citation Plan Inspired By Minami et al.

Core citation:

- Minami et al., "Scaling law of Sim2Real transfer learning in expanding computational materials databases for real-world predictions", npj Computational Materials, 2025. Use this as the main conceptual precedent.

Materials and simulation-data precedent to cite selectively:

- Yamada et al., 2019: little-data materials property prediction with transfer learning.
- Wu et al., 2019: polymer thermal conductivity prediction and molecular design.
- Aoki et al., 2023: multitask learning combining quantum-chemistry and experimental polymer-solvent miscibility data.
- Ju et al., 2021: transfer learning for lattice thermal conductivity with small target data.
- Mikami et al., 2023: theoretical/empirical Sim2Real scaling law precedent.

Computational database background to cite only if needed:

- Materials Project, AFLOW, NOMAD, OQMD, QM9, and RadonPy as examples of large-scale computational data resources.
- Do not overload the Introduction with all database citations unless the final text needs them; one compact sentence can establish the materials-informatics precedent.

Bridge citations to add outside the Minami reference chain:

- Protein language models and ESM2.
- Nanobody thermostability data source.
- FEP and Rosetta mutation-effect calculations.
- ThermoMPNN or other protein-stability predictors used as source labels.

## Related Nanobody Tm Prediction Work From Murakami et al.

The manuscript `paper/refs/murakami.pdf` is a closely related in-house prior manuscript under review. It should be used as background for the Tm-prediction side of the Introduction and Discussion. Because it is under review, cite it only if the submission policy and final status allow it; otherwise, describe the relevant ideas through published literature and keep Murakami et al. as internal guidance.

Relevant points to import into this manuscript's logic:

1. Fine-tuning protein language models on labeled nanobody thermostability data can substantially improve Tm prediction relative to using pretrained embeddings with only a regression head.
2. For nanobody thermostability, simply increasing ESM2 model size did not improve prediction accuracy in that prior work. The 8M ESM2 model with supervised fine-tuning performed strongly, while larger ESM2 models did not provide a simple scaling benefit.
3. Pretrained ESM2 embeddings did not show clear Tm-correlated structure, whereas supervised fine-tuning produced representations correlated with Tm.
4. Interpretable features from the fine-tuned model mapped to known nanobody stability determinants such as VHH-tetrad residues and disulfide bonds, as well as candidate stabilizing residues supported by FEP calculations.
5. These findings motivate the present paper's design: if model-size scaling alone is not enough for Tm prediction, the next question is whether physically meaningful simulation-derived labels can provide additional supervision.

How to position the present manuscript relative to Murakami et al.:

- Murakami et al. asks: what does a fine-tuned PLM learn for nanobody Tm prediction?
- The present manuscript asks: how can simulation-derived labels be used to improve Tm prediction beyond Tm-only learning?
- Murakami et al. provides the Tm-only and PLM-fine-tuning context.
- The present manuscript adds simulation-informed transfer learning and source-label comparison.
- The ESM2 size result in this manuscript should be interpreted consistently with Murakami et al.: larger ESM2 encoders do not automatically solve the Tm data-scarcity problem.

Citation plan from Murakami et al.:

- Protein language models: Rives et al. 2021, Elnaggar et al. 2022, Lin et al. 2023, Hayes et al. 2025.
- Protein thermostability prediction: Blaabjerg et al. 2023, Li et al. 2023, Alvarez and Dean 2024, Chu et al. 2024, Schmirler et al. 2024.
- Nanobody background: Muyldermans 2013, Muyldermans 2021, Alexander and Leong 2024.
- Nanobody thermostability and MD: Akiba et al. 2019, Ikeuchi et al. 2021, Bekker et al. 2019.
- Nanobody datasets and benchmarks: Valdes-Tresanco et al. 2023, Zhang and Tsuda 2025, Deszynski et al. 2022 if INDI or nanobody sequence resources are discussed.
- Antibody/nanobody language models: Leem et al. 2022, Barton et al. 2024, Tsuruta et al. 2024.
- FEP and simulation methods: Bennett 1976, Phillips et al. 2020, Best et al. 2012, Koenekoop et al. 2025, plus specific tools used in this manuscript.

### Curated Citation Use For This Manuscript

Use the Murakami reference list as the main source for Tm-prediction and nanobody citations. Suggested priority:

High-priority citations for Introduction:

- Rives et al. 2021: PLMs learn broad protein representations.
- Lin et al. 2023: ESM2 foundation model.
- Blaabjerg et al. 2023: rapid protein stability prediction using deep learning representations.
- Li et al. 2023: DeepTM, sequence-based melting-temperature prediction.
- Alvarez and Dean 2024: TEMPRO, nanobody melting-temperature estimation from protein embeddings.
- Valdes-Tresanco et al. 2023: NbThermo, nanobody thermostability database.
- Zhang and Tsuda 2025: NbBench, nanobody-property benchmark including thermostability.
- Muyldermans 2013 or 2021: nanobody/VHH background.
- Bekker et al. 2019: MD estimation of single-domain antibody thermal stability.

High-priority citations for Methods:

- Lin et al. 2023: ESM2 encoder.
- Valdes-Tresanco et al. 2023 and/or Zhang and Tsuda 2025: experimental Tm data source, depending on the actual dataset used.
- Bennett 1976: BAR/free-energy estimation if used.
- Phillips et al. 2020: NAMD if used.
- Best et al. 2012: CHARMM36 if used.
- Koenekoop et al. 2025: modern hybrid-topology protein mutation FEP precedent, if relevant to the FEP setup.

Moderate-priority citations, use if the text needs them:

- Elnaggar et al. 2022 and Hayes et al. 2025 for broader PLM context.
- Chu et al. 2024, Schmirler et al. 2024, Lafita et al. 2024, Wang et al. 2025 for supervised fine-tuning of PLMs.
- Leem et al. 2022, Barton et al. 2024, Tsuruta et al. 2024 for antibody/nanobody-specific language models.
- Akiba et al. 2019 and Ikeuchi et al. 2021 for experimental/biophysical nanobody thermostability studies.
- Deszynski et al. 2022 for large nanobody sequence resources only if INDI or related background is discussed.

Avoid in the main Introduction unless needed:

- Sparse-autoencoder and interpretability literature from Murakami et al. The present paper is not primarily about mechanistic interpretability.
- AlphaFold 3 and structural interpretation citations unless specific structures or FEP setup require them.
- Optuna and other implementation citations in the Introduction. Put them in Methods if used.

## Contributions To Emphasize

1. A case study of how simulation data can be used for experimental protein-property prediction when simulated labels are related to, but not identical to, the target phenotype.
2. A target-centered multi-task transfer-learning framework for using computational labels in low-data Tm prediction.
3. A controlled comparison of multiple computational label types under the same experimental split and model-selection rule.
4. Evidence that mutation free-energy labels improve experimental Tm prediction even though they are not Tm measurements.
5. A boundary condition: structural-dynamics labels do not automatically transfer to Tm prediction.
6. A selectivity result: under matched per-source tuning, only mutation free-energy (FEP, both regimes) and the matched-scan MD native-contact label (frozen) robustly transfer; Rosetta-family scores — plain Rosetta, ThermoMPNN, and Rosetta scores on ESM2-proposed or random variant sets — are weak-to-null. No reinforcement-learning / closed-loop design claim is made.

## Manuscript Architecture

### Abstract

Target length: 200 to 250 words.

Required moves:

1. State the broad challenge: simulations can generate large amounts of data, but using them to improve experimental protein-property prediction is nontrivial because simulated labels often do not match the experimental target.
2. Introduce nanobody Tm prediction as a concrete low-data case.
3. State that computational calculations can generate source labels for variants, but these labels measure quantities other than Tm.
4. Introduce the multi-task transfer-learning framework.
5. State the controlled evaluation design: shared experimental split, validation-set model selection, held-out Tm test set, paired comparison.
6. Report the main number: FEP labels improve held-out Tm prediction from MAE 6.61 to 6.26 deg C, a paired improvement of 0.35 deg C.
7. State source dependence: under matched tuning only FEP (both regimes) and the FEP-matched MD native-contact label (frozen) robustly help; Rosetta-family scores are weak-to-null.
8. End with the interpretation: mutation free-energy labels provide local stability-change information complementary to sparse absolute Tm measurements.

### Introduction

Goal: introduce the practical problem before introducing the thermodynamic interpretation.

Paragraph plan:

1. Start with the materials-informatics precedent following Minami et al.: machine learning can accelerate property prediction, but experimental labels are scarce because experiments are costly, multi-step, and not always openly shared.
2. Explain the response in materials science: high-throughput computational experiments and databases create large source datasets, and Sim2Real transfer learning uses those source data to improve limited experimental target tasks.
3. State the unresolved issue emphasized by Minami et al.: because simulations and experiments are separated by a domain gap, the value of simulation data must be evaluated by downstream real-world prediction, including scaling behavior as computational data increase.
4. Transfer this question to biomolecular design: protein engineering also has scarce experimental property labels, while simulations and physics-based calculations can generate many labels for variants.
5. Introduce the key additional difficulty in this paper: for biomolecules, the simulated label may differ from the experimental target not only by domain gap but also by physical quantity. In this case, Tm is the target, while FEP supplies mutation free-energy labels.
6. Present nanobody thermal stability as the concrete case: Tm is important for engineering, developability, storage, and downstream screening, but experimental Tm data are limited.
7. Acknowledge high-throughput experimental stability data: Tsuboyama et al. introduced the Nature 2023 mega-scale folding-stability dataset using cDNA-display proteolysis, with approximately 776,000 high-quality measurements for 40 to 72 amino-acid domains.
8. Explain why this does not solve the present problem directly: nanobody VHH domains are longer than the small domains covered by that dataset, and direct large-scale experimental Delta G measurements are not yet available at that nanobody length scale.
9. Cite the separate ESMtherm study by Chu et al. 2024: fine-tuning on the mega-scale dataset works well for small domains but transferred poorly to larger 177 to 501-residue proteins, motivating target-specific supervision for longer scaffolds.
10. Protein language models provide useful representations, and prior nanobody Tm work shows that supervised fine-tuning is important for extracting Tm-relevant representations.
11. However, that prior work also suggests that simply increasing ESM2 size does not automatically improve nanobody Tm prediction, motivating information sources beyond model-size scaling.
12. We use a shared-encoder multi-task transfer-learning framework and evaluate all claims on held-out experimental Tm examples.
13. We compare mutation free-energy labels, Rosetta-scored variant proposal labels, and an MD-derived structural-dynamics label.
14. We find that FEP-derived mutation free-energy labels most clearly improve Tm prediction, supporting the view that relative stability-change information complements sparse absolute Tm anchors.

Do not open the Introduction with a conceptual discussion of Tm versus ΔΔG. That interpretation belongs near the end.

### Materials And Methods

CSBJ encourages the first part of Methods to describe study design. Use a first subsection titled:

**Experimental and technical design**

Subsection plan:

1. **Experimental and technical design**
   - Study overview.
   - Broad question: how to use simulation data for experimental protein-property prediction when source labels do not equal the target phenotype.
   - Case study: low-data nanobody Tm prediction.
   - Experimental Tm is the target task.
   - Computational labels are source tasks.
   - All final claims use the same held-out experimental Tm test set.
   - Fig. 1 summarizes the design.

2. **Experimental Tm dataset**
   - Dataset origin.
   - Nanobody sequence inclusion criteria.
   - Tm units and preprocessing.
   - Train/validation/test split: train 57, validation 114, test 396.
   - Any sequence-level grouping or leakage prevention.

3. **Computational source labels**
   - FEP mutation free-energy labels.
   - Rosetta mutation-effect labels.
   - ThermoMPNN mutation-effect labels.
   - ESM2-proposed variants scored by Rosetta.
   - Random variants scored by Rosetta.
   - MD-derived Q-value labels.
   - For each source, report label definition, sign convention, number of labels, and whether labels are mutation-relative or sequence-level.

4. **Generated and random variant sets**
   - How ESM2-proposed variants were produced.
   - How random variants were produced.
   - How Rosetta scoring was applied to both sets.
   - State that ESM2-proposed-vs-random superiority is exploratory and not the main claim.

5. **Model architecture**
   - ESM2 sequence encoder.
   - Tm prediction head.
   - Source-label prediction head.
   - Shared representation.
   - Fine-tuned encoder and frozen-encoder control.
   - ESM2 size controls.
   - Link to prior Murakami et al. architecture: the present model keeps the same basic PLM-to-Tm prediction idea but adds source-task supervision.

6. **Training and model selection**
   - Tm-only baseline.
   - Multi-task transfer-learning objective.
   - Hyperparameter search space.
   - Model selection using experimental validation-set Tm performance.
   - Seed handling.
   - Early stopping rule.
   - This subsection must be explicit enough to avoid reviewer concern about unfair source-task selection.

7. **Evaluation and statistical analysis**
   - Held-out Tm test MAE.
   - Confidence intervals.
   - Paired bootstrap on per-example absolute errors.
   - Validation-set versus test-set comparison.
   - Label-count sweep analysis.
   - Software versions and hardware.

8. **Data and code availability**
   - Processed data and figure-generation scripts.
   - Availability of raw simulation data or reason for restricted/large-file availability.
   - Archive/DOI target if available.

### Results

The Results should follow the figures and keep interpretation controlled.

**UPDATED RESULTS ARC (two-axis story; replaces the earlier "MD Q-value is a negative control" arc).**
The old arc was: (1) framework; (2) source comparison with FEP positive and MD Q-value negative;
(3) MD descriptor choice; (4) structure-based + LM-proposed variants. The new arc is:
- **R1 — Framework** (Fig. 1): unchanged.
- **R2 — Which computational labels transfer** (Fig. 2): FEP best; **the FEP-matched MD
  native-contact label also transfers (≈ FEP frozen)**; Rosetta/ThermoMPNN intermediate; count sweeps.
- **R3 — Data-design axis** (Fig. 3): the *same* MD observable is null as a diverse screen
  (length-confounded) but transfers as an FEP-matched mutation scan → matched sequence design, not
  the ΔQ-vs-Q arithmetic (equivalent after min-max), is what makes MD transfer.
- **R4 — Physical-observable axis / depth** (Fig. 4): with matched design, FEP transfers in both
  encoder regimes but the MD native-contact label only with a frozen encoder → the physical
  observable sets the depth of transfer (whether it can reshape the encoder). Under tuning the
  Rosetta-family scores (plain Rosetta, ThermoMPNN, and the two variant-set sources) are weak-to-null;
  they appear only as menu comparators (Fig 2b) with NO reinforcement-learning / design-loop claim.
- **R5 — Controls**: encoder size does not substitute; charge-change corrections negligible;
  min-max/clip and extreme-value handling (do NOT clip; the unmeasurable extreme buried-charge ΔΔG
  carry disproportionate transfer signal).
The detailed subsection prose below is being rewritten to this arc.

#### Result 1: A framework for using simulation labels in experimental protein-property prediction

Display: Fig. 1, introduced before the Results section and used as the
framework reference for the first Results subsection.

Key points:

- The general problem is how to exploit simulation data when source labels are related to, but not identical to, the experimental target.
- Nanobody Tm prediction is the concrete target-task case study.
- Tm prediction is the target task.
- Computational labels are source tasks.
- Source labels are not used as Tm replacements.
- The final evaluation is held-out experimental Tm prediction.

Main claim:

The design permits computational labels to influence representation learning while preserving target-task evaluation.

#### Result 2: Source-label transfer depends on label content, model size, and encoder adaptation

Display: Fig. 2.

Key points:

- Experimental Tm-label count response establishes the low-data regime.
- FEP labels improve best held-out Tm performance when the full source label set is used.
- The FEP curve is not perfectly monotonic; do not claim a clean power law.
- The MD-derived Q-value does not show a reproducible improvement over Tm-only training.
- ESM2 size controls compare 8M, 35M, and 650M encoders.
- Larger ESM2 encoders do not improve absolute performance in this small-Tm-data setting.
- Frozen-encoder and hot-encoder controls show that FEP transfers in both
  regimes, with the largest gain when the encoder is updated.

Main claim:

The amount of source-label data matters, but data quantity and model size alone
do not explain improvement; the physical source label and encoder adaptation
matter.

#### Result 3: All-atom source labels depend on the simulated quantity

Display: Fig. 3.

Key numbers:

| condition | test MAE |
|---|---:|
| Tm labels only reference | 6.6185 |
| FEP mutation free-energy reference | 6.2611 |
| 300 K disulfide-distance fluctuation | 6.4827 |
| sequence CDR3 length | 6.5183 |
| 400 K Q-value slope | 6.6555 |
| 400 K MD Q-value | 6.6714 |

Key points:

- Fig. 3 should focus on how all-atom simulation information is converted into
  source labels for Tm prediction.
- Panel a should plot held-out test MAE only. It should include Tm labels only,
  FEP mutation free energy, selected 300 K and 400 K MD-derived descriptors,
  and the sequence-only CDR3-length control.
- FEP is a plotted comparator, not a vertical reference line, and uses the same
  green color as Fig. 2.
- The terminal 400 K Q-value does not improve the held-out Tm endpoint, but
  other descriptors move closer to the useful regime.
- Panel b should compare normalized source-label distributions for matched
  300 K and 400 K trajectory descriptors.

Main claim:

The useful source signal depends on the simulated physical quantity and the
descriptor used to summarize it. In this screen, FEP remains the strongest
all-atom source label, while MD-derived labels improve only when the descriptor
captures transferable structural variation.

#### Result 4: Structure-based labels and proposal-set scores are weaker source signals

Display: Fig. 4.

Key points:

- Rosetta mutation scores, ThermoMPNN stability scores, and Rosetta scores on
  proposal/control variants are compared outside the all-atom FEP-versus-MD
  figure.
- FEP should also be included in Fig. 4 as a comparator, so readers can see the
  weaker structure-based source signals relative to the main positive source.
- Two additional Rosetta-scored variant sets (ESM2-proposed and random variants)
  are shown only as ordinary comparators in the source menu (Fig 2).
- These source labels are context; they are not a quantitative claim.

Main claim:

Non-FEP structure-based labels provide weak-to-null source signals under matched
per-source tuning.

#### Result 5: The Rosetta-family scores (incl. the two variant-set sources) are weak-to-null

Display: Fig. 2b and Fig. 4a,b.

Key numbers (tuned, ΔMAE vs Tm-only @n=320; frozen / hot):

| source | frozen ΔMAE | hot ΔMAE |
|---|---:|---:|
| Rosetta mutation score | +0.002 | +0.078 |
| ThermoMPNN stability score | −0.141 (ns) | +0.073 |
| random variants + Rosetta | −0.013 | +0.144 |
| ESM2-proposed variants + Rosetta | +0.083 | +0.411* (worse) |

Main claim:

Under rigorous per-source tuning in the low-data regime, the Rosetta-family scores
do not robustly improve Tm prediction; ThermoMPNN gives only a weak (non-significant)
frozen gain. **We make NO reinforcement-learning / closed-loop design claim** — under
tuning the ESM2-proposed variant set does not beat random, so the earlier
"design-loop bridge" framing is dropped (user decision 2026-07-04). The two
variant-set sources appear purely as menu comparators.

#### Result 6: Mutation free-energy labels complement sparse absolute Tm anchors

Display: Discussion-level interpretation, supported by Figs. 2 and 3.

Key points:

- Tm provides sparse absolute stability anchors.
- Mutation free-energy labels provide local sequence-perturbation information.
- FEP works because its label is close to the relevant thermodynamic perturbation.
- The MD-derived Q-value provides a boundary condition: native-contact persistence alone did not transfer in this setting.

Main claim:

The useful source labels encode stability changes relevant to the target phenotype.

### Discussion

Paragraph plan:

1. Restate the main advance: a target-centered way to incorporate simulation-derived labels into experimental protein-property prediction, demonstrated in low-data nanobody Tm prediction.
2. Emphasize the main result: FEP mutation free-energy labels produce the clearest improvement.
3. Interpret why this matters: relative mutation free energies complement sparse absolute Tm labels.
4. Discuss source dependence: not every simulation-derived or physics-based label transfers.
5. Discuss encoder adaptation and model size: limited adaptation helps; larger language models were not sufficient in this low-data regime.
6. Discuss the Rosetta-family scores (plain Rosetta, ThermoMPNN, and the two variant-set sources) as weak-to-null under tuning; make no reinforcement-learning / closed-loop design claim (the ESM2-proposed variant set does not beat random).
7. Limitations:
   - small experimental Tm train set;
   - nanobody-specific dataset;
   - small number of exact NbBench sequence overlaps in the MD source table;
   - no new experimental validation of high-Tm candidates;
   - raw simulation data may be large and difficult to deposit fully.
8. Outlook:
   - matched-design simulation labels (both alchemical and, for a fixed representation, structural) as auxiliary supervision for other low-data protein properties;
   - the present paper stops at supervised evidence; no design-loop / reinforcement-learning claim is made.
9. Concluding paragraph:
   - The key practical lesson is to choose computational labels by their transferable physical content, not by availability alone.

### Acknowledgments And Required Statements

This section must include or be followed by the required CSBJ statements:

- Funding.
- Author contributions.
- Competing interests.
- Data availability.
- Code availability.
- AI-use disclosure, if used.
- Any third-party figure or asset permissions.

Draft statement placeholders:

- Data availability: Processed data required to reproduce the main and supplementary figures will be deposited in Zenodo at `ZENODO_DATA_DOI_PLACEHOLDER`. Raw simulation trajectories are large and will be made available at `RAW_DATA_LOCATION_OR_REQUEST_POLICY_PLACEHOLDER`.
- Code availability: Analysis, training, and figure-generation code will be available on GitHub at `GITHUB_REPOSITORY_URL_PLACEHOLDER`; an archival release will be deposited in Zenodo at `ZENODO_CODE_DOI_PLACEHOLDER`.
- Competing interests: Use the statement in `paper/tex/sections/acknowledgments.tex`.
- Author contributions: Use the CRediT-style draft in `paper/tex/sections/acknowledgments.tex` and confirm before submission.
- Funding: Use the JSPS KAKENHI and Fugaku support statement in `paper/tex/sections/acknowledgments.tex` and confirm grant details before submission.
- AI-use disclosure: Use the draft disclosure in `paper/tex/sections/acknowledgments.tex` and adjust to the journal's final submission form.
- Third-party permissions: Confirm that all figures are original or document any required permissions before submission.

Known placeholders still to fill later:

- Final Zenodo DOI for data.
- Final GitHub URL and Zenodo DOI for code.
- Suggested reviewers for submission.

## Fig. Plan

### Fig. 1. Multi-task transfer-learning framework for using simulation data in experimental Tm prediction

Purpose: introduce the general problem of using simulation labels for an experimental target, then instantiate it as nanobody Tm prediction. Do not introduce the Tm/ΔΔG interpretation here.

Placement: show this figure before the Results section so that the transfer-learning
architecture is visible before the source-label comparisons.

Design (figure_1_concept_protocol_v2.png, single-panel architecture schematic):

- Two input streams: experimental sequence data (left) and computational sequence data (right).
- Shared ESM2 protein language model encoder (flame/snowflake = fine-tuned hot vs. frozen) producing per-sequence embeddings.
- Shared multilayer perceptron, then a split into a Tm head (→ predicted experimental Tm) and a source head (→ predicted computational scores: ΔΔG / Q-value).
- Caption carries the explanatory text; no specific layer dimensions are stated in prose.

CSBJ figure rules:

- No in-panel title.
- Put explanatory text in the legend.

TODO (figure image): the placed v2 PNG shows the last shared layer as Linear(64) and the heads as "Linear(32)". The actual code (train.py) and Methods/Supplementary use shared 256→128→32 with Tm/source heads mapping the 32-dim representation to a scalar. The figure image needs correcting (64 → 32; head boxes should not read as 32-unit layers). Caption deliberately omits these numbers so the prose is not contradicted in the meantime.

### Fig. 2. Overview of source-label transfer in the low-data Tm setting

Purpose: show the overview controls before the detailed all-atom and lower-cost
source-label comparisons.

Panels:

- (a) Experimental Tm-label, FEP-label, and MD-derived Q-value count-sweep curves
  plotted together.
- (b) Best points within the label-count sweeps, replotted as interval
  estimates.
- (c) ESM2 encoder-size controls for Tm-only and FEP-assisted training.
- (d) Paired MAE changes for FEP and MD Q-value labels relative to the
  encoder-matched Tm-only reference, comparing frozen and hot encoders.

Claims (UPDATED for the two-axis story):

- Experimental Tm labels show the expected low-data count response.
- FEP reaches the best held-out Tm MAE and improves in both encoder regimes.
- **The FEP-matched MD native-contact label also improves held-out Tm — comparable
  to FEP with a frozen encoder** — so, with matched design, an MD stability label
  transfers (this replaces the earlier "MD Q-value does not help" claim).
- Other structure-based scores (plain Rosetta, ThermoMPNN, and Rosetta on ESM2-proposed
  or random variant sets) are weak-to-null under matched tuning (ThermoMPNN gives only a
  weak, non-significant frozen gain).
- Larger ESM2 encoders do not explain or substitute for the physical-label gain.
- Avoid claiming a strict monotonic law; report paired ΔMAE with bootstrap CIs.

(Panel (a)/(d) reader labels now include "MD native-contact stability (matched scan)"
alongside "mutation free energy".)

### Fig. 3. Data-design axis: matching the source's sequence design lets MD stability labels transfer

Purpose: the first design axis — show that whether an MD native-contact label transfers is
controlled by its **data design**, not by the observable arithmetic. The identical physical
observable fails as a diverse-nanobody screen (length-confounded) but transfers as an FEP-matched
mutation scan.

Panels:

- (a) Held-out Tm MAE for the MD native-contact label computed two ways: over a **diverse
  nanobody screen** (the earlier setup; no improvement) vs over the **FEP-matched mutation scan**
  on the same 1mel/4idl scaffolds (improves, ≈ FEP frozen). Tm-only and FEP shown as references.
- (b) The confound made explicit: source-label value vs sequence length — the diverse screen has
  a length spread and a nonzero label–length correlation, whereas the matched scan is constant
  length (correlation undefined / removed). (Provenance/data: `data/md/nanobody_qvalue_400K.csv`
  vs `data/source_labels/md_fep400k/`.)
- (c) Label-count scaling of the matched-scan MD label with paired ΔMAE(n) and bootstrap CI,
  showing the improvement grows with matched labels (frozen).

Claims:

- The same native-contact observable is a null result as a diverse screen and a real transfer
  signal as a matched mutation scan → **data design (matched sequence neighborhood), not the
  ΔQ-vs-Q arithmetic (equivalent after min-max), drives it.**
- The earlier diverse-screen label is confounded with sequence length; the matched scan removes it.
- Under matched design the MD label scales with label count (frozen).

Note: numbers to be finalized from the tuned re-run (`MD_FEP400K`, source_screen HPO, hot+frozen).

### Fig. 4. Physical-observable axis: the label's physical content sets the depth of transfer

Purpose: the second design axis — with data design matched, show that the **physical observable**
sets how *deep* the transfer goes. Alchemical free energy (FEP) reshapes the shared representation
and transfers even when the encoder is fine-tuned; the native-contact stability label only helps a
fixed (frozen) representation. Place the other ΔΔG-native labels (Rosetta, ThermoMPNN) on the same
axis.

Panels (finalized 2026-07-04; the old design-loop panel (c) was removed — see Decision Log):

- (a) Held-out Tm MAE for Tm-only, FEP, MD native-contact (matched scan), Rosetta mutation score,
  and ThermoMPNN stability score, under **frozen vs hot encoder** (grouped). Key contrast: FEP
  improves in the hot regime; the MD native-contact label improves only frozen and not hot.
- (b) Paired ΔMAE vs Tm-only for each source × encoder regime, with bootstrap CIs — quantifying the
  "hot only for free-energy-type labels" split. (FEP crosses 0 in both regimes; MD only frozen;
  Rosetta/ThermoMPNN essentially null.)
- (c) Interpretation panel: shared-representation schematic showing the auxiliary label reshaping the
  encoder (deep, free energies) vs only the fixed trunk (shallow, native-contact Q).

Claims:

- Under matched design, **FEP transfers in both regimes; the MD native-contact label transfers only
  with a frozen encoder** → the physical observable determines whether the source can reshape the
  representation (depth of transfer).
- Under rigorous per-source tuning, only FEP (both regimes) and MD ΔQ (frozen) robustly help; the
  Rosetta-family scores (plain Rosetta, ThermoMPNN, and the two variant-set sources) sit at/near
  baseline. So the free-energy-type advantage is real but selective, not a blanket "ΔΔG helps."
- The two additional Rosetta-scored variant sets (ESM2-proposed, random) are shown in Fig 2's source
  menu as ordinary comparators; **we make NO reinforcement-learning / closed-loop design claim** —
  under tuning ESM2-proposed does not beat random, so any design-loop framing is dropped (user
  decision 2026-07-04).

## Supplementary Material Plan

Expected supplementary components:

- Supplementary Methods: dataset construction, computational label definitions, model details, training objective, hyperparameter search, statistical testing.
- Supplementary Table 1: dataset split sizes and label counts.
- Supplementary Table 2: hyperparameter search space and selected settings.
- Supplementary Table 3: run-level final metrics by seed.
- Supplementary Fig. 1: processed source-label data and MD Q-value distributions.
- Supplementary Fig. 2: candidate-setting searches and validation-to-test behavior.
- Supplementary Fig. 3: encoder-mode, FEP source-head, and source-combination controls.
- Supplementary Fig. 4: interval sensitivity, per-count MD setting selection, and MD-window controls.
- Supplementary Fig. 5: MD-derived descriptor controls and descriptor relationships.
- Supplementary Data: processed inputs and plotting tables used for the figures.

Keep the main paper compact and put reproducibility details here.

## Writing Rules

- Avoid: "simulation data generally improves Tm prediction."
- Use: "the utility of computational labels is source-dependent."
- Avoid: "ΔΔG predicts Tm."
- Use: "mutation free-energy labels provide source-label information that improves Tm prediction."
- Avoid: "sequence-model proposals are better than random variants" and any design-loop / reinforcement-learning framing.
- Use: "the two Rosetta-scored variant sets (ESM2-proposed and random) are weak-to-null comparators; ESM2-proposed does not beat random under tuning."
- Avoid: opening the paper with the Tm/ΔΔG relationship.
- Use: the Tm/ΔΔG relationship as the final interpretation of why FEP works.
- Avoid local lab shorthand in the manuscript and figures.
- Use reader-facing terms: "validation set", "held-out test set", "source labels", "mutation free-energy labels", "MD-derived Q-value".

## Current Key Numbers

**DEFINITIVE tuned two-axis numbers (2026-07-04).** Per-source × per-regime staged HPO
(Stage 1 arch×head skeleton → Stage 2 lr/dropout/wd fine-tune, selected on Tm **validation**),
then final **test** eval (5 runs, full scaling n_ddg = 20/80/160/320), paired bootstrap ΔMAE vs
the tuned Tm-only baseline over shared test-sample indices (eval set n=396, swapped low-data split).
Winning configs recorded in `zenodo/_logs/tune_final_results.tsv` + `results/final_*/scaling.json`.

Tuned Tm-only baselines: **frozen 7.229 / hot 6.548**.

FROZEN (encoder frozen — aux shapes the shared trunk only):

| n_ddg | FEP MAE (ΔMAE, p) | MD ΔQ MAE (ΔMAE, p) |
|---:|---|---|
| 20  | 7.133 (−0.097, **0.001**) | 7.318 (+0.089, ns) |
| 80  | 7.182 (−0.047, ns)        | 7.157 (−0.072, ns) |
| 160 | 7.139 (−0.090, **0.044**) | 7.176 (−0.053, ns) |
| 320 | 7.008 (−0.221, **0.006**) | 7.034 (−0.195, **0.011**) |

HOT (encoder unfrozen):

| n_ddg | FEP MAE (ΔMAE, p) | MD ΔQ MAE (ΔMAE, p) |
|---:|---|---|
| 20  | 6.569 (+0.021, ns)        | 7.018 (+0.470, **worse**) |
| 80  | 6.474 (−0.074, ns)        | 6.785 (+0.237, **worse**) |
| 160 | 6.418 (−0.130, **0.026**) | 6.691 (+0.143, **worse**) |
| 320 | 6.395 (−0.153, **0.040**) | 6.577 (+0.029, ns) |

Head-to-head at n=320 (paired): **frozen** FEP 7.008 vs MD 7.034, ΔMAE −0.026 [−0.210,+0.156] p=0.41
(**statistical tie — MD ΔQ competitive with FEP when frozen**); **hot** FEP 6.395 vs MD 6.577,
ΔMAE −0.182 [−0.356,−0.007] p=0.044 (**FEP significantly better in hot**).

**FULL comparator table (all sources re-tuned in the identical staged protocol, 2026-07-04).**
ΔMAE at n=320 vs tuned Tm-only, paired bootstrap (`*` = 90% CI excludes 0). Slope = power-law b
(4-point fit; unstable for the noisy hot Rosetta-family curves — rely on ΔMAE@320 there).

FROZEN (baseline 7.229):

| source | MAE@320 | ΔMAE@320 (p) | slope |
|---|---:|---:|---:|
| FEP            | 7.008 | **−0.221*** | −0.032 |
| MD ΔQ          | 7.034 | **−0.195*** | −0.080 |
| ThermoMPNN     | 7.089 | −0.141 (ns) | −0.116 |
| Rosetta-random | 7.216 | −0.013 (ns) | −0.041 |
| Rosetta        | 7.231 | +0.002 (ns) | −0.013 |
| Rosetta-ESM    | 7.312 | +0.083 (ns) | −0.001 |

HOT (baseline 6.548):

| source | MAE@320 | ΔMAE@320 (p) | slope |
|---|---:|---:|---:|
| FEP            | 6.395 | **−0.153*** | −0.202 |
| MD ΔQ          | 6.577 | +0.029 (ns; degrades at low n, +0.470* @ n=20) | −0.129 |
| ThermoMPNN     | 6.621 | +0.073 (ns) | −0.248 |
| Rosetta        | 6.625 | +0.078 (ns) | −0.065 |
| Rosetta-random | 6.692 | +0.144 (ns) | (noisy) |
| Rosetta-ESM    | 6.959 | **+0.411*** (worse) | (noisy) |

**Tuned hierarchy (overturns the pre-tuning single-config ranking):** FEP is the ONLY source that
significantly helps in HOT and is best in FROZEN. In FROZEN, FEP ≈ MD ΔQ (statistical tie) lead, with
ThermoMPNN a weak third and the **Rosetta family essentially null/harmful**. The old single-config
numbers (where Rosetta variants and ThermoMPNN all looked helpful) were an artefact of un-tuned
comparison; under matched per-source tuning + the low-data split the transfer is much more selective.

**Two-axis reading (survives rigorous tuning + test eval):**
1. **Data design** — matched mutation-scan MD (native-contact ΔQ, same 1mel/4idl scaffolds as FEP)
   transfers in FROZEN and reaches −0.195 at n=320 (p=0.011), a statistical tie with FEP (−0.221).
   The old diverse-screen MD (Q–length confound) gave zero/negative transfer. → design, not observable.
2. **Physical observable** — alchemical ΔΔG (FEP) helps in BOTH regimes (reshapes the encoder →
   transfers hot). Native-contact ΔQ helps ONLY frozen; in hot it actively degrades (+0.47 at n=20),
   recovering only to baseline by n=320. → the free-energy observable is the more robust/deep signal.

Superseded reference (old single-config, pre-tuning): Tm-only 6.6145; FEP 6.2611 (−0.353);
ESM2-proposed/Rosetta 6.4484 (−0.165); ThermoMPNN 6.4607 (−0.153); random/Rosetta 6.5130 (−0.100);
Rosetta 6.5255 (−0.088); old diverse-MD Q-value 6.7304 (+0.117).

## Decision Log

- 2026-07-04: **Figures Fig 2/3/4 rebuilt with tuned numbers; RL/design-loop story dropped.** `plot/build_tuned_summaries.py` (new) writes `results/tuned_rep/{hot,frozen}_summary.json` + per-source representative single-point scaling.json from the 14 `final_*` runs; `plot/make_outline_figures.py` repointed to them, added source `MD_FEP400K` ("MD native-contact (matched scan)"). All 14 plotted numbers cross-checked PASS vs the tuned Key Numbers. **User decision:** the two Rosetta-scored variant sets (ESM2-proposed, random) are shown only as ordinary menu comparators in Fig 2b — **NO reinforcement-learning / closed-loop design claim** (under tuning ESM2-proposed 7.31/6.96 does NOT beat random 7.22/6.69). Consequently **Fig 4's old design-loop panel (c) was removed**; Fig 4 = (a) grouped frozen/hot MAE, (b) paired ΔMAE, (c) deep/shallow schematic. Old Result 5 "design-loop bridge" reframed to "Rosetta-family scores are weak-to-null"; design-loop/RL wording removed from contributions, abstract, results arc, discussion, writing-rules, TODO. Figures: `paper/tex/figures/fig_outline0{2,3,4}.{pdf,png,svg}`.
- 2026-07-04: **ALL comparators re-tuned (full staged HPO) — tuned hierarchy finalized.** Per user request, Rosetta / Rosetta-ESM / Rosetta-random / ThermoMPNN were put through the identical Stage1(arch×head, 48 cfg)→Stage2(lr/dropout/wd, 168 cfg)→final test(5 runs, full scaling) protocol as FEP/MD. Result (see Current Key Numbers full comparator table): FEP is the ONLY source significant in HOT (−0.153*) and best in FROZEN (−0.221*); MD ΔQ ties FEP in FROZEN (−0.195*); ThermoMPNN weak-third FROZEN (−0.141 ns); Rosetta family null/harmful (Rosetta +0.002, Rosetta-random −0.013, Rosetta-ESM +0.083 in frozen; all ≥baseline in hot, Rosetta-ESM +0.411* worse). This overturns the pre-tuning single-config ranking (where Rosetta/ThermoMPNN looked helpful). Winning configs in `zenodo/_logs/comp_final_results.tsv` + `results/final_{ros,rosesm,rosrnd,tmpnn}_{hot,frozen}/scaling.json`. Next: figures Fig 2/3/4 from the tuned numbers.
- 2026-05-30: Initial MD-centered story was weakened after controlled comparison.
- 2026-05-31: FEP mutation-effect labels identified as the main positive result.
- 2026-05-31: ESM2-proposed-variant result positioned as a bridge toward future design loops while avoiding a claim of optimized sequence design.
- 2026-05-31: MD-derived Q-value positioned as a boundary condition showing that source-label transfer is selective.
- 2026-05-31: Story reframed so the opening is about how to incorporate computational labels into Tm prediction; the Tm/ΔΔG relation is moved to the final interpretation.
- 2026-06-01: Submission target fixed to CSBJ General section as a compact Research Article.
- 2026-06-05: Train/test split was deliberately reassigned from NbBench's default to a low-data setting (57 train / 114 val / 396 test). Rationale: source-label transfer and label-count scaling effects are easier to see when experimental Tm training data are scarce; abundant Tm labels would wash out the simulation-label benefit. Rationale now stated in Methods (split definitions).
- 2026-06-05: Full manuscript prose rewrite (abstract, introduction, methods, results, discussion, supplementary) to remove AI-style phrasing and make the logic flow plainly; numbers, claims, citations, figure refs unchanged. Introduction subsection headers removed (continuous narrative); discussion subsections consolidated.
- 2026-06-05: Confirmed CSBJ AI policy (cover letter + acknowledgments disclosure required; AI not an author). Acknowledgments disclosure already compliant; cover-letter disclosure remains a pre-submission TODO.
- 2026-06-07: Fig. 1 replaced with figure_1_concept_protocol_v2.png, a single-panel architecture schematic (was a 4-panel a–d concept figure). Caption rewritten to describe the architecture (shared ESM2 encoder → shared MLP → Tm head + source head) without panel labels or specific layer dimensions; results.tex terminology aligned to "source head". Open TODO: the figure image's layer numbers (shared Linear(64), "Linear(32)" heads) contradict the code/Methods (shared 256→128→32, head 32→scalar) — figure image to be corrected; Methods/Supplementary left unchanged (code is authoritative).

- 2026-06-07: Terminology — removed the transfer-learning "source" wording throughout the manuscript and figure captions/labels; "source label/task/head" → "computational label / computational task / computational head" (≈190 replacements). "structure source" reworded to "input structure" (a different meaning). Plot axis labels updated too.
- 2026-06-07: Discussion restructured to CSBJ style — removed the content subsection headers ("Main finding and positioning", "Why mutation free energies can transfer", "What the controls rule out", "Physics-scored sequence proposals as a future direction", "Implications for large-scale data collection", "Outlook") and kept the prose as continuous text; only "Limitations" and "Conclusions" remain. Results titles de-jargoned.
- 2026-07-03: **MAJOR PIVOT — thesis + MD data swap + journal change.** (a) Replaced the MD source: the old diverse-nanobody 400 K native-contact Q-value (`data/md/nanobody_qvalue_400K.csv`, a `--md-source` auxiliary) → the new **FEP-matched mutation-scan MD ΔQ** (`MD_FEP400K`, 1mel 431 + 4idl 406, a `--ddg-source` treated like FEP). (b) **Thesis reframed from "MD does not transfer (negative control)" to a two-axis story:** *data design* (matched mutation scan removes the length confound and makes the same MD observable transfer; ΔQ ≡ Q after min-max, so it is the design not the arithmetic) and *physical observable* (FEP reshapes the encoder → transfers hot; MD native-contact Q only helps a frozen encoder → sets the *depth* of transfer). Controlled 2×2 + clip-threshold sweep established that clipping hurts monotonically and the extreme (experimentally unmeasurable, poor-yield) buried-charge ΔΔG carry disproportionate transfer signal → do NOT clip. (c) **Journal changed CSBJ → Biophysics and Physicobiology (BPPB)**, Biophysical Society of Japan; reframe toward biophysics; AUTHOR_GUIDELINES to be regenerated from BPPB instructions (format not yet confirmed). (d) Figures rescoped: Fig 2 adds MD ΔQ as a positive; Fig 3 becomes the data-design axis; Fig 4 becomes the physical-observable/depth axis. Tuned numbers being re-run (`source_screen` HPO for `MD_FEP400K`, hot+frozen). See memories `md-deltaq-transfer-experiment` and `fep-provenance-charge-correction`.
- 2026-06-07: Fig. 1 reduced to width=0.66\textwidth.
- 2026-06-07: Figure data made reproducible on any checkout — make_outline_figures.py now rebases the absolute scaling_json paths stored in the source-screen summary onto the local results tree (rebase_results()).
- 2026-06-07: Fig. 2 — panel (b) now reports the final validation-selected model MAE from the controlled source-screen summary (canonical) instead of test-argmin sweep points; panel (d) changed from paired ΔMAE to absolute held-out test MAE for Tm-only, FEP, and MD Q-value under frozen vs hot encoders (per request to drop the difference and include Tm-only). Fig. 2 is now internally consistent and matches Fig. 4 and the body (MD Q-value = 6.73, Tm-only = 6.61, FEP = 6.26).
- 2026-06-07: Fig. 3 — panel (b) replaced (the 4-descriptor normalized-value box plot was uninformative) with the raw MD Q-value (fraction native contacts) distribution at 300 K vs 400 K, showing 300 K saturates near one while 400 K spreads to lower values.
- 2026-06-07: Fig. 4 — removed panel (d) (the closed-loop "future direction" schematic; Discussion-flavoured, and Fig. 4 is the last Results figure). Fig. 4 is now (a) absolute MAE, (b) ΔMAE, (c) ESM2-proposed-minus-random.
- 2026-07-04: **RIGOROUS TUNING COMPLETE — two-axis story confirmed on test.** In response to the critique that all conditions were under-tuned, ran a staged per-source×per-regime HPO: Stage 1 (arch{shared/residual/latent}×head{separate/context}, 30 configs) → Stage 2 (encoder_lr/lr × dropout × weight_decay around each winning skeleton, 126 configs), all selected on Tm **validation**; then final **test** eval (5 runs, full scaling) + paired bootstrap vs tuned Tm-only. Result (see Current Key Numbers): FROZEN — both FEP (−0.221, p=0.006) and MD ΔQ (−0.195, p=0.011) scale and are a statistical TIE at n=320 (data-design axis holds). HOT — FEP helps (−0.153, p=0.040); MD ΔQ HURTS (+0.47 at n=20, back to baseline by n=320); FEP>MD in hot (p=0.044) (physical-observable axis holds). Winning configs: FEP hot=shared/separate,enc3e-5,d0.15,w0.1; FEP frozen=shared/separate,lr1e-3,d0.05,w0.02; MD hot=latent/context,enc1e-5,d0.15,w0.02; MD frozen=shared/separate,lr1e-3,d0.05,w0.02; Tm hot=residual,enc5e-5,d0.3,w0.02; Tm frozen=latent,lr1e-3,d0.05,w0.1. The shallow-HPO val blip (MD hot latent 5.8 beating FEP) did NOT survive to test = val overfitting. Story is now data-defensible; proceeding to figures. NOTE: Rosetta/ThermoMPNN/ESM2-proposed comparators still need re-tuning in the same protocol for secondary panels.
- 2026-06-07: CONSISTENCY ROOT CAUSE (Fig. 2/3/4 MD Q-value mismatch the user flagged): the same conditions were pulled from different experiment series with different MAE — sweep `*_tmselect` (MD Q-value 6.61), residual-descriptor `final_residual_*` (6.67), and source-screen `sourcefinal_*` (6.73). Decided canonical = source-screen summary; Fig. 2 was harmonized. Fig. 3a still uses the residual series (kept intentionally so the MD-descriptor comparison within 3a stays same-config/fair), so its Tm-only/FEP/MD Q-value still read 6.62/6.26/6.67 and differ slightly from the canonical 6.61/6.26/6.73. PENDING (needs new training, GPU): retrain all Fig. 3a descriptors at BOTH 300 K and 400 K in one canonical config so Fig. 3a becomes "all features × both temperatures" (#4) AND its shared conditions match Fig. 2/4. Until then Fig. 3a keeps its current single-temperature-per-descriptor layout.
- 2026-06-07: Fig. 3a DONE (#4) — trained the 3 missing-temperature residual runs on Apple MPS in the canonical config (hot encoder, MODEL_ARCH=residual, encoder-lr 3e-5, selection-scope tm, n_md 640, 3 seeds): MD Q-value 300 K (6.72), Q-value slope 300 K (6.57), RMSF max 400 K (6.69). Fig. 3a now shows every MD descriptor at both 300 K and 400 K where trajectory data exist (disulfide-distance and CDR3-residue fluctuation are 300 K only — no 400 K trajectories; CDR3 length is sequence-derived), colour-coded by temperature. Temperature effects are descriptor-specific (Q-value better at 400 K, structural fluctuations defined at 300 K) and small vs the bootstrap intervals. #5 resolved by explaining in the Fig. 3 caption that 3a is a separate residual training series from the source-screen models (Fig. 2/4), so its absolute MAE (e.g. MD Q-value 6.67) is not meant for cross-figure numerical comparison with the canonical source-screen value (6.73). Also fixed a dependency regression: transformers pinned <5.5 (5.10.2 broke training on torch 2.6 via torch.float8_e8m0fnu).

- 2026-06-07: Fig. 4 converted from difference plots to a scaling figure (user request). Removed the paired-ΔMAE panel and the ESM2-proposed-minus-random panel; Fig. 4 is now (a) final validation-selected MAE bars and (b) held-out MAE vs label count per template for FEP, ESM2-proposed+Rosetta, ThermoMPNN, random+Rosetta, and Rosetta mutation, with Tm-only as a dashed reference. The four variant/structure sources had only single n=320 points, so dedicated label-count sweeps (n=10,40,80,160,320, n_runs=10, hot/shared/enc-lr 3e-5, selection-scope tm) were trained on Apple MPS into results/sweep_ddg_* (checkpoints removed, scaling.json kept). FEP reuses its existing 10-seed sweep. As with Fig. 2, panel (b) sweep endpoints need not exactly equal the validation-selected models in (a) (noted in the caption); no body numbers changed. This also resolved the over-sized/awkward old Fig. 4c (the user retracted that separate comment). Reminder: prepare.py writes scaling.json to results/<exp-name>/, while --result-dir only holds checkpoints — set --exp-name.

## Drafting Checklist

- [ ] Start from the broad practical problem: how to use simulation data for experimental protein-property prediction when source labels differ from the target.
- [ ] Present nanobody Tm prediction as the concrete case study, not as the only possible use case.
- [ ] Present source-label training before discussing the Tm/ΔΔG relationship.
- [ ] Keep FEP as the main quantitative result.
- [ ] Use the MD-derived Q-value result to show source dependence.
- [ ] Treat the two Rosetta-scored variant sets (ESM2-proposed, random) as ordinary menu comparators only; make NO design-loop / reinforcement-learning claim (ESM2-proposed does not beat random under tuning).
- [ ] Place the Tm/ΔΔG conceptual interpretation near the end of Results or in Discussion.
- [ ] Add CSBJ-required statements: funding, author contributions, competing interests, data availability, code availability, and AI-use disclosure.
- [ ] Convert figure panel labels to `(a)`, `(b)`, `(c)` style.
- [ ] Keep all figure titles out of the figure panels.
- [ ] Prepare suggested reviewers before submission.
