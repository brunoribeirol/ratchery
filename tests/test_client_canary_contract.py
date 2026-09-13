#!/usr/bin/env python3
"""Static safety/coverage contract for the scheduled real-client canary."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/client-canary.yml"


class TestClientCanaryContract(unittest.TestCase):
    def setUp(self) -> None:
        if not WORKFLOW.exists():
            self.skipTest("CI-only workflow is intentionally absent from release archives")
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_scheduled_manual_and_read_only(self):
        self.assertRegex(self.text, r"(?m)^  schedule:$")
        self.assertRegex(self.text, r"(?m)^  workflow_dispatch:$")
        self.assertRegex(self.text, r"(?m)^permissions:\n  contents: read$")
        self.assertIn("persist-credentials: false", self.text)

    def test_covers_minimum_and_current_clients(self):
        for package, minimum in (
            ("@anthropic-ai/claude-code", "2.1.187"),
            ("@openai/codex", "0.138.0"),
        ):
            self.assertIn(package, self.text)
            self.assertIn(f'version: "{minimum}"', self.text)
        self.assertEqual(self.text.count('version: "latest"'), 2)

    def test_has_no_inference_or_secret_injection_step(self):
        forbidden = (
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "codex exec",
            "claude --print",
            "claude -p",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, self.text)
        self.assertIn("claude mcp get context7", self.text)
        self.assertIn('CODEX_HOME="$mcp_home" codex mcp get context7 --json', self.text)
        self.assertNotIn("codex --strict-config", self.text)
        self.assertIn('server.get("enabled_tools")', self.text)
        self.assertIn('codex sandbox -C "$project" -P project-edit /usr/bin/true', self.text)

    def test_every_remote_action_is_sha_pinned(self):
        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", self.text)
        self.assertTrue(uses)
        for reference in uses:
            self.assertRegex(reference, r"@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
