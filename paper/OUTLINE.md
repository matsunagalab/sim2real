# 論文アウトライン

## 中心メッセージ

**Computational stability labels can be used as auxiliary supervision for low-data nanobody Tm prediction, but the benefit depends strongly on what physical quantity is used.**

この論文の入口は、Tm と ΔΔG の概念的な関係ではない。入口はもっと実務的な課題である。

**実験 Tm が少ないとき、シミュレーションや物理計算で作れるラベルを、どうやって Tm 予測モデルの学習に取り込めばよいのか。**

本研究では、その一つの解決策として、実験 Tm を主タスク、計算ラベルを補助タスクとして学習する transfer-learning framework を作り、補助ラベルの種類を比較する。

結果として、FEP 由来の変異 ΔΔG ラベルが最も明確に Tm 予測を改善する。一方、単純な MD-derived contact-Q は同じ評価条件では改善しない。したがって、主張は「シミュレーションデータを足せばよい」ではなく、**Tm 学習に転移する計算ラベルを選ぶ必要があり、変異自由エネルギーに近いラベルが特に有効だった**というもの。

Tm と ΔΔG の関係は、冒頭の概念ではなく、最後の解釈で使う。すなわち、少数の実験 Tm が絶対スケールを与え、変異 ΔΔG が配列空間上の局所的な安定性変化を与えるため、FEP ラベルが Tm 予測を助けた、と解釈する。

---

## 中心課題と検証項目

- ナノボディの実験 Tm は少ない。
- 一方で、FEP、Rosetta、ThermoMPNN、MD などから、実験より多くの計算ラベルを作れる。
- しかし、それらのラベルは Tm そのものではない。
- 検証する点は以下。
  - 計算ラベルを、Tm 予測モデルの学習に補助情報として入れられるか。
  - どの種類の計算ラベルが Tm 予測に効くのか。
  - 計算ラベルの有効性は、単なるデータ量の効果なのか、物理量の種類に依存するのか。
  - 生成モデルが提案した配列を物理計算でラベル付けすると、将来の design loop につながる有用な学習信号になるか。

---

## ストーリーの順番

### 1. Problem: 実験 Tm が少ない

Tm 予測はナノボディ設計に有用だが、実験 Tm ラベルは少ない。Protein language model を fine-tune しても、低データ regime では限界がある。

ここでの自然な発想は、シミュレーションや物理計算から得られるラベルを学習に使うこと。しかし、計算ラベルは Tm とは異なる量であり、そのまま教師ラベルとして置き換えることはできない。

### 2. Method: 計算ラベルを補助タスクとして入れる

実験 Tm を主タスク、計算ラベルを補助タスクとして、同じ sequence encoder を共有するモデルを学習する。

重要なのは、比較条件を揃えること。

- 同じ Tm train / development / test split を使う。
- 補助ラベルごとにモデル設定を探索する。
- モデル選択は実験データ側の development set で統一する。
- 最終評価は held-out Tm test set で行う。
- 評価は同じ test examples 上の paired absolute error で比較する。

この段階では、Tm と ΔΔG の深い関係を前面に出さない。あくまで「どうやって simulation labels を Tm 学習に使うか」という方法論を提示する。

### 3. Result: FEP が最も明確に改善する

| condition | test MAE | ΔMAE vs Tm-only | 90% CI |
|---|---:|---:|---:|
| Tm-only | 6.6145 | - | - |
| FEP ΔΔG | 6.2611 | -0.3530 | [-0.4621, -0.2426] |

解釈はこの時点ではシンプルにする。

- FEP ラベルを補助タスクとして入れると、Tm-only より明確に良い。
- FEP は Tm を直接測っていない。
- それでも Tm 予測に役立つ計算ラベルである。

### 4. Result: どの計算ラベルでもよいわけではない

| source | test MAE | ΔMAE vs Tm-only | paired result |
|---|---:|---:|---|
| Tm-only | 6.6145 | - | baseline |
| FEP | 6.2611 | -0.3530 | strong |
| Rosetta-scored ESM2 variants | 6.4484 | -0.1652 | positive |
| ThermoMPNN | 6.4607 | -0.1525 | positive |
| Rosetta-scored random variants | 6.5130 | -0.0998 | weak / marginal |
| Rosetta | 6.5255 | -0.0880 | weak / marginal |
| MD contact-Q | 6.7304 | +0.1172 | negative |

ここから出す結論:

- 改善は、補助データ量を増やしただけでは説明できない。
- 補助ラベルの物理的意味が重要。
- 変異自由エネルギーに近いラベルは有効。
- 単純な構造持続性指標は、この条件では Tm 汎化に結びつかない。

### 5. Result: 生成配列に物理ラベルを付けても信号が残る

ESM2 が提案した配列を Rosetta で評価したデータも、Tm-only より改善した。

| condition | test MAE | ΔMAE vs Tm-only | 90% CI |
|---|---:|---:|---:|
| Rosetta-scored ESM2 variants | 6.4484 | -0.1652 | [-0.3058, -0.0250] |
| Rosetta-scored random variants | 6.5130 | -0.0998 | [-0.2248, +0.0259] |

ただし、ESM2 variants が random variants より明確に良いとはまだ言わない。

追加比較:

- ESM2 variants - random variants: ΔMAE -0.0654, 90% CI [-0.1949, +0.0639]

論文で言うべきこと:

- 生成モデル由来の配列に物理ラベルを付けても、Tm 予測に有用な学習信号が残る。
- これは将来の generator -> physics scoring -> Tm predictor -> candidate selection という loop に接続できる。
- 本論文では active learning や reinforcement learning は実施しない。将来展望として示す。

### 6. Interpretation: なぜ FEP ΔΔG が Tm に効くのか

ここで初めて、Tm と ΔΔG の関係を説明する。

- Tm は、タンパク質ごとの絶対的な熱安定性に関係する実験表現型。
- 変異 ΔΔG は、ある配列から別の配列へ動いたときの相対的な安定性変化。
- 両者は同じ安定性 landscape の異なる観測である。
- 少数の Tm ラベルが絶対スケールを anchor し、多数の ΔΔG ラベルが局所的な傾きや方向を与える。
- そのため、FEP ΔΔG は Tm を直接代替しなくても、Tm 予測モデルの表現学習を助ける。

この解釈は最後に置く。冒頭で置くと、読者には「なぜ突然 ΔΔG と Tm の哲学から始まるのか」が分かりにくい。

---

## 図構成

### Fig. 1 Transfer-Learning Architecture for Low-Data Tm Prediction

Purpose: transfer learning のアーキテクチャを最初に示す。target task、source task、共有 encoder、task-specific heads、評価の流れを見せる。

Panels:

- (A) Transfer-learning setup
  - measured Tm labels define the target task.
  - computational labels define source tasks.
  - both streams map into a shared sequence representation.
- (B) Shared-encoder architecture
  - sequence encoder shared by Tm and auxiliary label heads.
  - Tm-only baseline vs auxiliary-label model.
  - model selection governed by the experimental development set.
- (C) Candidate auxiliary sources
  - mutation free-energy labels: FEP, Rosetta, ThermoMPNN.
  - generated-variant labels: Rosetta-scored ESM2 and random variants.
  - structural-dynamics label: MD contact-Q.
- (D) Evaluation design
  - Tm train / development / test split.
  - final comparison on held-out Tm test examples.
  - paired bootstrap on absolute errors.

This figure should not contain the Tm vs ΔΔG landscape interpretation.

### Fig. 2 Scaling With Experimental and Computational Labels

Purpose: スケーリング結果。実験 Tm ラベルと計算ラベルを増やしたときに、held-out Tm prediction がどう変わるかを見せる。

Panels:

- (A) Experimental Tm-label scaling
  - Tm-only performance improves as experimental labels increase.
- (B) FEP-label scaling
  - adding FEP mutation-effect labels changes Tm test error.
  - show the best point in the scaling curve.
- (C) MD contact-Q scaling
  - adding MD-derived contact labels does not show the same robust improvement.
- (D) Best points from scaling runs
  - Tm-only, FEP, and MD contact-Q best points.
  - This motivates the final selected-setting comparison in Fig. 3.

### Fig. 3 Final Performance at Selected Settings

Purpose: 最大量まで計算ラベルを使い、モデル設定を選んだ後の最終精度をまとめる。今までの source screen はここに置く。

Panels:

- (A) Final test MAE with confidence intervals
  - Tm-only, FEP, Rosetta-scored ESM2 variants, ThermoMPNN, Rosetta-scored random variants, Rosetta, MD contact-Q.
- (B) Paired ΔMAE vs Tm-only
  - FEP clearly improves.
  - generated-variant labels are positive but weaker.
  - MD contact-Q worsens.
- (C) Development-set selected performance vs held-out test performance
  - model-selection performance and final test performance are not identical.
- (D) Source category map
  - mutation-effect labels, generated-variant labels, structural-dynamics labels.

Generated-variant result:

- Rosetta-scored ESM2 variants improve over Tm-only.
- ESM2 vs random remains unresolved.
- This is discussed as a design-loop bridge in the text and Discussion, not necessarily as a separate main figure.

### Fig. 4 Interpretation and Boundary Condition

Purpose: 最後の解釈。ここで Tm と ΔΔG の関係を説明する。

Panels:

- (A) Absolute-vs-relative stability information
  - Tm gives sparse absolute anchors.
  - ΔΔG gives local mutation directions.
  - together they can define a useful representation of stability.
- (B) FEP vs MD contact-Q contrast
  - FEP improves; MD contact-Q does not.
- (C) Contact-Q boundary condition
  - contact-Q captures structural persistence, but not necessarily the mutation free-energy information needed for Tm.
- (D) Take-home interpretation
  - useful auxiliary labels encode stability changes relevant to sequence perturbations.
  - the result is not generic simulation augmentation.

---

## セクション計画

### Abstract

- Tm prediction is useful for nanobody engineering but experimental labels are scarce.
- Computational methods can generate additional labels, but these labels measure quantities other than Tm.
- We test a controlled auxiliary-training framework for incorporating computational labels into Tm prediction.
- FEP mutation-effect labels improve held-out Tm prediction over Tm-only training by 0.353 deg C MAE.
- Rosetta-scored ESM2 variants also provide a positive signal, suggesting a route toward model-in-the-loop design.
- MD contact-Q does not improve test performance, showing that source choice matters.
- Interpretation: mutation free-energy labels help because they provide local stability-change information complementary to sparse absolute Tm labels.

### Introduction

1. Nanobody Tm prediction is practically important and experimentally label-limited.
2. Simulation and physics-based tools can produce labels for many variants.
3. The central challenge is not whether such labels exist, but how to use them for a target phenotype they do not directly measure.
4. We use auxiliary training to incorporate computational labels into Tm prediction.
5. We compare multiple sources under the same evaluation design.
6. We find that FEP mutation-effect labels are most effective, generated-variant labels are promising, and a structural-dynamics label does not transfer.
7. We interpret the result as evidence that relative mutation stability information can complement sparse absolute Tm labels.

### Methods

- Data:
  - Experimental Tm split: train 57 / development 114 / test 396.
  - Auxiliary sources:
    - FEP mutation-effect labels.
    - Rosetta mutation-effect labels.
    - ThermoMPNN mutation-effect labels.
    - Rosetta-scored random variants.
    - Rosetta-scored ESM2 variants.
    - MD contact-Q.
- Model:
  - ESM2 sequence encoder.
  - Tm prediction head.
  - Auxiliary prediction head.
- Evaluation:
  - Same experimental split for all comparisons.
  - Model settings selected with the experimental development set.
  - Final numbers reported on held-out Tm test set.
  - Paired bootstrap on per-example absolute errors.

### Results

1. **A framework for using computational labels in Tm prediction**
   - Introduce auxiliary-label training.
   - Show evaluation design.
   - Figure 1.

2. **FEP mutation-effect labels give the strongest Tm improvement**
   - First show label-count scaling.
   - FEP scaling and MD contact-Q scaling behave differently.
   - Figure 2.

3. **Final selected-setting comparison**
   - Show Tm-only vs FEP.
   - Main quantitative result.
   - Full source screen.
   - Figure 3A/B.

4. **The effect is source-dependent**
   - MD contact-Q as boundary condition.
   - Development-set selected performance vs final test performance.
   - Figure 3C/D and Figure 4B/C.

5. **Physics-labeled generated variants provide a route toward design loops**
   - Rosetta-scored ESM2 variants improve over Tm-only.
   - ESM2 vs random is not conclusive.
   - Discuss as design-loop bridge in text and Discussion.

6. **Interpretation: mutation-effect labels complement sparse Tm anchors**
   - Tm gives absolute anchors.
   - ΔΔG gives local mutation directions.
   - FEP works because its auxiliary label is close to the relevant thermodynamic perturbation.
   - Figure 4A/D.

### Discussion

- Main advance:
  - A practical framework for using computational labels in low-data Tm prediction.
- Key result:
  - FEP mutation-effect labels robustly improve Tm prediction.
- Boundary:
  - Not all simulation-derived labels help.
- Design implication:
  - Physics-labeled generated variants are a supervised precursor to active design loops.
- Mechanistic interpretation:
  - Tm and ΔΔG are different observations of stability, and their complementarity explains the FEP result.
- Limitations:
  - Small experimental Tm train set.
  - Nanobody-specific dataset.
  - Generated-variant result is not yet a direct design success.
  - No new experimental validation of proposed high-Tm variants.

---

## 重要な表現ルール

- Avoid: "simulation data generally improves Tm prediction."
- Use: "the utility of computational labels is source-dependent."
- Avoid: "ΔΔG predicts Tm."
- Use: "mutation-effect labels provide auxiliary information that improves Tm prediction."
- Avoid: "generated variants are better than random variants."
- Use: "Rosetta-scored generated variants improve over Tm-only, while superiority over random variants remains unresolved."
- Avoid: making the Tm/ΔΔG conceptual relation the opening claim.
- Use: Tm/ΔΔG relation as the final interpretation of why FEP works.

---

## Current Key Numbers

| condition | test MAE | ΔMAE vs Tm-only | 90% paired CI |
|---|---:|---:|---:|
| Tm-only | 6.6145 | - | - |
| FEP | 6.2611 | -0.3530 | [-0.4621, -0.2426] |
| Rosetta-scored ESM2 variants | 6.4484 | -0.1652 | [-0.3058, -0.0250] |
| ThermoMPNN | 6.4607 | -0.1525 | [-0.2958, -0.0067] |
| Rosetta-scored random variants | 6.5130 | -0.0998 | [-0.2248, +0.0259] |
| Rosetta | 6.5255 | -0.0880 | [-0.2008, +0.0247] |
| MD contact-Q | 6.7304 | +0.1172 | [+0.0120, +0.2235] |

Additional paired comparison:

- Rosetta-scored ESM2 variants minus Rosetta-scored random variants:
  - ΔMAE -0.0654
  - 90% CI [-0.1949, +0.0639]
  - Interpretation: suggestive but not conclusive.

---

## Decision Log

- 2026-05-30: Initial MD-centered story was weakened after controlled comparison.
- 2026-05-31: FEP mutation-effect labels identified as the robust main result.
- 2026-05-31: Generated-variant result positioned as a bridge toward future design loops, not proof of optimized design.
- 2026-05-31: MD contact-Q positioned as a boundary condition showing that not all simulation-derived labels help.
- 2026-05-31: Story reframed so the opening is about how to incorporate computational labels into Tm prediction; the Tm/ΔΔG relation is moved to the final interpretation.

---

## Writing Checklist

- [ ] Start from the practical problem: how to use computational labels for low-data Tm prediction.
- [ ] Present auxiliary-label training before discussing the Tm/ΔΔG relationship.
- [ ] Keep FEP as the main quantitative result.
- [ ] Use the MD contact-Q result to show source dependence.
- [ ] Treat generated-variant results as a design-loop bridge, not as proof of optimized design.
- [ ] Place the Tm/ΔΔG conceptual interpretation near the end of Results or in Discussion.
