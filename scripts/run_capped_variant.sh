#!/usr/bin/env bash
#
# run_capped_variant.sh — reproduce ONE MD variant of the fep_md_400k_all
# campaign, adding ACE/NME terminal caps at the prepare_complex step.
#
# Reconstructed from:
#   * node.json metadata under
#       mdclaw/studies/fep_md_400k_all/1mel_A104D/jobs/main/nodes/*
#   * WT pilot real argv in mdclaw/.mdclaw_jobs.jsonl (eq/prod/min scripts)
#   * mdclaw skills: md-prepare/{acquisition,prepare-complex}.md,
#     common/node-cli-patterns.md, hpc-run/submit-single.md
#   * `mdclaw <tool> --help` signatures (every flag below was verified).
#
# THE ONE CHANGE vs the original campaign: prepare_complex gets --cap-termini
# (== --n-terminal-cap ACE --c-terminal-cap NME). terminal_cap_forcefield
# defaults to ff19SB, matching the topology force field, so it is omitted.
#
# This script runs the LOGIN-NODE prep chain (source -> prep -> [mutate] ->
# solv -> topo) locally, then PRINTS (does not execute) the SLURM submit
# commands for min -> eq_001 -> eq_002 -> prod restricted to nodes n1,n2,n4,n5.
#
# Usage:
#   run_capped_variant.sh SYSTEM MUTATION STUDY_ROOT
#     SYSTEM    : 1mel | 4idl
#     MUTATION  : point mutant e.g. A104D  (WT -> skip the mutation node)
#     STUDY_ROOT: parent dir for per-variant studies,
#                 e.g. /home/yasu/tmp/sim2real/mdclaw/studies/fep_md_400k_all_ccap
#
# Example:
#   run_capped_variant.sh 1mel A104D /home/yasu/tmp/sim2real/mdclaw/studies/fep_md_400k_all_ccap
#   run_capped_variant.sh 4idl WT    /home/yasu/tmp/sim2real/mdclaw/studies/fep_md_400k_all_ccap
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
if [ "$#" -ne 3 ]; then
  echo "usage: $0 SYSTEM MUTATION STUDY_ROOT" >&2
  echo "  e.g. $0 1mel A104D /home/yasu/tmp/sim2real/mdclaw/studies/fep_md_400k_all_ccap" >&2
  exit 2
fi
SYSTEM="$1"          # 1mel | 4idl
MUTATION="$2"        # A104D ... | WT
STUDY_ROOT="$3"

# ---------------------------------------------------------------------------
# Paths / launcher
# ---------------------------------------------------------------------------
REPO="/home/yasu/tmp/sim2real"
# The `mdclaw` launcher (repo checkout). The existing jobs invoked bare
# `mdclaw ...`; on the login/compute nodes it is on PATH. Reference the repo
# copy explicitly for the login-node chain so the driver is location-robust.
MDCLAW="${MDCLAW_BIN:-$REPO/mdclaw/bin/mdclaw}"
# For the SLURM --script payload we emit bare `mdclaw` to match .mdclaw_jobs.jsonl
# exactly (compute nodes resolve it on PATH).
MDCLAW_RUN="mdclaw"

# Source PDB: local crystal structure under data/foldX (source_001 node.json
# metadata.original_path). 1mel -> 1MEL.pdb, 4idl -> 4IDL.pdb (the un-repaired
# crystal PDB, NOT *_Repair.pdb).
case "$SYSTEM" in
  1mel) SRC_PDB="$REPO/data/foldX/1MEL.pdb" ;;
  4idl) SRC_PDB="$REPO/data/foldX/4IDL.pdb" ;;
  *) echo "unknown SYSTEM: $SYSTEM (expected 1mel|4idl)" >&2; exit 2 ;;
esac
if [ ! -f "$SRC_PDB" ]; then echo "missing source PDB: $SRC_PDB" >&2; exit 1; fi

# Variant id / study layout: one study per variant, job 'main'.
VID="${SYSTEM}_${MUTATION}"
STUDY_DIR="$STUDY_ROOT/$VID"
JD="$STUDY_DIR/jobs/main"

# Chain-scoped mutation spec (prep_002 node.json metadata.mutation_specs),
# e.g. A104D -> "A:A104D".
MUT_SPEC="A:${MUTATION}"

echo "== capped variant: SYSTEM=$SYSTEM MUTATION=$MUTATION =="
echo "   source PDB : $SRC_PDB"
echo "   study_dir  : $STUDY_DIR"
echo "   job_dir    : $JD"
echo

# ---------------------------------------------------------------------------
# Helper: run create_node and echo the new node_id (parses JSON stdout).
# ---------------------------------------------------------------------------
new_node() {
  # args: --node-type X [--parent-node-ids ...] [--label ...] [--conditions ...]
  local out
  out="$("$MDCLAW" create_node --job-dir "$JD" "$@")"
  printf '%s\n' "$out" >&2
  printf '%s' "$out" | python3 -c 'import sys,re;m=re.search(r"\"node_id\"\s*:\s*\"([^\"]+)\"",sys.stdin.read());print(m.group(1) if m else "");' \
    | { read -r nid; [ -n "$nid" ] || { echo "FAILED to parse node_id from create_node" >&2; exit 1; }; printf '%s' "$nid"; }
}

# ===========================================================================
# 0. Bootstrap study/plan/job layout (bootstrap_md_workflow)
#    solvent-regime explicit (bootstrap default; matches prep_001 explicit).
# ===========================================================================
"$MDCLAW" bootstrap_md_workflow \
  --study-dir "$STUDY_DIR" \
  --question "Capped ($SYSTEM $MUTATION) FEP-condition MD Q-value at 400 K, ACE/NME termini" \
  --md-goal "Reproduce fep_md_400k_all $VID with terminal caps" \
  --solvent-regime explicit \
  --job-id main --job-role main

# ===========================================================================
# 1. source_001 (source): register the LOCAL crystal PDB as the source bundle.
#    acquisition.md canonical form: create source node, then
#    `fetch_structure --source local --file-path <abs.pdb>` (copies into node,
#    writes artifacts/source_bundle.json with metadata.original_path).
#    NOTE: `register_local_structure --file-path ...` is the compat alias and
#    produces an equivalent bundle (source_type=local, copy_mode=copy).
# ===========================================================================
SRC_ID="$(new_node --node-type source)"
"$MDCLAW" --job-dir "$JD" --node-id "$SRC_ID" \
  fetch_structure --source local --file-path "$SRC_PDB" --copy

# ===========================================================================
# 2. prep_001 (prep / prepare_complex): clean + merge + protonate + disulfides.
#    Flags from prep_001 node.json metadata:
#      - solvent-type explicit  (prep_solvent_type=explicit)
#      - ph 7.4                 (protonation_method pdb2pqr+propka, pH 7.4)
#      - disulfides AUTO-detected (do NOT pass --disulfide-pairs; 1mel finds
#        22-96, 33-109 automatically as in the original campaign)
#    THE ONE CHANGE: --cap-termini  (== ACE at N-term, NME at C-term).
#      terminal_cap_forcefield defaults to ff19SB, so it is omitted.
# ===========================================================================
PREP1_ID="$(new_node --node-type prep --parent-node-ids "$SRC_ID")"
"$MDCLAW" --job-dir "$JD" --node-id "$PREP1_ID" \
  prepare_complex \
    --ph 7.4 \
    --solvent-type explicit \
    --cap-termini

# ===========================================================================
# 3. prep_002 (prep / create_mutated_structure): HPacker point mutation.
#    Skipped in WT mode.
#    Flags from prep_002 node.json metadata:
#      - mutations "A:<MUT>"          (mutation_specs)
#      - repack-radius-angstrom 0.0   (repack_radius_angstrom=0.0)
#      - refinement-iterations 5      (default; recorded value)
#    HPacker is the only/implied backend (sidechain_method=hpacker); there is
#    no --backend flag. Input PDB auto-resolves from the prep_001 merged_pdb.
# ===========================================================================
if [ "$MUTATION" = "WT" ]; then
  echo "-- WT mode: skipping mutation node (prep_002) --"
  PREP_FRONTIER="$PREP1_ID"
else
  PREP2_ID="$(new_node --node-type prep --parent-node-ids "$PREP1_ID")"
  "$MDCLAW" --job-dir "$JD" --node-id "$PREP2_ID" \
    create_mutated_structure \
      --mutations "$MUT_SPEC" \
      --repack-radius-angstrom 0.0 \
      --refinement-iterations 5
  PREP_FRONTIER="$PREP2_ID"
fi

# ===========================================================================
# 4. solv_001 (solv / solvate_structure): OPC cubic box, 15 A buffer, 0.15 M salt.
#    Flags from solv_001 node.json metadata:
#      - water-model opc              (water_model=opc)
#      - --cubic                      (box_shape=cubic; default True, explicit)
#      - dist 15.0                    (buffer_distance_angstrom=15.0)
#      - --salt / saltcon 0.15        (salt_concentration_M=0.15, neutralize)
#    Input PDB auto-resolves from the frontier prep node (mutated_pdb or merged).
# ===========================================================================
SOLV_ID="$(new_node --node-type solv --parent-node-ids "$PREP_FRONTIER")"
"$MDCLAW" --job-dir "$JD" --node-id "$SOLV_ID" \
  solvate_structure \
    --water-model opc \
    --cubic \
    --dist 15.0 \
    --salt --saltcon 0.15

# ===========================================================================
# 5. topo_001 (topo / build_amber_system): ff19SB + OPC, HMR on.
#    Flags from topo_001 node.json metadata:
#      - forcefield ff19SB   (forcefield=ff19SB)
#      - water-model opc      (water_model=opc)
#      - --hmr                (hmr=True, hydrogen_mass 4 amu)
#    PDB + box_dimensions auto-resolve from the completed solv parent.
# ===========================================================================
TOPO_ID="$(new_node --node-type topo --parent-node-ids "$SOLV_ID")"
"$MDCLAW" --job-dir "$JD" --node-id "$TOPO_ID" \
  build_amber_system \
    --forcefield ff19SB \
    --water-model opc \
    --hmr

echo
echo "== login-node prep chain complete through topo ($TOPO_ID) =="

# ===========================================================================
# 6. min / eq_001 / eq_002 / prod : create nodes (login), then PRINT submit cmds.
#    Node structure & run params from the all-campaign node.json:
#      min_001  : run_minimization --platform CUDA
#      eq_001   : 300 K, 1.0 bar, NVT 0.2 ns + NPT 0.8 ns   (eq_001 metadata)
#      eq_002   : 400 K, 0 bar,  NVT 0.5 ns  (heat to 400 K; eq_002 metadata)
#      prod_001 : 40 ns, 400 K, 0 bar (NVT), output 10 ps   (prod_001 metadata)
#    (timestep is 4 fs via HMR — not passed on the CLI, matching WT pilot argv.)
#    SLURM restricted to nodes n1,n2,n4,n5 via submit_job --nodelist (-> -w).
#    submit_job is a HOST/native tool; the inner --script uses bare `mdclaw`
#    (matches .mdclaw_jobs.jsonl). --platform CUDA auto-selects a GPU; --gpus 1
#    is passed explicitly. time-limits mirror the WT pilot (min 2h/eq 6h/prod 3d).
# ===========================================================================
MIN_ID="$(new_node --node-type min --parent-node-ids "$TOPO_ID")"
EQ1_ID="$(new_node --node-type eq  --parent-node-ids "$MIN_ID")"
EQ2_ID="$(new_node --node-type eq  --parent-node-ids "$EQ1_ID")"
PROD_ID="$(new_node --node-type prod --parent-node-ids "$EQ2_ID")"

NODELIST="n1,n2,n4,n5"

cat <<EOF

############################################################################
# SLURM SUBMIT COMMANDS (NOT executed) — run these to launch the GPU chain.
# Restricted to nodes: $NODELIST
# Run in order; each captures its job id so the next can depend on it.
############################################################################

MIN_JID=\$($MDCLAW_RUN submit_job \\
  --job-dir "$JD" --node-id "$MIN_ID" \\
  --job-name "min_${VID}" \\
  --partition all --gpus 1 --time-limit "02:00:00" \\
  --nodelist "$NODELIST" \\
  --script "$MDCLAW_RUN --job-dir $JD --node-id $MIN_ID run_minimization --platform CUDA" \\
  | python3 -c 'import sys,re;print(re.search(r"\"job_id\"\s*:\s*\"?(\d+)",sys.stdin.read()).group(1))')

EQ1_JID=\$($MDCLAW_RUN submit_job \\
  --job-dir "$JD" --node-id "$EQ1_ID" \\
  --job-name "eq_${VID}_300K" \\
  --partition all --gpus 1 --time-limit "06:00:00" \\
  --nodelist "$NODELIST" --dependency "afterok:\$MIN_JID" \\
  --script "$MDCLAW_RUN --job-dir $JD --node-id $EQ1_ID run_equilibration --temperature-kelvin 300 --pressure-bar 1.0 --nvt-time-ns 0.2 --npt-time-ns 0.8 --platform CUDA" \\
  | python3 -c 'import sys,re;print(re.search(r"\"job_id\"\s*:\s*\"?(\d+)",sys.stdin.read()).group(1))')

EQ2_JID=\$($MDCLAW_RUN submit_job \\
  --job-dir "$JD" --node-id "$EQ2_ID" \\
  --job-name "eq_${VID}_400K" \\
  --partition all --gpus 1 --time-limit "06:00:00" \\
  --nodelist "$NODELIST" --dependency "afterok:\$EQ1_JID" \\
  --script "$MDCLAW_RUN --job-dir $JD --node-id $EQ2_ID run_equilibration --temperature-kelvin 400 --pressure-bar 0 --nvt-time-ns 0.5 --platform CUDA" \\
  | python3 -c 'import sys,re;print(re.search(r"\"job_id\"\s*:\s*\"?(\d+)",sys.stdin.read()).group(1))')

PROD_JID=\$($MDCLAW_RUN submit_job \\
  --job-dir "$JD" --node-id "$PROD_ID" \\
  --job-name "prod_${VID}" \\
  --partition all --gpus 1 --time-limit "3-00:00:00" \\
  --nodelist "$NODELIST" --dependency "afterok:\$EQ2_JID" \\
  --script "$MDCLAW_RUN --job-dir $JD --node-id $PROD_ID run_production --simulation-time-ns 40 --temperature-kelvin 400 --pressure-bar 0 --output-frequency-ps 10 --platform CUDA" \\
  | python3 -c 'import sys,re;print(re.search(r"\"job_id\"\s*:\s*\"?(\d+)",sys.stdin.read()).group(1))')

echo "submitted: min=\$MIN_JID eq300=\$EQ1_JID eq400=\$EQ2_JID prod=\$PROD_JID"
############################################################################
EOF
