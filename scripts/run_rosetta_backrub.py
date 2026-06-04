#!/usr/bin/env python
"""Run Rosetta backrub on all nanobody merged.pdbs in parallel.

300K equivalent (mc_kt=0.6), ntrials=10000, trajectory_stride=33 → ~300 frames.
8 parallel processes. Output: data/md/rosetta_traj/<pdb_id>_traj.pdb
"""

import os
import sys
import glob
import shutil
import subprocess
import multiprocessing as mp
import time
import tempfile

MDCLAW_ROOT = "/home/yasu/tmp/mdclaw"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "data", "md", "rosetta_traj")

ROSETTA_ROOT = "/opt/rosetta.source.release-371"
BACKRUB_BIN = f"{ROSETTA_ROOT}/main/source/bin/backrub.linuxgccrelease"
DATABASE = f"{ROSETTA_ROOT}/main/database"
LD_PATHS = (
    f"{ROSETTA_ROOT}/main/source/build/external/release/linux/5.15/64/x86/gcc/12.4/default:"
    f"{ROSETTA_ROOT}/main/source/build/src/release/linux/5.15/64/x86/gcc/12.4/default"
)

NTRIALS = 10000
MC_KT = 0.6
TRAJ_STRIDE = 33  # → ~300 frames
TIMEOUT_SEC = 1800  # 30 min per protein

# ff19SB → standard residue rename map for Rosetta compatibility
RESNAME_RENAME = {
    "HID": "HIS", "HIE": "HIS", "HIP": "HIS",
    "ASH": "ASP", "GLH": "GLU", "LYN": "LYS",
    "CYX": "CYS", "CYM": "CYS",
}


def preprocess_pdb(src: str, dst: str) -> None:
    """Copy PDB with ff19SB residue renames and strip hydrogens + non-ATOM lines.

    Rosetta's fill_missing_atoms fails on HID/HIE/HIP etc. Rename to HIS/ASP/GLU/LYS/CYS.
    Also strip hydrogens (Rosetta adds its own) and keep only ATOM/TER/END.
    """
    with open(src) as f_in, open(dst, "w") as f_out:
        for line in f_in:
            rec = line[:6]
            if rec.startswith(("ATOM  ", "HETATM")):
                resname = line[17:20]
                if resname in RESNAME_RENAME:
                    line = line[:17] + RESNAME_RENAME[resname] + line[20:]
                # Strip hydrogens (element column 77-78, or name starting with H/1H-9H)
                elem = line[76:78].strip()
                atom_name = line[12:16].strip()
                if elem == "H" or (elem == "" and (atom_name.startswith("H") or atom_name[:1].isdigit() and "H" in atom_name[:2])):
                    continue
                # Convert HETATM → ATOM (Rosetta sometimes complains)
                if rec == "HETATM":
                    line = "ATOM  " + line[6:]
                f_out.write(line)
            elif rec.startswith(("TER", "END")):
                f_out.write(line)


def process_one(job_dir: str) -> tuple[str, bool, str]:
    pdb_id = os.path.basename(job_dir).replace("job_nano_", "")
    merged = os.path.join(job_dir, "nodes", "prep_001", "artifacts", "merge", "merged.pdb")
    if not os.path.exists(merged):
        return (pdb_id, False, "no merged.pdb")

    out_traj = os.path.join(OUT_DIR, f"{pdb_id}_traj.pdb.gz")
    if os.path.exists(out_traj) and os.path.getsize(out_traj) > 500:
        return (pdb_id, True, "already done")

    # Run backrub in a tmp dir (Rosetta writes many files, we only keep _traj.pdb)
    with tempfile.TemporaryDirectory(prefix=f"backrub_{pdb_id}_") as td:
        # Preprocess PDB: rename ff19SB residue variants, strip H atoms
        clean_pdb = os.path.join(td, f"{pdb_id}_clean.pdb")
        try:
            preprocess_pdb(merged, clean_pdb)
        except Exception as e:
            return (pdb_id, False, f"preprocess failed: {e}")

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = LD_PATHS + ":" + env.get("LD_LIBRARY_PATH", "")
        cmd = [
            BACKRUB_BIN,
            "-database", DATABASE,
            "-in:file:s", clean_pdb,
            "-ignore_unrecognized_res",
            "-backrub:mc_kt", str(MC_KT),
            "-backrub:ntrials", str(NTRIALS),
            "-backrub:trajectory", "true",
            "-backrub:trajectory_gz", "true",
            "-backrub:trajectory_stride", str(TRAJ_STRIDE),
            "-nstruct", "1",
            "-overwrite",
            "-mute", "all",
        ]
        t0 = time.time()
        try:
            # Rosetta writes trajectory to CWD; use td as CWD
            result = subprocess.run(
                cmd, env=env, timeout=TIMEOUT_SEC, cwd=td,
                capture_output=True, text=True,
            )
        except subprocess.TimeoutExpired:
            return (pdb_id, False, f"timeout after {TIMEOUT_SEC}s")

        if result.returncode != 0:
            err = (result.stderr or result.stdout or "")[-500:]
            return (pdb_id, False, f"rc={result.returncode}: {err.strip()[:200]}")

        # Find generated trajectory file (ends with _traj.pdb.gz when trajectory_gz=true)
        cand = glob.glob(os.path.join(td, "*_traj.pdb.gz"))
        if not cand:
            cand = glob.glob(os.path.join(td, "*_traj.pdb"))
        if not cand:
            return (pdb_id, False, "no *_traj.pdb[.gz] produced")
        src = cand[0]
        # Ensure output is gzipped
        if src.endswith(".gz"):
            shutil.move(src, out_traj)
        else:
            subprocess.run(["gzip", "-q", src], check=True)
            shutil.move(src + ".gz", out_traj)
        elapsed = time.time() - t0
        return (pdb_id, True, f"ok {elapsed:.0f}s")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    job_dirs = sorted(glob.glob(os.path.join(MDCLAW_ROOT, "job_nano_*")))
    # Only those with merged.pdb
    valid = [
        j for j in job_dirs
        if os.path.exists(os.path.join(j, "nodes", "prep_001", "artifacts", "merge", "merged.pdb"))
    ]
    print(f"Found {len(valid)} nanobodies with merged.pdb", flush=True)
    print(f"Output dir: {OUT_DIR}", flush=True)
    print(f"Rosetta: backrub ntrials={NTRIALS}, mc_kt={MC_KT}, stride={TRAJ_STRIDE}", flush=True)

    n_parallel = 8
    print(f"Parallel workers: {n_parallel}", flush=True)

    t0 = time.time()
    done = 0
    failed = []
    with mp.Pool(n_parallel) as pool:
        for pdb_id, ok, msg in pool.imap_unordered(process_one, valid):
            done += 1
            if ok:
                print(f"[{done:4d}/{len(valid)}] {pdb_id}: {msg}", flush=True)
            else:
                print(f"[{done:4d}/{len(valid)}] {pdb_id}: FAIL {msg}", flush=True)
                failed.append((pdb_id, msg))

    elapsed = time.time() - t0
    print(f"\nTotal: {done}, failed: {len(failed)}, elapsed: {elapsed/3600:.1f}h", flush=True)
    if failed:
        with open(os.path.join(OUT_DIR, "_failed.txt"), "w") as f:
            for pdb_id, msg in failed:
                f.write(f"{pdb_id}\t{msg}\n")
        print(f"Failures logged to {OUT_DIR}/_failed.txt", flush=True)


if __name__ == "__main__":
    main()
