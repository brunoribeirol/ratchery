#!/usr/bin/env python3
"""Regenerate MANIFEST.json from the files actually shipped in the package.

Review and stage intended release changes before running this command. Run it
any time files are added/removed/modified, and always as the last step before
packaging a release archive. It is the single source of truth for the integrity
check exercised by tests/run-tests.sh.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from git_environment import clean_git_environment

ROOT = Path(__file__).resolve().parents[1]

# Files that are tracked in git but still never part of the shipped
# package (the manifest itself, and CI-only workflow config).
EXCLUDE_DIRS = {".github"}
EXCLUDE_FILES = {"MANIFEST.json"}


class ManifestGenerationError(ValueError):
    """Raised when the release inventory is ambiguous or unsafe."""


def is_release_path(rel: Path) -> bool:
    return rel.name not in EXCLUDE_FILES and not any(
        part in EXCLUDE_DIRS for part in rel.parts
    )


def git_paths(*arguments: str) -> list[Path]:
    try:
        raw_paths = subprocess.run(
            ["git", "-C", str(ROOT), *arguments, "-z"],
            check=True,
            capture_output=True,
            env=clean_git_environment(),
        ).stdout.split(b"\0")
        return [Path(raw.decode("utf-8")) for raw in raw_paths if raw]
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise ManifestGenerationError("could not read the Git release inventory") from exc


def path_preview(paths: list[Path]) -> str:
    preview = ", ".join(repr(rel.as_posix()) for rel in paths[:5])
    if len(paths) > 5:
        preview += f", ... ({len(paths)} total)"
    return preview


def iter_files() -> list[Path]:
    # Build only from the explicit Git index. A raw filesystem walk would
    # silently package ignored/local state, while silently ignoring untracked
    # release files lets a manifest pass locally and fail after those files are
    # committed. Require an explicit staging decision for every new file.
    unstaged = sorted(
        rel for rel in git_paths("diff", "--name-only") if is_release_path(rel)
    )
    if unstaged:
        raise ManifestGenerationError(
            "unstaged release changes must be reviewed and staged first: "
            + path_preview(unstaged)
        )

    untracked = sorted(
        rel
        for rel in git_paths("ls-files", "--others", "--exclude-standard")
        if is_release_path(rel)
    )
    if untracked:
        raise ManifestGenerationError(
            "untracked release candidates must be reviewed and staged first: "
            + path_preview(untracked)
        )

    out = []
    for rel in git_paths("ls-files"):
        if not is_release_path(rel):
            continue
        if (ROOT / rel).is_file():
            out.append(rel)
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    tree = ast.parse((ROOT / "lib" / "agent_workspace.py").read_text())
    version = next(
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )
    try:
        release_files = iter_files()
    except ManifestGenerationError as exc:
        print(f"MANIFEST.json generation FAILED: {exc}", file=sys.stderr)
        return 1
    files = []
    total_bytes = 0
    for rel in release_files:
        data = (ROOT / rel).read_bytes()
        total_bytes += len(data)
        files.append(
            {
                "path": str(rel),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )
    manifest = {
        "name": "ratchery",
        "version": version,
        "channel": "prerelease" if "-" in version else "stable",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "upgrade_from": ["8.1.0", "8.2.0", "8.2.1", "1.0.1"],
        "security_baseline": {
            "qmd_blocked_through": "2.6.3",
            "qmd_minimum_accepted": "2.6.4",
            "qmd_auto_install": False,
            "default_session_end_hook": False,
        },
        "file_count_excluding_manifest": len(files),
        "total_bytes_excluding_manifest": total_bytes,
        "files": files,
    }
    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"MANIFEST.json regenerated: {len(files)} files, {total_bytes} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
