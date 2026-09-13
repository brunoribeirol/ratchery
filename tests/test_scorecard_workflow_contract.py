#!/usr/bin/env python3
"""Regression tests for Scorecard visibility and token-permission boundaries."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scorecard.yml"


def job_block(text: str, name: str, next_name: str | None = None) -> str:
    start = f"  {name}:\n"
    if start not in text:
        raise AssertionError(f"missing workflow job: {name}")
    block = text.split(start, 1)[1]
    if next_name is not None:
        end = f"  {next_name}:\n"
        if end not in block:
            raise AssertionError(f"missing following workflow job: {next_name}")
        block = block.split(end, 1)[0]
    return block


class TestScorecardWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text()
        cls.private = job_block(cls.text, "private-analysis", "public-analysis")
        cls.public = job_block(cls.text, "public-analysis")

    def test_private_analysis_is_visibility_gated_and_read_only(self) -> None:
        self.assertIn("if: github.event.repository.private == true", self.private)
        self.assertIn("contents: read", self.private)
        self.assertIn("publish_results: false", self.private)
        self.assertNotIn("id-token: write", self.private)
        self.assertNotIn("security-events: write", self.private)
        self.assertNotIn("upload-sarif@", self.private)

    def test_private_results_are_short_lived_private_artifact(self) -> None:
        self.assertIn("actions/upload-artifact@", self.private)
        self.assertIn("retention-days: 1", self.private)
        self.assertIn("if-no-files-found: error", self.private)

    def test_public_analysis_alone_has_publication_permissions(self) -> None:
        self.assertIn("if: github.event.repository.private == false", self.public)
        self.assertIn("contents: read", self.public)
        self.assertIn("id-token: write", self.public)
        self.assertIn("security-events: write", self.public)
        self.assertIn("publish_results: true", self.public)
        self.assertIn("github/codeql-action/upload-sarif@", self.public)

    def test_checkout_never_persists_credentials(self) -> None:
        self.assertEqual(self.text.count("persist-credentials: false"), 2)


if __name__ == "__main__":
    unittest.main()
