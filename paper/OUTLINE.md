# CSBJ Manuscript Outline

## Submission Target

- Journal: Computational and Structural Biotechnology Journal (CSBJ)
- Section: General
- Article type: Research Article
- Strategy: compact Research Article, not Short Communication
- Target length: about 5,000 to 8,000 main-text words, excluding references, figure legends, and supplementary material
- Main display items: 4 multi-panel figures, 0 to 2 main tables only if needed
- Section order source of truth: `paper/AUTHOR_GUIDELINES.md`

SECTION_ORDER: abstract -> introduction -> methods -> results -> discussion -> acknowledgments

## Author And Submission Metadata

Author order:

1. Taihei Murakami
2. Kentaro Sasaki
3. Yasuhiro Matsunaga

Affiliations:

- `1`: Saitama University, Saitama, Japan
- `2`: RIKEN Center for Computational Science, Kobe, Japan

Author-affiliation mapping:

- Taihei Murakami: `1`
- Kentaro Sasaki: `1`
- Yasuhiro Matsunaga: `1,2`

Corresponding author:

- Yasuhiro Matsunaga
- Email: `ymatsunaga@riken.jp`

ORCID:

- Yasuhiro Matsunaga: `0000-0003-2872-3908`

Student ORCID IDs are not treated as required placeholders unless the authors already have them or the submission system requires them at upload.

## Working Title Options

Preferred:

**Simulation-informed transfer learning improves low-data nanobody thermal stability prediction**

Alternatives:

- **Learning from simulation data for experimental protein-property prediction**
- **Mutation free-energy labels improve low-data nanobody thermal stability prediction**
- **Multi-task transfer learning from computational stability labels for nanobody melting-temperature prediction**
- **Free-energy-guided transfer of simulation labels to nanobody thermal stability prediction**

The preferred title is broad enough for CSBJ while keeping the main technical contribution clear. Avoid title wording that implies generic simulation data always helps.

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

The main result is that FEP-derived mutation free-energy labels provide the clearest improvement over Tm-only training. Rosetta-scored generated variants provide a weaker but positive signal. A simple MD-derived contact-persistence label does not improve the held-out Tm prediction. Therefore, the message is not that adding simulation data is generically beneficial; rather, the computational label must encode information that transfers to the target phenotype.

The relation between Tm and mutation free energy is the final interpretation, not the opening premise. Sparse experimental Tm labels anchor the absolute stability scale, while mutation free-energy labels provide local stability-change information over sequence perturbations.

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
4. Therefore, the central question is not only whether simulation data scale, but which simulated physical quantity transfers to the experimental target.
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
6. A design-loop bridge: generated variants scored by physics-based calculations can still provide useful supervised signal, although this paper does not perform active learning or reinforcement learning.

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
7. State source dependence: Rosetta-scored generated variants are positive but weaker; MD-derived contact-persistence label does not improve performance.
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
7. Protein language models provide useful representations, and prior nanobody Tm work shows that supervised fine-tuning is important for extracting Tm-relevant representations.
8. However, that prior work also suggests that simply increasing ESM2 size does not automatically improve nanobody Tm prediction, motivating information sources beyond model-size scaling.
9. We use a shared-encoder multi-task transfer-learning framework and evaluate all claims on held-out experimental Tm examples.
10. We compare mutation free-energy labels, generated-variant physics labels, and an MD-derived structural-dynamics label.
11. We find that FEP-derived mutation free-energy labels most clearly improve Tm prediction, supporting the view that relative stability-change information complements sparse absolute Tm anchors.

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
   - Figure 1 summarizes the design.

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
   - Rosetta-scored generated variants.
   - Rosetta-scored random variants.
   - MD-derived contact-persistence label labels.
   - For each source, report label definition, sign convention, number of labels, and whether labels are mutation-relative or sequence-level.

4. **Generated and random variant sets**
   - How ESM2-generated variants were produced.
   - How random variants were produced.
   - How Rosetta scoring was applied to both sets.
   - State that generated-vs-random superiority is exploratory and not the main claim.

5. **Model architecture**
   - ESM2 sequence encoder.
   - Tm prediction head.
   - Source-label prediction head.
   - Shared representation.
   - Updated encoder and frozen-encoder control.
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
   - Label-count scaling analysis.
   - Software versions and hardware.

8. **Data and code availability**
   - Processed data and figure-generation scripts.
   - Availability of raw simulation data or reason for restricted/large-file availability.
   - Archive/DOI target if available.

### Results

The Results should follow the figures and keep interpretation controlled.

#### Result 1: A framework for using simulation labels in experimental protein-property prediction

Figure: Fig. 1.

Key points:

- The general problem is how to exploit simulation data when source labels are related to, but not identical to, the experimental target.
- Nanobody Tm prediction is the concrete target-task case study.
- Tm prediction is the target task.
- Computational labels are source tasks.
- Source labels are not used as Tm replacements.
- The final evaluation is held-out experimental Tm prediction.

Main claim:

The design permits computational labels to influence representation learning while preserving target-task evaluation.

#### Result 2: FEP labels show label-count-dependent improvement, unlike the MD-derived contact-persistence label boundary condition

Figure: Fig. 2.

Key points:

- Experimental Tm-label scaling establishes the low-data regime.
- FEP labels improve best held-out Tm performance when the full source label set is used.
- The FEP curve is not perfectly monotonic; do not claim a clean power law.
- MD-derived contact-persistence label does not show robust improvement over Tm-only training.

Main claim:

The amount of source-label data matters, but data quantity alone does not explain improvement; label type matters.

#### Result 3: Final selected-setting comparison identifies FEP as the strongest source label

Figure: Fig. 3a,b.

Key numbers:

| condition | test MAE | ΔMAE vs Tm-only | 90% paired CI |
|---|---:|---:|---:|
| Tm-only | 6.6145 | - | - |
| FEP | 6.2611 | -0.3530 | [-0.4621, -0.2426] |
| Rosetta-scored ESM2 variants | 6.4484 | -0.1652 | [-0.3058, -0.0250] |
| ThermoMPNN | 6.4607 | -0.1525 | [-0.2958, -0.0067] |
| Rosetta-scored random variants | 6.5130 | -0.0998 | [-0.2248, +0.0259] |
| Rosetta | 6.5255 | -0.0880 | [-0.2008, +0.0247] |
| MD-derived contact-persistence label | 6.7304 | +0.1172 | [+0.0120, +0.2235] |

Main claim:

FEP-derived mutation free-energy labels give the strongest and most statistically stable improvement over Tm-only learning.

#### Result 4: The gain is not explained by simply using a larger encoder

Figure: Fig. 3c,f.

Key points:

- ESM2 size controls compare 8M, 35M, and 650M encoders.
- Larger ESM2 encoders do not improve absolute performance in this small-Tm-data setting.
- FEP remains beneficial within each size comparison, but the best absolute result is the 8M updated encoder with FEP labels.
- This agrees with the related Murakami et al. observation that model-size scaling alone did not solve nanobody Tm prediction.

Main claim:

The result supports physics-informed source-label supervision rather than model-size scaling as the primary driver in this regime.

#### Result 5: The source-label signal is strongest when the encoder can adapt, but it is not entirely dependent on encoder updating

Figure: Fig. 3e.

Key points:

- FEP improves both updated-encoder and frozen-encoder settings.
- The updated-encoder setting gives the best absolute performance.
- Rosetta and MD-derived contact-persistence label remain weaker than FEP.

Main claim:

FEP contributes useful information to the representation, and limited encoder adaptation helps exploit it.

#### Result 6: Physics-labeled generated variants provide a design-loop bridge

Figure: Fig. 3a,b and Discussion.

Key numbers:

| comparison | ΔMAE | 90% paired CI |
|---|---:|---:|
| Rosetta-scored ESM2 variants vs Tm-only | -0.1652 | [-0.3058, -0.0250] |
| Rosetta-scored ESM2 variants vs Rosetta-scored random variants | -0.0654 | [-0.1949, +0.0639] |

Main claim:

Rosetta-scored generated variants improve over Tm-only training, but their superiority over random variants is not conclusive. This should be framed as a route toward future generator-physics-predictor design loops, not as proof that generated variants are optimized.

#### Result 7: Mutation free-energy labels complement sparse absolute Tm anchors

Figure: Fig. 4.

Key points:

- Tm provides sparse absolute stability anchors.
- Mutation free-energy labels provide local sequence-perturbation information.
- FEP works because its label is close to the relevant thermodynamic perturbation.
- MD-derived contact-persistence label provides a boundary condition: structural persistence alone did not transfer in this setting.

Main claim:

The useful source labels are not simply more labels; they encode stability changes relevant to the target phenotype.

### Discussion

Paragraph plan:

1. Restate the main advance: a target-centered way to incorporate simulation-derived labels into experimental protein-property prediction, demonstrated in low-data nanobody Tm prediction.
2. Emphasize the main result: FEP mutation free-energy labels produce the clearest improvement.
3. Interpret why this matters: relative mutation free energies complement sparse absolute Tm labels.
4. Discuss source dependence: not every simulation-derived or physics-based label transfers.
5. Discuss encoder adaptation and model size: limited adaptation helps; larger language models were not sufficient in this low-data regime.
6. Discuss generated variants: positive supervised signal, but no claim of completed design optimization.
7. Limitations:
   - small experimental Tm train set;
   - nanobody-specific dataset;
   - no new experimental validation of high-Tm candidates;
   - generated-variant comparison remains exploratory;
   - raw simulation data may be large and difficult to deposit fully.
8. Outlook:
   - candidate generation, physics scoring, Tm prediction, and iterative selection;
   - future active-learning or reinforcement-learning design loops;
   - the present paper stops at supervised evidence supporting this direction.
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
- Competing interests: The authors declare that they have no competing interests.
- Author contributions: Use the CRediT-style draft in `paper/tex/sections/acknowledgments.tex` and confirm before submission.
- Funding: Use the JSPS KAKENHI and Fugaku support statement in `paper/tex/sections/acknowledgments.tex` and confirm grant details before submission.
- AI-use disclosure: Use the draft disclosure in `paper/tex/sections/acknowledgments.tex` and adjust to the journal's final submission form.
- Third-party permissions: Confirm that all figures are original or document any required permissions before submission.

Known placeholders still to fill later:

- Final Zenodo DOI for data.
- Final GitHub URL and Zenodo DOI for code.
- Suggested reviewers for submission.

## Figure Plan

### Fig. 1. Multi-task transfer-learning framework for using simulation data in experimental Tm prediction

Purpose: introduce the general problem of using simulation labels for an experimental target, then instantiate it as nanobody Tm prediction. Do not introduce the Tm/ΔΔG interpretation here.

Panels:

- (a) General setting: scarce experimental target labels and larger simulation-derived source-label pools.
- (b) Case study: low-data nanobody Tm prediction with non-Tm computational labels.
- (c) Shared sequence encoder with Tm target head and source label head.
- (d) Evaluation workflow: fixed Tm train/validation/test split, validation-set model selection, held-out test comparison.

CSBJ figure rules:

- No in-panel title.
- Use lower-case panel labels in parentheses.
- Put explanatory text in the legend.

### Fig. 2. Label-count scaling of experimental and computational supervision

Purpose: show scaling behavior and motivate final source comparison.

Panels:

- (a) Experimental Tm-label scaling.
- (b) FEP-label scaling.
- (c) MD-derived contact-persistence label label-count control.
- (d) Best points from label-count sweeps.

Claims:

- Experimental Tm labels show the expected low-data scaling behavior.
- FEP reaches the best held-out Tm MAE at the full label set, but the curve is noisy.
- MD-derived contact-persistence label does not reproduce the FEP benefit.
- Avoid claiming a strict monotonic law.

### Fig. 3. Final held-out Tm performance across source labels and controls

Purpose: central quantitative result.

Panels:

- (a) Final test MAE with confidence intervals.
- (b) Paired ΔMAE versus Tm-only.
- (c) ESM2 size controls.
- (d) Validation-set performance versus held-out test performance.
- (e) Frozen versus updated encoder comparison.
- (f) FEP gain across ESM2 sizes.

Claims:

- FEP is the strongest source label.
- Rosetta-scored generated variants are positive but weaker.
- Larger ESM2 encoders do not improve this low-data regime.
- Encoder updating improves absolute performance.

### Fig. 4. Interpretation: absolute Tm anchors and mutation free-energy directions

Purpose: interpret why FEP labels transfer while the MD-derived contact-persistence label label does not.

Panels:

- (a) Sparse absolute Tm anchors and local mutation-effect directions.
- (b) FEP versus MD-derived contact-persistence label performance contrast.
- (c) Boundary condition for structural-dynamics labels.
- (d) Take-home model: useful source labels encode transferable stability-change information.

Claims:

- Tm and mutation free energy are different observations of stability.
- FEP labels help because they encode local mutation effects.
- Generic simulation augmentation is not sufficient.

## Supplementary Material Plan

Expected supplementary components:

- Supplementary Methods: dataset construction, computational label definitions, model details, training objective, hyperparameter search, statistical testing.
- Supplementary Table 1: dataset split sizes and label counts.
- Supplementary Table 2: hyperparameter search space and selected settings.
- Supplementary Table 3: run-level final metrics by seed.
- Supplementary Figure 1: all label-count sweeps with confidence intervals.
- Supplementary Figure 2: additional source comparisons and negative controls.
- Supplementary Figure 3: encoder-size and frozen-encoder controls, if not fully clear in the main figure.
- Supplementary Data: processed inputs and plotting tables used for the figures.

Keep the main paper compact and put reproducibility details here.

## Writing Rules

- Avoid: "simulation data generally improves Tm prediction."
- Use: "the utility of computational labels is source-dependent."
- Avoid: "ΔΔG predicts Tm."
- Use: "mutation free-energy labels provide source-label information that improves Tm prediction."
- Avoid: "generated variants are better than random variants."
- Use: "Rosetta-scored generated variants improve over Tm-only, while superiority over random variants remains unresolved."
- Avoid: opening the paper with the Tm/ΔΔG relationship.
- Use: the Tm/ΔΔG relationship as the final interpretation of why FEP works.
- Avoid local lab shorthand in the manuscript and figures.
- Use reader-facing terms: "validation set", "held-out test set", "source labels", "mutation free-energy labels", "MD-derived contact-persistence label".

## Current Key Numbers

| condition | test MAE | ΔMAE vs Tm-only | 90% paired CI |
|---|---:|---:|---:|
| Tm-only | 6.6145 | - | - |
| FEP | 6.2611 | -0.3530 | [-0.4621, -0.2426] |
| Rosetta-scored ESM2 variants | 6.4484 | -0.1652 | [-0.3058, -0.0250] |
| ThermoMPNN | 6.4607 | -0.1525 | [-0.2958, -0.0067] |
| Rosetta-scored random variants | 6.5130 | -0.0998 | [-0.2248, +0.0259] |
| Rosetta | 6.5255 | -0.0880 | [-0.2008, +0.0247] |
| MD-derived contact-persistence label | 6.7304 | +0.1172 | [+0.0120, +0.2235] |

Additional paired comparison:

- Rosetta-scored ESM2 variants minus Rosetta-scored random variants:
  - ΔMAE -0.0654
  - 90% CI [-0.1949, +0.0639]
  - Interpretation: suggestive but not conclusive.

## Decision Log

- 2026-05-30: Initial MD-centered story was weakened after controlled comparison.
- 2026-05-31: FEP mutation-effect labels identified as the robust main result.
- 2026-05-31: Generated-variant result positioned as a bridge toward future design loops, not proof of optimized design.
- 2026-05-31: MD-derived contact-persistence label positioned as a boundary condition showing that not all simulation-derived labels help.
- 2026-05-31: Story reframed so the opening is about how to incorporate computational labels into Tm prediction; the Tm/ΔΔG relation is moved to the final interpretation.
- 2026-06-01: Submission target fixed to CSBJ General section as a compact Research Article.

## Drafting Checklist

- [ ] Start from the broad practical problem: how to use simulation data for experimental protein-property prediction when source labels differ from the target.
- [ ] Present nanobody Tm prediction as the concrete case study, not as the only possible use case.
- [ ] Present source-label training before discussing the Tm/ΔΔG relationship.
- [ ] Keep FEP as the main quantitative result.
- [ ] Use the MD-derived contact-persistence label result to show source dependence.
- [ ] Treat generated-variant results as a design-loop bridge, not as proof of optimized design.
- [ ] Place the Tm/ΔΔG conceptual interpretation near the end of Results or in Discussion.
- [ ] Add CSBJ-required statements: funding, author contributions, competing interests, data availability, code availability, and AI-use disclosure.
- [ ] Convert figure panel labels to `(a)`, `(b)`, `(c)` style.
- [ ] Keep all figure titles out of the figure panels.
- [ ] Prepare suggested reviewers before submission.
