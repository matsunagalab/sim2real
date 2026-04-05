#!/usr/bin/env python
# coding: utf-8
"""
prepare.py — データ読込・トークナイズ・評価・スケーリング解析

NbBench thermo-tm データセット (train 396, val 57, test 114) を使用。
train.py の train() を呼んで学習を実行し、アンサンブル評価でメトリクスを出力する。

使い方:
    uv run python prepare.py --ddg-source FEP --n-ddg-list 20,80,280 --n-runs 3
    uv run python prepare.py --ddg-source FEP --n-ddg-list 20 --n-runs 1  # 最小テスト
"""

import argparse
import os
import random
import subprocess
import tempfile
import time
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from safetensors.torch import load_file
from scipy.optimize import curve_fit
from scipy.stats import spearmanr, pearsonr
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import RobustScaler, MinMaxScaler
from sklearn.pipeline import make_pipeline
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

# ---- Constants ----
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_NAME = "facebook/esm2_t12_35M_UR50D"
MAX_LENGTH = 160

DDG_PATHS = {
    "FEP": (
        "data/fep/fep1mel_435_processed.csv",
        "data/fep/fep4idl_409_processed.csv",
    ),
    "FoldX": (
        "data/foldX/1mel_all-var_ddg_with_rosettaddg_with_foldx_processed.csv",
        "data/foldX/4idl_all-var_ddg_with_rosettaddg_with_foldx_processed.csv",
    ),
    "rosetta": (
        "data/rosetta/1mel_rosettaddg_processed.csv",
        "data/rosetta/4idl_rosettaddg_processed.csv",
    ),
    "thermoMPNN": (
        "data/mpnn/1melMPNN2_processed.csv",
        "data/mpnn/4idlMPNN2_processed.csv",
    ),
    "rosetta_esm": (
        "data/rosetta_esm1000/esm2_650M_2muts_1mel_100000_top1pct_with_ddg_processed.csv",
        "data/rosetta_esm1000/esm2_650M_2muts_4idl_100000_top1pct_with_ddg_processed.csv",
    ),
    "rosetta_random": (
        "data/rosetta_random1000/random_2mut_1mel_1000_with_ddg_processed.csv",
        "data/rosetta_random1000/random_2mut_4idl_1000_with_ddg_processed.csv",
    ),
}


# ---- Utils ----
def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_tm_scaler():
    """Fit scaler on NbBench train labels (°C -> [0,1])."""
    train_csv = os.path.join(REPO_ROOT, "data", "nbbench", "train.csv")
    train_vals = pd.read_csv(train_csv)["label"].values.reshape(-1, 1)
    scaler = make_pipeline(RobustScaler(), MinMaxScaler(feature_range=(0, 1)))
    scaler.fit(train_vals)
    return scaler


# ---- Data loading ----
def load_and_prepare_datasets(seed: int, n_ddg: int | None = None, ddg_source: str | None = None):
    """Load NbBench Tm data (fixed split) + optional DDG data (seed-sampled)."""
    train_csv = os.path.join(REPO_ROOT, "data", "nbbench", "train.csv")
    val_csv = os.path.join(REPO_ROOT, "data", "nbbench", "val.csv")

    df_train = pd.read_csv(train_csv)
    df_val = pd.read_csv(val_csv)

    # Scale labels to [0,1]
    scaler = get_tm_scaler()
    df_train["label"] = scaler.transform(df_train["label"].values.reshape(-1, 1)).flatten()
    df_val["label"] = scaler.transform(df_val["label"].values.reshape(-1, 1)).flatten()

    # Add task column
    df_train["task"] = 0
    df_val["task"] = 0

    if ddg_source is None or ddg_source == "none":
        return (
            Dataset.from_pandas(df_train[["text", "label", "task"]]),
            Dataset.from_pandas(df_val[["text", "label", "task"]]),
        )

    ddg_1mel_path, ddg_4idl_path = DDG_PATHS[ddg_source]

    dfs_train = [df_train[["text", "label", "task"]]]
    dfs_val = [df_val[["text", "label", "task"]]]
    for task_id, rel_path in [(1, ddg_1mel_path), (2, ddg_4idl_path)]:
        df = pd.read_csv(os.path.join(REPO_ROOT, rel_path))
        if n_ddg is not None:
            df = df.sample(n=min(n_ddg, len(df)), random_state=seed).reset_index(drop=True)
        df = pd.DataFrame({
            'text': df['seq'].tolist(),
            'label': df['ddg_scaled01'].tolist(),
            'task': [task_id] * len(df)
        })
        ds = Dataset.from_pandas(df)
        split = ds.train_test_split(test_size=0.2, seed=seed)
        dfs_train.append(split['train'].to_pandas())
        dfs_val.append(split['test'].to_pandas())

    return (
        Dataset.from_pandas(pd.concat(dfs_train, ignore_index=True)),
        Dataset.from_pandas(pd.concat(dfs_val, ignore_index=True)),
    )


def precompute_embeddings(model, dataset, device, batch_size: int):
    model.eval()
    embeddings_list = []
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            hidden = model.encoder(input_ids=input_ids, attention_mask=attention_mask)[0]
            pooled = hidden[:, 0, :].cpu()
            embeddings_list.append(pooled)
    all_emb = torch.cat(embeddings_list, dim=0)
    emb_ds = Dataset.from_dict({
        "embedding": [all_emb[i].numpy() for i in range(len(all_emb))],
        "labels": [float(x) for x in dataset["label"]],
        "task_ids": [int(x) for x in dataset["task_ids"]],
    })
    emb_ds.set_format(type="torch", columns=["embedding", "labels", "task_ids"])
    return emb_ds


# ---- Evaluation ----
def evaluate_runs(model_dir: str, n_runs: int, device: torch.device):
    """Ensemble evaluation: all models predict on single test set, average predictions."""
    from train import MultiTaskModel
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # Load all models
    models = []
    for i in range(n_runs):
        safetensors_path = os.path.join(model_dir, "supervised", f"mtl_run{i+1}", "model.safetensors")
        state_dict = load_file(safetensors_path, device="cpu")
        model = MultiTaskModel(MODEL_NAME).to(device)
        model.load_state_dict(state_dict, strict=False)
        model.eval()
        models.append(model)

    def predict_raw(model, sequences):
        """Get raw [0,1] predictions from a model."""
        tasks = [0] * len(sequences)
        preds = []
        with torch.no_grad():
            for j in range(0, len(sequences), 32):
                batch_seqs = sequences[j:j+32]
                batch_tasks = torch.tensor(tasks[j:j+32], dtype=torch.long, device=device)
                enc = tokenizer(batch_seqs, padding=True, truncation=True,
                                max_length=MAX_LENGTH, return_tensors="pt").to(device)
                out = model(enc["input_ids"], enc["attention_mask"], task_ids=batch_tasks)
                logits = out.logits if hasattr(out, 'logits') else out['tm']
                preds.extend(logits.cpu().tolist())
        return np.array(preds)

    # Load single test set and scaler
    test_csv = os.path.join(REPO_ROOT, "data", "nbbench", "test.csv")
    df = pd.read_csv(test_csv)
    sequences = df["text"].tolist()
    labels = np.array(df["label"].tolist())  # °C

    scaler = get_tm_scaler()

    # Ensemble: average all models' [0,1] predictions, then inverse transform
    all_preds = np.stack([predict_raw(m, sequences) for m in models])
    ensemble_preds = all_preds.mean(axis=0)
    y_pred = scaler.inverse_transform(ensemble_preds.reshape(-1, 1)).flatten()

    # Compute metrics on ensemble prediction
    residuals = np.abs(y_pred - labels)
    mae = float(np.mean(residuals))
    mse = float(mean_squared_error(labels, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(labels, y_pred))
    sp = float(spearmanr(labels, y_pred).correlation)
    pr = float(pearsonr(labels, y_pred)[0])

    # Return as (1, 6) array for compatibility, plus residuals for bootstrap
    metrics = np.array([[mse, rmse, r2, mae, sp, pr]])
    return metrics, residuals


def bootstrap_ci(residuals, n_boot=10000, alpha=0.10, seed=42):
    """Bootstrap CI over test sample residuals (not over runs)."""
    residuals = np.asarray(residuals)
    residuals = residuals[~np.isnan(residuals)]
    if residuals.size == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    mae_samples = np.array([
        np.mean(rng.choice(residuals, size=len(residuals), replace=True))
        for _ in range(n_boot)
    ])
    return np.mean(residuals), np.percentile(mae_samples, 100 * alpha / 2), np.percentile(mae_samples, 100 * (1 - alpha / 2))


# ---- Scaling law fit ----
def power_law(n, a, b, c):
    return a * n**b + c


def fit_scaling_law(n_ddg_values, mae_means):
    x = np.array([n * 2 for n in n_ddg_values], dtype=float) / 1000.0
    y = np.array(mae_means, dtype=float)

    c0 = float(np.min(y) - 0.02)
    a0 = float(np.max(y) - c0)
    b0 = -0.2
    bounds = ((1e-6, -3.0, min(y) - 1.0), (50.0, -1e-3, max(y) + 1.0))

    try:
        popt, _ = curve_fit(power_law, x, y, p0=[a0, b0, c0], bounds=bounds, maxfev=20000)
        return popt[0], popt[1], popt[2]
    except Exception:
        c_grid = np.linspace(np.min(y) - 0.3, np.min(y) - 1e-3, 600)
        logx = np.log(x)
        best_sse, best_params = np.inf, None
        for c_try in c_grid:
            diff = y - c_try
            if np.any(diff <= 0):
                continue
            X = np.vstack([np.ones_like(logx), logx]).T
            beta, *_ = np.linalg.lstsq(X, np.log(diff), rcond=None)
            a_try, b_try = np.exp(beta[0]), beta[1]
            sse = np.sum((y - (a_try * x**b_try + c_try))**2)
            if sse < best_sse:
                best_sse, best_params = sse, (a_try, b_try, c_try)
        if best_params is None:
            return np.nan, np.nan, np.nan
        return best_params


# ---- Main ----
def main():
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
    os.environ['WANDB_DISABLED'] = 'true'

    parser = argparse.ArgumentParser(description="Run experiment: train → evaluate → scaling metrics")
    parser.add_argument("--ddg-source", type=str, default="FEP",
                        choices=["FEP", "FoldX", "rosetta", "thermoMPNN", "rosetta_esm", "rosetta_random"])
    parser.add_argument("--n-ddg-list", type=str, default="20,80,280",
                        help="Comma-separated n_ddg values")
    parser.add_argument("--n-runs", type=int, default=3, help="Number of runs (model seeds)")
    parser.add_argument("--result-dir", type=str, default=None)
    args = parser.parse_args()

    n_ddg_list = [int(x) for x in args.n_ddg_list.split(",")]
    device = get_device()
    print(f"Device: {device}", flush=True)
    print(f"DDG source: {args.ddg_source}", flush=True)
    print(f"Scaling points: {n_ddg_list}, Runs per point: {args.n_runs}", flush=True)

    from train import train as train_fn
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    result_base = args.result_dir or tempfile.mkdtemp(prefix="sim2real_")
    print(f"Results dir: {result_base}", flush=True)

    mae_means = []
    ci_widths = []

    total_start = time.time()

    for n_ddg in n_ddg_list:
        print(f"\n{'='*60}", flush=True)
        print(f"Scaling point: n_ddg={n_ddg}", flush=True)
        print(f"{'='*60}", flush=True)

        point_dir = os.path.join(result_base, f"n_ddg_{n_ddg}")

        # Train n_runs models (different init seeds, same Tm data, different DDG samples)
        for run in range(1, args.n_runs + 1):
            set_seed(run)
            print(f"\n  [Train] seed={run}, n_ddg={n_ddg}", flush=True)

            train_ds, eval_ds = load_and_prepare_datasets(run, n_ddg=n_ddg, ddg_source=args.ddg_source)
            print(f"    train: {len(train_ds)}, eval: {len(eval_ds)}", flush=True)

            def tokenize_fn(ex):
                return tokenizer(ex['text'], padding='max_length', truncation=True, max_length=MAX_LENGTH)
            train_ds = train_ds.map(tokenize_fn, batched=True, num_proc=4)
            eval_ds = eval_ds.map(tokenize_fn, batched=True, num_proc=4)
            train_ds = train_ds.rename_column("task", "task_ids")
            eval_ds = eval_ds.rename_column("task", "task_ids")
            train_ds.set_format(type='torch', columns=['input_ids', 'attention_mask', 'label', 'task_ids'])
            eval_ds.set_format(type='torch', columns=['input_ids', 'attention_mask', 'label', 'task_ids'])

            train_fn(train_ds, eval_ds, device, run, point_dir, multi_task=True)

        # Evaluate (ensemble of all runs on single test set)
        print(f"\n  [Eval] n_ddg={n_ddg}", flush=True)
        metrics, residuals = evaluate_runs(point_dir, args.n_runs, device)
        mean_mae, lo, hi = bootstrap_ci(residuals)
        ci_w = hi - lo

        mae_means.append(mean_mae)
        ci_widths.append(ci_w)
        print(f"    MAE: {mean_mae:.4f}  90% CI: [{lo:.4f}, {hi:.4f}]  width={ci_w:.4f}", flush=True)

    # Scaling law fit
    print(f"\n{'='*60}", flush=True)
    print("Scaling law analysis", flush=True)
    print(f"{'='*60}", flush=True)

    if len(n_ddg_list) >= 3:
        a, b, c = fit_scaling_law(n_ddg_list, mae_means)
        slope = b
        print(f"  Power law: MAE = {a:.4f} * (n/1000)^{b:.4f} + {c:.4f}", flush=True)
    else:
        slope = np.nan
        print("  (Need >= 3 points for power law fit)", flush=True)

    avg_ci_width = np.mean(ci_widths)
    avg_mae = np.mean(mae_means)

    print(f"\n  slope = {slope:.4f}")
    print(f"  avg_ci_width = {avg_ci_width:.4f}")
    print(f"  avg_mae = {avg_mae:.4f}")
    elapsed = time.time() - total_start
    print(f"  total_time = {elapsed:.0f}s")

    print(f"\nRESULT: slope={slope:.6f} ci_width={avg_ci_width:.6f} mae_mean={avg_mae:.6f}")

    # Append to results.tsv
    results_tsv = os.path.join(REPO_ROOT, "results.tsv")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()
    header = "timestamp\tcommit\tslope\tci_width\tmae_mean\tn_ddg_list\tn_runs\tddg_source\ttime_s\n"
    row = (f"{datetime.now().isoformat(timespec='seconds')}\t{commit}\t{slope:.6f}\t{avg_ci_width:.6f}\t"
           f"{avg_mae:.6f}\t{args.n_ddg_list}\t{args.n_runs}\t{args.ddg_source}\t{elapsed:.0f}\n")

    if not os.path.exists(results_tsv):
        with open(results_tsv, "w") as f:
            f.write(header)
    with open(results_tsv, "a") as f:
        f.write(row)

    print(f"\nResults appended to {results_tsv}")


if __name__ == "__main__":
    main()
