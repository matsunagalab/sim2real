#!/usr/bin/env python3
"""Create and verify one ZIP archive per Zenodo deposit component.

The unpacked staging tree is kept separate from the upload-ready archives so
that checksums describe only the deposited payload, not duplicate copies of it.
Archives retain paths relative to the staging-tree root; extracting every
archive into one empty directory recreates the assembled deposit.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable


ARCHIVES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bundle_metadata", ("README.md", "MANIFEST.tsv", "CHECKSUMS.sha256")),
    ("fep", ("fep",)),
    ("rosetta_backrub_trajectories", ("rosetta_backrub_trajectories",)),
    ("rosetta_ddg_scans", ("rosetta_ddg_scans",)),
    ("thermompnn", ("thermompnn",)),
    ("md_matched_400K_1mel", ("md/matched_400K/1mel",)),
    ("md_matched_400K_4idl", ("md/matched_400K/4idl",)),
    ("md_heterogeneous_300K", ("md/heterogeneous_300K",)),
    ("md_heterogeneous_400K", ("md/heterogeneous_400K",)),
)

DEFAULT_SOURCE = Path("zenodo/sim2real_deposit")
DEFAULT_OUTPUT = Path("zenodo/sim2real_deposit_archives_ready")
CHECKSUM_NAME = "ARCHIVES.sha256"
CHUNK_SIZE = 8 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    command: list[str], *, stdout: object | None = None, cwd: Path | None = None
) -> None:
    subprocess.run(command, check=True, stdout=stdout, cwd=cwd)


def _archive_path(output: Path, name: str) -> Path:
    return output / f"{name}.zip"


def _require_tools() -> None:
    for tool in ("zip", "unzip", "zipinfo"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"required executable was not found: {tool}")


def _validate_source(source: Path) -> None:
    for _, members in ARCHIVES:
        for member in members:
            path = source / member
            if not path.exists():
                raise FileNotFoundError(f"archive member does not exist: {path}")


def _archive_batches(source: Path, name: str, members: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Split the scan component so each ZIP invocation stays responsive.

    Its many small files are otherwise slow to enumerate on the staging file
    system.  Each batch is appended to the same ZIP, so the public archive is
    still one file per logical component.
    """

    if name != "rosetta_ddg_scans":
        return [members]

    component = source / "rosetta_ddg_scans"
    batches: list[tuple[str, ...]] = []
    root_files = tuple(
        str(path.relative_to(source))
        for path in sorted(component.iterdir())
        if path.is_file()
    )
    if root_files:
        batches.append(root_files)
    for directory in ("single_muts/fep_muts_data", "single_muts/nbthermo_data", "single_muts/run_test_1", "single_muts/run_test_2"):
        batches.append((f"rosetta_ddg_scans/{directory}",))
    for parent in ("single_muts/not_nbthermo_data", "multi_muts"):
        for child in sorted((component / parent).iterdir()):
            if child.is_dir():
                batches.append((str(child.relative_to(source)),))
    return batches


def _create_archive(source: Path, output: Path, name: str, members: tuple[str, ...]) -> None:
    destination = _archive_path(output, name)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output, prefix=f".{destination.name}.", suffix=".tmp"
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.unlink()
        for batch in _archive_batches(source, name, members):
            _run(
                # DCD and several input artifacts are already compact binary
                # formats.  Storing them avoids a long, low-yield recompression
                # pass while retaining the broadly supported Zip64 container.
                ["zip", "-q", "-r", "-0", str(temporary), *batch],
                stdout=subprocess.DEVNULL,
                cwd=source,
            )
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _verify_archive(source: Path, archive: Path) -> None:
    # The ZIP CRC test reads and decompresses every archive member.  The raw
    # bundle's SHA-256 manifest independently verifies the source payload.
    _run(["unzip", "-tqq", str(archive)], stdout=subprocess.DEVNULL)
    result = subprocess.run(
        ["zipinfo", "-1", str(archive)],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    archived_paths = {line for line in result.stdout.splitlines() if not line.endswith("/")}
    expected_paths: set[str] = set()
    for root, _, files in os.walk(source):
        for filename in files:
            expected_paths.add(str((Path(root) / filename).relative_to(source)))
    relevant_paths = {
        path
        for path in expected_paths
        if any(path == member or path.startswith(f"{member}/") for member in _members_for(archive.name))
    }
    if archived_paths != relevant_paths:
        raise RuntimeError(f"archive path mismatch: {archive.name}")


def _members_for(archive_name: str) -> tuple[str, ...]:
    for name, members in ARCHIVES:
        if f"{name}.zip" == archive_name:
            return members
    raise ValueError(f"unknown archive: {archive_name}")


def _write_checksums(output: Path, archive_paths: Iterable[Path]) -> None:
    destination = output / CHECKSUM_NAME
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output, prefix=f".{CHECKSUM_NAME}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for archive in archive_paths:
                handle.write(f"{_sha256(archive)}  {archive.name}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _verify_checksums(output: Path, archive_paths: Iterable[Path]) -> None:
    expected: dict[str, str] = {}
    for line in (output / CHECKSUM_NAME).read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", maxsplit=1)
        expected[name] = digest
    names = {archive.name for archive in archive_paths}
    if set(expected) != names:
        raise RuntimeError("ARCHIVES.sha256 does not describe exactly the component archives")
    for archive in archive_paths:
        actual = _sha256(archive)
        if actual != expected[archive.name]:
            raise RuntimeError(f"archive checksum mismatch: {archive.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--component",
        choices=[name for name, _ in ARCHIVES],
        action="append",
        help="build or verify only this archive (repeatable)",
    )
    parser.add_argument(
        "--refresh-checksums",
        action="store_true",
        help="write ARCHIVES.sha256 for an already complete archive directory",
    )
    parser.add_argument("--verify", action="store_true", help="verify existing archives only")
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    _require_tools()
    _validate_source(source)
    all_archive_paths = [_archive_path(output, name) for name, _ in ARCHIVES]
    if args.refresh_checksums:
        if args.component is not None or args.verify:
            parser.error("--refresh-checksums cannot be combined with --component or --verify")
        if any(not archive.is_file() for archive in all_archive_paths):
            raise RuntimeError("cannot write checksums before every component archive exists")
        _write_checksums(output, all_archive_paths)
        return
    selected = tuple(
        item for item in ARCHIVES if args.component is None or item[0] in args.component
    )
    archive_paths = [_archive_path(output, name) for name, _ in selected]

    if args.verify:
        if args.component is None:
            _verify_checksums(output, archive_paths)
        else:
            checksum_lines = (output / CHECKSUM_NAME).read_text(encoding="utf-8").splitlines()
            expected = {line.split("  ", maxsplit=1)[1]: line.split("  ", maxsplit=1)[0] for line in checksum_lines}
            for archive in archive_paths:
                if _sha256(archive) != expected.get(archive.name):
                    raise RuntimeError(f"archive checksum mismatch: {archive.name}")
        for archive in archive_paths:
            _verify_archive(source, archive)
            print(f"Verified {archive.name}", flush=True)
        return

    output.mkdir(parents=True, exist_ok=True)
    for (name, members), archive in zip(selected, archive_paths, strict=True):
        _create_archive(source, output, name, members)
        print(f"Created {archive.name}", flush=True)
    if args.component is None:
        _write_checksums(output, archive_paths)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
