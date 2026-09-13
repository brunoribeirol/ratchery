#!/usr/bin/env python3
"""wordcount: a tiny personal script to count word frequency in a text file.

Prototype / internal / no sensitive data. This is the T0 example project for
Ratchetry -- see README.md in this directory for the tier
score walkthrough.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path


def word_counts(text: str) -> Counter[str]:
    return Counter(word.strip(".,!?;:\"'()[]").lower() for word in text.split() if word.strip(".,!?;:\"'()[]"))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: main.py <path-to-text-file>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    counts = word_counts(path.read_text())
    for word, count in counts.most_common(10):
        print(f"{count:5d}  {word}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
