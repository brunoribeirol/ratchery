#!/usr/bin/env python3
"""Fail when a committed GitHub Action uses a mutable external reference."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.MULTILINE)
REMOTE = re.compile(
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./-]+)?@([0-9a-f]{40})\Z"
)
DOCKER = re.compile(r"docker://[^\s@]+@sha256:[0-9a-f]{64}\Z")


def workflow_files(root: Path) -> list[Path]:
    paths = sorted((root / ".github" / "workflows").glob("*.yml"))
    paths.extend(sorted((root / ".github" / "workflows").glob("*.yaml")))
    action = root / "action.yml"
    if action.is_file():
        paths.append(action)
    return paths


def unpinned_references(root: Path) -> list[str]:
    failures = []
    for path in workflow_files(root):
        text = path.read_text(encoding="utf-8")
        for match in USES.finditer(text):
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            if not (REMOTE.fullmatch(reference) or DOCKER.fullmatch(reference)):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(root)}:{line}: {reference}")
    return failures


def main() -> int:
    failures = unpinned_references(ROOT)
    if failures:
        print("GitHub Action pin verification FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    count = sum(
        len(USES.findall(path.read_text(encoding="utf-8")))
        for path in workflow_files(ROOT)
    )
    print(f"GitHub Action pins verified: {count} uses entries -- PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
