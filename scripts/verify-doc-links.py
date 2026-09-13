#!/usr/bin/env python3
"""Verify local Markdown links and heading fragments without external tools."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def link_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split(maxsplit=1)[0]


def github_slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text).strip().lower()
    text = "".join(char for char in text if char.isalnum() or char in " -_")
    return re.sub(r"\s+", "-", text)


def heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for heading in HEADING.findall(path.read_text(encoding="utf-8")):
        base = github_slug(heading)
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def markdown_files(root: Path) -> list[Path]:
    if (root / ".git").exists():
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                "*.md",
            ],
            check=True,
            capture_output=True,
        )
        return sorted(
            root / raw.decode("utf-8")
            for raw in result.stdout.split(b"\0")
            if raw
        )
    excluded = {".git", ".venv", "node_modules", "dist", "__pycache__"}
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in excluded for part in path.relative_to(root).parts)
    )


def broken_links(root: Path) -> list[str]:
    root = root.resolve()
    failures: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for source in markdown_files(root):
        text = source.read_text(encoding="utf-8")
        matches = [*INLINE_LINK.finditer(text), *REFERENCE_LINK.finditer(text)]
        for match in matches:
            target = link_target(match.group(1))
            if not target or target.startswith(EXTERNAL_SCHEMES):
                continue
            decoded = urllib.parse.unquote(target)
            path_text, separator, fragment = decoded.partition("#")
            if not path_text:
                destination = source
            elif path_text.startswith("/"):
                destination = root / path_text.lstrip("/")
            else:
                destination = source.parent / path_text
            destination = destination.resolve()
            line = text.count("\n", 0, match.start()) + 1
            try:
                destination.relative_to(root)
            except ValueError:
                failures.append(
                    f"{source.relative_to(root)}:{line}: link escapes repository: {target}"
                )
                continue
            if not destination.exists():
                failures.append(
                    f"{source.relative_to(root)}:{line}: missing target: {target}"
                )
                continue
            if separator and fragment and destination.suffix.lower() == ".md":
                anchors = anchor_cache.setdefault(destination, heading_anchors(destination))
                if fragment.lower() not in anchors:
                    failures.append(
                        f"{source.relative_to(root)}:{line}: missing heading fragment: {target}"
                    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    failures = broken_links(args.root)
    if failures:
        print("Markdown link verification FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    count = len(markdown_files(args.root.resolve()))
    print(f"Markdown links verified across {count} files -- PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
