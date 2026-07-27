#!/usr/bin/env python3
"""Controlled data-design comparison: matched mutation scan vs heterogeneous panel.

Isolated from prepare.py so existing manuscript results are untouched. Implements
the protocol from paper/analysis/md_data_design_review.md (valid-minimal scope):

  * both sources on the MD head (task_id=3), shared architecture, fixed MD loss
    weight, raw Q as the label (seq,ddg_scaled01);
  * nested prefix subsets (20 subset of 80 subset of 160 subset of 320) drawn once per
    subset seed; the scan pool is stratified 50:50 across 1MEL/4IDL;
  * NO auxiliary 80/20 hold-out -- every sampled label trains; checkpoint
    selection is on the experimental Tm validation set only;
  * per (source, n): 8 subset draws x 3 model-init seeds = 24 fits; the 3 seeds
    of ONE subset are ensembled, and the 8 subset ensembles are kept as
    independent replicates (never averaged into one prediction).

One invocation handles one (source, encoder_mode). Output: a JSON with, per n,
the 8 subset residual vectors over the NbBench test proteins. Compare two source
JSONs with the companion analysis at the bottom of this file (--analyze).
"""
from __future__ import annotations
import argparse, csv, json, os, sys
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
# Pool directory; overridable so the aligned-window Fig 2 pools can be used.
DESIGN_DIR = os.path.join(REPO, os.environ.get("DESIGN_DATA_DIR", "data/source_labels/md_design"))

SHARED_HP = {  # pre-specified simplest shared defaults, applied identically to both sources
    "frozen": {"MODEL_ARCH": "shared", "DDG_HEAD_MODE": "separate", "LEARNING_RATE": "0.001",
               "WEIGHT_DECAY": "0.02", "DROPOUT_RATE": "0.05"},
    "hot": {"MODEL_ARCH": "shared", "DDG_HEAD_MODE": "separate", "LEARNING_RATE": "0.0003",
            "ENCODER_LR": "1e-5", "WEIGHT_DECAY": "0.02", "DROPOUT_RATE": "0.15"},
}


def load_pool(source):
    """Return list of (seq, label) and, for scan_pool, the per-scaffold index split."""
    def read(path):
        rows = []
        with open(path) as fh:
            for r in csv.DictReader(fh):
                rows.append((r["seq"], float(r["ddg_scaled01"])))
        return rows
    if source == "none":
        return {"strata": []}  # Tm-only baseline: no auxiliary labels
    if source == "scan_pool":
        a = read(f"{DESIGN_DIR}/scan_ownframe0_1mel.csv")
        b = read(f"{DESIGN_DIR}/scan_ownframe0_4idl.csv")
        return {"strata": [a, b]}
    fname = {"hetero": "hetero_backbone_qc.csv",
             "scan_1mel": "scan_ownframe0_1mel.csv",
             "scan_4idl": "scan_ownframe0_4idl.csv"}[source]
    return {"strata": [read(f"{DESIGN_DIR}/{fname}")]}


def subset_rows(pool, n, subset_seed):
    """Nested prefix subset of size n for this subset_seed. Stratified across strata."""
    strata = pool["strata"]
    k = len(strata)
    if k == 0:  # Tm-only baseline
        return []
    per = [n // k] * k
    for i in range(n - sum(per)):
        per[i] += 1
    out = []
    for s_idx, rows in enumerate(strata):
        # Deterministic per-stratum permutation; prefix nesting holds across n.
        rng = np.random.default_rng(1000 * subset_seed + s_idx)
        order = rng.permutation(len(rows))
        take = min(per[s_idx], len(rows))
        out.extend(rows[i] for i in order[:take])
    return out


def build_datasets(aux_rows, tokenizer, MAX_LENGTH, get_tm_scaler):
    import pandas as pd
    from datasets import Dataset
    tr = pd.read_csv(os.path.join(REPO, "data/nbbench/train.csv"))
    va = pd.read_csv(os.path.join(REPO, "data/nbbench/val.csv"))
    scaler = get_tm_scaler()
    tr["label"] = scaler.transform(tr["label"].values.reshape(-1, 1)).flatten()
    va["label"] = scaler.transform(va["label"].values.reshape(-1, 1)).flatten()
    train_df = pd.DataFrame({"text": tr["text"], "label": tr["label"], "task": 0})
    aux_df = pd.DataFrame({"text": [s for s, _ in aux_rows],
                           "label": [q for _, q in aux_rows],
                           "task": 3})
    train_all = pd.concat([train_df, aux_df], ignore_index=True)
    # Selection scope = tm: eval is Tm val only.
    eval_df = pd.DataFrame({"text": va["text"], "label": va["label"], "task": 0})

    def tok(ex):
        return tokenizer(ex["text"], padding="max_length", truncation=True, max_length=MAX_LENGTH)
    tds = Dataset.from_pandas(train_all).map(tok, batched=True, num_proc=4).rename_column("task", "task_ids")
    eds = Dataset.from_pandas(eval_df).map(tok, batched=True, num_proc=4).rename_column("task", "task_ids")
    cols = ["input_ids", "attention_mask", "label", "task_ids"]
    tds.set_format(type="torch", columns=cols)
    eds.set_format(type="torch", columns=cols)
    return tds, eds


def predict_test(model_dirs, device, tokenizer, MODEL_NAME, MAX_LENGTH, get_tm_scaler):
    """Ensemble the given model dirs (one subset's seeds) on the NbBench test split."""
    import pandas as pd, torch
    from safetensors.torch import load_file
    from train import MultiTaskModel, resolve_encoder_mode
    df = pd.read_csv(os.path.join(REPO, "data/nbbench/test.csv"))
    seqs, labels = df["text"].tolist(), np.array(df["label"].tolist())
    scaler = get_tm_scaler()
    em = resolve_encoder_mode()

    def one(md):
        model = MultiTaskModel(MODEL_NAME, encoder_mode=em).to(device)
        model.load_state_dict(load_file(os.path.join(md, "model.safetensors"), device="cpu"), strict=False)
        model.eval()
        preds = []
        with torch.no_grad():
            for j in range(0, len(seqs), 32):
                enc = tokenizer(seqs[j:j+32], padding=True, truncation=True,
                                max_length=MAX_LENGTH, return_tensors="pt").to(device)
                tsk = torch.zeros(len(seqs[j:j+32]), dtype=torch.long, device=device)
                out = model(enc["input_ids"], enc["attention_mask"], task_ids=tsk)
                logits = out.logits if hasattr(out, "logits") else out["tm"]
                preds.extend(logits.cpu().tolist())
        return np.array(preds)

    ens = np.stack([one(md) for md in model_dirs]).mean(0)
    y = scaler.inverse_transform(ens.reshape(-1, 1)).flatten()
    return np.abs(y - labels), labels


def run(args):
    for k, v in SHARED_HP[args.encoder_mode].items():
        os.environ[k] = v
    os.environ["ENCODER_MODE"] = args.encoder_mode
    os.environ["MTL_WEIGHT_MODE"] = "fixed"
    os.environ["MD_WEIGHT"] = str(args.md_weight)
    os.environ["DETACH_AUX_ENCODER"] = "true"
    if args.epochs:
        os.environ["NUM_TRAIN_EPOCHS"] = str(args.epochs)
    import torch
    from transformers import AutoTokenizer
    from prepare import MODEL_NAME, MAX_LENGTH, get_tm_scaler, set_seed
    from train import train as train_fn
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    pool = load_pool(args.source)
    tm_only = (args.source == "none")
    # Tm-only has no auxiliary data, so n is meaningless; its replicate variance
    # comes only from initialisation, so use distinct model seeds per subset.
    n_list = [0] if tm_only else [int(x) for x in args.n_list.split(",")]
    out_root = os.path.join(REPO, "results", args.exp_name)

    result = {"source": args.source, "encoder_mode": args.encoder_mode,
              "md_weight": args.md_weight, "hp": SHARED_HP[args.encoder_mode],
              "n_subsets": args.n_subsets, "n_seeds": args.n_seeds, "per_n": {}}
    for n in n_list:
        subsets = []
        for s in range(1, args.n_subsets + 1):
            aux = subset_rows(pool, n, subset_seed=s)
            tds, eds = build_datasets(aux, tokenizer, MAX_LENGTH, get_tm_scaler)
            model_dirs = []
            for m in range(1, args.n_seeds + 1):
                seed = (s - 1) * args.n_seeds + m if tm_only else m
                os.environ["TRAIN_SEED"] = str(seed)
                os.environ["TRAIN_DATA_SEED"] = str(seed)
                set_seed(seed)
                point_dir = os.path.join(out_root, f"n{n}", f"subset{s}")
                run_id = f"m{m}"
                train_fn(tds, eds, device, run_id, point_dir, multi_task=True)
                model_dirs.append(os.path.join(point_dir, "supervised", f"mtl_run{run_id}"))
            resid, labels = predict_test(model_dirs, device, tokenizer, MODEL_NAME, MAX_LENGTH, get_tm_scaler)
            subsets.append({"subset_seed": s, "n_aux": len(aux),
                            "mae": float(resid.mean()), "residuals": resid.tolist()})
            print(f"[{args.source}/{args.encoder_mode}] n={n} subset={s}/{args.n_subsets} "
                  f"MAE={resid.mean():.4f}", flush=True)
        result["per_n"][str(n)] = {"subsets": subsets,
                                   "mae_mean": float(np.mean([x["mae"] for x in subsets])),
                                   "mae_std": float(np.std([x["mae"] for x in subsets]))}
        os.makedirs(out_root, exist_ok=True)
        json.dump(result, open(os.path.join(out_root, "design.json"), "w"), indent=1)
    print(f"wrote {out_root}/design.json", flush=True)


def analyze(args):
    """Two-way (subset-replicate x test-protein) bootstrap of MAE_scan - MAE_hetero."""
    scan = json.load(open(args.scan))
    het = json.load(open(args.hetero))
    rng = np.random.default_rng(42)
    print(f"scan={scan['source']}/{scan['encoder_mode']}  hetero={het['source']}/{het['encoder_mode']}")
    for n in sorted(set(scan["per_n"]) & set(het["per_n"]), key=int):
        S = np.array([x["residuals"] for x in scan["per_n"][n]["subsets"]])  # (8,396)
        H = np.array([x["residuals"] for x in het["per_n"][n]["subsets"]])
        point = S.mean() - H.mean()
        boot = []
        for _ in range(10000):
            si = rng.integers(0, S.shape[0], S.shape[0]); hi = rng.integers(0, H.shape[0], H.shape[0])
            pj = rng.integers(0, S.shape[1], S.shape[1])
            boot.append(S[np.ix_(si, pj)].mean() - H[np.ix_(hi, pj)].mean())
        lo, hi_ = np.percentile(boot, [2.5, 97.5])
        p = (np.array(boot) > 0).mean()
        print(f"  n={n:>3}  MAE_scan={S.mean():.3f}  MAE_hetero={H.mean():.3f}  "
              f"Δdesign={point:+.3f}  95%CI[{lo:+.3f},{hi_:+.3f}]  P(hetero better)={p:.3f}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--source", required=True, choices=["none", "scan_pool", "hetero", "scan_1mel", "scan_4idl"])
    r.add_argument("--encoder-mode", required=True, choices=["frozen", "hot"])
    r.add_argument("--n-list", default="20,80,160,320")
    r.add_argument("--n-subsets", type=int, default=8)
    r.add_argument("--n-seeds", type=int, default=3)
    r.add_argument("--md-weight", type=float, default=1.0)
    r.add_argument("--epochs", type=int, default=0, help="override epochs (smoke test)")
    r.add_argument("--exp-name", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--scan", required=True)
    a.add_argument("--hetero", required=True)
    args = ap.parse_args()
    if args.cmd == "run":
        run(args)
    else:
        analyze(args)


if __name__ == "__main__":
    main()
