# Manuscript Outline — Sim2Real Nanobody Tm

Last reconciled with the manuscript and tuned result files: **2026-07-12**.

This file is the manuscript's scientific decision log and structural source of truth. It should describe
the paper as it is now, not preserve superseded drafts. Numerical claims must be checked against
`results/final_*/scaling.json`; journal structure must follow `AUTHOR_GUIDELINES.md`.

## 1. Submission Snapshot

- **Journal:** Biophysics and Physicobiology (BPPB), Regular Article.
- **Scientific area:** biomolecular simulation, protein engineering, and simulation-to-experiment
  transfer learning.
- **Target system:** low-data nanobody melting-temperature (Tm) prediction.
- **Experimental split:** 57 training / 114 validation / 396 held-out test sequences.
- **Main figures:** three, plus one graphical abstract.
- **Current manuscript:** 12 pages in the official BPPB template; the BPPB section order is wired
  into `tex/main.tex`.
- **Production status:** scientific story and main figures are near-final; supplementary figures,
  Fig. 1, terminology, and the cover letter remain.

### Required section order

`SECTION_ORDER: introduction -> methods -> results-and-discussion -> conclusion`

Front matter: title, authors, abstract, keywords, and significance statement. The graphical abstract
and its caption are separate submission files.

Back matter: conflict of interest, author contributions, data availability, acknowledgements, and
references. Supplementary Materials are submitted as a separate PDF.

## 2. Title and One-Sentence Claim

### Preferred title

**Simulation design and physical observable affect the transfer of molecular simulation to nanobody
thermal-stability prediction**

The current title in `tex/main.tex` is more generic and should be reconciled with this preferred title
before submission.

### One-sentence claim

Simulation-derived labels improve low-data nanobody Tm prediction most strongly when their sequence
design is matched to the target problem, while the physical quantity encoded by the label determines
whether the benefit remains when the protein-language-model encoder is fine-tuned.

### Plain-language take-home message

Generating more simulation labels is not enough. The simulated variants must probe a relevant
sequence neighborhood, and the simulated quantity must carry information that transfers to the
experimental phenotype.

## 3. Main Story

The paper asks a broad Sim2Real question through one biological case study:

> How should simulation-derived labels be designed and used when they are related to, but are not the
> same quantity as, a scarce experimental target?

The experimental target is nanobody Tm. The computational labels include mutation free energies,
native-contact persistence, Rosetta scores, and ThermoMPNN scores. All labels are used as auxiliary
prediction tasks sharing an ESM2-based sequence representation with the Tm task. Models are selected
only on experimental Tm validation performance and compared on the same held-out Tm test proteins.

The answer has **two axes**.

### Axis 1 — Simulation design controls the strength of transfer

The same type of MD native-contact observable has different value under two sequence designs:

- In a diverse screen of unrelated nanobody sequences, the label has only a small frozen-encoder
  benefit ($\Delta$MAE $-0.049$ °C) and is harmful with a hot encoder ($+0.117$ °C). That panel spans
  58–461 residues and has a nonzero label–length correlation (Pearson $r=+0.13$), identifying
  heterogeneity and sequence length as potential shortcuts rather than proving one causal mechanism.
- In mutation scans on the same 1MEL and 4IDL scaffolds used for FEP, sequence length is fixed and the
  native-contact label gives a much larger frozen-encoder improvement ($-0.195$ °C), statistically
  tying FEP at the largest tested label-count setting. It remains neutral rather than beneficial in
  the hot regime ($+0.029$ °C).
- Raw per-mutant Q and WT-referenced $\Delta Q$ differ by a scaffold-specific constant. After the
  per-table min–max preprocessing used here, that offset does not explain the gain. The changed result
  is therefore attributed to sequence design, not label arithmetic.

**Claim boundary:** the two simulation-acquisition designs come from independently tuned experimental series, not a
single preregistered factorial experiment. The evidence supports the conservative statement that a
matched local mutation scan substantially strengthens frozen-encoder transfer and avoids the hot-
encoder penalty seen in the heterogeneous screen. It does not prove that sequence length alone caused
the difference or that every matched scan will transfer.

### Axis 2 — Physical observable determines the depth of transfer

Once simulation design is matched, FEP and MD native contacts behave differently across encoder regimes:

- FEP mutation free energy improves Tm with both a frozen and a fine-tuned (hot) encoder.
- The matched native-contact label improves Tm with a frozen encoder but gives no net benefit with a
  hot encoder and is harmful at low label counts.
- FEP directly beats the native-contact label in the hot regime but not in the frozen regime.

The regime contrast supports a **depth-of-transfer interpretation**: FEP labels remain useful during
encoder fine-tuning, whereas native-contact labels are useful only when operating
on a fixed pretrained representation.

**Claim boundary:** the experiments compare frozen and hot training outcomes; they do not directly
measure representational geometry or prove a molecular mechanism. Wording such as “consistent with
beneficially reshaping the encoder” is justified. Wording that claims the representation was directly
shown to be reshaped by a specific physical mechanism is too strong.

### Supporting hierarchy

Under matched per-source tuning:

- FEP is the only computational label that robustly improves the hot regime.
- FEP and matched-scan MD lead and statistically tie in the frozen regime.
- ThermoMPNN gives a weak, non-significant frozen improvement.
- Plain Rosetta and Rosetta scores on random or ESM2-proposed variants are null or harmful.
- ESM2-proposed variants do not outperform random variants after tuning.

These results support **selective transfer**, not a general claim that computational labels help.

### Explicitly excluded story

This is not a reinforcement-learning, active-learning, generator–predictor, or closed-loop design
paper. The ESM2-proposed and random variant sets are ordinary comparators. Do not describe the
ESM2-proposed set as a successful design strategy.

## 4. Evidence, Interpretation, and Scope

### Directly supported by held-out test evidence

1. The tuned frozen and hot baselines differ.
2. Matched-scan MD and FEP improve the frozen baseline at the largest tested setting.
3. Only FEP improves the hot baseline at that setting.
4. FEP and matched MD are indistinguishable when frozen; FEP is better when hot.
5. The matched MD scan produces a substantially larger frozen benefit than the diverse MD panel; the
   diverse panel is heterogeneous and contains a possible length shortcut.
6. Rosetta-family comparators do not robustly improve Tm under matched tuning.

### Mechanistic interpretation

1. Matching the mutation neighborhood removes a shortcut and exposes a transferable local stability
   signal.
2. Sparse experimental Tm labels anchor the absolute phenotype, while mutation-effect labels provide
   local directions in sequence space.
3. Mutation free energy is closer to the thermodynamic stability phenotype than native-contact
   persistence and therefore remains useful during encoder adaptation.

These interpretations should be presented as the most coherent explanation of the controlled
results, not as independently measured mechanisms.

### Generalization boundary

- One experimental benchmark and one deliberately low-data split.
- Two mutation-scan scaffolds for the positive FEP/matched-MD result.
- A limited menu of computational labels and model architectures.
- No new experimental validation of predicted stabilizing variants.
- Label-count curves are not sufficiently monotonic to claim a universal scaling law.
- Absolute improvements are modest and describe predictor error, not assay-level changes in protein Tm.

## 5. Reader Path and Terminology

### Reader path

1. Experimental Tm labels are scarce.
2. Simulations can produce many related labels, but those labels are not Tm.
3. Multi-task learning provides a direct way to test transfer while model selection uses only Tm data.
4. Simulation design controls how strongly an MD label transfers.
5. Physical observable determines whether transfer survives encoder fine-tuning.
6. These observations become practical rules for simulation-dataset construction.

### Preferred terminology

Use **computational label**, **computational task**, and **computational head** as the general terms.
“Auxiliary” may be used sparingly when explaining the machine-learning role, but it should not create
a second naming system.

At first mention, give physical meaning before abbreviations:

- “experimental melting temperature (Tm)”
- “pretrained protein language model ESM2”
- “mutation free-energy labels from alchemical free-energy perturbation (FEP)”
- “MD-derived native-contact persistence (Q-value)”
- “structure-based Rosetta mutation score”
- “ThermoMPNN stability score”

Figure labels should be reader-facing: “Tm labels only,” “mutation free energy,” “MD native contact
(matched scan),” “Rosetta mutation score,” and “ThermoMPNN stability score.”

### Language to avoid

- Avoid: “simulation data improve Tm prediction.”
  Use: “transfer depends on which variants are simulated.”
- Avoid: “$\Delta\Delta G$ predicts Tm.”
  Use: “mutation free-energy labels improve the Tm predictor.”
- Avoid: “MD does not transfer” or “length confounding caused the null result.”
  Use: “the matched mutation scan strengthens frozen transfer relative to the heterogeneous screen.”
- Avoid: “FEP reshapes the encoder” as a directly observed fact.
  Use: “FEP remains beneficial during encoder fine-tuning, consistent with deeper transfer.”
- Avoid: “statistically significant” without naming the interval or test convention.
- Avoid all design-loop and reinforcement-learning framing.

## 6. Contributions

The manuscript should claim four contributions, in this order:

1. **A clear model-selection and test procedure.** Computational labels share a sequence model with the Tm
   task, but models are selected only with experimental Tm validation data and final comparisons use
   paired errors on a common held-out test set.
2. **A simulation-design contrast.** The same native-contact observable gives a much larger frozen benefit
   in matched constant-length mutation scans than in a heterogeneous screen, while neither design is
   sufficient for a hot-encoder benefit.
3. **A physical-observable result.** FEP transfers in both frozen and hot regimes, whereas matched
   native contacts transfer only with a frozen encoder.
4. **A practical design rule.** Simulations intended for experimental prediction should be
   designed around both relevant sequence perturbations and phenotype-aligned observables.

The source-menu comparison and model-size controls support these contributions but are not separate
headline claims.

## 7. Manuscript Architecture

### Abstract

One paragraph, at most 250 words, with no references.

1. Experimental problem: nanobody Tm labels are scarce.
2. Domain gap: simulations produce related quantities rather than Tm itself.
3. Protocol: independently tuned computational tasks, experimental validation selection, common
   held-out test set.
4. Axis 1: matched-scan MD gives a substantially larger frozen benefit than diverse-screen MD.
5. Axis 2: FEP helps frozen and hot; matched MD only frozen.
6. Implication: simulation design and physical observable jointly affect transfer.

The abstract should report the best hot FEP result (6.40 °C from 6.55 °C) and the frozen matched-MD
gain (approximately 0.20 °C), without crowding it with the full comparator table.

### Introduction

Paragraph logic:

1. Experimental property data constrain protein engineering.
2. Sim2Real learning uses abundant computational data to support scarce experimental targets, but a
   domain gap means more simulation is not automatically useful.
3. Protein stability is a particularly sharp case because Tm, mutation $\Delta\Delta G$, structural
   scores, and trajectory summaries have related but non-identical meanings.
4. Nanobodies provide a useful low-data testbed; ESM2 supplies a shared sequence representation.
5. Gap: prior work does not establish which combination of sequence design and physical observable
   makes computational labels useful for nanobody Tm prediction.
6. Approach: compare independently tuned computational labels using target-only validation and paired
   held-out evaluation.
7. Preview the two axes and their practical design rule.

Use Minami et al. as the closest Sim2Real framing precedent, without claiming a universal biological
scaling law. Use published PLM, Tm, nanobody, FEP, and MD literature to establish the biological case.
The related in-house Murakami manuscript may guide framing but should be cited only if its submission
status and journal policy permit.

### Materials and Methods

Methods should allow reconstruction of every comparison in the main figures.

#### Experimental target

- NbBench-derived nanobody Tm data.
- Deliberately reassigned low-data split: 57 train / 114 validation / 396 test.
- Tm scaling fitted on the 57-sequence training set only.
- Explain the scientific reason for the low-data setting without implying that the split was chosen
  after looking at final test performance.

#### Computational labels

- FEP mutation $\Delta\Delta G$: 1MEL and 4IDL mutation tables.
- Matched MD native-contact label: the same mutation-scan scaffolds.
- Diverse MD native-contact panel: heterogeneous simulation-design comparison with variable sequence length.
- Plain Rosetta, ThermoMPNN, random-variant/Rosetta, and ESM2-proposed-variant/Rosetta comparators.
- Define preprocessing, direction conventions, per-table scaling, and separate/contextual heads.

#### Model

- ESM2 encoder, frozen or fully fine-tuned.
- Shared or architecture-specific MLP paths.
- Tm head and computational head(s), all scalar outputs.
- Shared-trunk implementation: encoder hidden size → 256 → 128 → 32; output heads 32 → 1.
- Huber losses with uncertainty weighting; relevant fixed-weight controls in Supplementary Material.

#### Selection protocol

- Stage 1: architecture × computational-head coupling.
- Stage 2: learning rate × dropout × weight decay around the selected skeleton.
- Tune every computational label separately in frozen and hot regimes.
- Three-seed validation ensembles; five-seed final test ensembles.
- Checkpoint selection and HPO use experimental Tm validation rows only.
- Final claims use the 396 held-out test proteins only after configuration selection.

#### Statistics

- Primary metric: ensemble MAE in °C.
- Single-condition uncertainty: nonparametric bootstrap over test proteins.
- Comparisons: paired bootstrap using the same resampled test indices for candidate and reference.
- Primary evidence display: paired $\Delta$MAE and 90% CI; negative values favor the candidate.
- Resolve and document the p-value convention before reporting p values. Current prose describes a
  one-sided tail probability, while `plot/build_tuned_summaries.py` currently emits a two-sided value.

#### Label-count notation

`prepare.py --n-ddg-list` samples up to `n` rows from each template-specific table. Before final
submission, ensure every occurrence of “n labels” states clearly whether `n` is a per-table cap or a
total across the two scaffold tables. Figures, captions, Methods, and supplementary tables must use
one convention.

### Results

The Results section should contain three movements aligned to the three main figures.

#### Result 1 — Model selection and held-out test comparison

- Define Tm as the target and computed quantities as related tasks rather than surrogate Tm labels.
- Explain the common encoder, task-specific heads, frozen/hot regimes, and target-only validation.
- Establish the low-data split and tuned baselines: 7.23 °C frozen, 6.55 °C hot.
- End with the two questions: what makes a label transfer, and how deeply can it act?

#### Result 2 — A matched mutation scan strengthens native-contact transfer

- Begin with a schematic contrasting heterogeneous variable-length sequences with fixed-scaffold
  local mutation scans.
- Compare diverse-panel and matched-scan native-contact labels as paired $\Delta$MAE against their
  own training-series Tm-only references, in both frozen and hot regimes. Do not compare absolute
  MAEs across the two series.
- Report the diverse panel's 58–461-residue range and $r=+0.13$ label–length correlation in the text
  and Supplementary Material as a possible shortcut, not a proven causal mechanism.
- Explain why Q and $\Delta Q$ are equivalent after the applied scaling.
- Show frozen label-count curves: FEP 7.13→7.01; matched MD 7.32→7.03 and crosses the baseline by the
  largest setting.
- At the largest setting, report FEP −0.22 °C and matched MD −0.20 °C versus baseline; their direct
  paired difference is −0.03 °C with a CI crossing zero.
- Conclude narrowly: the matched local scan substantially strengthens the frozen benefit and avoids
  the hot penalty of the heterogeneous screen, but matching alone is not enough for hot transfer.

#### Result 3 — Physical observable determines transfer depth

- Present the frozen hierarchy: FEP ≈ matched MD, ThermoMPNN weak third, Rosetta family at baseline.
- Contrast frozen and hot paired effects.
- FEP helps both regimes and reaches the overall best MAE of 6.40 °C.
- Matched MD helps only frozen, is harmful at the smallest hot setting (+0.47 °C), and returns to the
  hot baseline by the largest setting.
- Direct comparison: FEP ties matched MD when frozen but beats it when hot.
- Interpret the pattern as shallow versus deep transfer, with the evidence/interpretation boundary
  stated explicitly.
- Close with the negative comparator result and explicitly reject design-loop framing.

### Discussion

The Discussion should move from finding to mechanism to scope.

1. Restate the two axes without repeating the full Results table.
2. Explain why matched mutation scans remove a sequence-length shortcut and offer local stability
   directions.
3. Explain why mutation free energy and Tm are distinct but thermodynamically related; sparse Tm
   anchors the absolute phenotype while $\Delta\Delta G$ supplies relative mutation information.
4. Interpret the frozen/hot contrast as evidence about transfer depth, while acknowledging that no
   direct representation analysis was performed.
5. Use model-size, charge-correction, clipping, and source-menu controls to delimit alternative
   explanations.
6. Position the result relative to Sim2Real learning: useful computational data require aligned
   design, not just volume.
7. State limitations and the next scientific experiment: broader scaffold coverage, other physical
   observables, and prospective experimental validation.

Do not turn computational cost into a quantitative conclusion; cost was not systematically measured.
A qualitative breadth-versus-fidelity trade-off is acceptable.

### Conclusion

One compact paragraph:

- computational labels help selectively;
- matched sequence design strengthens native-contact transfer;
- free-energy content sustains transfer during encoder fine-tuning;
- simulation datasets for experimental prediction should be designed around both axes.

### Declarations

- Conflict of interest.
- Author contributions using confirmed CRediT roles.
- Data availability with final repository/archive identifiers.
- Acknowledgements, funding, and AI-assistance disclosure.

Exact CRediT roles for Soichiro Oda and Kazuma Okada remain a user-confirmation item.

## 8. Figure Plan

### Graphical abstract — The two design decisions

Show one flow with two gates:

1. Is the simulated sequence neighborhood matched to the target? Matching strengthens the useful
   signal and reduces heterogeneous shortcuts.
2. Is the observable aligned strongly enough with stability? If yes, transfer can persist during
   encoder fine-tuning; if not, benefit is limited to a fixed representation.

Keep it conceptual and do not reproduce detailed result panels.

### Fig. 1 — Multi-task training and Tm-based model selection

**Message:** computational labels influence a shared representation, while model selection and final
evaluation remain anchored to experimental Tm.

Required content:

- experimental and computational sequence inputs;
- ESM2 encoder and shared 256→128→32 MLP;
- scalar Tm and computational heads;
- frozen/hot encoder states;
- train 57 / validation 114 / test 396;
- target-only validation and paired test comparison.

Current placed image is stale: it says “Source head,” shows a 64-unit final shared layer, and depicts
the scalar heads as 32-unit layers. Regenerate it; do not merely relabel the existing boxes.

### Fig. 2 — Simulation-design axis

**Message:** a matched local mutation scan substantially strengthens frozen-encoder native-contact
transfer relative to a heterogeneous screen, but simulation design alone does not create hot transfer.

- **(a)** Design schematic: variable-length heterogeneous screen versus fixed-scaffold mutation scan,
  with the same native-contact observable computed in both.
- **(b)** Paired $\Delta$MAE versus each series' own Tm-only reference for both designs × both encoder
  regimes. Diverse: $-0.049/+0.117$ °C; matched: $-0.195/+0.029$ °C for frozen/hot, respectively.
- **(c)** Frozen FEP and matched-MD label-count curves with the tuned Tm-only baseline.

The caption must state that the diverse and matched results come from independently tuned series and
are expressed relative to their own Tm-only references. The length scatter moves to Supplementary
Material; length is a plausible design shortcut, not a proven explanation by itself.

### Fig. 3 — Physical-observable axis

**Message:** FEP transfers in both encoder regimes; native contacts transfer only with a frozen
encoder.

- **(a)** Source × encoder-regime map of paired $\Delta$MAE for all tuned computational labels.
- **(b)** Focused forest plot for FEP and matched MD, including their direct FEP-minus-MD contrast in
  each regime.
- **(c)** Hot-regime label-count curves: FEP improves with more labels, whereas matched MD recovers
  from low-count harm only to the Tm-only baseline.

Keep the main figure evidence-first. The old encoder-reshaping schematic moves out of the main figure;
mechanistic interpretation belongs in the Discussion and graphical abstract with qualified wording.

## 9. Supplementary Material Plan

The supplementary material should support the two-axis paper rather than preserve the pre-pivot
descriptor-screen narrative.

### Keep and update

- Detailed source-table construction and row counts.
- Full HPO space and selected settings for every source/regime.
- Run-level or ensemble-level final metrics and confidence intervals.
- FEP and matched-MD label-count tables.
- Frozen/hot comparator table.
- Model-size controls.
- FEP head/coupling controls where they clarify calibration across scaffolds.
- Charge-correction and clipping controls if their provenance is fully documented.
- Data and code provenance manifest.

### Redesign or remove

- Old source-screen panels using the 6.61/6.26/6.73 headline numbers.
- Diverse-panel MD presented as the primary MD result.
- FEP+MD combination panels that distract from the two-axis claim unless used as a clearly labeled
  non-additivity control.
- Legacy descriptor surveys as a headline supplementary figure. Retain only if they answer a current
  manuscript claim; otherwise move them to an archive or supplementary table.
- Per-count setting-selection figures that conflict with the final protocol of selecting one
  configuration and varying label count.

### Proposed supplementary sequence

1. **Supplementary Fig. 1:** datasets, split, source-table sizes, and matched-versus-diverse designs.
2. **Supplementary Fig. 2:** per-source/per-regime HPO and target-validation selection.
3. **Supplementary Fig. 3:** full frozen/hot source hierarchy and computational-head controls.
4. **Supplementary Fig. 4:** FEP/matched-MD label-count and model-size controls.
5. **Supplementary Fig. 5, only if retained:** diagnostic controls relevant to confounding,
   preprocessing, charge correction, or clipping—not a competing descriptor-screen story.

`plot/make_supplementary_figures.py`, `paper/analysis/supplementary/MANIFEST.tsv`, captions in
`tex/sections/supplementary.tex`, and `reproduce/manuscript_results.yaml` must be updated together.

## 10. Definitive Numerical Results

### Sources of truth

- `results/final_{tm,fep,mdq,ros,rosesm,rosrnd,tmpnn}_{hot,frozen}/scaling.json`
- `results/tuned_rep/{hot,frozen}_summary.json` for currently plotted paired summaries
- `zenodo/_logs/tune_final_results.tsv` and `comp_final_results.tsv` as run-selection records

Every final condition contains absolute errors for the same 396 held-out test proteins. Main claims
should be recomputed from these vectors rather than copied from prose.

### Baselines

| Encoder regime | Tm-only MAE (°C) |
|---|---:|
| Frozen | 7.229 |
| Hot | 6.548 |

### Largest label-count setting

An asterisk means the current 90% paired bootstrap CI versus the tuned Tm-only baseline excludes zero.
P values are intentionally omitted until the one-sided/two-sided convention is unified.

| Computational label | Frozen MAE | Frozen ΔMAE | Hot MAE | Hot ΔMAE |
|---|---:|---:|---:|---:|
| FEP mutation free energy | 7.008 | **−0.221*** | 6.395 | **−0.153*** |
| MD native contact, matched scan | 7.034 | **−0.195*** | 6.577 | +0.029 |
| ThermoMPNN | 7.089 | −0.141 | 6.621 | +0.073 |
| Rosetta mutation score | 7.231 | +0.002 | 6.625 | +0.078 |
| Random variants + Rosetta | 7.216 | −0.013 | 6.692 | +0.144 |
| ESM2-proposed variants + Rosetta | 7.312 | +0.083 | 6.959 | **+0.411*** |

Rounded paired 90% CIs used in the current manuscript:

- Frozen FEP versus baseline: −0.22 °C, CI [−0.36, −0.08].
- Frozen matched MD versus baseline: −0.20 °C, CI [−0.34, −0.05].
- Hot FEP versus baseline: −0.15 °C, CI [−0.30, −0.01].
- Hot matched MD versus baseline: +0.03 °C, CI crosses zero.
- Frozen FEP minus matched MD: −0.03 °C, CI [−0.21, +0.16].
- Hot FEP minus matched MD: −0.18 °C, CI [−0.36, −0.01].

### FEP and matched-MD label-count curves

| Setting | Frozen FEP | Frozen matched MD | Hot FEP | Hot matched MD |
|---:|---:|---:|---:|---:|
| 20 | 7.133 | 7.318 | 6.569 | 7.018 |
| 80 | 7.182 | 7.157 | 6.474 | 6.785 |
| 160 | 7.139 | 7.176 | 6.418 | 6.691 |
| 320 | 7.008 | 7.034 | 6.395 | 6.577 |

Do not describe these noisy four-point curves as a clean power law. Their role is to show label-count
behavior and the recovery/crossover pattern.

## 11. Submission Metadata

### Authors

1. Taihei Murakami — Saitama University and Epsilon Molecular Engineering, Inc.; equal contribution.
2. Kentaro Sasaki — Saitama University; equal contribution.
3. Soichiro Oda — Saitama University.
4. Kazuma Okada — Saitama University.
5. Yasuhiro Matsunaga — RIKEN Center for Computational Science and Saitama University;
   corresponding author.

Corresponding email: `ymatsunaga@riken.jp`

Yasuhiro Matsunaga ORCID: `0000-0003-2872-3908`

### Submission items still requiring confirmation

- Exact CRediT roles for Soichiro Oda and Kazuma Okada.
- Final data/archive DOI and raw-trajectory availability language.
- Final license choice.
- Final title.
- Suggested reviewers and any author ORCIDs required by the submission system.

## 12. Remaining Work in Priority Order

1. **Rebuild Supplementary Figs. 1–5 around the current two-axis story.** Update generator, tables,
   manifest, captions, and reproduction workflow together.
2. **Regenerate Fig. 1** with correct architecture and “computational head” terminology.
3. **Unify terminology** across Results, Discussion, Supplementary Material, and figures.
4. **Resolve statistical conventions:** p-value sidedness and label-count notation.
5. **Perform a claim audit:** every MAE, ΔMAE, CI, label count, and sample size against raw JSON/CSV.
6. **Revise the cover letter** from the old CSBJ/FEP-only story to BPPB and the two-axis result.
7. **Refresh repository-facing documentation** that still reports the original split or legacy best run.
8. **Run final format/citation/figure-resolution checks** in the official BPPB template.
9. **Confirm archive identifiers.**

Do not rerun GPU training unless a missing comparison is identified and explicitly approved.

## 13. Compact Decision Log

- **2026-06-05:** Experimental split deliberately reassigned to 57 train / 114 validation / 396 test
  to study transfer in a low-data target regime.
- **2026-07-03:** Main MD source changed from a diverse nanobody screen to FEP-matched 1MEL/4IDL
  mutation scans. Story pivoted from “MD is a negative control” to the two-axis simulation-design/physical-
  observable result. Target journal changed to BPPB.
- **2026-07-04:** Per-source, per-regime staged tuning completed. FEP remained beneficial frozen and
  hot; matched MD tied FEP frozen but not hot; Rosetta-family results became weak-to-null.
- **2026-07-04:** ESM2-proposed and random Rosetta-scored sets fixed as ordinary comparators. All
  reinforcement-learning and design-loop claims dropped.
- **2026-07-12:** Main text rewritten around the two axes; main figures reduced to three; BPPB front
  matter, declarations, conclusion, graphical abstract, and numeric citations added.
- **2026-07-12:** This outline was rewritten to remove superseded CSBJ, FEP-only, descriptor-screen,
  and four-figure planning from the active manuscript specification.

## 14. Final Drafting Checklist

- [x] Two-axis story controls the Abstract, Results, Discussion, and main figures.
- [x] Final claims use 57/114/396 and held-out paired test errors.
- [x] No reinforcement-learning or design-loop claim.
- [x] Three-main-figure structure.
- [x] BPPB section order, significance statement, keywords, graphical abstract, and declarations.
- [ ] Supplementary figures and captions rebuilt from tuned results.
- [ ] Fig. 1 architecture and terminology corrected.
- [ ] Computational/auxiliary terminology unified.
- [ ] P-value convention and label-count definition unified.
- [ ] Cover letter rewritten for BPPB and current results.
- [ ] CRediT roles and data availability finalized.
- [ ] Official BPPB template applied and final PDF audited.
