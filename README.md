# sim2real

**Transfer learning from computed stability data for nanobody
melting-temperature prediction**

実験データが少ないナノボディ融解温度（Tm）予測で、どの計算ラベルが転移学習に役立つかを比較する研究リポジトリです。ESM-2 を使い、実験 Tm に加えて FEP、MD native-contact Q、Rosetta、ThermoMPNN の変異ラベルを補助課題として学習します。

現在の結果では、計算データを作る条件の組み合わせによって、観測された転移効果が異なります。FEP-matched 変異系列では、FEP は frozen／fine-tuned の両方で Tm-only より低い test MAE を示しました。ただし、fine-tuned の差の95%区間はゼロを含みます。MD native-contact Q は frozen encoder では改善しましたが、fine-tuned encoder では改善しませんでした。異なるナノボディを広く集めた以前の MD 系列は、配列選択だけでなく contact の定義と trajectory の集計方法も異なり、配列長との交絡も含むため、一要因の比較ではなく計算設計全体の比較対照として扱っています。

| Encoder | Tm labels only | + FEP | + matched MD Q |
|---|---:|---:|---:|
| Frozen | 7.229 °C | 7.008 °C (−0.221) | 7.034 °C (−0.195) |
| Fine-tuned | 6.548 °C | 6.395 °C (−0.153) | 6.577 °C (+0.029) |

括弧内は、同じ encoder の Tm-only に対する held-out test MAE の差です。全条件の結果は `results/final_*_{frozen,hot}/scaling.json` と `results/tuned_rep/{frozen,hot}_summary.json` にあります。

## Experimental Tm split

NbBench `ZYMScott/thermo-tm` の公開 split を、低データ学習のため次のように割り当てています。

| Local file | Published split | Purpose | n |
|---|---|---|---:|
| `data/nbbench/train.csv` | validation | training | 57 |
| `data/nbbench/val.csv` | test | model selection | 114 |
| `data/nbbench/test.csv` | train | final held-out evaluation | 396 |

`data/nbbench/download.py` はこの割り当てを再現します。最終 test は候補設定の選択には使いません。

## Setup

[uv](https://docs.astral.sh/uv/) で依存関係を管理しています。

```bash
git clone https://github.com/matsunagalab/sim2real.git
cd sim2real
uv sync
```

Notebook を使う場合だけ追加依存を入れます。

```bash
uv sync --extra notebooks
```

## Reproduce the current manuscript

固定入力と、論文で参照する結果・図・PDFが揃っているかを読み取り専用で確認します。

```bash
uv run python scripts/reproduce_paper_results.py --check-only
```

既存の最終結果から集計を作り直すには、次を実行します。

```bash
uv run python scripts/reproduce_paper_results.py --stage summaries --force
```

Fig. 2/3、supplementary figures/tables、main PDF、supplementary PDF を作り直すには、次を実行します。著者が編集中の Fig. 1 は変更しません。

```bash
uv run python scripts/reproduce_paper_results.py --stage figures --force
```

PDF 生成には `tectonic`、または `pdflatex` と `bibtex` が必要です。Tectonic の場所を指定する場合は `TECTONIC=/path/to/tectonic` を設定します。

論文で報告する 14 個の選択済み構成（7 source conditions × frozen/fine-tuned）を固定 CSV から再学習し、その後に集計・図・PDFを作るには次を使います。

```bash
uv run python scripts/reproduce_paper_results.py \
  --stage all --gpus 0 --force
```

これは長時間の GPU 計算で、選択済み条件を順番に実行します。別の GPU を使う場合は `--gpus` にその ID を指定してください。実行コマンドだけを確認する場合は `--dry-run` を加えてください。

この簡潔な再現手順は、論文で採用した設定を再学習します。候補設定の全探索そのものは繰り返しません。候補と採用設定は `paper/analysis/supplementary/tables/candidate_validation.tsv` と `selected_settings.tsv` に保存されています。

raw MD、FEP、Rosetta、ThermoMPNN 計算はこの手順では実行しません。処理済み CSV を固定入力として使います。定義は `reproduce/manuscript_results.yaml`、実行スクリプトは `scripts/reproduce_paper_results.py` です。詳しくは `REPRODUCE.md` を参照してください。

## Run one selected configuration

例として、fine-tuned encoder と FEP labels の最終条件は次のコマンドです。

```bash
DETACH_AUX_ENCODER=true CUDA_VISIBLE_DEVICES=0 uv run python prepare.py \
  --train-mode mtl --selection-scope tm --final-eval-split test \
  --encoder-mode hot --ddg-source FEP --n-ddg-list 20,80,160,320 \
  --model-arch shared --ddg-head-mode separate --encoder-lr 3e-5 \
  --dropout-rate 0.15 --weight-decay 0.1 --n-runs 5 \
  --exp-name final_fep_hot
```

利用可能な引数は `uv run python prepare.py --help` で確認できます。過去の名前付き実験は `EXPERIMENTS.md` と `experiments.yaml` に残していますが、現在の論文結果とは区別してください。

## Repository layout

```text
prepare.py                         data loading, training driver, evaluation
train.py                           ESM-2 multitask model and training loop
data/nbbench/                      fixed 57/114/396 experimental Tm split
data/source_labels/                processed mutation-label tables
data/md/                           processed MD-derived quantities
results/final_*/scaling.json       selected held-out test results
results/tuned_rep/                 compact summaries used by main figures
plot/                              manuscript figure and table builders
paper/tex/                         main and supplementary LaTeX sources
reproduce/manuscript_results.yaml  current reproduction steps
```

## Manuscript

Authors: Taihei Murakami, Kentaro Sasaki, Soichiro Oda, Kazuma Okada, and Yasuhiro Matsunaga.

The public repository is <https://github.com/matsunagalab/sim2real>. The large-data deposit is described in `zenodo/README.md`; its DOI is intentionally left as a placeholder until the record is created.

## License

MIT License
