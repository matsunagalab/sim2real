#!/usr/bin/env python
# coding: utf-8

import os
import sys
import random
import time
import gc
from datetime import timedelta

import numpy as np
import torch
import torch.nn as nn
from transformers import (
    Trainer,
    TrainingArguments,
    AutoModel,
    AutoTokenizer,
    AutoConfig,
    PreTrainedModel,
    PretrainedConfig,
    TrainerCallback,
    TrainerState,
    TrainerControl,
    EarlyStoppingCallback,
)
from transformers.modeling_outputs import SequenceClassifierOutput
from datasets import Dataset
from torch.utils.data import DataLoader
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import json

# ---- Environment variables ----
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
os.environ['WANDB_DISABLED'] = 'true'
#os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# ---- Constants (adjust paths) ----
MODEL_NAME = "facebook/esm2_t6_8M_UR50D"
SELF_SUPERVISED_MODEL_PATH = "facebook/esm2_t6_8M_UR50D"

DATA_PATH_TM = None      # TmデータCSV
DATA_PATH_DDG_1mel = None  # ΔΔGデータCSV
DATA_PATH_DDG_4idl = None  # ΔΔGデータCSV
DATA_PATH_TM_TEST = None  # TmデータCSV


HPARAMS = {
    "num_train_epochs": 400,
    "batch_size": 8,
    "learning_rate": 2e-4,
    "weight_decay": 0.0637,
    "dropout_rate": 0.195,
    "seed": None,

    "early_stopping_patience": 10,
    "early_stopping_threshold": 0.0,

    "n_ddg": None,  # 訓練に使うddgデータ数（1mel/4idlそれぞれ）。Noneのときは全件使用
}


    


# ---- Utils ----
def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def format_time(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, rem = divmod(td.seconds, 3600)
    mins, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}日 {hours}時間 {mins}分 {secs}秒"
    if hours > 0:
        return f"{hours}時間 {mins}分 {secs}秒"
    return f"{mins}分 {secs}秒"


def load_and_prepare_datasets(seed: int, n_ddg: int | None = None):
    DATA_PATH_TM = "/data2/ssk/githubtest/sim2real/data/Tm/Tm10per/train2-"+ str(seed)+".csv"      # TmデータCSV
    DATA_PATH_DDG_1mel = "/data2/ssk/githubtest/sim2real/data/foldX/1mel_all-var_ddg_with_rosettaddg_with_foldx_processed.csv"   #ΔΔGデータCSV
    DATA_PATH_DDG_4idl = "/data2/ssk/githubtest/sim2real/data/foldX/4idl_all-var_ddg_with_rosettaddg_with_foldx_processed.csv"   #ΔΔGデータCSV

    # Tm
    df_tm = pd.read_csv(DATA_PATH_TM)
    df_tm = pd.DataFrame({
        'text': df_tm['text'].tolist(),
        'label': df_tm['label'].tolist(),
        'task': [0] * len(df_tm)  # Tm の task_id = 0
    })
    ds_tm = Dataset.from_pandas(df_tm)

    split_tm = ds_tm.train_test_split(test_size=0.2, seed=seed)
    train_ds_tm = split_tm['train']
    val_ds_tm = split_tm['test']

    # 1mel（n_ddg指定時はサンプリング、未指定時は全件）
    df_ddg1 = pd.read_csv(DATA_PATH_DDG_1mel)
    if n_ddg is not None:
        n_sample = min(n_ddg, len(df_ddg1))
        df_ddg1 = df_ddg1.sample(n=n_sample, random_state=seed).reset_index(drop=True)
    df_ddg1 = pd.DataFrame({
        'text': df_ddg1['seq'].tolist(),
        'label': df_ddg1['ddg_scaled01'].tolist(),
        'task': [1] * len(df_ddg1)   # 1mel の task_id = 1
    })
    ds_ddg1 = Dataset.from_pandas(df_ddg1)
    split_ddg1 = ds_ddg1.train_test_split(test_size=0.2, seed=seed)
    train_ds_ddg1 = split_ddg1['train']
    val_ds_ddg1 = split_ddg1['test']

    # 4idl（n_ddg指定時はサンプリング、未指定時は全件）
    df_ddg2 = pd.read_csv(DATA_PATH_DDG_4idl)
    if n_ddg is not None:
        n_sample = min(n_ddg, len(df_ddg2))
        df_ddg2 = df_ddg2.sample(n=n_sample, random_state=seed).reset_index(drop=True)
    df_ddg2 = pd.DataFrame({
        'text': df_ddg2['seq'].tolist(),
        'label': df_ddg2['ddg_scaled01'].tolist(),
        'task': [2] * len(df_ddg2)   # 4idl の task_id = 2
    })
    ds_ddg2 = Dataset.from_pandas(df_ddg2)
    split_ddg2 = ds_ddg2.train_test_split(test_size=0.2, seed=seed)
    train_ds_ddg2 = split_ddg2['train']
    val_ds_ddg2 = split_ddg2['test']


    df_train_combined = pd.concat(
        [
            train_ds_tm.to_pandas(),
            train_ds_ddg1.to_pandas(),
            train_ds_ddg2.to_pandas(),
        ],
        ignore_index=True
    )
    df_val_combined = pd.concat(
        [
            val_ds_tm.to_pandas(),
            val_ds_ddg1.to_pandas(),
            val_ds_ddg2.to_pandas(),
        ],
        ignore_index=True
    )

    train_ds = Dataset.from_pandas(df_train_combined)
    val_ds = Dataset.from_pandas(df_val_combined)


    return train_ds, val_ds


def precompute_embeddings(model, dataset, device, batch_size: int):
    """Run frozen encoder once to get embeddings; return Dataset with embedding, label, task_ids."""
    model.eval()
    embeddings_list = []
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    total_batches = (len(dataset) + batch_size - 1) // batch_size
    with torch.no_grad():
        for bi, batch in enumerate(loader):
            if (bi + 1) % 10 == 0 or bi == 0 or bi == total_batches - 1:
                print(f"      embedding batch {bi + 1}/{total_batches}", flush=True)
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            hidden = model.encoder(input_ids=input_ids, attention_mask=attention_mask)[0]
            pooled = hidden[:, 0, :].cpu()
            embeddings_list.append(pooled)
    all_emb = torch.cat(embeddings_list, dim=0)
    emb_ds = Dataset.from_dict({
        "embedding": [all_emb[i].numpy() for i in range(len(all_emb))],
        "labels": dataset["label"],
        "task_ids": dataset["task_ids"],
    })
    emb_ds.set_format(type="torch", columns=["embedding", "labels", "task_ids"])
    return emb_ds


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
        self.ddg_head2 = nn.Linear(32, 1)

        self.loss_fn = nn.MSELoss()
        

    def forward(self, input_ids=None, attention_mask=None,
                labels=None, task_ids=None, embedding=None, **kwargs):
        if embedding is not None:
            pooled = embedding
        else:
            hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask)[0]
            pooled = hidden[:, 0, :]

        feats = self.shared(pooled)

        tm_logits = self.tm_head(feats).view(-1)
        ddg_logits = self.ddg_head(feats).view(-1)
        ddg_logits2 = self.ddg_head2(feats).view(-1)

        if task_ids is not None:
            logits = torch.zeros_like(tm_logits)
            mask_tm = task_ids == 0
            mask_ddg = task_ids == 1
            mask_ddg2 = task_ids == 2
            logits[mask_tm] = tm_logits[mask_tm]
            logits[mask_ddg] = ddg_logits[mask_ddg]
            logits[mask_ddg2] = ddg_logits2[mask_ddg2]

            loss = None
            if labels is not None:
                losses = []
                # Tm 損失に重み
                if mask_tm.any():
                    losses.append((1/2)*self.loss_fn(tm_logits[mask_tm], labels[mask_tm]))
                # ΔΔG 損失に重み
                if mask_ddg.any():
                    losses.append((1/4) * self.loss_fn(ddg_logits[mask_ddg], labels[mask_ddg]))
                if mask_ddg2.any():
                    losses.append((1/4) * self.loss_fn(ddg_logits2[mask_ddg2], labels[mask_ddg2]))
                # どちらのマスクも空ならゼロテンソルを返す
                if losses:
                    loss = sum(losses)
                else:
                    loss = torch.tensor(0.0, device=tm_logits.device)
                
            return SequenceClassifierOutput(loss=loss, logits=logits)

        return {'tm': tm_logits, 'ddg': ddg_logits , 'ddg2': ddg_logits2}

# ---- Callback: log progress so we know how far we got ----
class ProgressLoggingCallback(TrainerCallback):
    def on_train_begin(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        print("      Training started (first step will run next).", flush=True)
        return control

    def on_step_end(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        step = state.global_step
        if step == 1:
            print("      First training step completed.", flush=True)
        elif step % 100 == 0:
            print(f"      Step {step}/{state.max_steps} completed.", flush=True)
        return control

    def on_epoch_end(self, args, state: TrainerState, control: TrainerControl, **kwargs):
        print(f"      Epoch {int(state.epoch)}/{int(args.num_train_epochs)} finished.", flush=True)
        return control


# ---- Metrics ----
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.flatten()
    mse = mean_squared_error(labels, preds)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(labels, preds)
    r2 = r2_score(labels, preds)
    return {'mse': mse, 'rmse': rmse, 'mae': mae, 'r2': r2}

# ---- Main ----
def main():
    if len(sys.argv) < 2:
        print("Usage: python ESM.py <run_num> [n_ddg]")
        print("  run_num: 実行番号（シード等に使用）")
        print("  n_ddg:   訓練に使うddgデータ数（1mel/4idlそれぞれ）。省略時は全件使用")
        sys.exit(1)
    run = int(sys.argv[1])
    n_ddg = int(sys.argv[2]) if len(sys.argv) >= 3 else HPARAMS.get("n_ddg")
    HPARAMS['seed'] = run
    HPARAMS['n_ddg'] = n_ddg
    set_seed(run)

    # load & split
    print("[1/6] Loading and splitting datasets...", flush=True)
    train_ds, eval_ds = load_and_prepare_datasets(run, n_ddg=n_ddg)
    print(f"      train: {len(train_ds)} samples, eval: {len(eval_ds)} samples", flush=True)

    # tokenize
    print("[2/6] Tokenizing...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    def tokenize_fn(ex):
        return tokenizer(ex['text'], padding='max_length', truncation=True, max_length=150)
    train_ds = train_ds.map(tokenize_fn, batched=True, num_proc=4)
    eval_ds = eval_ds.map(tokenize_fn, batched=True, num_proc=4)

    # rename & format
    train_ds = train_ds.rename_column("task", "task_ids")
    eval_ds = eval_ds.rename_column("task", "task_ids")
    train_ds.set_format(type='torch', columns=['input_ids','attention_mask','label','task_ids'])
    eval_ds.set_format(type='torch', columns=['input_ids','attention_mask','label','task_ids'])
    print("      done.", flush=True)

    print("[3/6] Building model and moving to device...", flush=True)
    model = MultiTaskModel(
        base_model_name=SELF_SUPERVISED_MODEL_PATH,
        hidden_dropout_prob=HPARAMS['dropout_rate']
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    print(f"      device: {device}", flush=True)

    # Precompute embeddings once (encoder is frozen, so no need to recompute each epoch)
    print("[4/6] Precomputing train embeddings...", flush=True)
    t0 = time.time()
    train_ds = precompute_embeddings(
        model, train_ds, device, HPARAMS["batch_size"]
    )
    print(f"      done in {format_time(time.time() - t0)}", flush=True)
    print("[5/6] Precomputing eval embeddings...", flush=True)
    t0 = time.time()
    eval_ds = precompute_embeddings(
        model, eval_ds, device, HPARAMS["batch_size"]
    )
    print(f"      done in {format_time(time.time() - t0)}", flush=True)

    # trainer args（結果保存先: 環境変数 RESULT_DIR が指定されていればその下、なければカレント）
    result_base = os.environ.get("RESULT_DIR", ".")
    ckpt_dir = os.path.join(result_base, "supervised", f"mtl_run{run}")
    os.makedirs(ckpt_dir, exist_ok=True)
    logging_dir = os.path.join(result_base, "supervised", "logs")

    targs = TrainingArguments(
        output_dir=ckpt_dir,
        num_train_epochs=HPARAMS['num_train_epochs'],
        per_device_train_batch_size=HPARAMS['batch_size'],
        per_device_eval_batch_size=HPARAMS['batch_size'],
        evaluation_strategy="epoch",         # 毎エポック評価
        save_strategy="epoch",               # 毎エポック保存

        learning_rate=HPARAMS['learning_rate'],
        weight_decay=HPARAMS['weight_decay'],
        logging_dir=logging_dir,
        logging_steps=10,

        load_best_model_at_end=True,         # ベストモデルを最後に自動読み込み
        metric_for_best_model="eval_mse",        # 指標に mse を使う
        greater_is_better=False,             # mse は小さいほうが良い
        save_total_limit=1,                  # 最大１つだけチェックポイントを残す
        warmup_steps=100,
        optim="adamw_torch",
        
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    #early_cb = EarlyStoppingCallback(
    #early_stopping_patience=HPARAMS["early_stopping_patience"],
    #early_stopping_threshold=HPARAMS["early_stopping_threshold"],
    #)

    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
        callbacks=[ProgressLoggingCallback()],
    )

    print("[6/6] Starting training loop...", flush=True)
    start = time.time()
    trainer.train()
    trainer.save_model(ckpt_dir)
    trainer.save_state()

    with open(os.path.join(ckpt_dir, "hyperparameters.json"), "w") as fp:
       json.dump({
           "dropout_rate": HPARAMS["dropout_rate"],
           "activate_fnc":   HPARAMS.get("activate_fnc", "ReLU"),
           "seed":           HPARAMS["seed"],
           "n_ddg":          HPARAMS.get("n_ddg"),
           "learning_rate":  HPARAMS["learning_rate"],
           "batch_size":     HPARAMS["batch_size"],
           "weight_decay":   HPARAMS["weight_decay"],
           "num_train_epochs": HPARAMS["num_train_epochs"]
       }, fp, indent=2)

    print(f"Training completed in {format_time(time.time()-start)}")

if __name__ == "__main__":
    main()
