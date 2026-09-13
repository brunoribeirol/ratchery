#!/usr/bin/env python3
"""Regenerate MANIFEST.json from the files actually shipped in the package.

Run this any time files are added/removed/modified, and always as the last
step before packaging a release archive. It is the single source of truth for
the integrity check exercised by tests/run-tests.sh.
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


def iter_files() -> list[Path]:
    # Enumerate via `git ls-files` rather than a raw filesystem walk: a
    # walk has no notion of .gitignore, so it previously picked up local,
    # untracked, and even gitignored scratch state (e.g.
    # .agents/state/task-policy.json) that has no business in a release
    # manifest. Tracked-in-git is the correct definition of "shipped" for
    # a project that installs by cloning/downloading this repo.
    out_bytes = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
        env=clean_git_environment(),
    ).stdout
    out = []
    for raw in out_bytes.split(b"\0"):
        if not raw:
            continue
        rel = Path(raw.decode())
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if rel.name in EXCLUDE_FILES:
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
    files = []
    total_bytes = 0
    for rel in iter_files():
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
