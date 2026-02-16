import numpy as np
import pandas as pd
from pathlib import Path

# ====== 設定項目 ======
PER_RUN_CSV = "mtl_eval_per_run_523.csv"  # 先ほど出力したCSV
# 選び方: "first"（先頭からN本）, "random"（無作為にN本）, "specific"（指定ランのみ）
SELECT_MODE = "first"
NUM_RUNS = 100               # "first"/"random" のときに使う本数
start_run = 1
end_run = 12

SPECIFIC_RUNS = [1, 5, 7]   # "specific" のときに使う run 番号（CSVの run 列）
CONF_LEVEL = 0.90           # 信頼係数（例: 0.90 で 90%CI）
N_BOOT = 10000              # ブートストラップ回数
SEED = 42                   # 乱数シード（再現性）
# 保存するなら True（任意）
SAVE_SUMMARY = True
SUMMARY_TXT = "mtl_eval_subset_summary_523_1-12.txt"
# ======================

RNG = np.random.default_rng(SEED)

# --- ブートストラップ（百分位法、平均のCI） ---
def bootstrap_ci_mean(x, n_boot=10000, conf_level=0.90, seed=42):
    """
    x: 1次元配列（NaNは事前に除去）
    conf_level: 信頼係数（0.90なら90%CI）
    戻り値: (point_mean, lower, upper)
    """
    x = np.asarray(x)
    x = x[~np.isnan(x)]
    if x.size == 0:
        return np.nan, np.nan, np.nan

    rng = np.random.default_rng(seed)
    n = x.shape[0]
    stats = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = rng.choice(x, size=n, replace=True)
        stats[i] = sample.mean()

    alpha = 1.0 - conf_level
    lo = np.percentile(stats, 100 * (alpha / 2))
    hi = np.percentile(stats, 100 * (1 - alpha / 2))
    return float(x.mean()), float(lo), float(hi)

# --- CSV読み込み ---
df = pd.read_csv(PER_RUN_CSV)

# 必須列チェック
required_cols = ["run", "MSE", "RMSE", "R2", "MAE", "Spearman", "Pearson"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"必要な列がCSVにありません: {missing}")

# --- サブセットの決め方 ---
df_sel = None
if SELECT_MODE == "first":
    if NUM_RUNS > len(df):
        raise ValueError(f"NUM_RUNS={NUM_RUNS} が総ラン数 {len(df)} を超えています。")
    # 例：101〜200 の範囲で抽出（inclusive）

    df_sel = df[(df["run"] >= start_run) & (df["run"] <= end_run)].sort_values("run")

    #df_sel = df.sort_values("run").head(NUM_RUNS)

elif SELECT_MODE == "random":
    if NUM_RUNS > len(df):
        raise ValueError(f"NUM_RUNS={NUM_RUNS} が総ラン数 {len(df)} を超えています。")
    # 置換なし無作為抽出
    idx = RNG.choice(df.index.values, size=NUM_RUNS, replace=False)
    df_sel = df.loc[idx].sort_values("run")

elif SELECT_MODE == "specific":
    # 指定run番号のみ
    df_sel = df[df["run"].isin(SPECIFIC_RUNS)].sort_values("run")
    if len(df_sel) == 0:
        raise ValueError(f"SPECIFIC_RUNS={SPECIFIC_RUNS} に一致する行が見つかりません。")
else:
    raise ValueError('SELECT_MODE は "first" / "random" / "specific" のいずれかにしてください。')

print(f"選択されたラン本数: {len(df_sel)}")
print(f"run一覧: {df_sel['run'].tolist()}")

metrics = ["MSE", "RMSE", "R2", "MAE", "Spearman", "Pearson"]

# --- 統計計算 ---
rows = []
for m in metrics:
    col = df_sel[m].astype(float).to_numpy()

    # 平均・標準偏差（NaNは除去）
    col_no_nan = col[~np.isnan(col)]
    mean_val = float(col_no_nan.mean()) if col_no_nan.size else np.nan
    std_val  = float(col_no_nan.std(ddof=1)) if col_no_nan.size > 1 else np.nan

    # ブートストラップCI（平均）
    point, lo, hi = bootstrap_ci_mean(
        col_no_nan,
        n_boot=N_BOOT,
        conf_level=CONF_LEVEL,
        seed=SEED
    )

    rows.append({
        "Metric": m,
        "Mean": mean_val,
        "Std": std_val,
        f"{int(CONF_LEVEL*100)}%CI_Lower": lo,
        f"{int(CONF_LEVEL*100)}%CI_Upper": hi,
        "NumRuns": len(col_no_nan)
    })

summary_df = pd.DataFrame(rows, columns=[
    "Metric", "Mean", "Std",
    f"{int(CONF_LEVEL*100)}%CI_Lower", f"{int(CONF_LEVEL*100)}%CI_Upper",
    "NumRuns"
])

# --- 表示 ---
print("\n=== Subset Summary ===")
print(summary_df.to_string(index=False))

# --- 保存（任意） ---
if SAVE_SUMMARY:
    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write(f"Runs used ({len(df_sel)}): {df_sel['run'].tolist()}\n")
        f.write(summary_df.to_csv(index=False))
    print(f"\nSaved subset summary to: {SUMMARY_TXT}")
