# Manuscript Outline — Sim2Real Nanobody Tm

Last revised: 2026-07-28

This file is the working plan for the manuscript. It records the story, the
figures, the numerical results, and the limits of the conclusions. The paper
should use plain words wherever a technical term is not needed.

## 1. Paper at a glance

- **Journal and article type:** Biophysics and Physicobiology, Regular Article.
- **Topic:** transfer learning from calculated protein-stability quantities to
  nanobody melting-temperature (Tm) prediction.
- **Experimental split:** 57 Tm values for training, 114 for validation, and
  396 reserved for final testing.
- **Main figures:** Fig. 1–3. Fig. 1 is being revised separately by the authors.
- **Supplementary figures:** Fig. S1 (FEP across ESM2 encoder sizes).
- **Main statistical display:** paired change in test MAE with a 95% bootstrap
  interval over the same 396 test sequences.

## 2. Title, question, and answer

### Title

**Transfer learning from computed stability data for nanobody
melting-temperature prediction**

The short title is **Transfer learning for nanobody Tm prediction**.

### Question

When experimental Tm values are scarce, which simulation plans and calculated
quantities provide useful additional training labels?

### Main answer

The number of calculated labels alone did not explain their value. Among the two
MD data designs, a sequence-diverse heterogeneous panel lowered Tm error once the
encoder was fine-tuned, whereas a single mutation scan of two fixed structures did
not help. Among the calculated quantities, FEP gave the lowest test error and was
the only source significant with both a frozen and a fine-tuned encoder; among the
empirical ΔΔG methods, FoldX transferred with a frozen encoder but Rosetta did
not.

### Practical lesson

Before running simulations for an experimental prediction problem, consider
both the systems to calculate and the quantity to report. More calculated
values are not automatically more useful.

## 3. What the data show

### Result 1 — Sequence-diverse data helped after fine-tuning; the single scan did not

Both data designs used 400 K MD and a hydrophilic native-contact Best–Hummer Q on
one common protocol (same [10, 40) ns window at 100 ps, parent-equilibration
reference, single MD head, shared architecture), so they differed only in the
sequences covered.

- The heterogeneous panel was 763 distinct nanobody sequences from SAbDab.
- The single mutation scan was single mutations of 1MEL and 4IDL (an 810-row pool).

At the largest label count (n = 320 per model), the heterogeneous panel changed
MAE by −0.09 °C frozen (95% CI, −0.18 to +0.02) and −0.30 °C fine-tuned (−0.56 to
−0.07), whereas the single mutation scan changed it by +0.01 °C in both encoders.
The direct scan-minus-heterogeneous contrast was +0.31 °C fine-tuned (95% CI,
+0.08 to +0.56). The sequence-diverse design, not the single mutation scan,
lowered Tm error, and only after fine-tuning.

### Result 2 — FEP was the only physical quantity significant with both encoders

At n = 320, ΔMAE against the shared Tm-only baseline (frozen 7.27, fine-tuned 6.72):

- FEP: −0.245 frozen (95% CI, −0.450 to −0.036) and −0.368 fine-tuned (−0.498 to
  −0.235); significant in both.
- FoldX: −0.181 frozen (−0.298 to −0.065), significant; −0.120 fine-tuned (ns).
  FoldX beat Rosetta directly (frozen −0.135; −0.223 to −0.047).
- MD native-contact Q: −0.111 frozen, +0.010 fine-tuned; both intervals include 0.
- Rosetta: −0.046 frozen, +0.037 fine-tuned; both intervals include 0.
- Rosetta on random variants: significant fine-tuned (−0.162; −0.291 to −0.033).
  Rosetta on ESM2-proposed variants was not significant.

FEP is the most direct thermodynamic proxy for Tm; among the two empirical ΔΔG
methods FoldX transferred but Rosetta did not, so the tool matters, not only the
quantity.

### Result 3 — The amount of data did not give a simple rule

Data-set size did not predict transfer. The heterogeneous panel (763) and the scan
(810) were sampled to the same n = 320, yet only the heterogeneous panel helped;
and the 1,000-variant Rosetta sets did not beat the smaller single-point scans.
FEP helped across the tested label counts and across ESM2 encoder sizes.

Here, \(n\) is the number sampled from each scaffold table for each ensemble
member. Eighty percent of those rows entered training and 20% were set aside
for monitoring the calculated-label task. Sampling was repeated independently
for each ensemble member.

## 4. Important checks and limits

### Sequence overlap

The aligned heterogeneous MD table (763 distinct sequences) had no exact
full-sequence match to any NbBench training, validation, or test sequence, so no
reserved target sequence appeared among the calculated labels.

### Repeated structures and sequence length

The aligned heterogeneous set is 763 distinct sequences, and the model did not
receive PDB identifiers. A weak dependence of the heterogeneous \(Q\) on sequence
length and truncation of the few sequences longer than the 158-residue input
remain possible sources of bias, not proof of a cause.

### Limits on the conclusions

- The Tm training set contains only 57 nanobodies.
- The single-mutation calculations cover only 1MEL and 4IDL.
- The two MD plans differ in more than one part of their setup.
- The selected FEP and MD models do not always use the same regression form.
- Bootstrap intervals resample the fixed test proteins after averaging trained
  models. They do not include uncertainty from row sampling, training seeds,
  or model selection.
- Wall-clock costs were not saved consistently enough for a broad cost claim.
- No new Tm measurements or prediction test on newly measured nanobodies was performed.

## 5. Order of the manuscript

### Abstract

Use one paragraph of at most 250 words.

1. Begin with why nanobody thermal stability matters and why measuring Tm for
   many sequences is costly.
2. Explain that stability calculations can add data but do not measure Tm.
3. Each calculated quantity and encoder setting was selected using Tm validation
   only, then compared using the same 396 test Tm values.
4. A sequence-diverse heterogeneous MD panel lowered Tm error after fine-tuning,
   while a single mutation scan of two fixed structures did not.
5. FEP gave the lowest error and was the only source significant with both encoder
   settings; FoldX also helped with a frozen encoder.
6. Simulations should be planned around both the systems and the reported
   quantity, rather than data count alone.

### Significance statement

Use fewer than 100 words and write for a reader outside the immediate field.
Begin with the importance of protein-stability measurements and the difficulty
of obtaining many Tm values. Then explain that simulations measure related
quantities rather than Tm itself, so making more simulated data is not enough.
Only after this background, state the main practical result: the choice of
variants and physical quantity must fit the experiment that the calculations
are meant to support. Do not open with the study design or model results.

### Introduction

1. Explain why low-data Tm prediction matters for nanobody engineering.
2. Explain why calculated labels may help but should not be called Tm data.
3. Distinguish Tm, mutation free energy, native-contact persistence, Rosetta
   scores, and FoldX predictions.
4. Present multi-task transfer learning as the way these labels are tested.
5. State the two questions: which simulation plan, and which calculated
   quantity?
6. Preview the results without claiming a single cause for the MD-plan
   difference.

### Materials and methods

Describe enough detail to reproduce every plotted comparison:

- NbBench source and the 57/114/396 split.
- FEP mutation calculations for 1MEL and 4IDL.
- Matched 400 K MD, native-contact definition, first 40 ns used for every
  variant, and per-structure scaling.
- Heterogeneous 400 K MD, 1,143 rows/833 unique sequences, row sampling,
  repeated sequences, and the input-length limit.
- Rosetta, FoldX, random variants, and ESM2-proposed variants.
- The 8M ESM2 model, regression heads, frozen and fine-tuned settings, losses,
  two-stage model search, and experimental-Tm-only selection.
- The meaning of \(n\), the 80/20 split of sampled calculated rows, and the
  independent sampling for each ensemble member.
- Five-model prediction averaging and paired 95% bootstrap intervals over 396
  test proteins.

Use “fine-tuned encoder” in the paper. The code and result directories use the
internal name `hot` for the same setting.

### Results and discussion

Keep Results and Discussion together.

1. Establish the common Tm test and the Tm-only values: 7.23 °C frozen and
   6.55 °C fine-tuned.
2. Compare the two complete MD plans in Fig. 2.
3. Report the sequence-overlap check and possible effects of length and
   repeated structures without assigning cause.
4. Compare FEP, MD, Rosetta, and FoldX in Fig. 3.
5. Explain why FEP may be more closely related to folding stability, while
   making clear that the molecular reason was not tested.
6. Cite the group’s mechanistic preprint as a future question about learned
   features, not as proof for the present models.
7. End with the additional checks and the study limits.

### Conclusion

The first paragraph should state the results and the practical lesson. The
second should describe future use: more scaffolds, sequential choice of
variants, active learning, and reinforcement learning. A future score used as
a reward must be compared with random sampling and simpler methods, and the
final test should use new experimental Tm measurements.

## 6. Figure plan

### Fig. 1 — Model and evaluation

**Purpose:** show how experimental Tm labels and one calculated label train a
shared sequence model, while model choice uses experimental Tm validation only
and final results use the reserved Tm test set.

The authors are revising this figure separately. Do not replace it during the
Fig. 2/3 work.

### Fig. 2 — Complete MD plans

**Message:** the matched mutation-scan plan gave a larger observed frozen-
encoder gain than the heterogeneous-panel plan; neither plan gave a clear
fine-tuned gain.

- **a:** horizontal paired ΔMAE for both plans and both encoder settings. Each
  point is compared with the Tm-only model from the same study. Zero must be
  clearly labelled.
- **b:** frozen-encoder FEP and matched-MD changes over four label counts.
  State that \(n\) is per scaffold table and ensemble member.
- Use 95% intervals and boxed axes. Do not bold points solely because an
  interval excludes zero.

### Fig. 3 — Calculated quantities

**Message:** FEP gave the lowest observed Tm error with frozen and fine-tuned
encoders; the fine-tuned FEP interval included zero.

- **a:** horizontal paired ΔMAE for all calculated labels, with frozen and
  fine-tuned points separated.
- **b:** direct FEP-minus-MD comparison. Zero means equal test MAE; negative
  values favor FEP and positive values favor MD.
- **c:** fine-tuned FEP and matched-MD changes over four label counts.
- Use 95% intervals and boxed axes. Keep labels and the zero reference readable
  at final printed size.

## 7. Supplementary material

Keep only material that helps interpret a main figure.

### Fig. S1 — Data and plan checks

- source-table sizes and sequence lengths;
- label distributions;
- the weak length–\(Q\) relation in the heterogeneous panel;
- overlap counts, repeated sequences, and truncation are stated in the text or
  source tables rather than expanded into extra panels unless needed.

### Fig. S2 — Additional checks

- fixed-setting 35M and 650M ESM2 checks, clearly labelled as within-size
  FEP-versus-Tm-only comparisons rather than a model-size ranking;
- analytical charge correction for FEP;
- clipping and added-Phe checks may remain in a compact panel or table only if
  they are cited in the main text.

Do not restore the removed supplementary figures unless they answer a specific
question raised by the main text.

## 8. Numerical reference

### Tm-only MAE

| Encoder | Test MAE (°C) |
|---|---:|
| Frozen | 7.27 |
| Fine-tuned | 6.72 |

### Largest label count

| Calculated label | Frozen MAE | Frozen ΔMAE | Fine-tuned MAE | Fine-tuned ΔMAE |
|---|---:|---:|---:|---:|
| FEP | 7.03 | −0.245 | 6.35 | −0.368 |
| MD native-contact \(Q\) | 7.16 | −0.111 | 6.73 | +0.010 |
| Rosetta | 7.23 | −0.046 | 6.76 | +0.037 |
| FoldX | 7.09 | −0.181 | 6.60 | −0.120 |
| Random variants + Rosetta | 7.25 | −0.026 | 6.56 | −0.162 |
| ESM2 proposals + Rosetta | 7.33 | +0.056 | 6.60 | −0.116 |

The displayed points and intervals are calculated from the saved 396
per-sequence absolute errors. Use the paired 95% intervals (2.5th to 97.5th
percentiles) throughout.

## 9. Wording

### Use

- calculated label or computed label;
- experimental Tm validation set and reserved Tm test set;
- complete simulation plan;
- frozen encoder and fine-tuned encoder;
- paired change in MAE;
- lowest observed error when a 95% interval includes zero;
- possible explanation when the cause was not tested.

### Avoid

- “simulation provides more stability labels than experiments” as a general
  statement;
- “FEP improves the fine-tuned model” without noting its 95% interval;
- “only FEP works”;
- “the sequence design caused the difference”;
- “FEP reshaped the encoder”;
- “statistically significant” without naming the comparison and interval;
- inflated terms where ordinary words such as plan, check, comparison, or
  procedure are clearer.

## 10. Submission details

- Affiliation order: RIKEN; Saitama University; Epsilon Molecular Engineering.
- Murakami alone has the Epsilon affiliation.
- Saitama addresses use `Saitama 338–8570, Japan`; the city and prefecture name
  are not repeated.
- Conflict of interest, author contributions, data availability, and
  acknowledgements follow the BPPB order.
- GitHub: `https://github.com/matsunagalab/sim2real`.
- Zenodo DOI remains a placeholder until deposition.

## 11. Items still open

1. Finish the author-led revision of Fig. 1 and check it against the code.
2. Replace the Zenodo DOI placeholder after the public record is created.
3. Confirm final author names, order, corresponding-author details, grants,
   and project numbers before submission.
4. Add final page and line numbers only if requested by the journal.
5. Build both main and supplementary PDFs after every final text or figure
   change.
