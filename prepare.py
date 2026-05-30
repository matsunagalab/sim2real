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
import json
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
MODEL_NAME = os.environ.get("BASE_MODEL_NAME", "facebook/esm2_t6_8M_UR50D")
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

# MD auxiliary task: single file (1 sequence per nanobody)
# Primary MD task uses task_id=3, optional auxiliary uses task_id=4
MD_PATHS = {
    "MD_Q": "data/md/nanobody_qvalue.csv",                    # all-all Q (115 seqs)
    "MD_Q_HPHIL": "data/md/nanobody_qvalue_hphil.csv",        # hphil-all Q from all-atom MD
    "ROSETTA_Q_HPHIL": "data/md/rosetta_qvalue_hphil.csv",    # hphil-all Q from Rosetta backrub
    "MD_RMSF": "data/md/nanobody_rmsf.csv",                   # mean Cα RMSF from all-atom MD
    "MD_Q_HIGHFLEX": "data/md/feat_q_highflex.csv",           # hphil Q on top-30% RMSF residues (CDR proxy)
    "MD_Q_LOWFLEX": "data/md/feat_q_lowflex.csv",             # hphil Q on bottom-70% RMSF residues (framework proxy)
    "MD_SALTBRIDGE": "data/md/feat_saltbridge.csv",           # native salt-bridge persistence
    # v2 lightweight features (autoresearch round 2):
    "MD_Q_MIN": "data/md/feat_q_min.csv",                     # min frame-wise Q (worst-case unfolding)
    "MD_Q_STD": "data/md/feat_q_std.csv",                     # std of Q over time (fluctuation)
    "MD_Q_SLOPE": "data/md/feat_q_slope.csv",                 # linear slope of Q vs frame index (kinetic)
    "MD_RMSF_MAX": "data/md/feat_rmsf_max.csv",               # max per-Cα RMSF (worst residue's flexibility)
    "MD_RG_STD": "data/md/feat_rg_std.csv",                   # std of radius of gyration (compactness fluctuation)
    # 400K trajectories (prod_002) — wider Q dynamic range
    "MD_Q_HPHIL_400K": "data/md/nanobody_qvalue_hphil_400K.csv",
    # Negative control: same Q distribution, seq->Q mapping shuffled (signal destroyed)
    "MD_Q_HPHIL_400K_SHUF": "data/md/feat_q_hphil_400K_shuffled.csv",
    # Short-trajectory Q (cost analysis): Q from only the first T ns of the 400K run
    "MD_Q_HPHIL_400K_T5":   "data/md/feat_q_hphil_400K_t5ns.csv",
    "MD_Q_HPHIL_400K_T10":  "data/md/feat_q_hphil_400K_t10ns.csv",
    "MD_Q_HPHIL_400K_T17":  "data/md/feat_q_hphil_400K_t17ns.csv",
    "MD_Q_HPHIL_400K_T30":  "data/md/feat_q_hphil_400K_t30ns.csv",
    "MD_Q_HPHIL_400K_T50":  "data/md/feat_q_hphil_400K_t50ns.csv",
    "MD_Q_HPHIL_400K_T100": "data/md/feat_q_hphil_400K_t100ns.csv",
    "MD_Q_MIN_400K": "data/md/feat_q_min_400K.csv",
    "MD_Q_STD_400K": "data/md/feat_q_std_400K.csv",
    "MD_Q_SLOPE_400K": "data/md/feat_q_slope_400K.csv",
    "MD_RMSF_MAX_400K": "data/md/feat_rmsf_max_400K.csv",
    "MD_RG_STD_400K": "data/md/feat_rg_std_400K.csv",
    # Nanobody-specific features (300K)
    "MD_Q_CDR3":         "data/md/feat_q_cdr3.csv",
    "MD_Q_FRAMEWORK":    "data/md/feat_q_framework.csv",
    "MD_RMSF_CDR3":      "data/md/feat_rmsf_cdr3.csv",
    "MD_RMSF_FRAMEWORK": "data/md/feat_rmsf_framework.csv",
    "MD_SS_DIST_MEAN":   "data/md/feat_ss_dist_mean.csv",
    "MD_SS_DIST_STD":    "data/md/feat_ss_dist_std.csv",
    "MD_CDR3_LEN":       "data/md/feat_cdr3_len.csv",
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
def load_and_prepare_datasets(seed: int, n_ddg: int | None = None, ddg_source: str | None = None,
                              n_md: int | None = None, md_source: str | None = None,
                              md_aux_source: str | None = None, n_tm: int | None = None):
    """Load NbBench Tm data (fixed split) + optional DDG (task_id=1,2) + optional MD (task_id=3, +4).

    n_tm: if set, subsample the experimental Tm (task_id=0) training set to this many
    sequences (reference axis for marginal-rate-of-substitution; val/test untouched).
    """
    train_csv = os.path.join(REPO_ROOT, "data", "nbbench", "train.csv")
    val_csv = os.path.join(REPO_ROOT, "data", "nbbench", "val.csv")

    df_train = pd.read_csv(train_csv)
    df_val = pd.read_csv(val_csv)

    # Experimental Tm data scaling (reference for MRS): subsample real training labels.
    if n_tm is not None:
        df_train = df_train.sample(n=min(n_tm, len(df_train)), random_state=seed).reset_index(drop=True)

    # Scale labels to [0,1]
    scaler = get_tm_scaler()
    df_train["label"] = scaler.transform(df_train["label"].values.reshape(-1, 1)).flatten()
    df_val["label"] = scaler.transform(df_val["label"].values.reshape(-1, 1)).flatten()

    # Add task column
    df_train["task"] = 0
    df_val["task"] = 0

    dfs_train = [df_train[["text", "label", "task"]]]
    dfs_val = [df_val[["text", "label", "task"]]]

    # ---- ddG auxiliary tasks (task_id=1,2) ----
    if ddg_source and ddg_source != "none":
        ddg_1mel_path, ddg_4idl_path = DDG_PATHS[ddg_source]
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

    # ---- MD auxiliary tasks: primary (task_id=3) and optional aux (task_id=4) ----
    for task_id, src in [(3, md_source), (4, md_aux_source)]:
        if not src or src == "none":
            continue
        md_path = MD_PATHS[src]
        df = pd.read_csv(os.path.join(REPO_ROOT, md_path))
        if n_md is not None:
            df = df.sample(n=min(n_md, len(df)), random_state=seed).reset_index(drop=True)
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
def evaluate_runs(model_dir: str, n_runs: int, device: torch.device, split: str = "test"):
    """Ensemble evaluation: all models predict on one NbBench split, average predictions."""
    from train import MultiTaskModel, resolve_encoder_mode
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    encoder_mode = resolve_encoder_mode()
    models = []
    for i in range(n_runs):
        safetensors_path = os.path.join(model_dir, "supervised", f"mtl_run{i+1}", "model.safetensors")
        state_dict = load_file(safetensors_path, device="cpu")
        model = MultiTaskModel(MODEL_NAME, encoder_mode=encoder_mode).to(device)
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

    # Load one NbBench split and scaler. Use val for hyperparameter search, test only
    # for final reporting after the search decision is fixed.
    if split not in {"val", "test"}:
        raise ValueError(f"Unknown eval split: {split}")
    split_csv = os.path.join(REPO_ROOT, "data", "nbbench", f"{split}.csv")
    df = pd.read_csv(split_csv)
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


def bootstrap_ci(residuals, n_boot=10000, alpha=0.10, seed=42, trim_pct=0.0):
    """Bootstrap CI over test sample residuals, with optional trimming of top outliers.

    trim_pct: fraction of largest residuals to remove before computing mean (default 10%).
    """
    residuals = np.asarray(residuals)
    residuals = residuals[~np.isnan(residuals)]
    if residuals.size == 0:
        return np.nan, np.nan, np.nan

    def trimmed_mean(x):
        if trim_pct <= 0:
            return np.mean(x)
        cutoff = np.quantile(x, 1.0 - trim_pct)
        return np.mean(x[x <= cutoff])

    rng = np.random.default_rng(seed)
    mae_samples = np.array([
        trimmed_mean(rng.choice(residuals, size=len(residuals), replace=True))
        for _ in range(n_boot)
    ])
    return trimmed_mean(residuals), np.percentile(mae_samples, 100 * alpha / 2), np.percentile(mae_samples, 100 * (1 - alpha / 2))


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
                        choices=["FEP", "FoldX", "rosetta", "thermoMPNN",
                                 "rosetta_esm", "rosetta_random", "none"])
    parser.add_argument("--n-ddg-list", type=str, default="20,80,280",
                        help="Comma-separated n_ddg values (ignored if ddg-source=none)")
    parser.add_argument("--md-source", type=str, default="none",
                        choices=["none", "MD_Q", "MD_Q_HPHIL", "ROSETTA_Q_HPHIL", "MD_RMSF",
                                 "MD_Q_HIGHFLEX", "MD_Q_LOWFLEX", "MD_SALTBRIDGE",
                                 "MD_Q_MIN", "MD_Q_STD", "MD_Q_SLOPE", "MD_RMSF_MAX", "MD_RG_STD",
                                 "MD_Q_HPHIL_400K", "MD_Q_HPHIL_400K_SHUF",
                                 "MD_Q_HPHIL_400K_T5", "MD_Q_HPHIL_400K_T10",
                                 "MD_Q_HPHIL_400K_T17", "MD_Q_HPHIL_400K_T30",
                                 "MD_Q_HPHIL_400K_T50", "MD_Q_HPHIL_400K_T100",
                                 "MD_Q_MIN_400K", "MD_Q_STD_400K", "MD_Q_SLOPE_400K",
                                 "MD_RMSF_MAX_400K", "MD_RG_STD_400K",
                                 "MD_Q_CDR3", "MD_Q_FRAMEWORK",
                                 "MD_RMSF_CDR3", "MD_RMSF_FRAMEWORK",
                                 "MD_SS_DIST_MEAN", "MD_SS_DIST_STD", "MD_CDR3_LEN"],
                        help="Primary MD auxiliary task source (task_id=3)")
    parser.add_argument("--md-aux-source", type=str, default="none",
                        choices=["none", "MD_Q", "MD_Q_HPHIL", "ROSETTA_Q_HPHIL", "MD_RMSF",
                                 "MD_Q_HIGHFLEX", "MD_Q_LOWFLEX", "MD_SALTBRIDGE",
                                 "MD_Q_MIN", "MD_Q_STD", "MD_Q_SLOPE", "MD_RMSF_MAX", "MD_RG_STD",
                                 "MD_Q_HPHIL_400K", "MD_Q_HPHIL_400K_SHUF",
                                 "MD_Q_HPHIL_400K_T5", "MD_Q_HPHIL_400K_T10",
                                 "MD_Q_HPHIL_400K_T17", "MD_Q_HPHIL_400K_T30",
                                 "MD_Q_HPHIL_400K_T50", "MD_Q_HPHIL_400K_T100",
                                 "MD_Q_MIN_400K", "MD_Q_STD_400K", "MD_Q_SLOPE_400K",
                                 "MD_RMSF_MAX_400K", "MD_RG_STD_400K",
                                 "MD_Q_CDR3", "MD_Q_FRAMEWORK",
                                 "MD_RMSF_CDR3", "MD_RMSF_FRAMEWORK",
                                 "MD_SS_DIST_MEAN", "MD_SS_DIST_STD", "MD_CDR3_LEN"],
                        help="Optional 2nd MD task in parallel (task_id=4); 'none' = Q-only")
    parser.add_argument("--n-md-list", type=str, default="",
                        help="Comma-separated n_md values; if set, iterates over these")
    parser.add_argument("--n-tm-list", type=str, default="",
                        help="Comma-separated n_tm (experimental Tm count) values; if set, "
                             "scales the real training set (MRS reference axis). Takes precedence "
                             "over --n-md-list/--n-ddg-list.")
    parser.add_argument("--fixed-n-ddg", type=int, default=None,
                        help="Use this many ddG samples per ddG task while scaling another axis.")
    parser.add_argument("--fixed-n-md", type=int, default=None,
                        help="Use this many MD samples per MD task while scaling another axis.")
    parser.add_argument("--n-runs", type=int, default=3, help="Number of runs (model seeds)")
    parser.add_argument("--result-dir", type=str, default=None)
    parser.add_argument("--train-mode", choices=["mtl", "single"], default="mtl",
                        help="mtl: task-aware MultiTaskModel loss; single: Tm-only loss path "
                             "(only valid without auxiliary data)")
    parser.add_argument("--selection-scope", choices=["mixed", "tm"], default="mixed",
                        help="Validation subset used for best checkpoint / early stopping. "
                             "'tm' uses only task_id=0 rows.")
    # Hyperparameter overrides (mirror env vars; CLI takes precedence).
    parser.add_argument("--encoder-mode", choices=["frozen", "lora", "hot"], default=None,
                        help="Override ENCODER_MODE env var")
    parser.add_argument("--base-model", type=str, default=None,
                        help="Override BASE_MODEL_NAME env var (e.g. facebook/esm2_t33_650M_UR50D)")
    parser.add_argument("--model-arch", choices=["shared", "residual", "dual", "latent", "moe"],
                        default=None, help="Override MODEL_ARCH env var")
    parser.add_argument("--ddg-head-mode", choices=["separate", "shared", "context", "calibrated"],
                        default=None, help="Override DDG_HEAD_MODE env var")
    parser.add_argument("--ddg-context-dim", type=int, default=None,
                        help="Override DDG_CONTEXT_DIM env var (used by ddg-head-mode=context)")
    parser.add_argument("--mtl-weight-mode", choices=["uncertainty", "fixed"], default=None,
                        help="Override MTL_WEIGHT_MODE env var")
    parser.add_argument("--md-weight", type=float, default=None,
                        help="Override MD_WEIGHT env var (used when mtl-weight-mode=fixed)")
    parser.add_argument("--learning-rate", type=float, default=None,
                        help="Override LEARNING_RATE env var for non-encoder params")
    parser.add_argument("--encoder-lr", type=float, default=None,
                        help="Override ENCODER_LR env var for hot-mode encoder params")
    parser.add_argument("--weight-decay", type=float, default=None,
                        help="Override WEIGHT_DECAY env var")
    parser.add_argument("--dropout-rate", type=float, default=None,
                        help="Override DROPOUT_RATE env var")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Override BATCH_SIZE env var")
    parser.add_argument("--warmup-steps", type=int, default=None,
                        help="Override WARMUP_STEPS env var")
    parser.add_argument("--num-train-epochs", type=int, default=None,
                        help="Override NUM_TRAIN_EPOCHS env var")
    parser.add_argument("--early-stopping-patience", type=int, default=None,
                        help="Override EARLY_STOPPING_PATIENCE env var")
    parser.add_argument("--final-eval-split", choices=["val", "test"], default="test",
                        help="Split used by the final ensemble evaluation. Use val for HPO, test for final reporting.")
    parser.add_argument("--exp-name", type=str, default=None,
                        help="Experiment label (used for results/<name>/ output dir and results.tsv)")
    args = parser.parse_args()

    # Apply CLI overrides to env BEFORE importing train (HPARAMS reads env at module load)
    if args.encoder_mode is not None:
        os.environ["ENCODER_MODE"] = args.encoder_mode
    if args.base_model is not None:
        os.environ["BASE_MODEL_NAME"] = args.base_model
        global MODEL_NAME
        MODEL_NAME = args.base_model
    if args.model_arch is not None:
        os.environ["MODEL_ARCH"] = args.model_arch
    if args.ddg_head_mode is not None:
        os.environ["DDG_HEAD_MODE"] = args.ddg_head_mode
    if args.ddg_context_dim is not None:
        os.environ["DDG_CONTEXT_DIM"] = str(args.ddg_context_dim)
    if args.mtl_weight_mode is not None:
        os.environ["MTL_WEIGHT_MODE"] = args.mtl_weight_mode
    if args.md_weight is not None:
        os.environ["MD_WEIGHT"] = str(args.md_weight)
    hparam_env_overrides = {
        "LEARNING_RATE": args.learning_rate,
        "ENCODER_LR": args.encoder_lr,
        "WEIGHT_DECAY": args.weight_decay,
        "DROPOUT_RATE": args.dropout_rate,
        "BATCH_SIZE": args.batch_size,
        "WARMUP_STEPS": args.warmup_steps,
        "NUM_TRAIN_EPOCHS": args.num_train_epochs,
        "EARLY_STOPPING_PATIENCE": args.early_stopping_patience,
    }
    for env_name, value in hparam_env_overrides.items():
        if value is not None:
            os.environ[env_name] = str(value)

    has_aux_requested = (
        args.ddg_source != "none" or
        args.md_source != "none" or
        args.md_aux_source != "none"
    )
    if args.train_mode == "single" and has_aux_requested:
        raise ValueError("--train-mode single is only valid when ddg-source=none, "
                         "md-source=none, and md-aux-source=none")

    # Determine scaling axis: Tm (real-data reference) > MD > ddG.
    use_tm_scaling = bool(args.n_tm_list.strip())
    use_md_scaling = (not use_tm_scaling) and bool(args.n_md_list.strip())
    if use_tm_scaling:
        scaling_list = [int(x) for x in args.n_tm_list.split(",") if x.strip()]
        scaling_name = "n_tm"
    elif use_md_scaling:
        scaling_list = [int(x) for x in args.n_md_list.split(",") if x.strip()]
        scaling_name = "n_md"
    else:
        scaling_list = [int(x) for x in args.n_ddg_list.split(",") if x.strip()]
        scaling_name = "n_ddg"

    device = get_device()
    print(f"Device: {device}", flush=True)
    print(f"DDG source: {args.ddg_source} | MD source: {args.md_source} "
          f"| MD aux: {args.md_aux_source}", flush=True)
    print(f"Train mode: {args.train_mode} | checkpoint selection: {args.selection_scope}",
          flush=True)
    print(f"Scaling ({scaling_name}) points: {scaling_list}, Runs per point: {args.n_runs}", flush=True)

    from train import train as train_fn
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    result_base = args.result_dir or tempfile.mkdtemp(prefix="sim2real_")
    print(f"Results dir: {result_base}", flush=True)

    mae_means = []
    ci_widths = []
    ci_bounds = []  # list of (lo, hi) per scaling point
    all_residuals = {}  # n_ddg -> residuals array (for paired bootstrap)

    total_start = time.time()

    tokenizer_local = tokenizer  # closure binding for inner fn

    for n_val in scaling_list:
        print(f"\n{'='*60}", flush=True)
        print(f"Scaling point: {scaling_name}={n_val}", flush=True)
        print(f"{'='*60}", flush=True)

        point_dir = os.path.join(result_base, f"{scaling_name}_{n_val}")

        # Per-scaling-point n_ddg / n_md / n_tm
        n_ddg_arg = args.fixed_n_ddg if args.fixed_n_ddg is not None else (
            n_val if (not use_tm_scaling and not use_md_scaling) else None
        )
        n_md_arg = args.fixed_n_md if args.fixed_n_md is not None else (
            n_val if use_md_scaling else None
        )
        n_tm_arg = n_val if use_tm_scaling else None
        md_src = args.md_source if args.md_source != "none" else None
        md_aux_src = args.md_aux_source if args.md_aux_source != "none" else None
        ddg_src = args.ddg_source if args.ddg_source != "none" else None

        # Train n_runs models (different init seeds, same Tm data, different aux samples)
        for run in range(1, args.n_runs + 1):
            set_seed(run)
            print(f"\n  [Train] seed={run}, {scaling_name}={n_val}", flush=True)

            train_ds, eval_ds = load_and_prepare_datasets(
                run, n_ddg=n_ddg_arg, ddg_source=ddg_src,
                n_md=n_md_arg, md_source=md_src, md_aux_source=md_aux_src,
                n_tm=n_tm_arg,
            )
            print(f"    train: {len(train_ds)}, eval: {len(eval_ds)}", flush=True)

            def tokenize_fn(ex):
                return tokenizer_local(ex['text'], padding='max_length', truncation=True, max_length=MAX_LENGTH)
            train_ds = train_ds.map(tokenize_fn, batched=True, num_proc=4)
            eval_ds = eval_ds.map(tokenize_fn, batched=True, num_proc=4)
            train_ds = train_ds.rename_column("task", "task_ids")
            eval_ds = eval_ds.rename_column("task", "task_ids")

            trainer_eval_ds = eval_ds
            if args.selection_scope == "tm":
                trainer_eval_ds = eval_ds.filter(lambda ex: int(ex["task_ids"]) == 0)
                print(f"    trainer_eval(selection=tm): {len(trainer_eval_ds)} / raw eval {len(eval_ds)}",
                      flush=True)
            else:
                print(f"    trainer_eval(selection=mixed): {len(trainer_eval_ds)}", flush=True)

            train_ds.set_format(type='torch', columns=['input_ids', 'attention_mask', 'label', 'task_ids'])
            trainer_eval_ds.set_format(type='torch', columns=['input_ids', 'attention_mask', 'label', 'task_ids'])

            train_fn(train_ds, trainer_eval_ds, device, run, point_dir,
                     multi_task=(args.train_mode == "mtl"))

        # Evaluate (ensemble of all runs on single test set)
        print(f"\n  [Eval:{args.final_eval_split}] {scaling_name}={n_val}", flush=True)
        metrics, residuals = evaluate_runs(point_dir, args.n_runs, device, split=args.final_eval_split)
        mean_mae, lo, hi = bootstrap_ci(residuals)
        ci_w = hi - lo

        mae_means.append(mean_mae)
        ci_widths.append(ci_w)
        ci_bounds.append((float(lo), float(hi)))
        all_residuals[n_val] = residuals
        print(f"    MAE: {mean_mae:.4f}  90% CI: [{lo:.4f}, {hi:.4f}]  width={ci_w:.4f}", flush=True)

    # Scaling law fit
    print(f"\n{'='*60}", flush=True)
    print("Scaling law analysis", flush=True)
    print(f"{'='*60}", flush=True)

    if len(scaling_list) >= 3:
        a, b, c = fit_scaling_law(scaling_list, mae_means)
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

    # ---- Paired bootstrap: ΔMAE with shared sample indices ----
    paired_per_n = []   # captured for JSON output
    delta_full_mean = float("nan")
    delta_full_lo = float("nan")
    delta_full_hi = float("nan")
    p_full = float("nan")
    if len(scaling_list) >= 2:
        print(f"\n{'='*60}", flush=True)
        print("Paired bootstrap: ΔMAE significance", flush=True)
        print(f"{'='*60}", flush=True)

        n_boot = 10000
        rng = np.random.default_rng(42)
        n_samples = len(all_residuals[scaling_list[0]])
        boot_idx = rng.integers(0, n_samples, size=(n_boot, n_samples))

        # Bootstrap MAE at each scaling point using SAME indices
        boot_maes = {}
        for n in scaling_list:
            r = all_residuals[n]
            boot_maes[n] = np.array([np.mean(r[idx]) for idx in boot_idx])

        # Pairwise ΔMAE (scaling[i] - scaling[0]), testing if significantly < 0
        print(f"  ΔMAE vs {scaling_name}={scaling_list[0]} (paired bootstrap):")
        print(f"  {scaling_name:>8s}  {'ΔMAE':>8s}  {'90% CI':>20s}  {'p(Δ>0)':>8s}")
        ref = boot_maes[scaling_list[0]]
        for n in scaling_list[1:]:
            delta = boot_maes[n] - ref
            lo_d, hi_d = np.percentile(delta, [5, 95])
            p_positive = float(np.mean(delta > 0))
            print(f"  {n:>8d}  {np.mean(delta):>+8.4f}  [{lo_d:>+7.4f}, {hi_d:>+7.4f}]  {p_positive:>8.4f}")
            paired_per_n.append({
                "n": int(n), "delta_mae": float(np.mean(delta)),
                "delta_ci_lo": float(lo_d), "delta_ci_hi": float(hi_d),
                "p_positive": p_positive,
            })

        # Full range comparison
        delta_full = boot_maes[scaling_list[-1]] - boot_maes[scaling_list[0]]
        lo_f, hi_f = np.percentile(delta_full, [5, 95])
        delta_full_mean = float(np.mean(delta_full))
        delta_full_lo = float(lo_f)
        delta_full_hi = float(hi_f)
        p_full = float(np.mean(delta_full > 0))
        print(f"\n  Full range ({scaling_name}={scaling_list[0]}→{scaling_list[-1]}):")
        print(f"    ΔMAE = {delta_full_mean:+.4f}°C  90% CI=[{delta_full_lo:+.4f}, {delta_full_hi:+.4f}]")
        print(f"    p(ΔMAE > 0) = {p_full:.4f}  (one-sided test of no-improvement)")
        if p_full < 0.05:
            print(f"    → 有意 (p < 0.05)")
        elif p_full < 0.10:
            print(f"    → 限界的有意 (p < 0.10)")
        else:
            print(f"    → 有意でない")

    print(f"\nRESULT: slope={slope:.6f} ci_width={avg_ci_width:.6f} mae_mean={avg_mae:.6f}")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, cwd=REPO_ROOT).stdout.strip()

    # ---- Structured JSON output: results/<exp-name>/scaling.json ----
    from train import HPARAMS as train_hparams
    from train import resolve_encoder_mode as _resolve_em
    exp_name = args.exp_name or "anonymous"
    out_dir = os.path.join(REPO_ROOT, "results", exp_name)
    os.makedirs(out_dir, exist_ok=True)
    best_idx = int(np.argmin(mae_means)) if mae_means else 0
    structured = {
        "exp_name": args.exp_name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "git_commit": commit,
        "args": vars(args),
        "env": {k: os.environ.get(k) for k in
                ["ENCODER_MODE", "BASE_MODEL_NAME", "MTL_WEIGHT_MODE", "MD_WEIGHT",
                 "MODEL_ARCH", "DDG_HEAD_MODE", "DDG_CONTEXT_DIM", "DETACH_AUX_ENCODER",
                 "LEARNING_RATE", "ENCODER_LR", "WEIGHT_DECAY", "DROPOUT_RATE",
                 "BATCH_SIZE", "WARMUP_STEPS", "NUM_TRAIN_EPOCHS",
                 "EARLY_STOPPING_PATIENCE"]},
        "resolved_encoder_mode": _resolve_em(),
        "hparams": {k: v for k, v in train_hparams.items()},
        "scaling": [
            {"n": int(n), "mae": float(m),
             "ci_lo": float(lo), "ci_hi": float(hi), "ci_width": float(hi - lo),
             "abs_errors": [float(x) for x in all_residuals[n]]}
            for n, m, (lo, hi) in zip(scaling_list, mae_means, ci_bounds)
        ],
        "best": {
            "n": int(scaling_list[best_idx]),
            "mae": float(mae_means[best_idx]),
            "ci_width": float(ci_bounds[best_idx][1] - ci_bounds[best_idx][0]),
        },
        "summary": {
            "slope": float(slope) if not (isinstance(slope, float) and np.isnan(slope)) else None,
            "ci_width_avg": float(avg_ci_width),
            "mae_avg": float(avg_mae),
            "elapsed_s": float(elapsed),
        },
        "paired_bootstrap": {
            "ref_n": int(scaling_list[0]) if scaling_list else None,
            "per_n": paired_per_n,
            "full_range": {
                "from": int(scaling_list[0]) if scaling_list else None,
                "to": int(scaling_list[-1]) if scaling_list else None,
                "delta_mae": delta_full_mean,
                "delta_ci_lo": delta_full_lo,
                "delta_ci_hi": delta_full_hi,
                "p_positive": p_full,
            },
        },
    }
    json_path = os.path.join(out_dir, "scaling.json")
    with open(json_path, "w") as f:
        json.dump(structured, f, indent=2, default=str)
    print(f"\nStructured results: {json_path}")

    # ---- Append to results.tsv (extended schema; existing rows leave new cols empty) ----
    results_tsv = os.path.join(REPO_ROOT, "results.tsv")
    header = ("timestamp\tcommit\tslope\tci_width\tmae_mean\tn_ddg_list\tn_runs\tddg_source\t"
              "time_s\tmd_source\tn_md_list\t"
              "encoder_mode\tbase_model\tmd_aux_source\tmtl_weight_mode\tmd_weight\texp_name\n")
    if use_tm_scaling:
        scaling_str = args.n_tm_list
    elif use_md_scaling:
        scaling_str = args.n_md_list
    else:
        scaling_str = args.n_ddg_list
    extras = (
        f"{_resolve_em()}\t"
        f"{train_hparams.get('base_model_name', '')}\t"
        f"{args.md_aux_source}\t"
        f"{train_hparams.get('mtl_weight_mode', '')}\t"
        f"{train_hparams.get('md_weight', '')}\t"
        f"{exp_name}"
    )
    row = (f"{datetime.now().isoformat(timespec='seconds')}\t{commit}\t{slope:.6f}\t{avg_ci_width:.6f}\t"
           f"{avg_mae:.6f}\t{scaling_str if not use_md_scaling else ''}\t{args.n_runs}\t{args.ddg_source}\t"
           f"{elapsed:.0f}\t{args.md_source}\t{args.n_md_list}\t{extras}\n")

    if not os.path.exists(results_tsv):
        with open(results_tsv, "w") as f:
            f.write(header)
    else:
        # Migrate header if it's the old 11-col version
        with open(results_tsv) as f:
            current_header = f.readline()
        if current_header.count("\t") < 16:
            # leave existing rows as-is; just ensure new appends use new schema
            pass
    with open(results_tsv, "a") as f:
        f.write(row)

    print(f"\nResults appended to {results_tsv}")


if __name__ == "__main__":
    main()
