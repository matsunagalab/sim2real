#!/usr/bin/env python3
"""Create and verify checksums for the assembled Zenodo deposit.

Generation writes one ``CHECKSUMS.sha256`` in each logical component, plus a
bundle-wide ``MANIFEST.tsv`` and ``CHECKSUMS.sha256`` at the deposit root.  The
component checksum paths are relative to their component; bundle-wide paths
are relative to the deposit root.  All generated files are replaced atomically.

The bundle-wide manifest intentionally does not contain itself.  Checksum files
are omitted from every inventory.  The bundle-wide checksum file does include
``MANIFEST.tsv``, so the manifest itself is protected by a digest.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator, Sequence


COMPONENTS: tuple[PurePosixPath, ...] = (
    PurePosixPath("fep"),
    PurePosixPath("rosetta_backrub_trajectories"),
    PurePosixPath("rosetta_ddg_scans"),
    PurePosixPath("foldx"),
    PurePosixPath("md/mutation_scan_400K/1mel"),
    PurePosixPath("md/mutation_scan_400K/4idl"),
    # Only the 400 K productions carry labels; the 300 K runs are not deposited.
    PurePosixPath("md/heterogeneous_400K"),
)

CHECKSUM_NAME = "CHECKSUMS.sha256"
MANIFEST_NAME = "MANIFEST.tsv"
MANIFEST_HEADER = "path\tcomponent\tsize_bytes\tsha256\n"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HASH_CHUNK_SIZE = 8 * 1024 * 1024
HASH_BATCH_SIZE = 2048


@dataclass(frozen=True)
class FileRecord:
    """Observed metadata and digest for one file."""

    path: PurePosixPath
    size: int
    sha256: str
    device: int
    inode: int
    mtime_ns: int


def _component_path(root: Path, component: PurePosixPath) -> Path:
    return root.joinpath(*component.parts)


def _is_checksum(path: PurePosixPath) -> bool:
    return path.name == CHECKSUM_NAME


def _is_top_manifest(path: PurePosixPath) -> bool:
    return path == PurePosixPath(MANIFEST_NAME)


def _validate_serializable_path(path: PurePosixPath) -> None:
    text = path.as_posix()
    if not text or "\n" in text or "\r" in text or "\t" in text:
        raise ValueError(f"path cannot be represented safely: {text!r}")


def _walk_files(root: Path) -> list[PurePosixPath]:
    """Return all regular files below *root* and reject symlinks/special files."""

    files: list[PurePosixPath] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)

        dirnames.sort()
        filenames.sort()
        for dirname in dirnames:
            child = directory_path / dirname
            if child.is_symlink():
                raise ValueError(f"symlinked directories are not allowed: {child}")

        for filename in filenames:
            child = directory_path / filename
            metadata = child.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError(f"symlinked files are not allowed: {child}")
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"non-regular files are not allowed: {child}")
            relative = PurePosixPath(child.relative_to(root).as_posix())
            _validate_serializable_path(relative)
            files.append(relative)

    files.sort(key=lambda path: path.as_posix())
    return files


def _hash_one(root: Path, relative: PurePosixPath) -> FileRecord:
    path = root.joinpath(*relative.parts)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"not a regular file: {path}")

    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        while chunk := handle.read(HASH_CHUNK_SIZE):
            digest.update(chunk)

    after = path.stat(follow_symlinks=False)
    signature_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    signature_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if signature_before != signature_after:
        raise RuntimeError(f"file changed while it was being hashed: {path}")

    return FileRecord(
        path=relative,
        size=after.st_size,
        sha256=digest.hexdigest(),
        device=after.st_dev,
        inode=after.st_ino,
        mtime_ns=after.st_mtime_ns,
    )


def _batched(values: Sequence[PurePosixPath], size: int) -> Iterator[Sequence[PurePosixPath]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _hash_files(
    root: Path,
    paths: Sequence[PurePosixPath],
    workers: int,
) -> dict[PurePosixPath, FileRecord]:
    """Hash paths with bounded batches to avoid one Future per deposit file."""

    records: dict[PurePosixPath, FileRecord] = {}
    completed = 0
    total = len(paths)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for batch in _batched(paths, HASH_BATCH_SIZE):
            for record in executor.map(lambda item: _hash_one(root, item), batch):
                records[record.path] = record
                completed += 1
            if total and (completed == total or completed % 10_000 < len(batch)):
                print(f"Hashed {completed:,}/{total:,} files", file=sys.stderr, flush=True)
    return records


def _atomic_write(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            os.fchmod(handle.fileno(), 0o644)
            for line in lines:
                handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        try:
            directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        except (AttributeError, OSError):
            return
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _component_for(path: PurePosixPath) -> str:
    parts = path.parts
    for component in COMPONENTS:
        component_parts = component.parts
        if parts[: len(component_parts)] == component_parts:
            return component.as_posix()
    return "bundle"


def _relative_to(path: PurePosixPath, parent: PurePosixPath) -> PurePosixPath:
    return PurePosixPath(*path.parts[len(parent.parts) :])


def _checksum_lines(
    paths: Iterable[PurePosixPath],
    records: dict[PurePosixPath, FileRecord],
    parent: PurePosixPath | None = None,
) -> Iterator[str]:
    for path in paths:
        output_path = _relative_to(path, parent) if parent is not None else path
        yield f"{records[path].sha256}  {output_path.as_posix()}\n"


def _manifest_lines(
    paths: Iterable[PurePosixPath],
    records: dict[PurePosixPath, FileRecord],
) -> Iterator[str]:
    yield MANIFEST_HEADER
    for path in paths:
        record = records[path]
        yield (
            f"{path.as_posix()}\t{_component_for(path)}\t"
            f"{record.size}\t{record.sha256}\n"
        )


def _ensure_components(root: Path) -> None:
    missing = [
        component.as_posix()
        for component in COMPONENTS
        if not _component_path(root, component).is_dir()
    ]
    if missing:
        details = "\n  ".join(missing)
        raise FileNotFoundError(f"missing logical component directories:\n  {details}")


def _check_inventory_unchanged(
    root: Path,
    expected: Sequence[PurePosixPath],
    records: dict[PurePosixPath, FileRecord],
) -> None:
    current = [
        path
        for path in _walk_files(root)
        if not _is_checksum(path) and not _is_top_manifest(path)
    ]
    if current != list(expected):
        raise RuntimeError("bundle file set changed while checksums were being prepared")

    for path in current:
        observed = root.joinpath(*path.parts).stat(follow_symlinks=False)
        record = records[path]
        signature = (
            observed.st_dev,
            observed.st_ino,
            observed.st_size,
            observed.st_mtime_ns,
        )
        expected_signature = (
            record.device,
            record.inode,
            record.size,
            record.mtime_ns,
        )
        if signature != expected_signature:
            raise RuntimeError(f"file changed after it was hashed: {path.as_posix()}")


def finalize(root: Path, workers: int) -> None:
    _ensure_components(root)
    all_files = _walk_files(root)
    data_paths = [
        path
        for path in all_files
        if not _is_checksum(path) and not _is_top_manifest(path)
    ]
    print(f"Hashing {len(data_paths):,} deposit files with {workers} workers", flush=True)
    records = _hash_files(root, data_paths, workers)
    _check_inventory_unchanged(root, data_paths, records)

    for component in COMPONENTS:
        component_paths = [
            path
            for path in data_paths
            if path.parts[: len(component.parts)] == component.parts
        ]
        target = _component_path(root, component) / CHECKSUM_NAME
        _atomic_write(
            target,
            _checksum_lines(component_paths, records, parent=component),
        )
        print(f"Wrote {target} ({len(component_paths):,} entries)", flush=True)

    manifest_path = root / MANIFEST_NAME
    _atomic_write(manifest_path, _manifest_lines(data_paths, records))
    manifest_relative = PurePosixPath(MANIFEST_NAME)
    records[manifest_relative] = _hash_one(root, manifest_relative)

    top_checksum_paths = [*data_paths, manifest_relative]
    top_checksum_paths.sort(key=lambda path: path.as_posix())
    top_checksum_path = root / CHECKSUM_NAME
    _atomic_write(
        top_checksum_path,
        _checksum_lines(top_checksum_paths, records),
    )
    print(f"Wrote {manifest_path} ({len(data_paths):,} entries)", flush=True)
    print(f"Wrote {top_checksum_path} ({len(top_checksum_paths):,} entries)", flush=True)


def _parse_relative_path(text: str, source: Path, line_number: int) -> PurePosixPath:
    path = PurePosixPath(text)
    if (
        not text
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != text
    ):
        raise ValueError(f"{source}:{line_number}: invalid relative POSIX path {text!r}")
    _validate_serializable_path(path)
    return path


def _read_checksums(path: Path) -> dict[PurePosixPath, str]:
    entries: dict[PurePosixPath, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if line.endswith("\r"):
                line = line[:-1]
            digest, separator, path_text = line.partition("  ")
            if separator != "  " or not SHA256_RE.fullmatch(digest):
                raise ValueError(f"{path}:{line_number}: malformed checksum line")
            relative = _parse_relative_path(path_text, path, line_number)
            if relative in entries:
                raise ValueError(f"{path}:{line_number}: duplicate path {path_text!r}")
            entries[relative] = digest
    return entries


def _read_manifest(path: Path) -> dict[PurePosixPath, tuple[str, int, str]]:
    entries: dict[PurePosixPath, tuple[str, int, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        header = handle.readline()
        if header != MANIFEST_HEADER:
            raise ValueError(f"{path}: unexpected manifest header")
        for line_number, raw_line in enumerate(handle, start=2):
            fields = raw_line.rstrip("\r\n").split("\t")
            if len(fields) != 4:
                raise ValueError(f"{path}:{line_number}: expected four tab-separated fields")
            path_text, component, size_text, digest = fields
            relative = _parse_relative_path(path_text, path, line_number)
            if relative in entries:
                raise ValueError(f"{path}:{line_number}: duplicate path {path_text!r}")
            try:
                size = int(size_text)
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: invalid size {size_text!r}") from error
            if size < 0 or not SHA256_RE.fullmatch(digest):
                raise ValueError(f"{path}:{line_number}: invalid size or SHA-256 digest")
            expected_component = _component_for(relative)
            if component != expected_component:
                raise ValueError(
                    f"{path}:{line_number}: component is {component!r}; "
                    f"expected {expected_component!r}"
                )
            entries[relative] = (component, size, digest)
    return entries


def _assert_path_set(
    label: str,
    declared: set[PurePosixPath],
    expected: set[PurePosixPath],
) -> None:
    missing = sorted(expected - declared, key=lambda item: item.as_posix())
    extra = sorted(declared - expected, key=lambda item: item.as_posix())
    if not missing and not extra:
        return
    details: list[str] = [f"{label}: path set does not match the deposit"]
    if missing:
        preview = ", ".join(path.as_posix() for path in missing[:10])
        details.append(f"  missing ({len(missing):,}): {preview}")
    if extra:
        preview = ", ".join(path.as_posix() for path in extra[:10])
        details.append(f"  extra ({len(extra):,}): {preview}")
    raise ValueError("\n".join(details))


def verify(root: Path, workers: int) -> None:
    _ensure_components(root)
    all_files = _walk_files(root)
    data_paths = [
        path
        for path in all_files
        if not _is_checksum(path) and not _is_top_manifest(path)
    ]
    data_set = set(data_paths)

    manifest_path = root / MANIFEST_NAME
    top_checksum_path = root / CHECKSUM_NAME
    if not manifest_path.is_file() or not top_checksum_path.is_file():
        raise FileNotFoundError("bundle-wide MANIFEST.tsv or CHECKSUMS.sha256 is missing")

    declared_digests: dict[PurePosixPath, list[tuple[str, str]]] = {}

    manifest = _read_manifest(manifest_path)
    _assert_path_set("MANIFEST.tsv", set(manifest), data_set)
    for path, (_, size, digest) in manifest.items():
        actual_size = root.joinpath(*path.parts).stat(follow_symlinks=False).st_size
        if size != actual_size:
            raise ValueError(
                f"MANIFEST.tsv: size mismatch for {path.as_posix()}: "
                f"declared {size}, actual {actual_size}"
            )
        declared_digests.setdefault(path, []).append((MANIFEST_NAME, digest))

    top_checksums = _read_checksums(top_checksum_path)
    manifest_relative = PurePosixPath(MANIFEST_NAME)
    expected_top = data_set | {manifest_relative}
    _assert_path_set(CHECKSUM_NAME, set(top_checksums), expected_top)
    for path, digest in top_checksums.items():
        declared_digests.setdefault(path, []).append((CHECKSUM_NAME, digest))

    for component in COMPONENTS:
        component_root = _component_path(root, component)
        checksum_path = component_root / CHECKSUM_NAME
        if not checksum_path.is_file():
            raise FileNotFoundError(f"component checksum is missing: {checksum_path}")
        checksums = _read_checksums(checksum_path)
        expected_root_paths = {
            path
            for path in data_set
            if path.parts[: len(component.parts)] == component.parts
        }
        expected_local_paths = {
            _relative_to(path, component) for path in expected_root_paths
        }
        _assert_path_set(
            f"{component.as_posix()}/{CHECKSUM_NAME}",
            set(checksums),
            expected_local_paths,
        )
        for local_path, digest in checksums.items():
            root_path = PurePosixPath(*component.parts, *local_path.parts)
            declared_digests.setdefault(root_path, []).append(
                (f"{component.as_posix()}/{CHECKSUM_NAME}", digest)
            )

    paths_to_hash = sorted(declared_digests, key=lambda path: path.as_posix())
    print(
        f"Verifying {len(paths_to_hash):,} unique files with {workers} workers",
        flush=True,
    )
    actual_records = _hash_files(root, paths_to_hash, workers)
    errors: list[str] = []
    for path, declarations in declared_digests.items():
        actual = actual_records[path].sha256
        for source, declared in declarations:
            if actual != declared:
                errors.append(
                    f"{source}: digest mismatch for {path.as_posix()}: "
                    f"declared {declared}, actual {actual}"
                )
    if errors:
        preview = "\n".join(errors[:20])
        suffix = "" if len(errors) <= 20 else f"\n... and {len(errors) - 20:,} more"
        raise ValueError(f"checksum verification failed:\n{preview}{suffix}")
    print(
        f"Verified path sets and SHA-256 digests for {len(paths_to_hash):,} files",
        flush=True,
    )


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("zenodo/sim2real_deposit"),
        help="deposit root (default: zenodo/sim2real_deposit)",
    )
    parser.add_argument(
        "--workers",
        type=_positive_integer,
        default=min(8, os.cpu_count() or 1),
        help="parallel file hashing workers (default: min(8, CPU count))",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="verify existing inventories and digests instead of regenerating them",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"deposit root is not a directory: {root}")
    if args.verify:
        verify(root, args.workers)
    else:
        finalize(root, args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
