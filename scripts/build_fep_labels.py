#!/usr/bin/env python3
"""Stage processed FEP ΔΔG labels from the three VHH-FEP campaign directories
(/data/{yasu,odas,kazu}/vhh_fep) into the Zenodo staging tree.

Only the small processed labels are copied (NOT the multi-TB raw trajectories).
Each label CSV has columns: resnum, wt_aa, mut_aa, ddG_kcal_mol, idx1, idx2.

Output:
  zenodo/fep/labels/<researcher>__<case>.csv
  zenodo/fep/labels/MANIFEST.tsv   (researcher, source_path, system, scan, n_mutations, sha256)
"""
import csv
import glob
import hashlib
import os
import re
import shutil

OUT = "zenodo/fep/labels"
ROOTS = {
    "yasu": "/data/yasu/vhh_fep",
    "odas": "/data/odas/vhh_fep",
    "kazu": "/data/kazu/vhh_fep",
}


def scan_type(name: str) -> str:
    n = name.lower()
    for key, lab in (("aspscan", "Asp"), ("glnscan", "Gln"), ("phescan", "Phe"),
                     ("tyrscan", "Tyr"), ("ilescan", "Ile"), ("alascan", "Ala")):
        if key in n:
            return lab
    for suf, lab in (("_ile", "Ile"), ("_phe", "Phe"), ("_tyr", "Tyr"),
                     ("_asp", "Asp"), ("_gln", "Gln"), ("_ala", "Ala")):
        if n.endswith(suf) or suf + "_" in n:
            return lab
    return "Ala"  # plain WT/alanine-scan default


def system_of(name: str) -> str:
    m = re.match(r"(EN\d{3}|[0-9a-zA-Z]{4})", name)
    return m.group(1) if m else name


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def n_rows(path):
    with open(path) as fh:
        return sum(1 for ln in fh if ln.strip())


def collect():
    items = []  # (researcher, source_path, case_name)
    # yasu: ddG/<system>_<scan>.csv
    for p in sorted(glob.glob(f"{ROOTS['yasu']}/ddG/*.csv")):
        items.append(("yasu", p, os.path.basename(p)[:-4]))
    # odas + kazu: <case>/ionized-FEP/ddG.csv
    for r in ("odas", "kazu"):
        for p in sorted(glob.glob(f"{ROOTS[r]}/*/ionized-FEP/ddG.csv")):
            case = p.split("/vhh_fep/")[1].split("/")[0]
            items.append((r, p, case))
    return items


def main():
    os.makedirs(OUT, exist_ok=True)
    items = collect()
    rows = []
    for researcher, src, case in items:
        dst_name = f"{researcher}__{case}.csv"
        dst = os.path.join(OUT, dst_name)
        shutil.copy2(src, dst)
        rows.append({
            "file": dst_name, "researcher": researcher, "system": system_of(case),
            "scan": scan_type(case), "n_mutations": n_rows(src),
            "source_path": src, "sha256": sha256(dst),
        })
    cols = ["file", "researcher", "system", "scan", "n_mutations", "source_path", "sha256"]
    with open(os.path.join(OUT, "MANIFEST.tsv"), "w") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["system"], x["scan"], x["researcher"])):
            w.writerow(r)

    # summary
    nmut = sum(r["n_mutations"] for r in rows)
    systems = sorted({r["system"] for r in rows})
    scans = sorted({r["scan"] for r in rows})
    print(f"staged {len(rows)} label files, {nmut} total mutations")
    print(f"systems: {', '.join(systems)}")
    print(f"scans  : {', '.join(scans)}")
    by = {}
    for r in rows:
        by.setdefault(r["researcher"], [0, 0])
        by[r["researcher"]][0] += 1
        by[r["researcher"]][1] += r["n_mutations"]
    for k, (nf, nm) in sorted(by.items()):
        print(f"  {k}: {nf} files, {nm} mutations")


if __name__ == "__main__":
    main()
