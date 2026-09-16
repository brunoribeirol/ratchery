#!/usr/bin/env python3
"""Contract tests for stable CI checks and downstream Action references."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
CODEQL = ROOT / ".github/workflows/codeql.yml"
CI_GATE = ROOT / "docs/CI_GATE.md"


class TestCiWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text()
        cls.shellcheck = cls.text.split(
            "      - name: Shellcheck (install.sh, command shims, integration suite)\n",
            1,
        )[1].split("\n      - name:", 1)[0]

    def test_shellcheck_is_a_blocking_linux_matrix_gate(self) -> None:
        self.assertIn("if: runner.os == 'Linux'", self.shellcheck)
        self.assertIn(
            "run: shellcheck install.sh bin/ratchery bin/agent-workspace tests/run-tests.sh",
            self.shellcheck,
        )
        self.assertNotIn("continue-on-error", self.shellcheck)
        self.assertNotIn("informational", self.shellcheck.lower())

    def test_existing_six_required_contexts_are_preserved(self) -> None:
        self.assertIn("os: [ubuntu-latest, macos-latest]", self.text)
        self.assertIn('python-version: ["3.11", "3.12", "3.13"]', self.text)
        self.assertEqual(self.text.count("jobs:\n"), 1)
        self.assertIn("  test:\n", self.text)

    def test_downstream_action_uses_exact_immutable_stable_tag(self) -> None:
        docs = CI_GATE.read_text()
        self.assertIn("uses: brunoribeirol/ratchery@v1.0.0", docs)
        self.assertNotIn("uses: brunoribeirol/ratchery@v1\n", docs)
        self.assertNotIn("brunoribeirol/ratchery@v1.0.0-rc", docs)

    def test_codeql_is_python_only_and_least_privilege(self) -> None:
        text = CODEQL.read_text()
        self.assertIn("permissions: {}", text)
        self.assertIn("contents: read", text)
        self.assertIn("security-events: write", text)
        self.assertNotIn("id-token: write", text)
        self.assertNotIn("contents: write", text)
        self.assertEqual(text.count("github/codeql-action/init@"), 1)
        self.assertEqual(text.count("github/codeql-action/analyze@"), 1)
        self.assertIn("languages: python", text)
        self.assertIn("persist-credentials: false", text)


if __name__ == "__main__":
    unittest.main()
