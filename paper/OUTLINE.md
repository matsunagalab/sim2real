# 論文アウトライン

## 中心メッセージ

**Relative physics labels can teach absolute thermal stability.**

実験 Tm は、タンパク質ごとの絶対的な熱安定性を表す表現型である。一方、FEP や Rosetta で計算している補助ラベルは、変異による相対自由エネルギー変化、すなわち ΔΔG であり、Tm そのものでも絶対 ΔG でもない。

本研究の主張は、少数の実験 Tm が絶対スケールを anchor し、多数の ΔΔG ラベルが配列空間における stability landscape の局所的な傾きや方向性を与えることで、Tm 予測が改善する、というもの。

この意味で、本研究の発明・貢献は単なるデータ拡張ではなく、**absolute phenotype prediction に relative thermodynamic supervision を使う transfer-learning protocol** である。

---

## 研究課題

- ナノボディの Tm 実験データは少ない。タンパク質言語モデルを fine-tune しても、低データ regime では汎化に限界がある。
- シミュレーションや物理計算からは大量の補助ラベルを作れるが、それらは Tm とは異なる量である。
- 問いは以下。
  - Tm という絶対安定性表現型に、変異 ΔΔG という相対量は補助教師として効くのか。
  - 効くなら、どの種類の補助ラベルが有効なのか。
  - LM が提案した design sequence に physics label を付けることで、将来の closed-loop design / RL に接続できる兆候があるか。
  - 単純な MD-derived structural features は同じ protocol で転移するのか。

---

## 主要な発見

### 1. FEP ΔΔG は Tm-only を明確に改善する

Fair protocol で最も強い結果。

| condition | test MAE | ΔMAE vs Tm-only | 90% CI |
|---|---:|---:|---:|
| Tm-only | 6.6145 | - | - |
| FEP ΔΔG | 6.2611 | -0.3530 | [-0.4621, -0.2426] |

解釈:

- FEP は絶対 Tm を直接予測していない。
- それでも Tm prediction を改善する。
- したがって、FEP ΔΔG は shared stability representation を学習するための有効な補助教師である。
- これは「Tm と ΔΔG は別物だから使えない」ではなく、「同じ stability landscape の異なる観測量として統合できる」ことを示す。

### 2. Rosetta-scored design data も Tm transfer signal を持つ

ESM2 が提案した配列を Rosetta で評価した `rosetta_esm` も、Tm-only より改善した。

| condition | test MAE | ΔMAE vs Tm-only | 90% CI |
|---|---:|---:|---:|
| rosetta_esm | 6.4484 | -0.1652 | [-0.3058, -0.0250] |
| rosetta_random | 6.5130 | -0.0998 | [-0.2248, +0.0259] |

重要な解釈:

- `rosetta_esm` は Tm-only に対して有意に改善する。
- ただし `rosetta_esm - rosetta_random = -0.0654`, 90% CI `[-0.1949, +0.0639]` であり、random より優れるとはまだ断言しない。
- 論文では「ESM2 proposal が random より明確に良い」ではなく、**LM-proposed sequence space に physics labels を付けても Tm transfer signal が残る**と主張する。
- 将来的には、sequence generator -> physics scoring -> Tm predictor -> candidate selection という design loop に自然に接続できる。

### 3. 補助ラベルなら何でもよいわけではない

同じ fair protocol で MD_Q_HPHIL_400K は悪化した。

| condition | test MAE | ΔMAE vs Tm-only | 90% CI |
|---|---:|---:|---:|
| MD_Q_HPHIL_400K | 6.7304 | +0.1172 | [+0.0120, +0.2235] |

解釈:

- 400K MD の hydrophilic-contact Q-value は、validation では良く見えることがあるが、test には移らない。
- 単純な structural persistence feature は、少なくともこの protocol では Tm 汎化に十分でない。
- これにより、主張はより強くなる。改善は「補助データを増やしたから」ではなく、**free-energy-like relative stability labels が特に有効**だからである。

### 4. Source quality matters

Final test の全体像。

| source | test MAE | ΔMAE vs Tm-only | paired result |
|---|---:|---:|---|
| Tm-only | 6.6145 | - | baseline |
| FEP | 6.2611 | -0.3530 | strong |
| rosetta_esm | 6.4484 | -0.1652 | positive |
| thermoMPNN | 6.4607 | -0.1525 | positive |
| rosetta_random | 6.5130 | -0.0998 | weak / marginal |
| rosetta | 6.5255 | -0.0880 | weak / marginal |
| MD_Q_HPHIL_400K | 6.7304 | +0.1172 | negative |

論文上の整理:

- 主結果: FEP ΔΔG。
- 設計ループへの橋: ESM2 + Rosetta.
- 補助ラベルの選別: ThermoMPNN / Rosetta / random / MD-Q を並べて、source によって転移性が違うことを示す。
- negative control 的結果: MD-Q は汎化せず、free-energy-like ΔΔG の重要性を補強する。

---

## 提案する論文タイトル候補

- Relative free-energy supervision improves absolute thermal-stability prediction of nanobodies
- Learning absolute protein thermal stability from relative mutation free energies
- Thermodynamic transfer learning from mutation ΔΔG to nanobody melting temperature
- Physics-labeled design variants improve low-data nanobody Tm prediction

現時点では 2 番目か 3 番目が一番内容に近い。

---

## 貢献

1. **Thermodynamic transfer learning**
   - 実験 Tm という absolute phenotype に対し、FEP/Rosetta/ThermoMPNN などの relative mutation ΔΔG を補助教師として使う protocol を定義した。
   - checkpoint selection / early stopping / HPO は Tm validation のみに限定し、補助タスクの validation に引っ張られない fair protocol とした。

2. **Relative-to-absolute transfer の実証**
   - FEP ΔΔG が Tm-only を明確に改善した。
   - これは ΔΔG が Tm を直接代替するというより、shared stability representation を形成する補助信号として機能することを示す。

3. **Design-data route の提示**
   - ESM2 が提案した配列に Rosetta ΔΔG を付けたデータも Tm-only を改善した。
   - これは将来の model-in-the-loop design、active learning、reinforcement learning への橋になる。
   - 本論文では RL そのものは扱わず、RL に接続可能な supervised prelude として位置づける。

4. **補助データの限界の同定**
   - MD-derived Q-value は同じ fair protocol では test 汎化しない。
   - したがって「simulation data を足せばよい」ではなく、「Tm に転移する物理量を選ぶ必要がある」と結論する。

---

## セクション計画

### Abstract

- Tm prediction is important for nanobody engineering but experimental labels are scarce.
- Simulation can provide many labels, but they often measure relative mutation effects rather than absolute thermal stability.
- We develop a fair multitask transfer-learning protocol that uses mutation ΔΔG labels as auxiliary supervision while selecting checkpoints solely on Tm validation.
- FEP ΔΔG improves Tm prediction over Tm-only by 0.353°C MAE with paired confidence interval excluding zero.
- Rosetta-scored ESM2-designed variants also improve Tm prediction, suggesting a route toward model-in-the-loop design.
- MD hydrophilic-contact Q-values do not generalize under the same protocol, showing that source choice is essential.
- Conclusion: relative thermodynamic labels can teach absolute thermal stability, but transfer depends on the physical relevance of the auxiliary label.

### Introduction

1. **Motivation**
   - Nanobody stability is a practical bottleneck in therapeutic and diagnostic applications.
   - Tm is a useful experimental phenotype but data are sparse.
   - PLMs help, but low-data fine-tuning remains label-limited.

2. **Why simulation labels are tempting**
   - FEP, Rosetta, ThermoMPNN, and MD can generate labels for many variants.
   - However, these labels are not the same as Tm.
   - In particular, mutation ΔΔG is relative, whereas Tm is an absolute thermal-stability phenotype.

3. **Conceptual gap**
   - Prior work often asks whether simulated labels correlate with stability.
   - The deeper question is whether relative stability information can improve prediction of an absolute phenotype when combined with a small number of experimental anchors.

4. **Our hypothesis**
   - Tm labels anchor the absolute scale.
   - ΔΔG labels provide local slopes on the stability landscape.
   - Multitask learning can integrate both into a shared representation.

5. **What we show**
   - FEP ΔΔG robustly improves Tm prediction.
   - Rosetta-scored ESM2 design variants provide a positive design-data route.
   - MD Q-value features do not transfer, demonstrating that not all simulation labels are useful.

### Methods

1. **Data**
   - Experimental Tm data: low-data nanobody split, train 57 / validation 114 / test 396.
   - Auxiliary ΔΔG sources:
     - FEP
     - Rosetta
     - ThermoMPNN
     - Rosetta on random variants
     - Rosetta on ESM2-proposed variants
   - MD feature source:
     - MD_Q_HPHIL_400K, hydrophilic-contact Best-Hummer Q-value at 400K.
   - FoldX is excluded from the main story because of setup complexity and interpretability issues.

2. **Model**
   - ESM2-based sequence encoder.
   - Multitask heads for Tm and auxiliary labels.
   - Hot encoder setting is used for current fair source screen.
   - DDG head uses the selected fair head mode from prior search.

3. **Fair protocol**
   - All source comparisons use the same Tm train/validation/test split.
   - HPO is done separately for each source.
   - Best checkpoint, early stopping, and HPO selection use only Tm validation rows.
   - Final numbers are test MAE with `n_runs=10`.
   - Paired bootstrap is performed on per-example absolute errors.

4. **Auxiliary-label interpretation**
   - Tm is treated as an absolute stability phenotype.
   - ΔΔG is treated as a local relative stability label.
   - The model is not asked to convert ΔΔG directly to Tm; instead it learns a shared representation useful for both.

### Results

#### R1. Relative FEP ΔΔG improves absolute Tm prediction

Main result.

- Show Tm-only vs FEP.
- Report test MAE and paired ΔMAE.
- Emphasize that the auxiliary label is ΔΔG, not Tm or absolute ΔG.
- Interpretation: FEP teaches local stability landscape information.

Figure target: Fig. 2A/B.

#### R2. The transfer is source-dependent

- Compare all sources under the same fair protocol.
- FEP strongest.
- ThermoMPNN and rosetta_esm positive.
- Rosetta and random Rosetta weaker.
- MD_Q_HPHIL_400K negative.

Figure target: Fig. 2C/D.

#### R3. Physics-labeled design variants provide a path toward design loops

- ESM2-proposed variants scored by Rosetta improve over Tm-only.
- Do not overclaim superiority over random; random comparison remains inconclusive.
- Present this as a constructive result:
  - generate sequence candidates
  - score by physics
  - use as auxiliary supervision
  - improve Tm predictor

Figure target: Fig. 3.

#### R4. MD Q-value is an informative negative result

- MD_Q_HPHIL_400K worsens on test.
- HPHIL Q-value definition goes to Methods or Supplement.
- This result rules out the weak claim that any simulation-derived scalar helps.
- It supports the stronger claim that free-energy-like relative labels transfer better.

Figure target: Fig. 4.

#### R5. Fair protocol matters

- Earlier apparent improvements from MD-Q or mixed validation selection were unstable.
- Tm-only checkpoint selection changes the conclusion.
- This should be presented carefully as a methodological control, not as the main biological result.

Figure target: Supplement or small panel in Fig. 1.

### Discussion

1. **Why ΔΔG can help Tm**
   - Tm and ΔΔG are different observables of the same underlying stability landscape.
   - Tm gives absolute anchors.
   - ΔΔG gives local directional derivatives.
   - The shared representation combines anchors and slopes.

2. **Why FEP is strongest**
   - FEP is closest to a thermodynamic mutation free energy.
   - It likely provides less task-mismatched supervision than structural Q-values.
   - It directly encodes stability changes from sequence perturbations.

3. **Design-loop implication**
   - `rosetta_esm` result is not the final optimization algorithm, but it shows that physics-labeled generated variants can improve a Tm predictor.
   - This supports a future loop:
     - propose sequence
     - score or simulate
     - update predictor
     - select next candidates
   - Reinforcement learning is a future direction, not part of the present claim.

4. **Negative result is useful**
   - MD Q-value failure clarifies that structural persistence alone is not enough.
   - This prevents overgeneralizing the method as generic simulation augmentation.

5. **Limitations**
   - Small Tm train set.
   - Nanobody-specific split.
   - FEP source size and coverage limited.
   - Rosetta ESM vs random difference not yet significant.
   - No experimental validation of newly proposed high-Tm variants yet.

6. **Future work**
   - Larger generated variant libraries.
   - Iterative active learning.
   - Explicit optimization or RL using Tm predictor as reward model.
   - Combining FEP, Rosetta, and experimental feedback.

---

## 図案

### Fig. 1 Concept and Fair Protocol

Purpose: 本研究の発明を一目で示す。

Panels:

- (A) Tm vs ΔΔG concept
  - Tm: absolute stability phenotype.
  - ΔΔG: relative mutation effect.
  - 少数 Tm anchors + 多数 ΔΔG slopes -> shared stability landscape.
- (B) Multitask learning protocol
  - ESM2 encoder, Tm head, auxiliary ΔΔG head.
  - checkpoint / early stopping / HPO selected by Tm validation only.
- (C) Auxiliary sources
  - FEP, Rosetta, ThermoMPNN, rosetta_random, rosetta_esm, MD_Q_HPHIL_400K.
- (D) Evaluation protocol
  - train 57 / val 114 / test 396.
  - paired bootstrap on held-out Tm test.

### Fig. 2 Main Source Screen

Purpose: 主要結果。どの補助ラベルが Tm に転移するか。

Panels:

- (A) Test MAE bar plot with CI
  - Tm-only, FEP, rosetta_esm, thermoMPNN, rosetta_random, rosetta, MD_Q_HPHIL_400K.
- (B) Paired ΔMAE vs Tm-only
  - zero line.
  - FEP clearly negative.
  - MD_Q positive.
- (C) HPO-selected validation vs final test
  - validation で良く見えても test で崩れる source を可視化。
- (D) Source interpretation map
  - free-energy-like / design-scored / structural-dynamics feature の分類。

### Fig. 3 Design-Data Bridge

Purpose: ESM2 + Rosetta の positive story を将来の design loop につなげる。

Panels:

- (A) rosetta_esm generation/scoring workflow
  - ESM2 proposes variants.
  - Rosetta scores ΔΔG.
  - Multitask predictor learns with Tm anchors.
- (B) rosetta_esm vs Tm-only vs rosetta_random
  - MAE / ΔMAE.
- (C) Paired ΔMAE distribution
  - rosetta_esm improves over Tm-only.
  - rosetta_esm vs random is suggestive but not significant.
- (D) Future loop schematic
  - generator -> physics label -> Tm predictor -> candidate selection.
  - RL/active learning shown as future, not claimed as performed.

### Fig. 4 What Does Not Transfer

Purpose: negative control / boundary condition.

Panels:

- (A) MD_Q_HPHIL_400K result vs Tm-only.
- (B) Validation/test mismatch for MD-Q.
- (C) Definition of HPHIL Q-value or simplified contact schematic.
- (D) Take-home: free-energy-like relative labels transfer; simple structural persistence does not.

### Supplementary Figures

- Full HPO table.
- frozen vs hot ddG-head comparison.
- Different DDG heads.
- Earlier MD-Q scaling and short-trajectory sweeps, framed as exploratory/negative controls.
- All per-source absolute-error paired bootstrap distributions.

---

## 重要な表現ルール

- Avoid: "simulation data generally improves Tm prediction."
- Use: "free-energy-like relative stability labels can improve Tm prediction."
- Avoid: "ESM2 designs are better than random."
- Use: "Rosetta-scored ESM2-proposed variants retain a positive Tm transfer signal; superiority over random remains unresolved."
- Avoid: "MD data is useless."
- Use: "hydrophilic-contact Q-value did not generalize under the fair Tm-selected protocol."
- Avoid: "ΔΔG predicts Tm."
- Use: "ΔΔG provides auxiliary supervision for a shared stability representation anchored by experimental Tm."

---

## Methods Detail To Preserve

- HPHIL means hydrophilic residues: D/E/Q/N/R/K/H plus ff19SB variants.
- MD_Q_HPHIL_400K is Best-Hummer Q-value over native contacts where at least one atom belongs to a hydrophilic residue.
- Contact definition:
  - backbone heavy atoms
  - native contact cutoff 0.45 nm
  - residue gap > 3
  - final 30 ns average
  - 400K trajectory
- FEP/Rosetta/ThermoMPNN labels are treated as mutation ΔΔG-like auxiliary labels.
- All final source-screen values are from `results/source_screen/final_source_screen_summary.json`.
- Current source-screen commit: `2515c87 screen fair auxiliary sources`.

---

## Current Key Numbers

| condition | selected HPO | test MAE | CI width | ΔMAE vs Tm-only | 90% paired CI |
|---|---|---:|---:|---:|---:|
| Tm-only | shared/drop0.05 | 6.6145 | 0.8678 | - | - |
| FEP | shared/enc3e-5 | 6.2611 | 0.8182 | -0.3530 | [-0.4621, -0.2426] |
| rosetta | shared/lr1e-4_enc3e-5 | 6.5255 | 0.8453 | -0.0880 | [-0.2008, +0.0247] |
| thermoMPNN | shared/enc3e-5 | 6.4607 | 0.8419 | -0.1525 | [-0.2958, -0.0067] |
| rosetta_random | shared/enc3e-5 | 6.5130 | 0.8495 | -0.0998 | [-0.2248, +0.0259] |
| rosetta_esm | shared/enc3e-5 | 6.4484 | 0.8572 | -0.1652 | [-0.3058, -0.0250] |
| MD_Q_HPHIL_400K | residual/lr1e-4_enc3e-5 | 6.7304 | 0.8468 | +0.1172 | [+0.0120, +0.2235] |

Additional paired comparison:

- `rosetta_esm - rosetta_random`: ΔMAE -0.0654, 90% CI [-0.1949, +0.0639].
- Interpretation: suggestive but not conclusive.

---

## Open Questions

- How strongly should we foreground ThermoMPNN?
  - It improves test MAE with CI just below zero, but the physical interpretation is less clean than FEP.
  - Likely include in source screen, not as a central story.
- Do we want an additional final experiment with FEP + rosetta_esm combined?
  - It could support "complementary physics/design labels" but risks delaying figures.
- Do we want a stricter ESM2-vs-random design comparison with larger n or matched distribution?
  - Useful for future, not required for current story.
- Should MD-Q be main-text negative result or supplementary?
  - Recommendation: main-text boundary condition, because it sharpens the claim.

---

## Decision Log

- 2026-05-30: Initial MD-Q-centered story was weakened after fair comparison.
- 2026-05-31: Fair source screen was rerun with Tm-only checkpoint selection, source-specific HPO, and final test evaluation.
- 2026-05-31: FoldX excluded from the main story.
- 2026-05-31: FEP ΔΔG identified as the robust main result.
- 2026-05-31: Reframed central contribution as relative ΔΔG supervision for absolute Tm prediction.
- 2026-05-31: ESM2 + Rosetta positioned as a bridge toward future design loops, not as proof of optimized design.
- 2026-05-31: MD_Q_HPHIL_400K positioned as an important negative control/boundary condition.

---

## Writing Checklist

- [ ] Every quantitative claim points to `results/source_screen/final_source_screen_summary.json` or a specific committed result file.
- [ ] Do not claim random-vs-ESM superiority unless additional evidence is added.
- [ ] Clearly distinguish Tm, ΔG, and ΔΔG.
- [ ] State that checkpoint selection used Tm validation only.
- [ ] Explain why MD-Q negative result strengthens, rather than weakens, the source-specific transfer claim.
- [ ] Keep RL/design-loop language in Discussion/Future Work, not Results.
