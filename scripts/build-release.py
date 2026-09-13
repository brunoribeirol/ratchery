#!/usr/bin/env python3
"""Build deterministic release artifacts from the committed manifest.

The runtime remains stdlib-only: this release helper deliberately uses no
packaging or SBOM dependency. It consumes bytes only after validating them
against MANIFEST.json, then normalizes archive metadata so rebuilds of the
same commit and source epoch produce the same output.
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from git_environment import clean_git_environment

ROOT = Path(__file__).resolve().parents[1]
SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SAFE_REPOSITORY = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*\Z"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
SUPPORTED_GIT_MODES = {"100644": 0o644, "100755": 0o755}
EXCLUDE_DIRS = {".github"}
EXCLUDE_FILES = {"MANIFEST.json"}


class ReleaseBuildError(ValueError):
    """Raised when release inputs do not satisfy the publication contract."""


@dataclass(frozen=True)
class SourceFile:
    """Validated, immutable snapshot of one file included in the archive."""

    path: str
    data: bytes
    mode: int


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            env=clean_git_environment(),
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleaseBuildError(f"git {' '.join(args)} failed") from exc


def git_modes(root: Path) -> dict[str, str]:
    """Return stage-zero paths and modes without parsing human-formatted Git output."""
    modes: dict[str, str] = {}
    for record in run_git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, _object_id, stage = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise ReleaseBuildError("could not parse the Git index") from exc
        if stage == "0":
            modes[path] = mode
    return modes


def read_runtime_version(root: Path) -> str:
    version_path = root / "lib" / "agent_workspace.py"
    try:
        tree = ast.parse(version_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ReleaseBuildError("could not read the runtime VERSION") from exc
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if any(isinstance(target, ast.Name) and target.id == "VERSION" for target in targets):
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                return value.value
            break
    raise ReleaseBuildError("lib/agent_workspace.py has no literal VERSION")


def checked_path(root: Path, rel: str) -> Path:
    """Resolve a canonical manifest path while rejecting links and traversal."""
    pure = PurePosixPath(rel)
    if (
        not rel
        or pure.is_absolute()
        or rel != pure.as_posix()
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise ReleaseBuildError(f"unsafe manifest path: {rel!r}")
    path = root.joinpath(*pure.parts)
    current = root
    for part in pure.parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ReleaseBuildError(f"missing manifest file: {rel}") from exc
        if stat.S_ISLNK(mode):
            raise ReleaseBuildError(f"manifest path traverses a symlink: {rel}")
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ReleaseBuildError(f"manifest path is not a regular file: {rel}")
    return path


def load_sources(root: Path) -> tuple[dict[str, Any], list[SourceFile], bytes]:
    manifest_path = checked_path(root, "MANIFEST.json")
    try:
        manifest_data = manifest_path.read_bytes()
        manifest = json.loads(manifest_data)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseBuildError("MANIFEST.json is unreadable or malformed") from exc
    if not isinstance(manifest, dict):
        raise ReleaseBuildError("MANIFEST.json must contain an object")

    name = manifest.get("name")
    version = manifest.get("version")
    entries = manifest.get("files")
    if not isinstance(name, str) or not SAFE_COMPONENT.fullmatch(name):
        raise ReleaseBuildError("manifest name is not a safe package component")
    if not isinstance(version, str) or not SAFE_COMPONENT.fullmatch(version):
        raise ReleaseBuildError("manifest version is not a safe package component")
    if version != read_runtime_version(root):
        raise ReleaseBuildError("manifest version does not match runtime VERSION")
    if not isinstance(entries, list):
        raise ReleaseBuildError("manifest files must be a list")

    modes = git_modes(root)
    sources: list[SourceFile] = []
    seen: set[str] = set()
    total_bytes = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise ReleaseBuildError("each manifest file entry must be an object")
        rel = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not isinstance(rel, str):
            raise ReleaseBuildError("manifest file path must be a string")
        if rel == "MANIFEST.json":
            raise ReleaseBuildError("MANIFEST.json cannot list itself")
        if rel in seen:
            raise ReleaseBuildError(f"duplicate manifest path: {rel}")
        seen.add(rel)
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            raise ReleaseBuildError(f"invalid sha256 for {rel}")
        if (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
        ):
            raise ReleaseBuildError(f"invalid size for {rel}")
        path = checked_path(root, rel)
        data = path.read_bytes()
        if len(data) != expected_size or sha256(data) != expected_hash:
            raise ReleaseBuildError(f"manifest content mismatch: {rel}")
        git_mode = modes.get(rel)
        if git_mode not in SUPPORTED_GIT_MODES:
            raise ReleaseBuildError(f"unsupported or untracked manifest path: {rel}")
        sources.append(SourceFile(rel, data, SUPPORTED_GIT_MODES[git_mode]))
        total_bytes += len(data)

    count = manifest.get("file_count_excluding_manifest")
    total = manifest.get("total_bytes_excluding_manifest")
    if count != len(sources) or total != total_bytes:
        raise ReleaseBuildError("manifest aggregate counts do not match its entries")

    expected_inventory = {
        rel
        for rel in modes
        if PurePosixPath(rel).name not in EXCLUDE_FILES
        and not any(part in EXCLUDE_DIRS for part in PurePosixPath(rel).parts)
    }
    if seen != expected_inventory:
        missing = sorted(expected_inventory - seen)
        extra = sorted(seen - expected_inventory)
        details = []
        if missing:
            details.append("missing from manifest: " + ", ".join(missing[:5]))
        if extra:
            details.append("not tracked for release: " + ", ".join(extra[:5]))
        raise ReleaseBuildError("Git release inventory differs; " + "; ".join(details))

    manifest_mode = modes.get("MANIFEST.json")
    if manifest_mode not in SUPPORTED_GIT_MODES:
        raise ReleaseBuildError("MANIFEST.json is untracked or has an unsupported mode")
    sources.append(
        SourceFile("MANIFEST.json", manifest_data, SUPPORTED_GIT_MODES[manifest_mode])
    )
    return manifest, sorted(sources, key=lambda item: item.path), manifest_data


def source_epoch(root: Path, override: int | None) -> int:
    if override is not None:
        epoch = override
    elif "SOURCE_DATE_EPOCH" in os.environ:
        try:
            epoch = int(os.environ["SOURCE_DATE_EPOCH"])
        except ValueError as exc:
            raise ReleaseBuildError("SOURCE_DATE_EPOCH must be an integer") from exc
    else:
        try:
            epoch = int(run_git(root, "show", "-s", "--format=%ct", "HEAD"))
        except ValueError as exc:
            raise ReleaseBuildError("Git commit timestamp is invalid") from exc
    if not 0 <= epoch <= 4_294_967_295:
        raise ReleaseBuildError("source epoch is outside the gzip timestamp range")
    return epoch


def atomic_output(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise ReleaseBuildError(f"refusing to replace symlink output: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_output_directory(path: Path) -> Path:
    """Create an output directory without accepting it or its closest parent as a link."""
    absolute = Path(os.path.abspath(os.fspath(path.expanduser())))

    def validate_nearest_existing() -> None:
        current = absolute
        while True:
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                parent = current.parent
                if parent == current:
                    raise ReleaseBuildError("output directory has no existing parent")
                current = parent
                continue
            except OSError as exc:
                raise ReleaseBuildError(
                    f"could not inspect output directory component: {current}"
                ) from exc
            if stat.S_ISLNK(mode):
                raise ReleaseBuildError(
                    f"output directory must not traverse a symlink: {current}"
                )
            if not stat.S_ISDIR(mode):
                raise ReleaseBuildError(
                    f"output directory component is not a directory: {current}"
                )
            return

    # Checking before canonicalization is essential: Path.resolve() would turn
    # a direct symlink such as `dist -> elsewhere` into an ordinary directory.
    # The nearest-existing rule also catches `dist-link/new-child` while still
    # supporting macOS temporary paths whose system `/var` prefix is itself a
    # compatibility symlink to `/private/var`.
    validate_nearest_existing()
    try:
        absolute.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReleaseBuildError("could not create output directory") from exc
    validate_nearest_existing()
    return absolute


def build_archive(
    sources: list[SourceFile], package_prefix: str, epoch: int
) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
        with tarfile.open(
            fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT
        ) as archive:
            for source in sources:
                info = tarfile.TarInfo(f"{package_prefix}/{source.path}")
                info.size = len(source.data)
                info.mode = source.mode
                info.mtime = epoch
                info.uid = 0
                info.gid = 0
                info.uname = "root"
                info.gname = "root"
                archive.addfile(info, io.BytesIO(source.data))
    return raw.getvalue()


def spdx_file_id(path: str) -> str:
    return f"SPDXRef-File-{hashlib.sha256(path.encode()).hexdigest()}"


def package_verification_code(sources: list[SourceFile]) -> str:
    hashes = sorted(hashlib.sha1(source.data).hexdigest() for source in sources)
    return hashlib.sha1("".join(hashes).encode("ascii")).hexdigest()


def build_sbom(
    manifest: dict[str, Any],
    sources: list[SourceFile],
    archive_name: str,
    archive_digest: str,
    epoch: int,
    repository: str | None,
) -> bytes:
    name = manifest["name"]
    version = manifest["version"]
    if repository is not None and not SAFE_REPOSITORY.fullmatch(repository):
        raise ReleaseBuildError("repository must use the owner/name form")
    if repository:
        namespace_base = f"https://github.com/{repository}/attestations/spdx"
        download = (
            f"https://github.com/{repository}/releases/download/v{version}/{archive_name}"
        )
    else:
        namespace_base = f"https://spdx.invalid/{name}"
        download = "NOASSERTION"

    package_id = "SPDXRef-Package"
    prefix = f"{name}-{version}"
    files = []
    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": package_id,
        }
    ]
    for source in sources:
        file_id = spdx_file_id(source.path)
        files.append(
            {
                "fileName": f"./{prefix}/{source.path}",
                "SPDXID": file_id,
                "checksums": [
                    {"algorithm": "SHA1", "checksumValue": hashlib.sha1(source.data).hexdigest()},
                    {"algorithm": "SHA256", "checksumValue": sha256(source.data)},
                ],
                "licenseConcluded": "NOASSERTION",
                "licenseInfoInFiles": ["NOASSERTION"],
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": package_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": file_id,
            }
        )

    created = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{name}-{version}-source",
        "documentNamespace": (
            f"{namespace_base}/{version}/{archive_digest}"
        ),
        "creationInfo": {
            "created": created,
            "creators": [f"Tool: {name}-release-builder-{version}"],
        },
        "documentDescribes": [package_id],
        "packages": [
            {
                "name": name,
                "SPDXID": package_id,
                "versionInfo": version,
                "packageFileName": archive_name,
                "downloadLocation": download,
                "filesAnalyzed": True,
                "checksums": [
                    {"algorithm": "SHA256", "checksumValue": archive_digest}
                ],
                "packageVerificationCode": {
                    "packageVerificationCodeValue": package_verification_code(sources)
                },
                "licenseConcluded": "MIT",
                "licenseDeclared": "MIT",
                "copyrightText": "Copyright (c) 2026 Ratchetry contributors",
                "primaryPackagePurpose": "SOURCE",
            }
        ],
        "files": files,
        "relationships": relationships,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def build_release(
    root: Path,
    output_dir: Path,
    epoch_override: int | None,
    repository: str | None,
) -> list[Path]:
    root = root.resolve()
    manifest, sources, manifest_data = load_sources(root)
    epoch = source_epoch(root, epoch_override)
    prefix = f"{manifest['name']}-{manifest['version']}"
    archive_name = f"{prefix}.tar.gz"
    sbom_name = f"{prefix}.spdx.json"

    archive_data = build_archive(sources, prefix, epoch)
    archive_digest = sha256(archive_data)
    sbom_data = build_sbom(
        manifest,
        sources,
        archive_name,
        archive_digest,
        epoch,
        repository,
    )
    output_dir = prepare_output_directory(output_dir)
    if any(output_dir.iterdir()):
        raise ReleaseBuildError("output directory must be empty")
    archive_path = output_dir / archive_name
    sbom_path = output_dir / sbom_name
    manifest_copy = output_dir / "MANIFEST.json"
    atomic_output(archive_path, archive_data)
    atomic_output(sbom_path, sbom_data)
    atomic_output(manifest_copy, manifest_data)

    checksum_targets = sorted(
        [archive_path, sbom_path, manifest_copy], key=lambda path: path.name
    )
    checksum_data = "".join(
        f"{sha256(path.read_bytes())}  {path.name}\n" for path in checksum_targets
    ).encode()
    checksum_path = output_dir / "SHA256SUMS.txt"
    atomic_output(checksum_path, checksum_data)
    return [archive_path, sbom_path, manifest_copy, checksum_path]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--source-date-epoch", type=int)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="GitHub owner/name used for SPDX download and namespace URLs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        outputs = build_release(
            args.root, args.output_dir, args.source_date_epoch, args.repository
        )
    except ReleaseBuildError as exc:
        print(f"release build failed: {exc}", file=sys.stderr)
        return 1
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
