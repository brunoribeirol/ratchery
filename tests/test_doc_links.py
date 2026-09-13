#!/usr/bin/env python3
"""Tests for the repository-local Markdown link verifier."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "verify-doc-links.py"


class TestDocLinks(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_checker(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(self.project)],
            text=True,
            capture_output=True,
        )

    def test_accepts_file_fragment_and_reference_links(self) -> None:
        (self.project / "guide.md").write_text("# Setup guide\n")
        (self.project / "README.md").write_text(
            "[inline](guide.md#setup-guide) and [reference][guide]\n\n"
            "[guide]: guide.md\n"
        )
        self.assertEqual(self.run_checker().returncode, 0)

    def test_reports_missing_file_and_fragment(self) -> None:
        (self.project / "guide.md").write_text("# Existing\n")
        (self.project / "README.md").write_text(
            "[file](missing.md) and [heading](guide.md#missing)\n"
        )
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing target", result.stderr)
        self.assertIn("missing heading fragment", result.stderr)

    def test_rejects_repository_escape(self) -> None:
        outside = self.project.parent / "outside.md"
        outside.write_text("# Outside\n")
        self.addCleanup(outside.unlink)
        (self.project / "README.md").write_text("[outside](../outside.md)\n")
        result = self.run_checker()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
