#!/usr/bin/env python
# coding: utf-8

import argparse
import os
import sys

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from safetensors.torch import load_file
from transformers import AutoTokenizer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import spearmanr, pearsonr
from tqdm import tqdm
from sklearn.preprocessing import RobustScaler, MinMaxScaler
from sklearn.pipeline import make_pipeline
from pathlib import Path

# MultiTaskModel を ESM.py からインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ESM import MultiTaskModel

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
HUGGINGFACE_BACKBONE = "facebook/esm2_t6_8M_UR50D"


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


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained models on test523 dataset")
    parser.add_argument("--n-runs", type=int, default=None,
                        help="評価するrun数。省略時はsupervised/mtl_run*を自動検出")
    parser.add_argument("--model-dir", type=str, default=".",
                        help="supervised/mtl_run* があるディレクトリ（デフォルト: カレント）")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="結果出力先（デフォルト: model-dir）")
    args = parser.parse_args()

    model_dir = args.model_dir
    output_dir = args.output_dir or model_dir

    # run数の自動検出
    if args.n_runs is not None:
        n_runs = args.n_runs
    else:
        supervised_dir = os.path.join(model_dir, "supervised")
        if os.path.isdir(supervised_dir):
            run_dirs = sorted([
                d for d in os.listdir(supervised_dir)
                if d.startswith("mtl_run") and os.path.isdir(os.path.join(supervised_dir, d))
            ])
            n_runs = len(run_dirs)
        else:
            n_runs = 5
    print(f"Evaluating {n_runs} runs from {model_dir}", flush=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(HUGGINGFACE_BACKBONE)

    metricss = []
    for i in range(n_runs):
        MODEL_SAFETENSORS = os.path.join(model_dir, "supervised", f"mtl_run{i+1}", "model.safetensors")
        TEST_CSV = os.path.join(REPO_ROOT, "data", "Tm", "Tm10per", f"test523_{i+1}.csv")
        TRAIN_CSV = os.path.join(REPO_ROOT, "data", "Tm", "Tm10per", f"train1-{i+1}.csv")

        print(f"Run {i+1} Evaluation Results:")

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
        fixed_task_id = 0
        tasks = [fixed_task_id] * len(df)

        # ---- Inference ----
        batch_size = 32
        preds = []
        with torch.no_grad():
            for j in tqdm(range(0, len(sequences), batch_size), desc="Evaluating"):
                batch_seqs = sequences[j:j+batch_size]
                batch_tasks= torch.tensor(tasks[j:j+batch_size], dtype=torch.long, device=device)
                enc = tokenizer(batch_seqs, padding=True, truncation=True,
                                max_length=150, return_tensors="pt").to(device)
                out = model(enc["input_ids"], enc["attention_mask"],
                            task_ids=batch_tasks)
                if hasattr(out, 'logits'):
                    logits = out.logits
                else:
                    logits = out['tm']
                preds.extend(logits.cpu().tolist())

        df2 = pd.read_csv(TRAIN_CSV)
        train_values = df2["label"].tolist()

        train_values = np.array(train_values).reshape(-1, 1)
        pipe = make_pipeline(
            RobustScaler(),
            MinMaxScaler(feature_range=(0, 1))
        )
        pipe.fit(train_values)

        y_pred2 = np.array(preds).reshape(-1, 1)
        y_pred3 = pipe.inverse_transform(y_pred2)
        y_pred4 = y_pred3.flatten().tolist()

        # ---- Compute metrics ----
        mse, rmse, r2, mae, spearman, pearson = compute_all_metrics(labels, y_pred4)
        metricss.append([mse, rmse, r2, mae, spearman, pearson])

    average = np.array(metricss).mean(axis=0)
    print(average)
    st = np.array(metricss).std(axis=0, ddof=1)
    print(st)

    # --- ブートストラップ関数（百分位法） ---
    def bootstrap_ci(x, n_boot=10000, alpha=0.10, seed=42, stat_func=np.mean):
        x = np.asarray(x)
        x = x[~np.isnan(x)]
        if x.size == 0:
            return np.nan, np.nan, np.nan
        rng = np.random.default_rng(seed)
        n = x.shape[0]
        stats = np.empty(n_boot, dtype=float)
        for j in range(n_boot):
            sample = rng.choice(x, size=n, replace=True)
            stats[j] = stat_func(sample)
        lower = np.percentile(stats, 100 * (alpha / 2))
        upper = np.percentile(stats, 100 * (1 - alpha / 2))
        point = stat_func(x)
        return point, lower, upper

    metricss_arr = np.array(metricss, dtype=float)
    metric_names = ["MSE", "RMSE", "R2", "MAE", "Spearman", "Pearson"]

    results = {}
    for idx, name in enumerate(metric_names):
        col = metricss_arr[:, idx]
        point, lo, hi = bootstrap_ci(col, n_boot=10000, alpha=0.10, seed=42, stat_func=np.mean)
        results[name] = {"mean": point, "ci90": (lo, hi)}

    print("=== Mean & 90% Bootstrap CI (percentile) ===")
    for name in metric_names:
        mean = results[name]["mean"]
        lo, hi = results[name]["ci90"]
        print(f"{name:9s}  mean = {mean: .6f}   90% CI = [{lo: .6f}, {hi: .6f}]")

    # ---- 保存 ----
    OUTPUT_TXT = os.path.join(output_dir, "mtl_eval_summary523.txt")
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

    PER_RUN_CSV = os.path.join(output_dir, "mtl_eval_per_run_523.csv")
    per_run_df = pd.DataFrame(
        metricss,
        columns=["MSE", "RMSE", "R2", "MAE", "Spearman", "Pearson"]
    )
    per_run_df.insert(0, "run", np.arange(1, len(metricss) + 1))
    Path(PER_RUN_CSV).parent.mkdir(parents=True, exist_ok=True)
    per_run_df.to_csv(PER_RUN_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved per-run metrics to: {PER_RUN_CSV}")


if __name__ == "__main__":
    main()
