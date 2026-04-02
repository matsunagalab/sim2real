#!/usr/bin/env python
# coding: utf-8
"""
train.py — エージェントが自由に編集するファイル

モデルアーキテクチャ、ハイパーパラメータ、学習ループを定義する。
prepare.py から呼ばれる。prepare.py は変更不可。
"""

import os
import time
import json

import numpy as np
import torch
import torch.nn as nn
from transformers import (
    Trainer,
    TrainingArguments,
    AutoModel,
    AutoConfig,
    TrainerCallback,
    TrainerState,
    TrainerControl,
    EarlyStoppingCallback,
)
from transformers.modeling_outputs import SequenceClassifierOutput
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# ---- Hyperparameters (エージェントが調整) ----
HPARAMS = {
    "num_train_epochs": 400,
    "batch_size": 16,
    "learning_rate": 5e-4,
    "weight_decay": 0.01,
    "dropout_rate": 0.1,
    "early_stopping_patience": 15,
    "early_stopping_threshold": 0.0,
    "warmup_steps": 100,
    "loss_weights": {"tm": 0.3, "ddg1": 0.35, "ddg2": 0.35},
}


# ---- Model (エージェントがアーキテクチャを変更可能) ----
class MultiTaskModel(nn.Module):

    def __init__(self, base_model_name: str, hidden_dropout_prob: float = 0.195,
                 multi_task: bool = True):
        super().__init__()
        cfg = AutoConfig.from_pretrained(base_model_name)
        cfg.output_hidden_states = False
        self.encoder = AutoModel.from_pretrained(base_model_name, config=cfg)
        for p in self.encoder.parameters():
            p.requires_grad = False

        hs = self.encoder.config.hidden_size
        p = hidden_dropout_prob

        # Thin shared projection (general protein features)
        self.shared = nn.Sequential(
            nn.Linear(hs, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Dropout(p),
        )

        # Deep task-specific paths (each protein type has own energy landscape)
        self.tm_head = nn.Sequential(
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 1),
        )
        self.ddg_head = nn.Sequential(  # 1mel-specific
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 1),
        )
        self.ddg_head2 = nn.Sequential(  # 4idl-specific
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 1),
        )

        # Xavier initialization for stability
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

        self.multi_task = multi_task
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

        if not self.multi_task:
            logits = tm_logits
            loss = self.loss_fn(logits, labels) if labels is not None else None
            return SequenceClassifierOutput(loss=loss, logits=logits)

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
                w = HPARAMS["loss_weights"]
                losses = []
                if mask_tm.any():
                    losses.append(w["tm"] * self.loss_fn(tm_logits[mask_tm], labels[mask_tm]))
                if mask_ddg.any():
                    losses.append(w["ddg1"] * self.loss_fn(ddg_logits[mask_ddg], labels[mask_ddg]))
                if mask_ddg2.any():
                    losses.append(w["ddg2"] * self.loss_fn(ddg_logits2[mask_ddg2], labels[mask_ddg2]))
                loss = sum(losses) if losses else torch.tensor(0.0, device=tm_logits.device)

            return SequenceClassifierOutput(loss=loss, logits=logits)

        return {'tm': tm_logits, 'ddg': ddg_logits, 'ddg2': ddg_logits2}


# ---- Callback ----
class ProgressLoggingCallback(TrainerCallback):
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


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h{m}m{s}s"
    return f"{m}m{s}s"


# ---- Train function (prepare.py から呼ばれる) ----
def train(train_ds, eval_ds, device, run, result_dir, multi_task):
    """学習を実行し、モデルを保存する。prepare.py から呼ばれる。"""
    model = MultiTaskModel(
        base_model_name="facebook/esm2_t6_8M_UR50D",
        hidden_dropout_prob=HPARAMS['dropout_rate'],
        multi_task=multi_task,
    )
    model.to(device)

    # Precompute embeddings (encoder is frozen)
    from prepare import precompute_embeddings
    print("    Precomputing embeddings...", flush=True)
    t0 = time.time()
    train_ds = precompute_embeddings(model, train_ds, device, HPARAMS["batch_size"])
    eval_ds = precompute_embeddings(model, eval_ds, device, HPARAMS["batch_size"])
    print(f"    done in {format_time(time.time() - t0)}", flush=True)

    ckpt_dir = os.path.join(result_dir, "supervised", f"mtl_run{run}")
    os.makedirs(ckpt_dir, exist_ok=True)
    logging_dir = os.path.join(result_dir, "supervised", "logs")

    metric_for_best = "eval_loss" if not multi_task else "eval_mse"

    targs = TrainingArguments(
        output_dir=ckpt_dir,
        num_train_epochs=HPARAMS['num_train_epochs'],
        per_device_train_batch_size=HPARAMS['batch_size'],
        per_device_eval_batch_size=HPARAMS['batch_size'],
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=HPARAMS['learning_rate'],
        weight_decay=HPARAMS['weight_decay'],
        logging_dir=logging_dir,
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model=metric_for_best,
        greater_is_better=False,
        save_total_limit=1,
        warmup_steps=HPARAMS['warmup_steps'],
        lr_scheduler_type="cosine",
        optim="adamw_torch",
        report_to="none",
        fp16=(device.type == "cuda"),
    )

    callbacks = [
        ProgressLoggingCallback(),
        EarlyStoppingCallback(
            early_stopping_patience=HPARAMS["early_stopping_patience"],
            early_stopping_threshold=HPARAMS["early_stopping_threshold"],
        ),
    ]

    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
        callbacks=callbacks,
    )

    print(f"    Training run {run}...", flush=True)
    start = time.time()
    trainer.train()
    trainer.save_model(ckpt_dir)

    with open(os.path.join(ckpt_dir, "hyperparameters.json"), "w") as fp:
        json.dump(HPARAMS, fp, indent=2)

    print(f"    Run {run} completed in {format_time(time.time() - start)}", flush=True)
