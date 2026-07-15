# Manuscript Outline — Sim2Real Nanobody Tm

Last revised: 2026-07-15

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
- **Supplementary figures:** Fig. S1–S2.
- **Main statistical display:** paired change in test MAE with a 95% bootstrap
  interval over the same 396 test sequences.

## 2. Title, question, and answer

### Title

**Transfer learning with simulated variants and calculated quantities for
nanobody melting-temperature prediction**

The short title is **Transfer learning for nanobody Tm prediction**.

### Question

When experimental Tm values are scarce, which simulation plans and calculated
quantities provide useful additional training labels?

### Main answer

The number of calculated labels alone did not explain their value. Among the
two complete MD plans tested, local mutation scans gave a larger observed gain
with a frozen encoder than a heterogeneous structure panel. Among the calculated
quantities, FEP gave the lowest observed test error with both frozen and
fine-tuned encoders. The 95% interval for the fine-tuned FEP change included
zero, so that result should be described as the lowest observed error, not as a
clear improvement.

### Practical lesson

Before running simulations for an experimental prediction problem, consider
both the systems to calculate and the quantity to report. More calculated
values are not automatically more useful.

## 3. What the data show

### Result 1 — The two complete MD plans gave different results

Both plans used 400 K MD and a native-contact quantity from the Best–Hummer
family, but they differed in several other ways.

- The heterogeneous plan contained 1,143 PDB-derived rows representing 833
  unique sequences. Rows differed in sequence length, contact selection, and
  structure.
- The matched plan used single mutations of 1MEL and 4IDL, with 837 sequence
  rows that were also present in the 844-row FEP pool.
- The two plans used different contact definitions, averaging windows,
  preprocessing, and independently selected model settings.

For the frozen encoder, the heterogeneous plan changed MAE by
−0.049 °C (95% CI, −0.092 to −0.006 °C), whereas the matched plan changed it by
−0.195 °C (95% CI, −0.366 to −0.030 °C). Neither plan gave a clear gain after
encoder fine-tuning.

This is a comparison of complete plans, not a test in which only the selected
sequences changed. The paper must not assign the difference to one factor.

### Result 2 — FEP gave the lowest observed error in both encoder settings

At the largest label count:

- Frozen FEP: ΔMAE = −0.221 °C (95% CI, −0.393 to −0.051 °C).
- Frozen matched MD: ΔMAE = −0.195 °C (95% CI, −0.366 to −0.030 °C).
- Fine-tuned FEP: ΔMAE = −0.153 °C (95% CI, −0.323 to +0.020 °C).
- Fine-tuned matched MD: ΔMAE = +0.029 °C
  (95% CI, −0.139 to +0.197 °C).

FEP and matched MD both gave clear frozen-encoder gains. Their direct frozen
difference was small and unresolved: FEP minus MD = −0.026 °C
(95% CI, −0.243 to +0.192 °C). With a fine-tuned encoder, FEP had a lower
observed error than MD by 0.182 °C, but the 95% interval still included zero
(−0.393 to +0.024 °C).

Plain Rosetta, ThermoMPNN, and Rosetta scores for random variants gave little or
no gain. ESM2-proposed variants followed by Rosetta increased error by
0.411 °C (95% CI, +0.140 to +0.698 °C).

### Result 3 — The amount of data did not give a simple rule

For the frozen encoder, both FEP and matched MD improved between the smallest
and largest label counts, but the four points were not monotonic enough to fit
a scaling law. For the fine-tuned encoder, matched MD was harmful at the
smallest count and returned near the Tm-only value at the largest count. FEP
ended with the lowest observed error, but its 95% interval included zero.

Here, \(n\) is the number sampled from each scaffold table for each ensemble
member. Eighty percent of those rows entered training and 20% were set aside
for monitoring the calculated-label task. Sampling was repeated independently
for each ensemble member.

## 4. Important checks and limits

### Sequence overlap

The heterogeneous MD table had exact full-sequence matches to 2 Tm-training,
4 Tm-validation, and 8 Tm-test sequences. The model could see calculated
\(Q\) values for these sequences, but never their reserved test Tm values.
Removing the eight test matches from the error calculation left the main
contrast almost unchanged:

- frozen encoder: −0.049 °C, 95% CI −0.094 to −0.005 °C;
- fine-tuned encoder: +0.122 °C, 95% CI −0.005 to +0.248 °C.

This check shows that the test errors of the eight matches did not drive the
result. We did not retrain after removing overlapping calculated-label rows, so
the check does not rule out an effect on training or model selection.

### Repeated structures and sequence length

Ninety-seven sequences account for 407 of the 1,143 heterogeneous rows. The
model did not receive PDB identifiers, but row sampling gives repeated
sequences more weight. The heterogeneous \(Q\) value also has a weak positive
correlation with sequence length (Pearson \(r=+0.13\)). Eleven rows are longer
than the 158-residue input limit and are truncated. These observations are
possible explanations or sources of bias, not proof of a cause.

### Limits on the conclusions

- The Tm training set contains only 57 nanobodies.
- The matched calculations cover only 1MEL and 4IDL.
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
4. The local mutation-scan MD plan gave a larger frozen-encoder gain than the
   heterogeneous plan, while the plans differed in several ways.
5. FEP gave the lowest observed error in both encoder settings; the fine-tuned
   95% interval included zero.
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
   scores, and ThermoMPNN predictions.
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
- Rosetta, ThermoMPNN, random variants, and ESM2-proposed variants.
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
4. Compare FEP, matched MD, Rosetta, and ThermoMPNN in Fig. 3.
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
| Frozen | 7.229 |
| Fine-tuned | 6.548 |

### Largest label count

| Calculated label | Frozen MAE | Frozen ΔMAE | Fine-tuned MAE | Fine-tuned ΔMAE |
|---|---:|---:|---:|---:|
| FEP | 7.008 | −0.221 | 6.395 | −0.153 |
| Matched MD \(Q\) | 7.034 | −0.195 | 6.577 | +0.029 |
| ThermoMPNN | 7.089 | −0.141 | 6.621 | +0.073 |
| Rosetta | 7.231 | +0.002 | 6.625 | +0.078 |
| Random variants + Rosetta | 7.216 | −0.013 | 6.692 | +0.144 |
| ESM2 proposals + Rosetta | 7.312 | +0.083 | 6.959 | +0.411 |

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
