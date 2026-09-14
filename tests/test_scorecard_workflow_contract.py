#!/usr/bin/env python3
"""Regression tests for public-only Scorecard execution and permissions."""
from __future__ import annotations

import re
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
        cls.public = job_block(cls.text, "public-analysis")

    def test_private_analysis_job_is_absent(self) -> None:
        jobs_text = self.text.split("\njobs:\n", 1)[1]
        jobs = re.findall(r"^  ([a-z0-9-]+):$", jobs_text, flags=re.MULTILINE)
        self.assertEqual(jobs, ["public-analysis"])
        self.assertNotIn("private-analysis:", self.text)
        self.assertNotIn("github.event.repository.private == true", self.text)
        self.assertNotIn("publish_results: false", self.text)

    def test_public_analysis_is_visibility_gated_with_required_permissions(self) -> None:
        self.assertIn("if: github.event.repository.private == false", self.public)
        self.assertIn("contents: read", self.public)
        self.assertIn("id-token: write", self.public)
        self.assertIn("security-events: write", self.public)
        self.assertIn("publish_results: true", self.public)
        self.assertIn("github/codeql-action/upload-sarif@", self.public)

    def test_private_only_read_scopes_are_not_added(self) -> None:
        self.assertNotIn("issues: read", self.text)
        self.assertNotIn("pull-requests: read", self.text)
        self.assertNotIn("checks: read", self.text)

    def test_scorecard_path_has_one_nonpersistent_checkout(self) -> None:
        self.assertIn("permissions: {}", self.text)
        self.assertEqual(self.text.count("ossf/scorecard-action@"), 1)
        self.assertEqual(self.text.count("persist-credentials: false"), 1)
        self.assertNotIn("actions/upload-artifact@", self.text)


if __name__ == "__main__":
    unittest.main()
