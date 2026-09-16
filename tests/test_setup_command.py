#!/usr/bin/env python3
"""Black-box contract for package-manager post-install setup."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "lib" / "agent_workspace.py"


class TestSetupCommand(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.vault = self.tmp / "vault"
        self.projects = self.tmp / "projects"
        self.client_bin = self.tmp / "clients"
        self.home.mkdir()
        self.vault.mkdir()
        self.client_bin.mkdir()
        (self.vault / "existing.md").write_text("# Keep me\n")
        for command, version in (("claude", "2.1.187"), ("codex", "0.138.0")):
            client = self.client_bin / command
            client.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n")
            client.chmod(0o755)
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.home)
        self.env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        self.env["XDG_STATE_HOME"] = str(self.home / ".local/state")
        self.env["PATH"] = str(self.client_bin) + os.pathsep + "/usr/bin:/bin"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_cli(
        self, *args: str, input_data: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.tmp,
            env=self.env,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=45,
        )

    def setup_args(self, *extra: str) -> tuple[str, ...]:
        return (
            "setup",
            "--vault",
            str(self.vault),
            "--projects-root",
            str(self.projects),
            "--project-layout",
            "categorized",
            "--external-tools",
            "none",
            *extra,
        )

    def snapshot(self) -> list[tuple[str, bytes]]:
        return [
            (str(path.relative_to(self.tmp)), path.read_bytes())
            for path in sorted(self.tmp.rglob("*"))
            if path.is_file()
        ]

    def test_dry_run_is_read_only(self) -> None:
        before = self.snapshot()
        result = self.run_cli(*self.setup_args("--dry-run"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dry run only. No files were changed.", result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())

    def test_apply_is_idempotent_and_doctor_clean(self) -> None:
        first = self.run_cli(*self.setup_args("--yes"))
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self.run_cli(*self.setup_args("--yes"))
        self.assertEqual(second.returncode, 0, second.stderr)

        config = json.loads(
            (self.home / ".config/ratchery/config.json").read_text()
        )
        self.assertEqual(config["vault_path"], str(self.vault.resolve()))
        self.assertEqual(config["projects_root"], str(self.projects.resolve()))
        self.assertEqual(config["project_layout"], "categorized")
        self.assertEqual((self.vault / "existing.md").read_text(), "# Keep me\n")
        self.assertEqual(
            (self.vault / "AGENTS.md").read_text().count(
                "<!-- agent-workspace:v8:start -->"
            ),
            1,
        )
        self.assertEqual(
            (self.vault / "VAULT-INDEX.md").read_text().count(
                "<!-- agent-workspace:v8:index:start -->"
            ),
            1,
        )
        self.assertTrue((self.projects / "personal/README.md").is_file())
        self.assertTrue((self.home / ".claude/CLAUDE.md").is_file())
        self.assertTrue((self.home / ".codex/AGENTS.md").is_file())

        doctor = self.run_cli("doctor-global", "--deep")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn("Global doctor: 0 error(s)", doctor.stdout)

    def test_missing_vault_is_rejected_before_writes(self) -> None:
        missing = self.tmp / "missing"
        result = self.run_cli(
            "setup", "--vault", str(missing), "--projects-root", str(self.projects), "--yes"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Vault path is unavailable", result.stderr)
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())
        self.assertFalse(self.projects.exists())

    def test_user_owned_global_skill_collision_fails_before_writes(self) -> None:
        collision = self.home / ".agents/skills/workspace-save"
        collision.mkdir(parents=True)
        sentinel = collision / "owned.txt"
        sentinel.write_text("keep\n")

        result = self.run_cli(*self.setup_args("--yes"))

        self.assertEqual(result.returncode, 1)
        self.assertIn("Refusing to overwrite user-owned global Skill", result.stderr)
        self.assertEqual(sentinel.read_text(), "keep\n")
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())
        self.assertFalse(self.projects.exists())

    def test_symlinked_vault_managed_file_is_never_read_or_replaced(self) -> None:
        outside = self.tmp / "outside.txt"
        outside.write_text("private sentinel\n")
        (self.vault / "AGENTS.md").symlink_to(outside)

        result = self.run_cli(*self.setup_args("--yes"))

        self.assertEqual(result.returncode, 2)
        self.assertIn("Vault managed file must not be a symlink", result.stderr)
        self.assertNotIn("private sentinel", result.stdout + result.stderr)
        self.assertTrue((self.vault / "AGENTS.md").is_symlink())
        self.assertEqual(outside.read_text(), "private sentinel\n")
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())

    def test_broken_vault_template_symlink_is_rejected_before_writes(self) -> None:
        (self.vault / "templates").mkdir()
        (self.vault / "templates/project-home.md").symlink_to(
            self.tmp / "missing-outside.md"
        )

        result = self.run_cli(*self.setup_args("--yes"))

        self.assertEqual(result.returncode, 2)
        self.assertIn("Vault managed file must not be a symlink", result.stderr)
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())

    def test_symlinked_vault_managed_directory_is_rejected_before_writes(self) -> None:
        outside = self.tmp / "outside-vault-projects"
        outside.mkdir()
        (self.vault / "projects").symlink_to(outside, target_is_directory=True)

        result = self.run_cli(*self.setup_args("--yes"))

        self.assertEqual(result.returncode, 2)
        self.assertIn("Vault managed directory must not be a symlink", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())

    def test_symlinked_projects_root_is_rejected_before_writes(self) -> None:
        outside = self.tmp / "outside-projects"
        outside.mkdir()
        self.projects.symlink_to(outside, target_is_directory=True)

        result = self.run_cli(*self.setup_args("--yes"))

        self.assertEqual(result.returncode, 2)
        self.assertIn("Projects root must not be a symlink", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())

    def test_symlinked_global_managed_file_fails_before_config_write(self) -> None:
        outside = self.tmp / "global-outside.txt"
        outside.write_text("private global sentinel\n")
        (self.home / ".claude").mkdir()
        (self.home / ".claude/CLAUDE.md").symlink_to(outside)

        result = self.run_cli(*self.setup_args("--yes"))

        self.assertEqual(result.returncode, 1)
        self.assertIn("Refusing a symlinked global managed file", result.stderr)
        self.assertNotIn("private global sentinel", result.stdout + result.stderr)
        self.assertTrue((self.home / ".claude/CLAUDE.md").is_symlink())
        self.assertEqual(outside.read_text(), "private global sentinel\n")
        self.assertFalse((self.home / ".config/ratchery/config.json").exists())

    def test_confirmation_refusal_is_read_only(self) -> None:
        before = self.snapshot()
        result = self.run_cli(*self.setup_args(), input_data="n\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Setup cancelled.", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_missing_confirmation_input_fails_closed(self) -> None:
        before = self.snapshot()
        result = self.run_cli(*self.setup_args(), input_data="")
        self.assertEqual(result.returncode, 1)
        self.assertIn("confirmation input was unavailable", result.stderr)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
