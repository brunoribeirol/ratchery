#!/usr/bin/env python3
"""Black-box tests for the explicit curated-memory CLI boundary."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - product mutations also fail closed off POSIX
    fcntl = None

SCRIPT = Path(__file__).resolve().parents[1] / "lib" / "agent_workspace.py"
PROJECT_ID = "123e4567-e89b-42d3-a456-426614174000"


def handoff_payload(next_action: str = "Continue with the documentation.") -> dict:
    return {
        "source_client": "claude-code",
        "target_client": "codex",
        "objective": "Finish the provider-neutral handoff.",
        "completed": ["Implemented the bounded schema."],
        "changed_files": ["lib/memory_engine.py"],
        "checks": [
            {
                "command": "python3 -m unittest tests.test_memory_engine",
                "status": "passed",
                "summary": "Unit tests passed.",
            }
        ],
        "open_risks": ["Release smoke has not run."],
        "next_action": next_action,
    }


class TestMemoryCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.project = self.tmp / "project"
        self.vault = self.tmp / "vault"
        self.vault_project = self.vault / "projects/demo-project"
        (self.home / ".config/ratchery").mkdir(parents=True)
        (self.project / ".agents/state").mkdir(parents=True)
        self.vault_project.mkdir(parents=True)
        (self.project / ".agents/state/project-id").write_text(PROJECT_ID + "\n")
        (self.vault_project / "Home.md").write_text(
            "---\n"
            'title: "demo"\n'
            f'project_id: "{PROJECT_ID}"\n'
            "---\n\n# Demo\n"
        )
        config = {
            "version": "1.0.1",
            "vault_path": str(self.vault),
            "projects_root": str(self.tmp),
            "project_layout": "flat",
            "external_tools": "none",
            "thresholds": {
                "medium_files": 150,
                "medium_lines": 25000,
                "large_files": 800,
                "large_lines": 120000,
                "large_packages": 5,
            },
        }
        (self.home / ".config/ratchery/config.json").write_text(
            json.dumps(config)
        )
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.home)
        self.env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        self.env["XDG_STATE_HOME"] = str(self.home / ".local/state")

    def tearDown(self):
        self._tmp.cleanup()

    @property
    def handoff_path(self) -> Path:
        return self.vault_project / "Handoff.json"

    def run_cli(self, *args: str, input_data: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.project,
            env=self.env,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def write(self, payload: dict | None = None, *extra: str) -> subprocess.CompletedProcess:
        return self.run_cli(
            "memory",
            "handoff",
            "write",
            "--path",
            str(self.project),
            "--stdin",
            *extra,
            input_data=json.dumps(payload or handoff_payload()),
        )

    def test_status_json_is_clean_and_reports_no_pending_handoff(self):
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["backend"], "curated-vault")
        self.assertFalse(payload["automatic_capture"])
        self.assertFalse(payload["network"])
        self.assertFalse(payload["pending_handoff"])
        self.assertEqual(payload["errors"], [])

    def test_write_show_and_clear_round_trip(self):
        written = self.write()
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(self.handoff_path.is_file())
        self.assertEqual(stat.S_IMODE(self.handoff_path.stat().st_mode), 0o600)

        shown = self.run_cli(
            "memory", "handoff", "show", "--path", str(self.project), "--json"
        )
        self.assertEqual(shown.returncode, 0, shown.stderr)
        record = json.loads(shown.stdout)
        self.assertEqual(record["project_id"], PROJECT_ID)
        self.assertEqual(record["source_client"], "claude-code")
        self.assertEqual(record["target_client"], "codex")
        self.assertEqual(record["git"], {"commit": None, "dirty": None})

        dry = self.run_cli(
            "memory", "handoff", "clear", "--path", str(self.project)
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertTrue(self.handoff_path.exists())
        self.assertIn("Dry run only", dry.stdout)

        cleared = self.run_cli(
            "memory", "handoff", "clear", "--path", str(self.project), "--apply"
        )
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertFalse(self.handoff_path.exists())
        backups = list((self.home / ".local/state/ratchery/memory-backups").rglob("Handoff.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backups[0].parent.stat().st_mode), 0o700)
        self.assertEqual(json.loads(backups[0].read_text())["project_id"], PROJECT_ID)

    def test_existing_handoff_requires_replace_and_is_backed_up(self):
        self.assertEqual(self.write().returncode, 0)
        original = self.handoff_path.read_bytes()

        refused = self.write(handoff_payload("A different action."))
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(self.handoff_path.read_bytes(), original)

        replaced = self.write(handoff_payload("A different action."), "--replace")
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertEqual(
            json.loads(self.handoff_path.read_text())["next_action"], "A different action."
        )
        backups = list((self.home / ".local/state/ratchery/memory-backups").rglob("Handoff.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    def test_write_requires_explicit_noninteractive_stdin(self):
        result = self.run_cli(
            "memory", "handoff", "write", "--path", str(self.project), input_data="{}"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("pass --stdin", result.stderr)
        self.assertFalse(self.handoff_path.exists())

    def test_secret_like_input_is_rejected_without_echo(self):
        secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
        payload = handoff_payload(f"Use {secret} next.")
        result = self.write(payload)
        self.assertEqual(result.returncode, 1)
        self.assertIn("secret-like", result.stderr)
        self.assertNotIn(secret, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.handoff_path.exists())

    def test_invalid_stored_handoff_fails_cleanly(self):
        self.handoff_path.write_text('{"schema_version": 999}\n')
        self.handoff_path.chmod(0o600)
        result = self.run_cli(
            "memory", "handoff", "show", "--path", str(self.project), "--json"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported schema", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_vault_home_identity_must_match_exactly(self):
        (self.vault_project / "Home.md").write_text(
            "---\nproject_id: \"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa\"\n---\n"
        )
        result = self.run_cli("memory", "doctor", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["errors"])
        self.assertFalse(payload["pending_handoff"])

    def test_vault_home_identity_in_body_is_not_trusted(self):
        (self.vault_project / "Home.md").write_text(
            "# Untrusted body\n\n"
            "```yaml\n"
            f'project_id: "{PROJECT_ID}"\n'
            "```\n"
        )
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["errors"])
        self.assertFalse(payload["pending_handoff"])

    def test_duplicate_project_id_fields_are_not_trusted(self):
        (self.vault_project / "Home.md").write_text(
            "---\n"
            f'project_id: "{PROJECT_ID}"\n'
            'project_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"\n'
            "---\n"
        )
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)["errors"])

    def test_symlinked_handoff_is_rejected_without_reading_target(self):
        outside = self.tmp / "outside.json"
        outside.write_text(json.dumps({"private": "do-not-read"}))
        self.handoff_path.symlink_to(outside)
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["errors"])
        self.assertNotIn("do-not-read", result.stdout + result.stderr)
        self.assertEqual(json.loads(outside.read_text()), {"private": "do-not-read"})

    def test_handoff_with_group_or_other_permissions_is_rejected(self):
        self.assertEqual(self.write().returncode, 0)
        self.handoff_path.chmod(0o644)
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("group or other permissions", result.stdout)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO test requires POSIX")
    def test_fifo_handoff_is_rejected_without_blocking(self):
        os.mkfifo(self.handoff_path)
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("regular file", result.stdout)

    def test_duplicate_vault_identity_is_rejected(self):
        duplicate = self.vault / "projects/duplicate"
        duplicate.mkdir()
        (duplicate / "Home.md").write_text(
            f"---\nproject_id: \"{PROJECT_ID}\"\n---\n"
        )
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Multiple Vault projects", result.stdout)

    def test_status_and_plan_never_execute_discovered_ai_memory(self):
        fake_bin = self.tmp / "bin"
        fake_bin.mkdir()
        sentinel = self.tmp / "executed"
        fake = fake_bin / "ai-memory"
        fake.write_text(f"#!/bin/sh\n: > '{sentinel}'\n")
        fake.chmod(0o755)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env.get("PATH", "")

        status = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        plan = self.run_cli("memory", "plan", "ai-memory", "--json")
        backends = self.run_cli("memory", "backends", "--json")

        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertTrue(json.loads(status.stdout)["ai_memory"]["executable_present"])
        self.assertFalse(json.loads(status.stdout)["ai_memory"]["enabled"])
        self.assertEqual(json.loads(plan.stdout)["activation"], "experimental")
        self.assertEqual(json.loads(backends.stdout)["active"], "curated-vault")
        self.assertFalse(sentinel.exists())

    def test_git_fsmonitor_from_repository_config_is_never_executed(self):
        sentinel = self.tmp / "fsmonitor-executed"
        monitor = self.tmp / "fsmonitor"
        monitor.write_text(f"#!/bin/sh\n: > '{sentinel}'\n")
        monitor.chmod(0o755)
        for command in (
            ["git", "init", "-q"],
            ["git", "config", "core.fsmonitor", str(monitor)],
        ):
            done = subprocess.run(
                command,
                cwd=self.project,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if done.returncode != 0:
                self.skipTest("git fsmonitor fixture is unavailable")
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())

    @unittest.skipUnless(fcntl is not None, "advisory lock test requires POSIX")
    def test_concurrent_mutations_fail_without_replacing_or_clearing(self):
        self.assertEqual(self.write().returncode, 0)
        original = self.handoff_path.read_bytes()
        lock_path = self.vault_project / ".Handoff.lock"
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            replaced = self.write(handoff_payload("Concurrent update."), "--replace")
            cleared = self.run_cli(
                "memory", "handoff", "clear", "--path", str(self.project), "--apply"
            )
        self.assertEqual(replaced.returncode, 1)
        self.assertEqual(cleared.returncode, 1)
        self.assertIn("already in progress", replaced.stderr)
        self.assertIn("already in progress", cleared.stderr)
        self.assertEqual(self.handoff_path.read_bytes(), original)

    def test_symlinked_backup_directory_cannot_redirect_a_replace(self):
        self.assertEqual(self.write().returncode, 0)
        original = self.handoff_path.read_bytes()
        state = self.home / ".local/state/ratchery"
        state.mkdir(parents=True)
        outside = self.tmp / "outside-backups"
        outside.mkdir()
        (state / "memory-backups").symlink_to(outside, target_is_directory=True)

        result = self.write(handoff_payload("Replace through a symlink."), "--replace")

        self.assertEqual(result.returncode, 1)
        self.assertIn("unavailable or unsafe", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(self.handoff_path.read_bytes(), original)

    def test_missing_project_state_error_does_not_expose_absolute_path(self):
        (self.project / ".agents/state/project-id").unlink()
        (self.project / ".agents/state").rmdir()
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(str(self.project), result.stdout + result.stderr)

    def test_configured_vault_root_symlink_is_rejected(self):
        vault_link = self.tmp / "vault-link"
        vault_link.symlink_to(self.vault, target_is_directory=True)
        config_path = self.home / ".config/ratchery/config.json"
        config = json.loads(config_path.read_text())
        config["vault_path"] = str(vault_link)
        config_path.write_text(json.dumps(config))
        result = self.run_cli("memory", "status", "--path", str(self.project), "--json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must not be a symlink", result.stdout)

    def test_human_and_json_status_share_the_same_facts(self):
        self.assertEqual(self.write().returncode, 0)
        machine = self.run_cli(
            "memory", "status", "--path", str(self.project), "--json"
        )
        human = self.run_cli("memory", "status", "--path", str(self.project))
        payload = json.loads(machine.stdout)
        self.assertEqual(machine.returncode, human.returncode)
        self.assertIn(f"Memory backend: {payload['backend']}", human.stdout)
        self.assertIn("Pending handoff: yes", human.stdout)
        self.assertIn(
            f"Handoff: {payload['handoff_source']} -> {payload['handoff_target']}",
            human.stdout,
        )


if __name__ == "__main__":
    unittest.main()
