# Research Program: sim2real

## Goal

スケーリング則の傾き（slope）をより急に、ブートストラップ CI 幅をより狭くする。

## Metrics

- **slope**: べき乗則 `MAE(n) = a * (n/1000)^b + c` の `b` パラメータ。より負（急）が良い。
- **ci_width**: 各スケーリング点での MAE 90% CI 幅の平均。より小さいが良い。

## Files

| File | Owner | 説明 |
|------|-------|------|
| `train.py` | Agent | モデル・ハイパラ・学習ループ。**自由に編集可能** |
| `prepare.py` | Human | データ・評価・メトリクス。**変更不可** |
| `program.md` | Human | この研究方針。**変更不可** |
| `results.tsv` | Auto | 実験ログ（自動追記） |

## Constraints

- `prepare.py` は編集しない
- `train.py` のみ編集する
- 新しい依存関係（pip パッケージ）は追加しない
- ESM-2 エンコーダは凍結のまま（`requires_grad = False`）

## What to try

- `train.py` の `HPARAMS` を調整（learning_rate, dropout, weight_decay, loss_weights, batch_size）
- `MultiTaskModel` のアーキテクチャ変更（層の幅・深さ、活性化関数、残差接続）
- 学習スケジューラの変更
- Early stopping の patience 調整

## Loop

```
1. train.py を編集
2. git commit -m "description of change"
3. uv run python prepare.py --ddg-source FEP --n-ddg-list 20,80,280 --n-runs 3 > run.log 2>&1
4. grep "^RESULT:" run.log から slope, ci_width を読む
5. results.tsv に結果が自動追記される
6. 改善なければ git revert HEAD
7. 繰り返し — 止まらず実験を続ける
```

## Quick test (1 point, 1 run)

```bash
uv run python prepare.py --ddg-source FEP --n-ddg-list 20 --n-runs 1
```
