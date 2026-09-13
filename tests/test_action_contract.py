#!/usr/bin/env python3
"""Regression tests for the reusable Action's shell/input trust boundary."""
from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "action.yml"


def action_script() -> str:
    marker = "      run: |\n"
    content = ACTION.read_text()
    if marker not in content:
        raise AssertionError("action.yml has no composite run block")
    script = textwrap.dedent(content.split(marker, 1)[1])
    return script.replace("${{ github.action_path }}", str(ROOT))


class TestActionContract(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.output = self.base / "github-output"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_action(self, path: str, deep: str = "false") -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "GITHUB_WORKSPACE": str(self.workspace),
                "GITHUB_OUTPUT": str(self.output),
                "INPUT_PATH": path,
                "INPUT_DEEP": deep,
            }
        )
        return subprocess.run(
            ["bash", "-c", action_script()],
            cwd=self.workspace,
            env=environment,
            text=True,
            capture_output=True,
        )

    def test_rejects_absolute_parent_and_symlink_escape(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        (self.workspace / "escape").symlink_to(outside, target_is_directory=True)

        absolute = self.run_action(str(outside))
        self.assertNotEqual(absolute.returncode, 0)
        self.assertIn("relative to GITHUB_WORKSPACE", absolute.stdout)

        for candidate in ("../outside", "escape"):
            with self.subTest(candidate=candidate):
                result = self.run_action(candidate)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("remain inside GITHUB_WORKSPACE", result.stdout)

    def test_path_input_is_data_not_shell(self) -> None:
        sentinel = self.base / "PWNED"
        result = self.run_action(f".; touch {sentinel}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not resolve to an existing directory", result.stdout)
        self.assertFalse(sentinel.exists())

    def test_invalid_deep_value_cannot_silently_disable_probe(self) -> None:
        result = self.run_action(".", "tru")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deep must be exactly", result.stdout)
        self.assertFalse(self.output.exists())

    def test_valid_workspace_path_reaches_doctor_and_writes_json_output(self) -> None:
        result = self.run_action(".")
        self.assertNotEqual(result.returncode, 0, "an empty project should fail doctor")
        self.assertNotIn("path must", result.stdout)
        self.assertIn("result<<DOCTOR_JSON_EOF_", self.output.read_text())


if __name__ == "__main__":
    unittest.main()
