#!/bin/bash
#SBATCH -p all
#SBATCH -J r_1mel_2muts_plm
#SBATCH -n 1
#SBATCH -c 1
#SBATCH -o run.log
set -euo pipefail

PDB_ID=1MEL
CHAIN_ID=A

# Rosetta paths
ROSETTA_ROOT=/opt/rosetta.source.release-371/main
ROSETTA_BIN="${ROSETTA_ROOT}/source/bin"
ROSETTA_DB="${ROSETTA_ROOT}/database"
ROSETTA_SRC_LIB="${ROSETTA_ROOT}/source/build/src/release/linux/5.15/64/x86/gcc/12.4/default"
ROSETTA_EXT_LIB="${ROSETTA_ROOT}/source/build/external/release/linux/5.15/64/x86/gcc/12.4/default"

# Force using Rosetta's libcifparse first
export LD_PRELOAD="${ROSETTA_EXT_LIB}/libcifparse.so"

# Library search path: Rosetta → system
export LD_LIBRARY_PATH="${ROSETTA_EXT_LIB}:${ROSETTA_SRC_LIB}:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu"

# Clean PDB (extract chain)
"${ROSETTA_ROOT}/tools/protein_tools/scripts/clean_pdb.py" --keepzeroocc "${PDB_ID}.pdb" "${CHAIN_ID}"

# Generate mutation list and sequences
/usr/bin/python3 csv_to_rosetta_mutations.py \
  --csv_file esm2_650M_large_scale_variants_1mel_100000_top1pct.csv \
  --output_file muts.txt \
  --num_files 20