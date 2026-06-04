#!/usr/bin/env python
"""Fine-tune ESM-2 8M on VHH NGS sequences using Masked Language Modeling."""

import os
import time

os.environ['WANDB_DISABLED'] = 'true'

import pandas as pd
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForMaskedLM,
    DataCollatorForLanguageModeling,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from datasets import Dataset

# ---- Config ----
MODEL_NAME = "facebook/esm2_t6_8M_UR50D"
TRAIN_CSV = "/home/yasu/tmp/vhh/PLM/csv/ngs_train_500k.csv"
EVAL_CSV = "/home/yasu/tmp/vhh/PLM/csv/ngs_10k_for_eval.csv"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "esm2_t6_8M_vhh")

EPOCHS = 10
BATCH_SIZE = 32
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 0.01
WARMUP_STEPS = 500
MLM_PROBABILITY = 0.15

# ---- Load data ----
print(f"Loading training data from {TRAIN_CSV}")
df_train = pd.read_csv(TRAIN_CSV)
df_eval = pd.read_csv(EVAL_CSV)
print(f"Train: {len(df_train)}, Eval: {len(df_eval)}")

# ---- Tokenize ----
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(examples):
    return tokenizer(examples["sequence"], truncation=True, padding="max_length", max_length=160)

train_ds = Dataset.from_pandas(df_train[["sequence"]])
eval_ds = Dataset.from_pandas(df_eval[["sequence"]])

print("Tokenizing...")
train_ds = train_ds.map(tokenize, batched=True, num_proc=4, remove_columns=["sequence"])
eval_ds = eval_ds.map(tokenize, batched=True, num_proc=4, remove_columns=["sequence"])

# ---- Model ----
print(f"Loading model: {MODEL_NAME}")
model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME)
print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Device: {device}")

# ---- MLM data collator ----
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=True,
    mlm_probability=MLM_PROBABILITY,
)

# ---- Training ----
os.makedirs(OUTPUT_DIR, exist_ok=True)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
    warmup_steps=WARMUP_STEPS,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    logging_steps=500,
    report_to="none",
    fp16=(device.type == "cuda"),
    optim="adamw_torch",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    data_collator=data_collator,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
)

print(f"\nStarting MLM fine-tuning: {EPOCHS} epochs, {len(train_ds)} samples")
start = time.time()
trainer.train()
elapsed = time.time() - start
print(f"\nTraining completed in {elapsed/60:.1f} minutes")

# ---- Save ----
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"\nModel saved to {OUTPUT_DIR}")

# ---- Final eval ----
eval_results = trainer.evaluate()
print(f"Final eval_loss: {eval_results['eval_loss']:.4f}")
