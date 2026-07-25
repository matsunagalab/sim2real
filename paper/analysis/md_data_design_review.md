# MD native-contact Q のデータ設計比較レビュー

**作成日:** 2026-07-25  
**対象:** matched 単一変異スキャン vs heterogeneous nanobody panel  
**目的:** Tm 転移性能に対する「データ設計」の効果を、ラベル量・モデル・学習経路などの交絡から分離して比較する

## Executive summary

両データを `md-source` の単一プール、同一 `task_id=3` に載せる案は、現行コードで実施できる最も対称な主解析である。モデル側の追加 head は不要で、1MEL と 4IDL は一つの scan pool として扱うのがよい。

ただし、現在の CSV と `prepare.py` をそのまま使って 24 runs を実行しても、まだ「データ設計だけ」の比較にはならない。主解析前に、少なくとも以下を直す必要がある。

1. scan と heterogeneous で native reference の時点を production frame 0 に統一する。
2. heterogeneous を行単位ではなく、一意なモデル入力配列単位に整理する。
3. `n` を実際に学習へ入る一意なラベル数として定義し、nested subset を固定する。
4. 異なる subset を学習した24モデルを一つにensembleしない。
5. subset抽出、モデル初期値、Trainerのseedを分離して保存する。
6. 可能なら、MD production中の同じ絶対時間区間と同じframe cadenceを使う。

この修正後に得られる推定対象は、厳密には次である。

> 同一の学習アルゴリズムへ、同じ件数の sequence–Q pair を与えたとき、今回構築した two-scaffold mutation-scan pool と heterogeneous pool のどちらが NbBench Tm test error をより低下させるか。

これは「今回の二つの実現済みpool」のcontrolled comparisonであり、mutation scan一般の普遍的な因果効果ではない。

## 1. `md-source` 単一プール案

### 判断

主解析として妥当であり、推奨する。

現行 `MultiTaskModel` の `md_head` は、名前に反してMD固有の物理機構を持たない通常の1次元回帰headである。`ddg_head` と `md_head` は同じsharedまたはauxiliary trunkから分岐する。

- [`train.py`](../../train.py#L162): shared architectureのtask heads
- [`train.py`](../../train.py#L188): ddG headsの初期化
- [`train.py`](../../train.py#L265): shared architectureでの各headのforward
- [`train.py`](../../train.py#L295): non-shared architectureでの各headのforward

両データを同じ

- `task_id=3`
- architecture
- label transform
- loss weighting
- batch size
- optimizer設定
- checkpoint selection

に載せれば、headやtask数による交絡を除ける。

### 推奨architecture

主解析は `shared` architectureを推奨する。最も単純で、MD向けに特別なfusion仮定を置かず、補助データがshared representationへ与える効果を直接比較できる。

`latent` または `residual` を、両データ共通の感度解析として追加する。単一architectureだけで得られる結論は、常に「その学習器の下でのデータ設計効果」である。

### 実装上の注意

`MD_PATHS` への2エントリ追加だけではCLIから選択できない。`--md-source` と `--md-aux-source` のchoicesがハードコードされている。

- [`prepare.py`](../../prepare.py#L100): `MD_PATHS`
- [`prepare.py`](../../prepare.py#L396): `--md-source` choices
- [`prepare.py`](../../prepare.py#L410): `--md-aux-source` choices

モデル変更は不要だが、parserは `choices=["none", *MD_PATHS]` のようにdictionaryから生成する方が安全である。

新しいprocessed label tableは、少なくとも次の列を持つ必要がある。

```text
seq,ddg_scaled01
```

現在のMD loaderはこの列名を固定で読む。

- [`prepare.py`](../../prepare.py#L218)

## 2. 1MEL と 4IDL を一つのscan poolへ結合するか

### 主解析

一つのpoolへ結合する。ただし各 `n` で1MELと4IDLを50:50に層別抽出する。

例:

| total n | 1MEL | 4IDL |
|---:|---:|---:|
| 20 | 10 | 10 |
| 80 | 40 | 40 |
| 160 | 80 | 80 |
| 320 | 160 | 160 |

full poolでは431:406をそのまま使用する。

単純random samplingでも大標本ではほぼ半々になるが、n=20ではscaffold比率のrun間変動が大きくなる。これは不要な分散なので、主解析では固定する。

### per-structure headを主解析にしない理由

1MELと4IDLを別task/headにすると、scan側だけが次の利点または相違を持つ。

- 2 task
- 2 output heads
- 最大2個のauxiliary loss項
- structure-specific calibration
- 現行loaderでは `n` が構造ごとに適用されるため、総数が `2n`

heterogeneousは1 taskのままなので、対称比較ではなくなる。

### 必須のper-structure感度解析

poolを主解析にしても、以下は同じ `md-head` で別に実行する。

- 1MEL-only
- 4IDL-only

ローカル監査では、両scaffoldとNbBenchの関係が大きく異なった。

- 1MELの431変異配列は、NbBench trainの1配列に約99.2% identity。
- 4IDLの最近傍NbBench配列は約64.7–67.2% identity。

したがって、pooled scanの効果が1MELのみで駆動される可能性がある。その場合に支持される主張は

> Tm training sequence近傍の局所mutation scanが有効だった

であり、

> single-mutation scan一般がheterogeneous designより優れる

ではない。

本文では “single-fold scan” よりも “two-scaffold matched mutation scan” と呼ぶ方が正確である。

## 3. matched-n と full-n

### 主結果

matched-nを主結果にする。`n` は次で定義する。

> 実際にauxiliary trainingへ投入された、一意なmodel-visible sequence–Q pairの数

主点は次の4点でよい。

```text
n = 20, 80, 160, 320
```

計算予算が許せば、`n=640` またはfull poolを追加する。

### 現行loaderの問題

現在は `n_md` 行を抽出した後、80/20に分ける。

- [`prepare.py`](../../prepare.py#L220): `n_md` 行の抽出
- [`prepare.py`](../../prepare.py#L227): auxiliary train/test split

そのため、表示上の `n` と実学習数は次のようになる。

| 表示n | 実学習数 |
|---:|---:|
| 20 | 16 |
| 80 | 64 |
| 160 | 128 |
| 320 | 256 |

さらに、同じseedを使った `df.sample` の総抽出集合はnestedだが、その後に各nで独立に `train_test_split` するため、実際のtraining集合はnestedではない。

### 推奨

checkpoint selectionをexperimental Tm valだけで行うなら、auxiliary holdoutを設けず、抽出したn件をすべて学習へ使う。

各outer subset seedについて一つの順列を作り、

```text
20 ⊂ 80 ⊂ 160 ⊂ 320
```

となるprefixを使用する。使用したrecord IDをmanifestとして保存する。

`--selection-scope tm` は必須とする。

- [`prepare.py`](../../prepare.py#L608)

### full-nの解釈

full-nも副次結果として併記するが、意味を分ける。

| 比較 | 答える問い |
|---|---|
| matched-n | 同じlabel数なら、どちらのdesignが有効か |
| full-n | 現在利用可能な全計算結果を使うと、どちらのplanが有効か |

heterogeneousを一意配列へ整理すると、現topology-derived sequenceでは846 unique、既存canonical tableでは833 uniqueである。scanは837 uniqueなので、deduplicate後のfull-nはほぼquantity-matchedになる。

一方、heterogeneousを1,143または1,145行のまま使うfull-nは、データ設計とデータ量を同時に比較する結果になる。

## 4. `md-head` と歴史的 `ddg-head` 性能

### 主解析で `md-head` を使う意味

`md-head`で揃えた結果は、共通学習器の下でのcontrolled effectを答える。

歴史的なscanのtuned `ddg-head` 結果は、

> scan designから現在の探索範囲で引き出せたbest-achievable performance

を答える。

この二つは別のestimandであり、両方を報告できるが、同じA対B contrastへ混ぜてはいけない。

### 推奨する報告

1. **主解析:** 両データ共通の `md-head`、architecture、HP。
2. **副解析:** 両データへ同じ予算で個別HPOを行ったbest-achievable性能。
3. **参考値:** 過去のscan tuned `ddg-head`。

heterogeneousをddG側へ載せるためだけに新task/headを追加する価値は低い。確認が必要なら、n=320だけで両データをtask 1とtask 3へ載せるchannel-swap感度解析を少数seedで行えばよい。

## 5. 主解析前に解消すべき交絡

### 5.1 Native referenceの時点が一致していない

現在のscan `selfref` は `own_topo` である。多くの行では

```text
topo_001/artifacts/system.topology.pdb
```

をnative referenceにしている。

- [`recompute_common_md_q.py`](../../scripts/recompute_common_md_q.py#L151)
- [`recompute_common_md_q.py`](../../scripts/recompute_common_md_q.py#L158)

一方、heterogeneous stagingのPDBは、保存スクリプト上、元の400 K production trajectoryのframe 0である。

- [`strip_md_solvent.py`](../../scripts/strip_md_solvent.py#L19)
- [`strip_md_solvent.py`](../../scripts/strip_md_solvent.py#L84)

したがって、真に対称なscan条件は

```bash
--reference own_frame0
```

である。

#### fallback referenceの問題

現在のscan `selfref` CSVでは、canonical topologyが無い行に次のfallbackが使われている。

| system | production-final参照 | equilibrated参照 |
|---|---:|---:|
| 1MEL | 18 | 0 |
| 4IDL | 12 | 1 |
| 合計 | 30 | 1 |

production-final構造をnative referenceにすると、heterogeneousのproduction frame 0参照と一致しないだけでなく、最終状態に近い構造を基準にQを測ることになる。

#### 現CSVのmetadata不整合

例として `1mel_A104D` を直接再計算すると、

| reference | Q | n_contacts |
|---|---:|---:|
| `own_topo` | 0.9662588 | 559 |
| `own_frame0` | 0.9711205 | 511 |

現在の `selfref` CSVはQとして0.9662588、`n_contacts`として511を持つ。すなわちQは `own_topo`、metadataは `own_frame0` に対応している。

主解析では既存行をmergeまたはresumeせず、837件を `own_frame0` でclean regenerationする。

### 5.2 同じfinal 30 nsでも絶対時間が違う

scanとheterogeneousではproduction長が異なる。

| design | production | Q window | output cadence |
|---|---:|---:|---:|
| scan | 約40 ns | 約10–40 ns | 10 ps |
| heterogeneous | 原則100 ns | 約70–100 ns | 100 ps |

scan protocol:

- [`methods.tex`](../tex/sections/methods.tex#L165)

heterogeneous protocol:

- [`methods.tex`](../tex/sections/methods.tex#L190)
- [`supplementary.tex`](../tex/sections/supplementary.tex#L19)

高温Qがunfolding kineticsを含むなら、window長が30 nsで同じだけでは十分でない。可能ならproduction開始後の同じ絶対時間、例えば10–40 nsを両方で使う。

またscanを100 ps cadenceへdownsampleし、heterogeneousと同じ300 frameで計算する感度解析を行う。密なframeは独立なMD replicateではなく、推定精度と自己相関が異なる。

この時間軸を揃えられない場合、結果は「既存の二つのMD planの比較」であり、「配列デザインだけの効果」とは表現しない。

### 5.3 heterogeneousのrow数とunique sequence数

現在のcommon-window CSVと既存canonical tableは一致していない。

| table | rows | unique sequences |
|---|---:|---:|
| current topology-derived common-window CSV | 1,145 | 846 |
| existing canonical heterogeneous table | 1,143 | 833 |

current CSVでは、

- duplicate rows: 299
- duplicated sequence groups: 92
- maximum multiplicity: 81

である。

sequence-only modelは同じ配列に付いた異なるstructure-specific Qを区別できない。row samplingのままでは、頻出配列へ最大81倍の重みを与える。

### 5.4 sequence qualityとmodel-visible input

current heterogeneous CSVには次が含まれる。

| 項目 | 件数または範囲 |
|---|---:|
| sequence length | 16–461 |
| length > 158 | 10 |
| `X`を含むsequence | 146 |
| length < 50 | 3 |

ESM inputはspecial tokenを含めて `MAX_LENGTH=160` なので、実効的なamino-acid上限は約158である。

- [`prepare.py`](../../prepare.py#L40)
- [`prepare.py`](../../prepare.py#L601)

長い構造ではQが全構造から計算される一方、モデルは先頭158残基程度しか見ない。これは明確なinput–label mismatchである。

#### 推奨QC

1. canonical VHH domainを定義する。
2. モデルへ渡す配列とQ計算に使う残基を一致させる。
3. fusion、tag、極端なfragment、multidomain chainを除外する。
4. noncanonical residueのmapping規則を固定する。
5. 同一canonical sequenceをdeduplicateする。

### 5.5 重複配列をどう処理するか

主解析では、一つのcanonical sequenceにつき一構造を選ぶ。

選択規則はQと独立に事前定義する。例:

1. complete VHH domain
2. missing residueが少ない
3. structure resolutionが高い
4. 同順位ならPDB IDで決定

複数structureのQを平均する方法は副解析として有用だが、一つのlabelを作るために複数MDを消費するため、scanとの計算予算比較が変わる。

### 5.6 NbBenchとのsequence overlap

exact overlap数はsequence sourceによって変わる。

| sequence mapping | train | val | test |
|---|---:|---:|---:|
| current topology-derived | 1 | 3 | 4 |
| existing canonical table | 2 | 4 | 8 |

最終的にモデルへ渡すcanonical domain sequenceで再計算し、主解析poolからNbBench train/val/testとのexact overlapを除く。

near-homologyはデータ設計の一部でもあるため、主解析では除去せず、各auxiliary sequenceからNbBench train/val/testへのnearest identity分布を報告する。必要ならidentity-threshold exclusionを感度解析とする。

### 5.7 Q label scaling

Qはもともと理論的に `[0,1]` なので、最も明快な共通変換はraw Qをそのまま `ddg_scaled01` として使うことである。

避けるべき組合せは、

- scanを構造ごとに別min–max
- heterogeneousをpool全体でmin–max

とすることである。この場合、同じ物理Qでもpreprocessingが異なる。

主解析案:

```text
ddg_scaled01 = q_value
```

感度解析:

- QC後のunionで一つの共通fixed transform
- source-wise rank normalization

conclusionが両者で一致するか確認する。

### 5.8 Loss weighting

主解析では

```text
MTL_WEIGHT_MODE=fixed
MD_WEIGHT=<predeclared common value>
```

を使用する。

learned uncertainty weightingを使うと、scanとheterogeneousのlabel variance、noise、learnabilityに応じて実効auxiliary weightが変わる。これは同じアルゴリズムではあるが、「名目上同じ補助強度」の比較ではない。

uncertainty weightingは感度解析として実行し、各runの最終 `log_sigma_tm` と `log_sigma_md` を保存する。

### 5.9 Checkpoint selection

checkpoint selectionはexperimental Tm val114だけで行う。

```bash
--selection-scope tm
```

mixed auxiliary validationを使うと、ラベル予測の難しさが異なる二つのdesignで、選ばれるepochまで変わる。

test396はarchitecture、HP、label transform、QC、primary endpointを固定した後に一度だけ評価する。

## 6. 24 runsの設計と統計

### 現行ensembleの問題

現在の `evaluate_runs` は、異なるauxiliary subsetを使った全runの予測を平均する。

- [`prepare.py`](../../prepare.py#L260)
- [`prepare.py`](../../prepare.py#L301)

現行samplerでrun 1–24をensembleすると、n=320でも実学習subsetのunionは次のようになる。

| pool | full size | 24-run training union at n=320 |
|---|---:|---:|
| scan rows | 837 | 837 |
| heterogeneous rows | 1,145 | 1,143 |
| heterogeneous unique | 846 | 846 |

したがって、最終ensembleはほぼfull poolを見ており、n=320のlabel-budget比較ではない。

### 推奨する24 fitsの配分

各design・各nについて、

```text
8 outer subset draws × 3 model initialization seeds = 24 fits
```

とする。

各outer subset内では、

- 同じn件のauxiliary labels
- 同じTm train/val
- 3つの異なるmodel seeds

を使う。

3モデルをensembleしてもよいが、ensembleは同じsubset内だけで行う。8つのsubset ensembleは独立なreplicateとして保持し、全subsetを一つのpredictionへ平均しない。

より単純には、24 single-model runsを独立replicateとして扱い、ensemble性能を副次結果にする方法でもよい。

### Seedの分離

現在のrun seedはsubset抽出とmodel initializationの両方へ使われている。

- [`prepare.py`](../../prepare.py#L591)

一方、`TrainingArguments` に `seed` と `data_seed` が渡されていない。

- [`train.py`](../../train.py#L408)

ローカル環境のTransformersでは既定値が `seed=42` であり、`Trainer.train()` 開始時に乱数が既定seedへ戻る。少なくとも次を明示する。

```python
TrainingArguments(
    ...,
    seed=model_seed,
    data_seed=data_order_seed,
)
```

保存すべきseed:

- `subset_seed`
- `model_seed`
- `data_order_seed`
- bootstrap seed

### Primary endpoint

最大matched pointを事前にprimary endpointとする。

```text
primary n = 320
Δdesign = MAE_scan − MAE_heterogeneous
```

- `Δdesign < 0`: scanが良い
- `Δdesign > 0`: heterogeneousが良い

各designのTm-only baselineからの差も報告するが、A対Bの直接差を主contrastとする。

Tm-only baselineは、共通architecture・HP・model seedで一つだけ用意する。designごとに異なるTm-only baselineを選ばない。

### Uncertainty estimation

現在のbootstrapは、trained ensembleを固定したまま396 test proteinsだけを再標本化する。

- [`prepare.py`](../../prepare.py#L324)

新解析では、少なくとも以下の二軸を再標本化する。

1. outer subset/model replicate
2. test protein

すなわちtwo-way bootstrapまたは対応するcrossed random-effects解析を使う。

報告値:

- mean `Δdesign`
- 95% CI
- seed-level paired differences
- test-protein-level paired differences
- subset variance
- initialization variance

scaling curveの4点はすべて表示し、testで最良だったnだけを選ばない。

## 7. 推奨する主解析仕様

| 項目 | 主解析仕様 |
|---|---|
| scan source | 1MEL+4IDL `own_frame0` Q |
| scan sampling | 各nで50:50、fullのみ431:406 |
| heterogeneous source | canonical VHH、exact dedup、1配列1構造 |
| target overlap | NbBench train/val/test exact matchを除外 |
| MD window | 可能なら同じproduction elapsed time |
| frame cadence | 共通100 ps、またはcadence感度解析 |
| Q definition | backbone Best–Hummer Q、同じparameter |
| label transform | raw Q `[0,1]` |
| task channel | 両方 `task_id=3` |
| architecture | shared |
| loss weighting | fixed、共通MD weight |
| n | 実学習unique数 20,80,160,320 |
| subset | nested、ID manifestを保存 |
| checkpoint selection | Tm val114のみ |
| repetitions | 8 subsets × 3 initializations |
| final test | 設定固定後にtest396を一度 |
| primary endpoint | n=320の直接 `MAE_scan − MAE_heterogeneous` |
| CI | replicate × test proteinのtwo-way bootstrap |

## 8. 副解析と感度解析

優先順位順:

1. 1MEL-only vs heterogeneous
2. 4IDL-only vs heterogeneous
3. full unique pool
4. common `latent` または `residual` architecture
5. raw Q vs rank-normalized Q
6. fixed vs uncertainty loss weighting
7. scan 10 ps vs100 ps cadence
8. exact-overlap除外前後
9. heterogeneous duplicate-row weighting
10. equal-budget separate HPO
11. historical tuned scan `ddg-head`

### HPOを追加する場合

二つの問いを区別する。

#### Controlled design effect

- 両designで同一architecture・HP
- 主解析

#### Best-achievable plan performance

- designごとに個別HPO
- 同じsearch space
- 同じ候補数
- 同じ3-seed validation budget
- testは選択後のみ
- 副解析

過去にscanだけで選ばれたHPまたはheterogeneousだけで選ばれたHPを、共通主解析のHPとして使わない。共通HPは、

- Tm-onlyで事前選択する
- 両designのvalidation MAE平均でjoint selectionする
- 最も単純なshared defaultを事前指定する

のいずれかとする。

## 9. 結論として許される主張

### この設計で支持できる主張

> 同じQ定義、同じ学習channel、同じarchitecture、同じ実学習label数の下で、今回のtwo-scaffold matched mutation-scan poolは、今回のdeduplicated heterogeneous nanobody poolより高い／低い／同程度のTm transfer効果を示した。

### この設計だけでは支持できない主張

> 単一変異scanは一般にheterogeneous protein panelより優れている。

> 一つまたは二つのfoldへ計算予算を集中することが、任意のTm予測問題で最適である。

> 観測差は局所mutation構造だけに起因する。

今回のscanには、1MELがNbBench training sequenceへ極めて近いというanchor-selection要因がある。per-scaffold解析なしに一般化しない。

## 10. より強い将来実験

データ設計そのものをより因果的に分離するには、総計算数を

```text
n = K × m
```

として固定し、

- `K`: scaffold数
- `m`: scaffold当たりmutation数

を振る。

例:

| design | scaffold数 K | variants/scaffold m | total n |
|---|---:|---:|---:|
| deep-local | 2 | 160 | 320 |
| intermediate | 8 | 40 | 320 |
| intermediate | 32 | 10 | 320 |
| broad | 160 | 2 | 320 |
| near-singleton | 320 | 1 | 320 |

全条件で、

- scaffoldを同じ親分布から抽出
- 同じstructure-quality filter
- 同じmutation proposal
- 同じMD preparation
- 同じproduction length
- 同じQ
- 同じTm targetとのsimilarity分布

を使う。

このfactorial designなら、「少数scaffoldを深くscanすること」と「多数scaffoldを広く覆うこと」の効果を、現在の二つの完成済みplanより直接的に比較できる。

## 11. 最小実装変更案

モデルは変更しない。

### Data preparation

- scanを `own_frame0` でclean regeneration
- heterogeneous canonical-domain QC
- exact dedup
- target overlap removal
- 共通processed CSV生成
- subset manifest生成

### `prepare.py`

- `MD_PATHS` に2 source追加
- CLI choicesを `MD_PATHS` から動的生成
- precomputed subset manifestを読むoption追加
- `selection_scope=tm` 時にauxiliary 80/20 splitを無効化
- `n` 超過時にsilent clampせずerror
- per-run prediction matrixを保存

### `train.py`

- `TrainingArguments.seed`
- `TrainingArguments.data_seed`
- learned task weightsの保存

### Evaluation

- single-run predictionsを保存
- same-subset ensembleだけを構築
- direct A–B contrastを計算
- two-way bootstrapを実装

## 参考文献

- Kendall A, Gal Y, Cipolla R. [Multi-Task Learning Using Uncertainty to Weigh Losses for Scene Geometry and Semantics](https://openaccess.thecvf.com/content_cvpr_2018/html/Kendall_Multi-Task_Learning_Using_CVPR_2018_paper.html). CVPR 2018.
- Standley T, et al. [Which Tasks Should Be Learned Together in Multi-task Learning?](https://proceedings.mlr.press/v119/standley20a). ICML 2020.
- Bouthillier X, et al. [Accounting for Variance in Machine Learning Benchmarks](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html). MLSys 2021.

