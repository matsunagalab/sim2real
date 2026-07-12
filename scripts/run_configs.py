#!/usr/bin/env python3
"""Run a list of prepare.py configs across a GPU pool; collect val/test MAE.

Input: a JSON file = list of config dicts, each with keys:
  exp, source ("none"/FEP/MD_FEP400K/...), encoder_mode (hot/frozen),
  model_arch, ddg_head_mode, encoder_lr, dropout, weight_decay (any may be omitted),
  split ("val"/"test"), n_ddg_list (str), n_runs (int)
Distributes over --gpus (one job per GPU at a time), writes <out>.tsv with exp<TAB>mae_mean.
Used for the staged source-tuning HPO (arch/head skeleton -> lr/dropout/wd fine-tune -> final test).
"""
import argparse
import json
import os
import re
import subprocess
import time
from multiprocessing import Process, Queue

REPO = "/home/yasu/tmp/sim2real"
LOGDIR = "zenodo/_logs/tune"


def build_cmd(c):
    cmd = ["uv", "run", "python", "prepare.py",
           "--ddg-source", str(c["source"]),
           "--encoder-mode", c["encoder_mode"],
           "--n-ddg-list", str(c.get("n_ddg_list", "320")),
           "--n-runs", str(c.get("n_runs", 3)),
           "--final-eval-split", c.get("split", "val"),
           "--selection-scope", c.get("selection_scope", "tm"),
           "--exp-name", c["exp"]]
    for flag, key in [("--model-arch", "model_arch"), ("--ddg-head-mode", "ddg_head_mode"),
                      ("--encoder-lr", "encoder_lr"), ("--dropout-rate", "dropout"),
                      ("--weight-decay", "weight_decay"), ("--learning-rate", "learning_rate"),
                      ("--mtl-weight-mode", "mtl_weight_mode")]:
        if c.get(key) is not None:
            cmd += [flag, str(c[key])]
    return cmd


def worker(gpu, q, results):
    os.makedirs(LOGDIR, exist_ok=True)
    while True:
        c = q.get()
        if c is None:
            return
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
        env["TRAIN_EPOCH_LOGS"] = "0"
        log = f"{LOGDIR}/{c['exp']}.log"
        with open(log, "w") as fh:
            rc = subprocess.run(build_cmd(c), cwd=REPO, env=env, stdout=fh,
                                stderr=subprocess.STDOUT).returncode
        mae = None
        try:
            m = re.search(r"mae_mean=([\d.]+)", open(log).read())
            mae = float(m.group(1)) if m else None
        except Exception:
            pass
        results.put((c["exp"], mae, rc, gpu))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", required=True)
    ap.add_argument("--gpus", default="0,1,2,3,4,5,6")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    configs = json.load(open(args.configs))
    gpus = [g.strip() for g in args.gpus.split(",") if g.strip()]
    q, results = Queue(), Queue()
    for c in configs:
        q.put(c)
    for _ in gpus:
        q.put(None)
    procs = [Process(target=worker, args=(g, q, results)) for g in gpus]
    for p in procs:
        p.start()
    got, t0 = [], time.time()
    for _ in range(len(configs)):
        exp, mae, rc, gpu = results.get()
        got.append((exp, mae))
        print(f"[{len(got)}/{len(configs)}] {exp} mae={mae} rc={rc} gpu={gpu} "
              f"({(time.time()-t0)/60:.1f}m)", flush=True)
    for p in procs:
        p.join()
    with open(args.out, "w") as fh:
        for exp, mae in sorted(got, key=lambda x: (x[1] is None, x[1])):
            fh.write(f"{exp}\t{mae}\n")
    print(f"wrote {args.out}", flush=True)
    ok = [(e, m) for e, m in got if m is not None]
    if ok:
        best = min(ok, key=lambda x: x[1])
        print(f"BEST: {best[0]} mae={best[1]:.4f}", flush=True)


if __name__ == "__main__":
    main()
