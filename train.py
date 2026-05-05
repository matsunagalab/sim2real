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
from peft import LoraConfig, get_peft_model
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
    "learning_rate": 3e-4,
    "encoder_lr": 1e-4,
    "weight_decay": 0.04,
    "dropout_rate": 0.15,
    "early_stopping_patience": 15,
    "early_stopping_threshold": 0.0,
    "warmup_steps": 100,
    "lora_r": 8,
    "lora_alpha": 16,
    "use_lora": False,
    # Encoder training mode (overrides use_lora when set explicitly):
    #   "frozen" → encoder weights frozen, embeddings precomputed (fastest, current default)
    #   "lora"   → LoRA adapter on attention; equivalent to use_lora=True
    #   "hot"    → full encoder fine-tuning with separate (lower) encoder LR
    "encoder_mode": os.environ.get("ENCODER_MODE", ""),
    # Base model name (env var BASE_MODEL_NAME overrides):
    #   "facebook/esm2_t6_8M_UR50D"   → 8M params (default, fast)
    #   "facebook/esm2_t12_35M_UR50D" → 35M params
    #   "facebook/esm2_t33_650M_UR50D" → 650M params (recommend lora/frozen, hot may OOM)
    "base_model_name": os.environ.get("BASE_MODEL_NAME", "facebook/esm2_t6_8M_UR50D"),
    # Multi-task loss weighting:
    #   "uncertainty" → learnable Kendall et al. 2018 weights (default)
    #   "fixed"       → static weights tm:1.0, ddg1/ddg2:1.0, md:MD_WEIGHT
    "mtl_weight_mode": os.environ.get("MTL_WEIGHT_MODE", "uncertainty"),
    "md_weight": float(os.environ.get("MD_WEIGHT", "1.0")),
}


def resolve_encoder_mode() -> str:
    """Resolve encoder mode from HPARAMS. Falls back to use_lora flag if encoder_mode unset."""
    mode = HPARAMS.get("encoder_mode") or ""
    if mode in ("frozen", "lora", "hot"):
        return mode
    return "lora" if HPARAMS.get("use_lora") else "frozen"


# ---- Model (エージェントがアーキテクチャを変更可能) ----
class MultiTaskModel(nn.Module):

    def __init__(self, base_model_name: str, hidden_dropout_prob: float = 0.195,
                 multi_task: bool = True, use_lora: bool = False,
                 encoder_mode: str | None = None):
        super().__init__()
        cfg = AutoConfig.from_pretrained(base_model_name)
        cfg.output_hidden_states = False
        self.encoder = AutoModel.from_pretrained(base_model_name, config=cfg)

        # Resolve mode: explicit arg > derived from use_lora > "frozen"
        if encoder_mode is None:
            encoder_mode = "lora" if use_lora else "frozen"
        assert encoder_mode in ("frozen", "lora", "hot"), f"bad encoder_mode={encoder_mode}"

        if encoder_mode == "lora":
            lora_config = LoraConfig(
                r=HPARAMS["lora_r"],
                lora_alpha=HPARAMS["lora_alpha"],
                target_modules=["query", "value"],
                lora_dropout=0.05,
                bias="none",
            )
            self.encoder = get_peft_model(self.encoder, lora_config)
            self.encoder.print_trainable_parameters()
        elif encoder_mode == "frozen":
            for p in self.encoder.parameters():
                p.requires_grad = False
        # encoder_mode == "hot": leave encoder fully trainable

        hs = cfg.hidden_size
        p = hidden_dropout_prob

        self.shared = nn.Sequential(
            nn.Linear(hs, 256),
            nn.ReLU(),
            nn.Dropout(p),

            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(p),

            nn.Linear(128, 32),
            nn.ReLU(),
        )

        self.tm_head = nn.Linear(32, 1)
        self.ddg_head = nn.Linear(32, 1)
        self.ddg_head2 = nn.Linear(32, 1)
        self.md_head = nn.Linear(32, 1)   # task_id=3: primary MD (e.g. Q-value)
        self.md_head2 = nn.Linear(32, 1)  # task_id=4: aux MD (e.g. RMSF)

        self.multi_task = multi_task
        self.loss_fn = nn.HuberLoss(delta=1.0)

        # Learnable task uncertainty (Kendall et al. 2018)
        self.log_sigma_tm = nn.Parameter(torch.tensor(0.0))
        self.log_sigma_ddg1 = nn.Parameter(torch.tensor(0.0))
        self.log_sigma_ddg2 = nn.Parameter(torch.tensor(0.0))
        self.log_sigma_md = nn.Parameter(torch.tensor(0.0))
        self.log_sigma_md2 = nn.Parameter(torch.tensor(0.0))

        self._use_lora = (encoder_mode == "lora")
        self._encoder_mode = encoder_mode
        self._weight_mode = HPARAMS.get("mtl_weight_mode", "uncertainty")
        self._md_weight = HPARAMS.get("md_weight", 1.0)

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
        md_logits = self.md_head(feats).view(-1)
        md_logits2 = self.md_head2(feats).view(-1)

        if task_ids is not None:
            logits = torch.zeros_like(tm_logits)
            mask_tm = task_ids == 0
            mask_ddg = task_ids == 1
            mask_ddg2 = task_ids == 2
            mask_md = task_ids == 3
            mask_md2 = task_ids == 4
            logits[mask_tm] = tm_logits[mask_tm]
            logits[mask_ddg] = ddg_logits[mask_ddg]
            logits[mask_ddg2] = ddg_logits2[mask_ddg2]
            logits[mask_md] = md_logits[mask_md]
            logits[mask_md2] = md_logits2[mask_md2]

            loss = None
            if labels is not None:
                losses = []
                if mask_tm.any():
                    l = self.loss_fn(tm_logits[mask_tm], labels[mask_tm])
                    if self._weight_mode == "fixed":
                        losses.append(l)
                    else:
                        losses.append(l / (2 * torch.exp(2 * self.log_sigma_tm)) + self.log_sigma_tm)
                if mask_ddg.any():
                    l = self.loss_fn(ddg_logits[mask_ddg], labels[mask_ddg])
                    if self._weight_mode == "fixed":
                        losses.append(l)
                    else:
                        losses.append(l / (2 * torch.exp(2 * self.log_sigma_ddg1)) + self.log_sigma_ddg1)
                if mask_ddg2.any():
                    l = self.loss_fn(ddg_logits2[mask_ddg2], labels[mask_ddg2])
                    if self._weight_mode == "fixed":
                        losses.append(l)
                    else:
                        losses.append(l / (2 * torch.exp(2 * self.log_sigma_ddg2)) + self.log_sigma_ddg2)
                if mask_md.any():
                    l = self.loss_fn(md_logits[mask_md], labels[mask_md])
                    if self._weight_mode == "fixed":
                        losses.append(self._md_weight * l)
                    else:
                        losses.append(l / (2 * torch.exp(2 * self.log_sigma_md)) + self.log_sigma_md)
                if mask_md2.any():
                    l = self.loss_fn(md_logits2[mask_md2], labels[mask_md2])
                    if self._weight_mode == "fixed":
                        losses.append(self._md_weight * l)
                    else:
                        losses.append(l / (2 * torch.exp(2 * self.log_sigma_md2)) + self.log_sigma_md2)
                loss = sum(losses) if losses else torch.tensor(0.0, device=tm_logits.device)

            return SequenceClassifierOutput(loss=loss, logits=logits)

        return {'tm': tm_logits, 'ddg': ddg_logits, 'ddg2': ddg_logits2,
                'md': md_logits, 'md2': md_logits2}


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
    encoder_mode = resolve_encoder_mode()

    model = MultiTaskModel(
        base_model_name=HPARAMS["base_model_name"],
        hidden_dropout_prob=HPARAMS['dropout_rate'],
        multi_task=multi_task,
        encoder_mode=encoder_mode,
    )
    model.to(device)

    if encoder_mode == "frozen":
        # Precompute embeddings (encoder is frozen, fastest path)
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

    # Hot mode: encoder gets its own (lower) LR via param groups
    trainer_cls = Trainer
    if encoder_mode == "hot":
        class HotModeTrainer(Trainer):
            def create_optimizer(self):
                if self.optimizer is None:
                    enc_params, head_params = [], []
                    for n, p in self.model.named_parameters():
                        if not p.requires_grad:
                            continue
                        (enc_params if n.startswith("encoder.") else head_params).append(p)
                    self.optimizer = torch.optim.AdamW(
                        [
                            {"params": enc_params, "lr": HPARAMS["encoder_lr"]},
                            {"params": head_params, "lr": HPARAMS["learning_rate"]},
                        ],
                        weight_decay=HPARAMS["weight_decay"],
                    )
                return self.optimizer
        trainer_cls = HotModeTrainer

    trainer = trainer_cls(
        model=model,
        args=targs,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
        callbacks=callbacks,
    )

    print(f"    Training run {run} (encoder={encoder_mode}, "
          f"mtl_weight={HPARAMS['mtl_weight_mode']}, md_w={HPARAMS['md_weight']})...",
          flush=True)
    start = time.time()
    trainer.train()
    trainer.save_model(ckpt_dir)

    with open(os.path.join(ckpt_dir, "hyperparameters.json"), "w") as fp:
        json.dump(HPARAMS, fp, indent=2)

    print(f"    Run {run} completed in {format_time(time.time() - start)}", flush=True)
