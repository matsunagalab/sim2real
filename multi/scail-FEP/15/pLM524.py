#!/usr/bin/env python
# coding: utf-8

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from safetensors.torch import load_file
from transformers import AutoModel, AutoConfig, AutoTokenizer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr, pearsonr
from tqdm import tqdm


from sklearn.preprocessing import RobustScaler, MinMaxScaler
from sklearn.pipeline import make_pipeline

import seaborn as sns

HUGGINGFACE_BACKBONE = "facebook/esm2_t6_8M_UR50D"


# ---- Device ----
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---- Model class definitions ----
class MultiTaskModel(nn.Module):
    def __init__(self, base_model_name: str, hidden_dropout_prob: float = 0.195):
        super().__init__()
        cfg = AutoConfig.from_pretrained(base_model_name)
        cfg.output_hidden_states = False
        self.encoder = AutoModel.from_pretrained(base_model_name, config=cfg)
        for p in self.encoder.parameters():
            p.requires_grad = False

        hs = self.encoder.config.hidden_size
        p  = hidden_dropout_prob
        self.shared = nn.Sequential(
            nn.Linear(hs, 256),
            nn.ReLU(),
            nn.Dropout(p),

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(p),

            nn.Linear(128, 32),
            nn.ReLU(),    # 最後は Dropout 挟まず
        )

        self.tm_head = nn.Linear(32, 1)
        self.ddg_head = nn.Linear(32, 1)
    def forward(self, input_ids, attention_mask, task_ids):
        # encoder
        hidden = self.encoder(input_ids=input_ids,
                              attention_mask=attention_mask)[0]
        pooled = hidden[:,0,:]                 # CLS token
        feat   = self.shared(pooled)
        tm_logits  = self.tm_head(feat).view(-1)
        ddg_logits = self.ddg_head(feat).view(-1)
        # select by task
        logits = torch.where(task_ids==0, tm_logits, ddg_logits)
        return logits

# ---- Metrics ----
def compute_all_metrics(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    mse      = mean_squared_error(y_true, y_pred)
    rmse     = np.sqrt(mse)
    mae      = mean_absolute_error(y_true, y_pred)
    r2       = r2_score(y_true, y_pred)
    spearman = spearmanr(y_true, y_pred).correlation
    pearson  = pearsonr(y_true, y_pred)[0]
    return mse, rmse, r2, mae, spearman, pearson

metricss = []
for i in range(100):
    # ---- Paths (adjust as needed) ----
    MODEL_SAFETENSORS = "supervised/mtl_run"+ str(i+1) +"/model.safetensors"
    TEST_CSV = "/data2/ssk/ESM2/splitdata/Tm10/splitdata2/merged_"+ str(i+1) +".csv"
    TRAIN_CSV = "/data2/ssk/ESM2/splitdata/Tm10/splitdata/train1-"+ str(i+1) +".csv"
    #/data2/ssk/ESM2/splitdata/Tm10/splitdata/test10-1.csv
    print("Run" +str(i+1) +"Evaluation Results:")
    # ---- Load model ----
    print("Loading model weights...")
    state_dict = load_file(MODEL_SAFETENSORS, device="cpu")
    model = MultiTaskModel(HUGGINGFACE_BACKBONE).to(device)
    model.load_state_dict(state_dict, strict=False)
    model.eval()

    # ---- Load test data ----
    df = pd.read_csv(TEST_CSV)
    sequences = df["text"].tolist()
    labels    = df["label"].tolist()
    # assume CSV has a 'task' column: 0 for Tm, 1 for ddG
    fixed_task_id = 0 # ← ここを 0 または 1 に変えてください
    tasks = [fixed_task_id] * len(df)

    # ---- Tokenizer ----
    tokenizer = AutoTokenizer.from_pretrained(HUGGINGFACE_BACKBONE)

    # ---- Inference ----
    batch_size = 32
    preds = []
    with torch.no_grad():
        for i in tqdm(range(0, len(sequences), batch_size), desc="Evaluating"):
            batch_seqs = sequences[i:i+batch_size]
            batch_tasks= torch.tensor(tasks[i:i+batch_size], dtype=torch.long, device=device)
            enc = tokenizer(batch_seqs, padding=True, truncation=True,
                            max_length=150, return_tensors="pt").to(device)
            logits = model(enc["input_ids"], enc["attention_mask"], batch_tasks)
            preds.extend(logits.cpu().tolist())



    df2 = pd.read_csv(TRAIN_CSV)
    train_values = df2["label"].tolist()

    train_values = np.array(train_values).reshape(-1, 1)
    pipe = make_pipeline(
    RobustScaler(),       # 中央値・IQR ベースでロバストに中心化／スケーリング
    MinMaxScaler(feature_range=(0, 1))  # 最終的に 0–1 範囲へ
    )
    pipe.fit(train_values) # train_values を 2D 配列に変換

    y_pred2 = np.array(preds).reshape(-1, 1)
    y_pred3 = pipe.inverse_transform(y_pred2)
    y_pred4 = y_pred3.flatten().tolist()


    # ---- Plot true vs predicted ----
    y_true = np.array(labels)
    y_pred = np.array(y_pred4)


    # ---- Compute metrics ----
    mse, rmse, r2, mae, spearman, pearson = compute_all_metrics(labels, y_pred4)
    metricss.append([mse, rmse, r2, mae, spearman, pearson])


average = np.array(metricss).mean(axis=0)
print(average)
st = np.array(metricss).std(axis=0, ddof=1)
print(st)

import numpy as np

# --- ブートストラップ関数（百分位法） ---
def bootstrap_ci(x, n_boot=10000, alpha=0.10, seed=42, stat_func=np.mean):
    """
    x: 1次元配列（NaNは事前に取り除く）
    n_boot: ブートストラップ回数
    alpha: 1 - 信頼係数（90%CIなら 0.10）
    stat_func: 統計量（平均など）
    """
    x = np.asarray(x)
    x = x[~np.isnan(x)]  # NaN除去
    if x.size == 0:
        return np.nan, np.nan, np.nan

    rng = np.random.default_rng(seed)
    n = x.shape[0]
    stats = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sample = rng.choice(x, size=n, replace=True)
        stats[i] = stat_func(sample)

    lower = np.percentile(stats, 100 * (alpha / 2))
    upper = np.percentile(stats, 100 * (1 - alpha / 2))
    point = stat_func(x)
    return point, lower, upper

# --- metricss を配列化（形: (runs, 6)） ---
metricss_arr = np.array(metricss, dtype=float)  # 列順: [mse, rmse, r2, mae, spearman, pearson]

metric_names = ["MSE", "RMSE", "R2", "MAE", "Spearman", "Pearson"]

# --- 各指標について平均と90%CIを算出 ---
results = {}
for idx, name in enumerate(metric_names):
    col = metricss_arr[:, idx]
    point, lo, hi = bootstrap_ci(col, n_boot=10000, alpha=0.10, seed=42, stat_func=np.mean)
    results[name] = {"mean": point, "ci90": (lo, hi)}

# --- 表示 ---
print("=== Mean & 90% Bootstrap CI (percentile) ===")
for name in metric_names:
    mean = results[name]["mean"]
    lo, hi = results[name]["ci90"]
    print(f"{name:9s}  mean = {mean: .6f}   90% CI = [{lo: .6f}, {hi: .6f}]")


# =========================
# ここから「保存」機能を最小追加
# =========================
from pathlib import Path

OUTPUT_TXT = "mtl_eval_summary521.txt"  # 固定パスに保存
out_path = Path(OUTPUT_TXT)
out_path.parent.mkdir(parents=True, exist_ok=True)

with open(out_path, "w", encoding="utf-8") as f:
    f.write("=== Mean & 90% Bootstrap CI (percentile) ===\n")
    for name in metric_names:
        mean = results[name]["mean"]
        lo, hi = results[name]["ci90"]
        f.write(f"{name:9s}  mean = {mean: .6f}   90% CI = [{lo: .6f}, {hi: .6f}]\n")
    f.write("\n=== Sample Std (across runs) ===\n")
    for name, std_val in zip(metric_names, st):
        f.write(f"{name:9s}  std  = {std_val: .6f}\n")

print(f"Saved summary averages to: {out_path}")


PER_RUN_CSV = "mtl_eval_per_run_524.csv"

per_run_df = pd.DataFrame(
    metricss,
    columns=["MSE", "RMSE", "R2", "MAE", "Spearman", "Pearson"]
)
per_run_df.insert(0, "run", np.arange(1, len(metricss) + 1))

# 保存（Excel互換性を意識するなら utf-8-sig 推奨）
Path(PER_RUN_CSV).parent.mkdir(parents=True, exist_ok=True)
per_run_df.to_csv(PER_RUN_CSV, index=False, encoding="utf-8-sig")

print(f"Saved per-run metrics to: {PER_RUN_CSV}")