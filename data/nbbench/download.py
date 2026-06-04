#!/usr/bin/env python
"""Download NbBench thermo-tm dataset from HuggingFace and save as local CSVs."""

from datasets import load_dataset

ds = load_dataset("ZYMScott/thermo-tm")

for split, out_name in [("train", "train"), ("validation", "val"), ("test", "test")]:
    df = ds[split].to_pandas()
    # Rename seq -> text for compatibility with prepare.py
    df = df.rename(columns={"seq": "text"})
    # Keep only text and label columns
    df = df[["text", "label"]]
    df.to_csv(f"data/nbbench/{out_name}.csv", index=False)
    max_len = df["text"].str.len().max()
    print(f"{split}: {len(df)} samples, label range [{df['label'].min():.1f}, {df['label'].max():.1f}], max_seq_len={max_len}")
