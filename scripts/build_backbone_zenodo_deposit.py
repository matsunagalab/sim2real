#!/usr/bin/env python3
"""Build the backbone-only MD part of the paper's Zenodo deposit.

Every deposited trajectory is the window the manuscript analysed: production
time in [10, 40) ns sampled every 100 ps, giving 300 frames, with the parent
equilibration structure as the native reference.  This is the window and the
reference used by :mod:`scripts.recompute_aligned_hphil_q`, so the published Q
labels can be recomputed from the deposited files alone.

The deposit contains two kinds of trajectories:

* ``md/mutation_scan_400K/{1mel,4idl}``: the 1MEL and 4IDL single mutation
  scans, subsampled from their 10 ps source cadence; and
* ``md/heterogeneous_{300K,400K}``: the heterogeneous nanobody panel, read from
  the full production trajectories, at its native 100 ps cadence.

The window is selected by time and never by frame index, because the source
productions differ in both length and sampling interval.

Only the backbone heavy atoms used by the published Q calculation (N, CA, C,
and O; MDAnalysis selection ``backbone``) are written.  Each component gets a
``MANIFEST.tsv`` and ``MISSING.tsv``.  Conversion is resumable: a valid PDB/DCD
pair is kept, while an incomplete or invalid pair is rebuilt.  New files and
manifests are written to temporary paths in the destination directory and moved
into place only after validation.

Examples
--------
Build everything with eight workers::

    uv run python scripts/build_backbone_zenodo_deposit.py --nproc 8

Test one heterogeneous trajectory outside the repository::

    uv run python scripts/build_backbone_zenodo_deposit.py \
        --components heterogeneous_300K --limit 1 --nproc 1 \
        --out-root /tmp/sim2real_backbone_test
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
import uuid
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


BACKBONE_SELECTION = "backbone"
BACKBONE_NAMES = frozenset({"N", "CA", "C", "O"})
# The analysed production window, identical for both data designs and equal to
# the window in scripts/recompute_aligned_hphil_q.py.  Sources are saved every
# 10 ps (mutation scans) or 100 ps (heterogeneous panel) and run for 40 ns or
# 100 ns, so the window is resolved from frame times rather than frame indices.
WINDOW_LO_PS = 10_000.0
WINDOW_HI_PS = 40_000.0
CADENCE_PS = 100.0
WINDOW_N_FRAMES = int(round((WINDOW_HI_PS - WINDOW_LO_PS) / CADENCE_PS))

COMPONENT_DIRS = {
    "scan_1mel": "md/mutation_scan_400K/1mel",
    "scan_4idl": "md/mutation_scan_400K/4idl",
    "heterogeneous_300K": "md/heterogeneous_300K",
    "heterogeneous_400K": "md/heterogeneous_400K",
}

MANIFEST_COLUMNS = [
    "component",
    "record_id",
    "dataset_role",
    "system",
    "mutation",
    "temperature_K",
    "sequence",
    "status",
    "reason",
    "source_topology",
    "source_trajectory",
    "reference_definition",
    "output_reference_pdb",
    "output_trajectory_dcd",
    "frame_start",
    "n_frames_source",
    "n_frames_kept",
    "n_atoms_backbone",
    "time_start_ps",
    "time_step_ps",
    "pdb_bytes",
    "dcd_bytes",
]


@dataclass(frozen=True)
class ConversionTask:
    """One independent PDB/DCD conversion job (safe to pickle)."""

    component: str
    record_id: str
    dataset_role: str
    system: str
    mutation: str
    temperature_k: str
    sequence: str
    source_dcd: str
    topology_candidates: tuple[str, ...]
    native_pdb: str
    output_pdb: str
    output_dcd: str
    window_lo_ps: float
    window_hi_ps: float
    cadence_ps: float
    reference_definition: str
    repo_root: str
    component_root: str
    force: bool = False


def display_path(path: Path, repo_root: Path) -> str:
    """Prefer a stable repository-relative path in manifests."""

    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def output_relative(path: Path, component_root: Path) -> str:
    return path.resolve().relative_to(component_root.resolve()).as_posix()


def atomic_write_tsv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    """Atomically replace a TSV after all rows have been serialized."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=MANIFEST_COLUMNS,
                delimiter="\t",
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in MANIFEST_COLUMNS})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def read_tsv_by_id(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {row["record_id"]: row for row in rows if row.get("record_id")}


def _production_and_reference(
    nodes_root: Path, want_temp: float | None
) -> tuple[Path, Path]:
    """Return (production trajectory, parent equilibration PDB) for one system.

    Resolved from the workflow DAG exactly as
    scripts/recompute_aligned_hphil_q.py resolves it, so the deposited
    trajectory and its native reference are the ones the published Q labels were
    computed from.  ``want_temp`` selects the production node by temperature;
    the heterogeneous panel has a 300 K and a 400 K production, the mutation
    scans a single one.
    """
    chosen: tuple[Path, dict] | None = None
    for path in sorted(nodes_root.glob("prod_*/artifacts/trajectory.dcd"), key=str):
        node = path.parent.parent.name
        node_json = nodes_root / node / "node.json"
        if not node_json.is_file():
            continue
        with node_json.open(encoding="utf-8") as handle:
            meta = json.load(handle)
        temperature = meta.get("conditions", {}).get("temperature_kelvin")
        if want_temp is None or temperature == want_temp:
            chosen = (path, meta)
    if chosen is None:
        raise FileNotFoundError(
            f"no production node at {want_temp} K under {nodes_root}"
        )
    path, meta = chosen
    parents = meta.get("parent_node_ids") or []
    if not parents:
        raise FileNotFoundError(f"production node under {nodes_root} has no parent")
    return path, nodes_root / parents[0] / "artifacts" / "equilibrated.pdb"


def _scan_topology_candidates(
    variant_root: Path, reference_pdb: Path
) -> tuple[Path, ...]:
    nodes = variant_root / "jobs" / "main" / "nodes"
    paths = [
        # The native reference doubles as the topology, as in the Q calculation.
        reference_pdb,
        nodes / "topo_001" / "artifacts" / "system.topology.pdb",
        nodes / "prod_001" / "artifacts" / "final_structure.pdb",
    ]
    paths.extend(
        sorted(nodes.glob("eq_*/artifacts/equilibrated.pdb"), key=str)
    )
    # Preserve fallback order while removing duplicate paths.
    return tuple(dict.fromkeys(paths))


def _base_row(task: ConversionTask) -> dict[str, object]:
    repo_root = Path(task.repo_root)
    component_root = Path(task.component_root)
    return {
        "component": task.component,
        "record_id": task.record_id,
        "dataset_role": task.dataset_role,
        "system": task.system,
        "mutation": task.mutation,
        "temperature_K": task.temperature_k,
        "sequence": task.sequence,
        "status": "not_checked",
        "reason": "not selected in this limited run",
        "source_topology": "",
        "source_trajectory": display_path(Path(task.source_dcd), repo_root),
        "reference_definition": task.reference_definition,
        "output_reference_pdb": output_relative(
            Path(task.output_pdb), component_root
        ),
        "output_trajectory_dcd": output_relative(
            Path(task.output_dcd), component_root
        ),
        "frame_start": "",
        "n_frames_source": "",
        "n_frames_kept": "",
        "n_atoms_backbone": "",
        "time_start_ps": "",
        "time_step_ps": "",
        "pdb_bytes": "",
        "dcd_bytes": "",
    }


def discover_scan(
    repo_root: Path,
    out_root: Path,
    study_root: Path,
    system: str,
) -> tuple[list[ConversionTask], list[dict[str, object]]]:
    component = f"scan_{system}"
    component_root = out_root / COMPONENT_DIRS[component]
    trajectory_root = component_root / "trajectories"
    csv_path = repo_root / "data" / "md" / f"study_qvalue_fep400k_{system}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"mutation-scan label table not found: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    ids = [row.get("vid", "") for row in source_rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"empty or duplicate vid in {csv_path}")

    tasks: list[ConversionTask] = []
    rows: list[dict[str, object]] = []
    for source_row in source_rows:
        record_id = source_row["vid"]
        variant_root = study_root / record_id
        nodes_root = variant_root / "jobs" / "main" / "nodes"
        unresolved = ""
        try:
            source_dcd, reference_pdb = _production_and_reference(
                nodes_root, want_temp=None
            )
        except (FileNotFoundError, ValueError, KeyError) as exc:
            source_dcd = nodes_root / "prod_001" / "artifacts" / "trajectory.dcd"
            reference_pdb = nodes_root / "eq_003" / "artifacts" / "equilibrated.pdb"
            unresolved = f"{type(exc).__name__}: {exc}"
        candidates = _scan_topology_candidates(variant_root, reference_pdb)
        stem = f"{record_id}_400K_backbone"
        task = ConversionTask(
            component=component,
            record_id=record_id,
            dataset_role="single mutation scan",
            system=source_row.get("system", system),
            mutation=source_row.get("mutation", ""),
            temperature_k="400",
            sequence=source_row.get("seq", ""),
            source_dcd=str(source_dcd),
            topology_candidates=tuple(str(path) for path in candidates),
            native_pdb=str(reference_pdb),
            output_pdb=str(trajectory_root / f"{stem}.pdb"),
            output_dcd=str(trajectory_root / f"{stem}.dcd"),
            window_lo_ps=WINDOW_LO_PS,
            window_hi_ps=WINDOW_HI_PS,
            cadence_ps=CADENCE_PS,
            reference_definition=(
                "parent equilibration structure, the coordinates that entered "
                "production (native reference used for Q)"
            ),
            repo_root=str(repo_root),
            component_root=str(component_root),
        )
        row = _base_row(task)
        if not source_dcd.is_file():
            reason = "source trajectory.dcd not found"
            if unresolved:
                reason += f"; production node unresolved ({unresolved})"
            row.update(status="missing", reason=reason)
        elif not reference_pdb.is_file():
            reason = "parent equilibration PDB not found"
            if unresolved:
                reason += f"; production node unresolved ({unresolved})"
            row.update(status="missing", reason=reason)
        elif not any(path.is_file() for path in candidates):
            row.update(status="missing", reason="no usable topology PDB candidate found")
        else:
            tasks.append(task)
        rows.append(row)
    return tasks, rows


def _heterogeneous_entries(source_root: Path, temp: str) -> list[dict[str, str]]:
    """One entry per ``job_nano_<pdb>`` job in the heterogeneous MD source.

    The window has to come from the full productions under the study root; the
    older protein-only staging directories keep the final 30 ns only and reset
    their time axis, so the analysed 10 to 40 ns cannot be recovered from them.
    """
    want_temp = float(temp.removesuffix("K"))
    entries: list[dict[str, str]] = []
    for job_root in sorted(source_root.glob("job_nano_*"), key=str):
        record_id = job_root.name.removeprefix("job_nano_")
        entry = {
            "record_id": record_id,
            "pdb": "",
            "dcd": "",
            "source_status": "ok",
            "source_reason": "",
        }
        try:
            trajectory, reference = _production_and_reference(
                job_root / "nodes", want_temp=want_temp
            )
            entry["dcd"] = str(trajectory)
            entry["pdb"] = str(reference)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            entry["source_status"] = "unresolved"
            entry["source_reason"] = f"{type(exc).__name__}: {exc}"
        entries.append(entry)
    return entries


def discover_heterogeneous(
    repo_root: Path,
    out_root: Path,
    source_root: Path,
    temp: str,
) -> tuple[list[ConversionTask], list[dict[str, object]]]:
    component = f"heterogeneous_{temp}"
    component_root = out_root / COMPONENT_DIRS[component]
    trajectory_root = component_root / "trajectories"
    entries = _heterogeneous_entries(source_root, temp)
    tasks: list[ConversionTask] = []
    rows: list[dict[str, object]] = []
    for entry in entries:
        record_id = entry["record_id"]
        source_pdb = Path(entry["pdb"]) if entry["pdb"] else source_root / "missing.pdb"
        source_dcd = Path(entry["dcd"]) if entry["dcd"] else source_root / "missing.dcd"
        stem = f"{record_id}_{temp}_backbone"
        task = ConversionTask(
            component=component,
            record_id=record_id,
            dataset_role="heterogeneous SAbDab nanobody panel",
            system="",
            mutation="",
            temperature_k=temp.removesuffix("K"),
            sequence="",
            source_dcd=str(source_dcd),
            topology_candidates=(str(source_pdb),),
            native_pdb=str(source_pdb),
            output_pdb=str(trajectory_root / f"{stem}.pdb"),
            output_dcd=str(trajectory_root / f"{stem}.dcd"),
            window_lo_ps=WINDOW_LO_PS,
            window_hi_ps=WINDOW_HI_PS,
            cadence_ps=CADENCE_PS,
            reference_definition=(
                "parent equilibration structure, the coordinates that entered "
                "production (native reference used for Q)"
            ),
            repo_root=str(repo_root),
            component_root=str(component_root),
        )
        row = _base_row(task)
        source_status = entry.get("source_status", "ok")
        source_reason = entry.get("source_reason", "")
        if source_status != "ok":
            reason = f"source status={source_status}"
            if source_reason:
                reason += f": {source_reason}"
            row.update(status="missing", reason=reason)
        elif not source_pdb.is_file() and not source_dcd.is_file():
            row.update(status="missing", reason="source PDB and DCD not found")
        elif not source_pdb.is_file():
            row.update(status="missing", reason="source native-reference PDB not found")
        elif not source_dcd.is_file():
            row.update(status="missing", reason="source trajectory DCD not found")
        else:
            tasks.append(task)
        rows.append(row)
    return tasks, rows


def _atom_signature(atoms: object) -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (str(atom.name), str(atom.resname), int(atom.resid)) for atom in atoms
    )


def _select_backbone(universe: object, context: str) -> object:
    atoms = universe.select_atoms(BACKBONE_SELECTION)
    if atoms.n_atoms == 0:
        raise ValueError(f"{context}: backbone selection contains zero atoms")
    unexpected = sorted(set(str(name) for name in atoms.names) - BACKBONE_NAMES)
    if unexpected:
        raise ValueError(
            f"{context}: backbone selection contains unexpected atom names: {unexpected}"
        )
    return atoms


def _window_frames(
    trajectory: object, lo_ps: float, hi_ps: float, cadence_ps: float
) -> list[int]:
    """Frame indices with time in ``[lo_ps, hi_ps)`` at ``cadence_ps`` spacing.

    Mirrors the frame selection in scripts/recompute_aligned_hphil_q.py: solve
    for the index range from the first frame time and the source interval, so a
    long or short production is windowed by time rather than by position.
    """
    trajectory[0]
    t0 = float(trajectory.time)
    dt = float(trajectory.dt)
    if dt <= 0.0:
        raise ValueError("source trajectory reports a non-positive timestep")
    stride = max(1, int(round(cadence_ps / dt)))
    if abs(stride * dt - cadence_ps) > 1.0e-3:
        raise ValueError(
            f"source interval {dt:g} ps cannot be subsampled to {cadence_ps:g} ps"
        )
    lo_i = max(0, math.ceil((lo_ps - t0) / dt))
    hi_i = min(len(trajectory) - 1, math.floor((hi_ps - 1.0e-6 - t0) / dt))
    return [
        index
        for index in range(lo_i, hi_i + 1, stride)
        if lo_ps - 1.0e-6 <= t0 + index * dt < hi_ps
    ]


def _load_source(task: ConversionTask) -> tuple[object, object, str]:
    import MDAnalysis as mda

    failures = []
    for topology in task.topology_candidates:
        if not Path(topology).is_file():
            continue
        try:
            universe = mda.Universe(topology, task.source_dcd)
            atoms = _select_backbone(universe, topology)
            # Force DCD header/frame access so an incompatible topology is rejected.
            if len(universe.trajectory) == 0:
                raise ValueError("trajectory contains zero frames")
            universe.trajectory[0]
            _ = atoms.positions
            return universe, atoms, topology
        except Exception as exc:  # noqa: BLE001 - fallback to next topology is intended
            failures.append(f"{Path(topology).name}: {type(exc).__name__}: {exc}")
    detail = "; ".join(failures) if failures else "no candidate exists"
    raise ValueError(f"no topology candidate could load the DCD ({detail})")


def _validate_output(
    pdb_path: Path,
    dcd_path: Path,
    expected_signature: Sequence[tuple[str, str, int]],
    expected_reference: object,
    expected_first: object,
    expected_last: object,
    expected_frames: int,
    expected_start_ps: float,
    expected_dt_ps: float,
) -> None:
    import MDAnalysis as mda
    import numpy as np

    if not pdb_path.is_file() or not dcd_path.is_file():
        raise ValueError("output PDB/DCD pair is incomplete")
    reference_u = mda.Universe(str(pdb_path))
    reference_atoms = _select_backbone(reference_u, str(pdb_path))
    if _atom_signature(reference_atoms) != tuple(expected_signature):
        raise ValueError("output PDB atom identity/order differs from the source")
    if not np.allclose(reference_atoms.positions, expected_reference, atol=2.0e-3):
        raise ValueError("output PDB does not preserve the required reference coordinates")

    output_u = mda.Universe(str(pdb_path), str(dcd_path))
    output_atoms = _select_backbone(output_u, str(dcd_path))
    if output_atoms.n_atoms != len(expected_signature):
        raise ValueError(
            f"output DCD has {output_atoms.n_atoms} atoms; expected {len(expected_signature)}"
        )
    if len(output_u.trajectory) != expected_frames:
        raise ValueError(
            f"output DCD has {len(output_u.trajectory)} frames; expected {expected_frames}"
        )
    output_u.trajectory[0]
    if not np.isclose(output_u.trajectory.time, expected_start_ps, atol=2.0e-4):
        raise ValueError(
            f"output DCD starts at {output_u.trajectory.time} ps; "
            f"expected {expected_start_ps} ps"
        )
    if not np.isclose(output_u.trajectory.dt, expected_dt_ps, atol=2.0e-4):
        raise ValueError(
            f"output DCD timestep is {output_u.trajectory.dt} ps; "
            f"expected {expected_dt_ps} ps"
        )
    if not np.allclose(output_atoms.positions, expected_first, atol=2.0e-3):
        raise ValueError("first output DCD frame differs from the source")
    output_u.trajectory[-1]
    if not np.allclose(output_atoms.positions, expected_last, atol=2.0e-3):
        raise ValueError("last output DCD frame differs from the source")


def convert_one(task: ConversionTask) -> dict[str, object]:
    """Convert and validate one task; exceptions become manifest error rows."""

    warnings.filterwarnings("ignore")
    row = _base_row(task)
    output_pdb = Path(task.output_pdb)
    output_dcd = Path(task.output_dcd)
    tmp_pdb: Path | None = None
    tmp_dcd: Path | None = None
    try:
        universe, atoms, topology_used = _load_source(task)
        signature = _atom_signature(atoms)
        n_source = len(universe.trajectory)
        frame_indices = _window_frames(
            universe.trajectory, task.window_lo_ps, task.window_hi_ps, task.cadence_ps
        )
        if len(frame_indices) != WINDOW_N_FRAMES:
            raise ValueError(
                f"[{task.window_lo_ps:g}, {task.window_hi_ps:g}) ps at "
                f"{task.cadence_ps:g} ps yielded {len(frame_indices)} frames of "
                f"{n_source}; expected {WINDOW_N_FRAMES}"
            )
        n_kept = len(frame_indices)
        frame_start = frame_indices[0]
        universe.trajectory[frame_start]
        start_time_ps = float(universe.trajectory.time)
        # Deposited sampling interval, not the source one: the scans are
        # subsampled from 10 ps to the analysed 100 ps cadence.
        time_step_ps = task.cadence_ps
        first_coordinates = atoms.positions.copy()
        universe.trajectory[frame_indices[-1]]
        last_coordinates = atoms.positions.copy()
        if task.native_pdb:
            import MDAnalysis as mda

            native_u = mda.Universe(task.native_pdb)
            native_atoms = _select_backbone(native_u, task.native_pdb)
            if _atom_signature(native_atoms) != signature:
                raise ValueError(
                    "native-reference PDB backbone atom identity/order differs from DCD topology"
                )
            reference_coordinates = native_atoms.positions.copy()
            reference_atoms = native_atoms
        else:
            universe.trajectory[0]
            reference_coordinates = atoms.positions.copy()
            reference_atoms = atoms

        validation_args = (
            signature,
            reference_coordinates,
            first_coordinates,
            last_coordinates,
            n_kept,
            start_time_ps,
            time_step_ps,
        )
        if not task.force and output_pdb.exists() and output_dcd.exists():
            try:
                _validate_output(output_pdb, output_dcd, *validation_args)
                row.update(status="existing", reason="valid output already present")
                row.update(
                    source_topology=display_path(Path(topology_used), Path(task.repo_root)),
                    n_frames_source=n_source,
                    n_frames_kept=n_kept,
                    frame_start=frame_start,
                    n_atoms_backbone=atoms.n_atoms,
                    time_start_ps=f"{start_time_ps:.9g}",
                    time_step_ps=f"{time_step_ps:.9g}",
                    pdb_bytes=output_pdb.stat().st_size,
                    dcd_bytes=output_dcd.stat().st_size,
                )
                return row
            except Exception:
                # Rebuild both files if either member of the pair is invalid.
                pass

        output_pdb.parent.mkdir(parents=True, exist_ok=True)
        token = f"{os.getpid()}.{uuid.uuid4().hex}"
        tmp_pdb = output_pdb.with_name(f".{output_pdb.stem}.{token}.tmp.pdb")
        tmp_dcd = output_dcd.with_name(f".{output_dcd.stem}.{token}.tmp.dcd")

        reference_atoms.write(str(tmp_pdb))
        import MDAnalysis as mda

        # Use nsavc=1 and express the source start in output-frame units.  This
        # preserves both the source sampling interval and its first-frame time.
        istart = int(round(start_time_ps / time_step_ps))
        with mda.Writer(
            str(tmp_dcd),
            n_atoms=atoms.n_atoms,
            dt=time_step_ps,
            nsavc=1,
            istart=istart,
        ) as writer:
            for index in frame_indices:
                universe.trajectory[index]
                writer.write(atoms)

        _validate_output(tmp_pdb, tmp_dcd, *validation_args)
        # The two files have been validated as a pair.  Individual replacements
        # are atomic; a crash between them is repaired on the next run.
        os.replace(tmp_pdb, output_pdb)
        tmp_pdb = None
        os.replace(tmp_dcd, output_dcd)
        tmp_dcd = None
        _validate_output(output_pdb, output_dcd, *validation_args)

        row.update(status="ok", reason="")
        row.update(
            source_topology=display_path(Path(topology_used), Path(task.repo_root)),
            n_frames_source=n_source,
            n_frames_kept=n_kept,
            frame_start=frame_start,
            n_atoms_backbone=atoms.n_atoms,
            time_start_ps=f"{start_time_ps:.9g}",
            time_step_ps=f"{time_step_ps:.9g}",
            pdb_bytes=output_pdb.stat().st_size,
            dcd_bytes=output_dcd.stat().st_size,
        )
        return row
    except Exception as exc:  # noqa: BLE001 - record per-file failure and continue
        row.update(status="error", reason=f"{type(exc).__name__}: {exc}")
        return row
    finally:
        for tmp_path in (tmp_pdb, tmp_dcd):
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass


def run_tasks(tasks: Sequence[ConversionTask], nproc: int) -> dict[str, dict[str, object]]:
    if not tasks:
        return {}
    results: dict[str, dict[str, object]] = {}
    if nproc == 1:
        iterator = enumerate((convert_one(task) for task in tasks), start=1)
        for index, row in iterator:
            results[str(row["record_id"])] = row
            print(
                f"[{index}/{len(tasks)}] {row['component']} {row['record_id']}: "
                f"{row['status']}",
                flush=True,
            )
        return results

    with ProcessPoolExecutor(max_workers=nproc) as pool:
        future_to_task = {pool.submit(convert_one, task): task for task in tasks}
        for index, future in enumerate(as_completed(future_to_task), start=1):
            task = future_to_task[future]
            try:
                row = future.result()
            except BaseException as exc:  # worker/pickle failures should still be recorded
                row = _base_row(task)
                row.update(status="error", reason=f"worker failure: {type(exc).__name__}: {exc}")
            results[str(row["record_id"])] = row
            print(
                f"[{index}/{len(tasks)}] {row['component']} {row['record_id']}: "
                f"{row['status']}",
                flush=True,
            )
    return results


def merge_component_rows(
    component_root: Path,
    base_rows: Sequence[dict[str, object]],
    results: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    previous = read_tsv_by_id(component_root / "MANIFEST.tsv")
    merged = []
    for base in base_rows:
        record_id = str(base["record_id"])
        if base["status"] == "missing":
            row = dict(base)
        elif record_id in results:
            row = dict(results[record_id])
        elif record_id in previous:
            # Preserve a previous completed row in --limit runs, but refresh the
            # immutable discovery metadata from the current source tables.
            row = dict(previous[record_id])
            for key in (
                "component",
                "record_id",
                "dataset_role",
                "system",
                "mutation",
                "temperature_K",
                "sequence",
                "source_trajectory",
                "reference_definition",
                "output_reference_pdb",
                "output_trajectory_dcd",
            ):
                row[key] = base.get(key, row.get(key, ""))
        else:
            row = dict(base)
        merged.append(row)
    return sorted(merged, key=lambda row: str(row["record_id"]))


def parse_components(value: str) -> list[str]:
    requested = [part.strip() for part in value.split(",") if part.strip()]
    if not requested or requested == ["all"]:
        return list(COMPONENT_DIRS)
    unknown = sorted(set(requested) - set(COMPONENT_DIRS))
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown component(s): {', '.join(unknown)}; choose from "
            f"{', '.join(COMPONENT_DIRS)}"
        )
    return list(dict.fromkeys(requested))


def build_parser(repo_root: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=repo_root, help="sim2real repository root"
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=repo_root / "zenodo" / "sim2real_deposit",
        help="single deposit staging directory",
    )
    parser.add_argument(
        "--study-root",
        type=Path,
        default=repo_root / "mdclaw" / "studies" / "fep_md_400k_all",
        help="1MEL/4IDL single mutation scan MD study directory",
    )
    # Both temperatures live in the same study root; the production node is
    # selected by temperature.  The full productions are required: the older
    # protein-only staging directories keep the final 30 ns only.
    heterogeneous_root = Path(os.path.expanduser("~/tmp/mdclaw_nanobodies"))
    parser.add_argument(
        "--heterogeneous-300k-root", type=Path, default=heterogeneous_root
    )
    parser.add_argument(
        "--heterogeneous-400k-root", type=Path, default=heterogeneous_root
    )
    parser.add_argument(
        "--components",
        default="all",
        help="comma-separated components or 'all': " + ", ".join(COMPONENT_DIRS),
    )
    parser.add_argument(
        "--nproc", type=int, default=min(8, os.cpu_count() or 1), help="worker processes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="convert only the first N available records per component (smoke tests)",
    )
    parser.add_argument(
        "--force", action="store_true", help="rebuild even if an output pair validates"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    inferred_root = Path(__file__).resolve().parents[1]
    parser = build_parser(inferred_root)
    args = parser.parse_args(argv)
    if args.nproc < 1:
        parser.error("--nproc must be at least 1")
    if args.limit < 0:
        parser.error("--limit cannot be negative")
    try:
        components = parse_components(args.components)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    repo_root = args.repo_root.resolve()
    out_root = args.out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    discoveries: dict[str, tuple[list[ConversionTask], list[dict[str, object]]]] = {}
    for component in components:
        if component == "scan_1mel":
            discoveries[component] = discover_scan(
                repo_root, out_root, args.study_root.resolve(), "1mel"
            )
        elif component == "scan_4idl":
            discoveries[component] = discover_scan(
                repo_root, out_root, args.study_root.resolve(), "4idl"
            )
        elif component == "heterogeneous_300K":
            discoveries[component] = discover_heterogeneous(
                repo_root, out_root, args.heterogeneous_300k_root.resolve(), "300K"
            )
        elif component == "heterogeneous_400K":
            discoveries[component] = discover_heterogeneous(
                repo_root, out_root, args.heterogeneous_400k_root.resolve(), "400K"
            )

    exit_code = 0
    for component in components:
        tasks, base_rows = discoveries[component]
        selected = tasks[: args.limit] if args.limit else tasks
        selected = [ConversionTask(**{**asdict(task), "force": args.force}) for task in selected]
        missing_before = sum(1 for row in base_rows if row["status"] == "missing")
        print(
            f"{component}: expected={len(base_rows)} available={len(tasks)} "
            f"selected={len(selected)} source_missing={missing_before}",
            flush=True,
        )
        results = run_tasks(selected, args.nproc)
        component_root = out_root / COMPONENT_DIRS[component]
        rows = merge_component_rows(component_root, base_rows, results)
        atomic_write_tsv(component_root / "MANIFEST.tsv", rows)
        problems = [row for row in rows if row.get("status") in {"missing", "error"}]
        atomic_write_tsv(component_root / "MISSING.tsv", problems)
        counts: dict[str, int] = {}
        for row in rows:
            status = str(row.get("status", ""))
            counts[status] = counts.get(status, 0) + 1
        print(
            f"{component}: wrote MANIFEST.tsv and MISSING.tsv; statuses={counts}",
            flush=True,
        )
        if any(row.get("status") == "error" for row in rows):
            exit_code = 1

    print(f"deposit root: {out_root}", flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
