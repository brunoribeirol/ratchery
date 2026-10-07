#!/usr/bin/env python3
"""Generate a read-only report for curated technology radar sources."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import technology_watch as tw  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online",
        action="store_true",
        help="Explicitly query api.github.com for curated GitHub repository metadata.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    try:
        report = tw.build_watch_report(
            ROOT,
            online=args.online,
            token=os.environ.get("GITHUB_TOKEN") if args.online else None,
            timeout=args.timeout,
        )
    except tw.TechnologyWatchError as exc:
        print(f"Technology watch failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(tw.render_markdown(report), end="")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
