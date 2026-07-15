#!/usr/bin/env python
"""Download NbBench thermo-tm and recreate the low-data split used in this study."""

from datasets import load_dataset

ds = load_dataset("ZYMScott/thermo-tm")

# The published split names are deliberately reassigned for the study's
# low-data setting: 57 examples for training, 114 for validation/model
# selection, and 396 held out for the final test.  Keep this mapping in sync
# with prepare.py and the manuscript.
SPLIT_MAP = [
    ("validation", "train"),
    ("test", "val"),
    ("train", "test"),
]

for source_split, out_name in SPLIT_MAP:
    df = ds[source_split].to_pandas()
    # Rename seq -> text for compatibility with prepare.py
    df = df.rename(columns={"seq": "text"})
    # Keep only text and label columns
    df = df[["text", "label"]]
    df.to_csv(f"data/nbbench/{out_name}.csv", index=False)
    max_len = df["text"].str.len().max()
    print(
        f"Hugging Face {source_split} -> {out_name}.csv: {len(df)} samples, "
        f"label range [{df['label'].min():.1f}, {df['label'].max():.1f}], "
        f"max_seq_len={max_len}"
    )
