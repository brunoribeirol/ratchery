#!/usr/bin/env python3
"""Verify MANIFEST.json against the files actually on disk.

Checks schema, safe relative paths, regular-file/symlink boundaries, runtime
version, deterministic ordering, size, SHA-256, and aggregate totals. It can
also stage exactly the verified inventory for install.sh, excluding every
untracked/ignored file from the installed runtime.

This is the same integrity check exercised inline by tests/run-tests.sh
(kept there too, calling into this script) -- extracted here so it can also
run as a standalone CI step and be invoked locally via `make verify`.

Usage:
    python3 scripts/verify-manifest.py [root_dir] [--stage DIR] [--print-version]

`root_dir` defaults to the repository root (parent of this script's
directory).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

from git_environment import clean_git_environment

SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
EXCLUDE_DIRS = {".github"}
EXCLUDE_FILES = {"MANIFEST.json"}


class ManifestError(ValueError):
    """Raised when the package manifest cannot be trusted."""


def checked_file(root: Path, rel: str) -> Path:
    pure = PurePosixPath(rel)
    if (
        not rel
        or pure.is_absolute()
        or rel != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise ManifestError(f"unsafe manifest path: {rel!r}")
    current = root
    for part in pure.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ManifestError(f"missing file: {rel}") from exc
        if stat.S_ISLNK(mode):
            raise ManifestError(f"manifest path traverses a symlink: {rel}")
    if not stat.S_ISREG(current.lstat().st_mode):
        raise ManifestError(f"manifest path is not a regular file: {rel}")
    return current


def runtime_version(root: Path) -> str:
    try:
        tree = ast.parse(checked_file(root, "lib/agent_workspace.py").read_text())
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ManifestError("could not read the runtime VERSION") from exc
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if (
            any(isinstance(target, ast.Name) and target.id == "VERSION" for target in targets)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise ManifestError("lib/agent_workspace.py has no literal VERSION")


def tracked_release_inventory(root: Path) -> set[str] | None:
    """Return expected package paths when root is itself a Git checkout."""
    try:
        top_level = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            env=clean_git_environment(),
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if Path(top_level).resolve() != root.resolve():
        return None
    try:
        raw_paths = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            env=clean_git_environment(),
        ).stdout.split(b"\0")
        paths = {raw.decode("utf-8") for raw in raw_paths if raw}
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise ManifestError("could not read the Git release inventory") from exc
    if "MANIFEST.json" not in paths:
        raise ManifestError("MANIFEST.json is not tracked in this Git checkout")
    return {
        rel
        for rel in paths
        if PurePosixPath(rel).name not in EXCLUDE_FILES
        and not any(part in EXCLUDE_DIRS for part in PurePosixPath(rel).parts)
    }


def verify_manifest(
    root: Path,
) -> tuple[dict[str, object], list[tuple[str, bytes, int]], bytes]:
    """Return the validated manifest and immutable file snapshots."""
    root = root.resolve()
    manifest_path = checked_file(root, "MANIFEST.json")
    try:
        manifest_data = manifest_path.read_bytes()
        manifest = json.loads(manifest_data)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError("MANIFEST.json is unreadable or malformed") from exc
    if not isinstance(manifest, dict):
        raise ManifestError("MANIFEST.json must contain a JSON object")
    name = manifest.get("name")
    version = manifest.get("version")
    entries = manifest.get("files")
    if not isinstance(name, str) or not SAFE_COMPONENT.fullmatch(name):
        raise ManifestError("manifest name is not a safe package component")
    if not isinstance(version, str) or not SAFE_COMPONENT.fullmatch(version):
        raise ManifestError("manifest version is not a safe package component")
    if version != runtime_version(root):
        raise ManifestError("manifest version does not match runtime VERSION")
    if not isinstance(entries, list):
        raise ManifestError("manifest files must be a list")

    snapshots: list[tuple[str, bytes, int]] = []
    seen: set[str] = set()
    total_bytes = 0
    for item in entries:
        if not isinstance(item, dict):
            raise ManifestError("each manifest file entry must be an object")
        rel = item.get("path")
        expected_hash = item.get("sha256")
        expected_size = item.get("size_bytes")
        if not isinstance(rel, str):
            raise ManifestError("manifest file path must be a string")
        if rel == "MANIFEST.json":
            raise ManifestError("MANIFEST.json cannot list itself")
        if rel in seen:
            raise ManifestError(f"duplicate manifest path: {rel}")
        seen.add(rel)
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            raise ManifestError(f"invalid sha256 for {rel}")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
            raise ManifestError(f"invalid size for {rel}")
        source = checked_file(root, rel)
        data = source.read_bytes()
        if len(data) != expected_size:
            raise ManifestError(f"size mismatch: {rel}")
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ManifestError(f"sha256 mismatch: {rel}")
        mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
        snapshots.append((rel, data, mode))
        total_bytes += len(data)

    paths = [rel for rel, _data, _mode in snapshots]
    if paths != sorted(paths):
        raise ManifestError("manifest file entries must be sorted by path")
    if manifest.get("file_count_excluding_manifest") != len(snapshots):
        raise ManifestError("file_count_excluding_manifest does not match file entries")
    if manifest.get("total_bytes_excluding_manifest") != total_bytes:
        raise ManifestError("total_bytes_excluding_manifest does not match file sizes")
    tracked = tracked_release_inventory(root)
    if tracked is not None and set(paths) != tracked:
        missing = sorted(tracked - set(paths))
        extra = sorted(set(paths) - tracked)
        details = []
        if missing:
            details.append("missing from manifest: " + ", ".join(missing[:5]))
        if extra:
            details.append("not tracked for release: " + ", ".join(extra[:5]))
        raise ManifestError("Git release inventory differs; " + "; ".join(details))
    return manifest, snapshots, manifest_data


def stage_verified_package(
    root: Path,
    destination: Path,
    snapshots: list[tuple[str, bytes, int]],
    manifest_data: bytes,
) -> None:
    root = root.resolve()
    destination = destination.resolve()
    if destination == root or root in destination.parents:
        raise ManifestError("staging destination must be outside the source tree")
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ManifestError("staging destination must be empty")
    for rel, data, mode in [*snapshots, ("MANIFEST.json", manifest_data, 0o644)]:
        target = destination.joinpath(*PurePosixPath(rel).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage", type=Path, help="copy only verified files into an empty directory")
    parser.add_argument("--print-version", action="store_true")
    args = parser.parse_args()
    try:
        manifest, snapshots, manifest_data = verify_manifest(args.root)
        if args.stage:
            stage_verified_package(args.root, args.stage, snapshots, manifest_data)
    except (ManifestError, OSError) as exc:
        print(f"MANIFEST.json verification FAILED: {exc}", file=sys.stderr)
        return 1
    if args.print_version:
        print(manifest["version"])
        return 0
    print(
        f"MANIFEST.json verified: {manifest['file_count_excluding_manifest']} files, "
        f"{manifest['total_bytes_excluding_manifest']} bytes -- PASS"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
