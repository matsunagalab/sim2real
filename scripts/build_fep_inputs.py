#!/usr/bin/env python3
"""Stage representative FEP input/setup files (one set per VHH system) into the
Zenodo staging tree. Small inputs only — NO trajectories/fepout/logs.

Per system: starting + ionized structures, CHARMM topology, one example mutation's
FEP setup (config only), and the scan definition. CHARMM toppar is deduplicated
into a single shared copy.

Output:
  zenodo/fep/inputs/<system>/{structures, example_fep_<mut>}/...
  zenodo/fep/inputs/_charmm_toppar/        (shared, once)
  zenodo/fep/inputs/MANIFEST.tsv
"""
import csv
import glob
import os
import shutil

OUT = "zenodo/fep/inputs"

# system -> source FEP run dir with the full 1_oripdb..5_ionize pipeline
SYSTEMS = {
    "1fvc":  "/data/yasu/vhh_fep/1fvc",
    "1mel":  "/data/odas/vhh_fep/1mel",
    "3b9v":  "/data/yasu/vhh_fep/3b9v",
    "4idl":  "/data/yasu/vhh_fep/4idl",
    "4tyu":  "/data/yasu/vhh_fep/4tyu",
    "4w70":  "/data/yasu/vhh_fep/4w70",
    "5sv4":  "/data/kazu/vhh_fep/5sv4",
    "EN565": "/data/yasu/vhh_fep/EN565_aspscan",
    "EN577": "/data/yasu/vhh_fep/EN577_aspscan",
}

# files to copy from each setup stage (small inputs only)
STAGE_FILES = {
    "1_oripdb":  ["*.pdb"],
    "3_psfgen":  ["protein.pdb", "protein.psf"],
    "5_ionize":  ["ionized.pdb", "ionized.psf"],
}
ROOT_FILES = ["top_all36_hybrid.inp", "par_all36_prot.prm", "*scan.tcl"]
# example-mutation FEP setup (config only; exclude bulk)
FEP_KEEP_EXT = (".fep", ".fep.psf", ".namd", ".tcl", "run.sh")
FEP_SKIP_EXT = (".dcd", ".fepout", ".log", ".coor", ".vel", ".xst", ".xsc", ".restart")


def copy_globs(src_dir, patterns, dst_dir):
    n = 0
    for pat in patterns:
        for p in glob.glob(os.path.join(src_dir, pat)):
            if os.path.isfile(p):
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(p, os.path.join(dst_dir, os.path.basename(p)))
                n += 1
    return n


def pick_example_mut(src):
    fep = os.path.join(src, "ionized-FEP")
    if not os.path.isdir(fep):
        return None
    subs = sorted(d for d in glob.glob(os.path.join(fep, "*"))
                  if os.path.isdir(d) and "2" in os.path.basename(d))  # e.g. 1-GLU2ALA
    return subs[0] if subs else None


def copy_fep_setup(mut_dir, dst_dir):
    n = 0
    for p in sorted(glob.glob(os.path.join(mut_dir, "*"))):
        if not os.path.isfile(p):
            continue
        name = os.path.basename(p)
        if any(name.endswith(s) for s in FEP_SKIP_EXT):
            continue
        if name.endswith(FEP_KEEP_EXT) or name == "run.sh":
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copy2(p, os.path.join(dst_dir, name))
            n += 1
    return n


def dir_bytes(path):
    return sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(path) for f in fs)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    toppar_done = False
    for system, src in SYSTEMS.items():
        if not os.path.isdir(src):
            print(f"WARN missing source: {system} {src}")
            continue
        sysdst = os.path.join(OUT, system)
        nfiles = 0
        for stage, pats in STAGE_FILES.items():
            nfiles += copy_globs(os.path.join(src, stage), pats,
                                 os.path.join(sysdst, "structures"))
        nfiles += copy_globs(src, ROOT_FILES, os.path.join(sysdst, "structures"))

        mut = pick_example_mut(src)
        ex_name = ""
        if mut:
            ex_name = os.path.basename(mut)
            nfiles += copy_fep_setup(mut, os.path.join(sysdst, f"example_fep_{ex_name}"))

        # shared CHARMM toppar once
        if not toppar_done:
            tp = os.path.join(src, "toppar_c36_jul20")
            if os.path.isdir(tp):
                shutil.copytree(tp, os.path.join(OUT, "_charmm_toppar"),
                                dirs_exist_ok=True)
                toppar_done = True

        rows.append({"system": system, "source_dir": src, "example_mutation": ex_name,
                     "n_files": nfiles, "bytes": dir_bytes(sysdst)})
        print(f"[{system}] {nfiles} files, {dir_bytes(sysdst)/1e6:.1f} MB  (example: {ex_name})")

    with open(os.path.join(OUT, "MANIFEST.tsv"), "w") as fh:
        w = csv.DictWriter(fh, fieldnames=["system", "source_dir", "example_mutation",
                                           "n_files", "bytes"], delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    total = dir_bytes(OUT)
    print(f"\nTOTAL inputs: {total/1e6:.1f} MB across {len(rows)} systems "
          f"(+ shared _charmm_toppar)")


if __name__ == "__main__":
    main()
