#!/usr/bin/env python3
"""Recompute the 400-K MD label sets with one Q definition and time window.

Both sequence designs use the final 30 ns of production dynamics and all
backbone heavy-atom contacts in the Best--Hummer Q definition.  They differ only
in the native reference, chosen with --reference:

  * wt_crystal (N, default for the scans): every mutant is referenced to the
    shared wild-type crystal chain (data/foldX/{1MEL,4IDL}.pdb), so Q measures
    deviation from the true native fold.  Backbone atoms exist in every variant,
    so the reference is atom-comparable across chemically distinct mutants.
  * own_topo (S): each variant is referenced to its own starting structure.
    This is the same protocol as the heterogeneous panel, which makes the scans
    and the heterogeneous set directly comparable.
  * own_frame0: each variant is referenced to its own production frame 0.

The heterogeneous panel has no shared wild type, so it is always referenced to
each entry's own starting structure (the S protocol).  Its staging trajectories
are already reduced to the final 333 frames of 100-ps output, so their final 300
frames provide the common window; matched trajectories were saved every 10 ps,
so their final 3,000 frames are used.
"""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import MDAnalysis as mda
from MDAnalysis.lib.util import convert_aa_code

warnings.filterwarnings("ignore", category=UserWarning, module="MDAnalysis")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="MDAnalysis")


REPO_ROOT = Path(__file__).resolve().parents[1]
MATCHED_STUDY = REPO_ROOT / "mdclaw/studies/fep_md_400k_all"
HETERO_SOURCE = REPO_ROOT / "zenodo/md_trajectories_400K/trajectories"
WT_CRYSTAL = {"1mel": REPO_ROOT / "data/foldX/1MEL.pdb", "4idl": REPO_ROOT / "data/foldX/4IDL.pdb"}
MATCHED_FRAMES = 3_000
HETERO_FRAMES = 300
BETA = 50.0
LAMBDA = 1.8
CUTOFF_NM = 0.45
MIN_RESIDUE_GAP = 3


def sequence_from_atoms(atoms: Any) -> str:
    sequence: list[str] = []
    for residue in atoms.residues:
        try:
            sequence.append(convert_aa_code(residue.resname))
        except ValueError:
            sequence.append("X")
    return "".join(sequence)


def wt_chain_backbone(wt_pdb: str, expected_n_atoms: int) -> tuple[np.ndarray, np.ndarray]:
    """Backbone heavy-atom coordinates (nm) and residue indices of the single
    wild-type chain whose backbone atom count matches ``expected_n_atoms``.

    The crystal deposit stores several copies of the domain; the mutation scan
    covers one chain, so we select the chain with the matching backbone count.
    Backbone atoms are ordered residue-by-residue (N, CA, C, O) identically to
    the trajectory selection, so the returned array corresponds positionally to
    ``trajectory.select_atoms("backbone and not name H*")``.
    """
    universe = mda.Universe(wt_pdb)
    for segment in universe.select_atoms("protein").segments:
        backbone = segment.atoms.select_atoms("backbone and not name H*")
        if backbone.n_atoms == expected_n_atoms:
            return backbone.positions / 10.0, backbone.resindices - backbone.resindices.min()
    raise ValueError(f"no wild-type chain in {wt_pdb} with {expected_n_atoms} backbone atoms")


def q_from_pair(
    reference_pdb: str,
    trajectory_dcd: str,
    n_frames: int,
    native_from_dcd: bool,
    wt_native_pdb: str | None = None,
) -> dict[str, Any]:
    """Return Q over the final ``n_frames`` from a chosen native reference.

    Native contacts come from one of three references:
      * ``wt_native_pdb`` set: a shared wild-type crystal chain (reference N);
      * ``native_from_dcd``: this variant's own production frame 0;
      * otherwise: this variant's own starting structure ``reference_pdb`` (S).
    All three evaluate the same trajectory backbone atoms, so only the reference
    distances differ.
    """

    reference = mda.Universe(reference_pdb)
    ref_atoms = reference.select_atoms("backbone and not name H*")
    trajectory = mda.Universe(reference_pdb, trajectory_dcd)
    atoms = trajectory.select_atoms("backbone and not name H*")
    if ref_atoms.n_atoms != atoms.n_atoms:
        raise ValueError(f"backbone atom mismatch: {ref_atoms.n_atoms} != {atoms.n_atoms}")
    if ref_atoms.n_atoms == 0:
        raise ValueError("no backbone heavy atoms")

    if wt_native_pdb is not None:
        native, residue_indices = wt_chain_backbone(wt_native_pdb, atoms.n_atoms)
    elif native_from_dcd:
        trajectory.trajectory[0]
        native = atoms.positions / 10.0
        residue_indices = atoms.resindices
    else:
        native = ref_atoms.positions / 10.0
        residue_indices = ref_atoms.resindices
    distances = np.sqrt(((native[:, None, :] - native[None, :, :]) ** 2).sum(axis=-1))
    contact_mask = (
        (distances < CUTOFF_NM)
        & (np.abs(residue_indices[:, None] - residue_indices[None, :]) > MIN_RESIDUE_GAP)
        & np.triu(np.ones_like(distances, dtype=bool), k=1)
    )
    ii, jj = np.where(contact_mask)
    if not len(ii):
        raise ValueError("no native contacts")
    native_distances = distances[ii, jj]
    atom_i, atom_j = atoms.indices[ii], atoms.indices[jj]

    total = len(trajectory.trajectory)
    start = max(0, total - n_frames)
    q_sum = 0.0
    n_used = 0
    for _ in trajectory.trajectory[start:]:
        coordinates = trajectory.atoms.positions / 10.0
        current_distances = np.sqrt(
            ((coordinates[atom_i] - coordinates[atom_j]) ** 2).sum(axis=-1)
        )
        q_sum += (1.0 / (1.0 + np.exp(BETA * (current_distances - LAMBDA * native_distances)))).mean()
        n_used += 1
    return {
        "q_value": q_sum / n_used,
        "n_frames_source": total,
        "n_frames_used": n_used,
        "frame_start": start,
        "n_contacts": len(ii),
        "sequence": sequence_from_atoms(ref_atoms),
    }


def matched_task(system: str, record_id: str, reference: str) -> dict[str, Any]:
    nodes = MATCHED_STUDY / record_id / "jobs/main/nodes"
    topology_candidates = (
        nodes / "topo_001/artifacts/system.topology.pdb",
        nodes / "prod_001/artifacts/final_structure.pdb",
        *sorted(nodes.glob("eq_*/artifacts/equilibrated.pdb"), key=str),
    )
    reference_pdb = next((path for path in topology_candidates if path.is_file()), topology_candidates[0])
    # own_frame0 (S was the earlier default): own production frame 0.
    # own_topo (S): each variant's own starting structure, the reference_pdb.
    # wt_crystal (N): the shared wild-type crystal chain.
    return {
        "record_id": record_id,
        "system": system,
        "mutation": record_id.partition("_")[2],
        "reference_pdb": str(reference_pdb),
        "trajectory_dcd": str(nodes / "prod_001/artifacts/trajectory.dcd"),
        "n_frames": MATCHED_FRAMES,
        "native_from_dcd": reference == "own_frame0",
        "wt_native_pdb": str(WT_CRYSTAL[system]) if reference == "wt_crystal" else "",
    }


def hetero_task(record_id: str) -> dict[str, Any]:
    # No shared wild type exists across the heterogeneous panel, so each entry is
    # always referenced to its own starting structure (the S protocol).
    return {
        "record_id": record_id,
        "system": "",
        "mutation": "",
        "reference_pdb": str(HETERO_SOURCE / f"{record_id}_400K.pdb"),
        "trajectory_dcd": str(HETERO_SOURCE / f"{record_id}_400K.dcd"),
        "n_frames": HETERO_FRAMES,
        "native_from_dcd": False,
        "wt_native_pdb": "",
    }


TASK_ONLY_KEYS = {"n_frames", "native_from_dcd", "wt_native_pdb"}


def run_task(task: dict[str, Any]) -> dict[str, Any]:
    row = {key: value for key, value in task.items() if key not in TASK_ONLY_KEYS}
    try:
        result = q_from_pair(
            task["reference_pdb"],
            task["trajectory_dcd"],
            task["n_frames"],
            task["native_from_dcd"],
            wt_native_pdb=task["wt_native_pdb"] or None,
        )
        return {**row, **result, "status": "ok", "reason": ""}
    except Exception as error:  # noqa: BLE001
        return {**row, "status": "error", "reason": f"{type(error).__name__}: {error}"}


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "record_id", "system", "mutation", "sequence", "q_value", "n_frames_source",
        "n_frames_used", "frame_start", "n_contacts", "status", "reason",
        "reference_pdb", "trajectory_dcd",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda row: row["record_id"]))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("matched_1mel", "matched_4idl", "heterogeneous"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--reference",
        choices=("wt_crystal", "own_topo", "own_frame0"),
        default="wt_crystal",
        help="native reference for the mutation scans: wt_crystal (N, shared wild-type "
        "crystal chain), own_topo (S, each variant's own starting structure), or "
        "own_frame0 (each variant's own production frame 0). Ignored for heterogeneous.",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="resume from rows already written to --out")
    args = parser.parse_args()

    if args.source.startswith("matched_"):
        system = args.source.removeprefix("matched_")
        table = REPO_ROOT / f"data/md/study_qvalue_fep400k_{system}.csv"
        with table.open(newline="", encoding="utf-8") as handle:
            tasks = [matched_task(system, row["vid"], args.reference) for row in csv.DictReader(handle)]
    else:
        if args.reference == "wt_crystal":
            parser.error("heterogeneous has no shared wild type; use --reference own_topo")
        tasks = [hetero_task(path.name.removesuffix("_400K.dcd")) for path in sorted(HETERO_SOURCE.glob("*_400K.dcd"))]
    if args.resume and args.out.exists():
        with args.out.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        # Retry failure rows: some old jobs lack the canonical topology PDB but
        # retain an equivalent production or equilibration structure.
        completed = {
            row["record_id"] for row in rows
            if row.get("record_id") and row.get("status") == "ok"
        }
        rows = [row for row in rows if row.get("status") == "ok"]
        tasks = [task for task in tasks if task["record_id"] not in completed]
        print(f"{args.source}: resuming with {len(rows)} completed rows", flush=True)
    else:
        rows = []
    if args.limit:
        tasks = tasks[: args.limit]

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run_task, task) for task in tasks]
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            # A trajectory scan can run for hours.  Persist each completed row
            # so an external interruption never discards completed MD labels.
            write_rows(args.out, rows)
            # Keep a visible heartbeat during long trajectory scans; this also
            # makes interrupted runs immediately diagnosable.
            if index % 10 == 0 or index == len(tasks):
                print(f"{args.source}: {index}/{len(tasks)}", flush=True)
    write_rows(args.out, rows)
    failures = sum(row["status"] != "ok" for row in rows)
    print(f"wrote {args.out}: {len(rows) - failures} ok, {failures} failed", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
