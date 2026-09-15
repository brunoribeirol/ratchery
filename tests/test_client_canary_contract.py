#!/usr/bin/env python3
"""Static safety/coverage contract for the scheduled real-client canary."""
from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/client-canary.yml"
CODEX_TEMPLATE = ROOT / "assets/project/.codex/config.base.toml"


class TestClientCanaryContract(unittest.TestCase):
    def setUp(self) -> None:
        if not WORKFLOW.exists():
            self.skipTest("CI-only workflow is intentionally absent from release archives")
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_scheduled_manual_and_read_only(self):
        self.assertRegex(self.text, r"(?m)^  schedule:$")
        self.assertRegex(self.text, r"(?m)^  workflow_dispatch:$")
        self.assertRegex(self.text, r"(?m)^permissions: \{\}$")
        self.assertRegex(
            self.text,
            r"(?ms)^  prepare:.*?^    permissions:\n      contents: read$",
        )
        self.assertRegex(
            self.text,
            r"(?ms)^  generated-config:.*?^    permissions: \{\}$",
        )
        self.assertIn("persist-credentials: false", self.text)

    def test_client_installers_never_receive_the_repository_checkout(self):
        client_job = self.text.split("\n  generated-config:", 1)[1]
        self.assertNotIn("actions/checkout@", client_job)
        self.assertIn("needs: prepare", client_job)
        self.assertIn("ratchery-generated-client-config", client_job)
        self.assertLess(
            client_job.index("Install Claude Code with its required native-binary step"),
            client_job.index("Download the source-free generated fixture"),
        )
        self.assertLess(
            client_job.index("Install Codex without package lifecycle scripts"),
            client_job.index("Download the source-free generated fixture"),
        )

    def test_only_claude_allows_its_required_installation_script(self):
        self.assertIn(
            'run: npm install --global "${CLIENT_PACKAGE}@${CLIENT_VERSION}"',
            self.text,
        )
        self.assertIn(
            'run: npm install --global --ignore-scripts "${CLIENT_PACKAGE}@${CLIENT_VERSION}"',
            self.text,
        )
        self.assertEqual(self.text.count("npm install --global"), 2)

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
        self.assertIn("codex --strict-config sandbox --help", self.text)
        self.assertIn("server.enabled_tools", self.text)
        self.assertIn("grep -Eq -- '--permissions?-profile'", self.text)
        self.assertNotIn('codex sandbox -C "$project"', self.text)

    def test_codex_agent_controls_keep_the_minimum_compatible_shape(self):
        config = tomllib.loads(CODEX_TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(config["max_threads"], 4)
        self.assertIs(config["interrupt_message"], False)
        agents = config["agents"]
        self.assertEqual(
            set(agents),
            {"explorer", "reviewer", "security_reviewer", "test_runner"},
        )
        self.assertTrue(all(isinstance(role, dict) for role in agents.values()))

    def test_every_remote_action_is_sha_pinned(self):
        uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", self.text)
        self.assertTrue(uses)
        for reference in uses:
            self.assertRegex(reference, r"@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
