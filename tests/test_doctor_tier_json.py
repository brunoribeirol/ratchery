#!/usr/bin/env python3
"""Unit/smoke tests for the `--json` flag on `doctor` and `tier`
(docs/specs/ci-json-doctor-gate.md). Invokes the real CLI as a subprocess --
these two commands' JSON-vs-text branching lives inline in main()'s dispatch,
not in an easily unit-testable function, so black-box invocation is the
faithful test here (same style as tests/run-tests.sh). Stdlib only, no deps.

Run: python3 tests/test_doctor_tier_json.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "lib" / "agent_workspace.py"
ROOT = SCRIPT.parents[1]
sys.path.insert(0, str(SCRIPT.parent))
import agent_workspace as aw  # noqa: E402


class _IsolatedHome(unittest.TestCase):
    """Redirect HOME/XDG_STATE_HOME to a throwaway dir so these subprocess
    runs never touch the real machine's ~/.config or ~/.local/state, and run
    against an empty temp project dir outside any git repo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"; self.home.mkdir()
        self.project = self.tmp / "project"; self.project.mkdir()
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.home)
        self.env["XDG_STATE_HOME"] = str(self.home / ".local/state")
        self.env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        stable_clients = self.tmp / "stable-clients"
        stable_clients.mkdir()
        for command, version in (("claude", "2.1.187"), ("codex", "0.138.0")):
            client = stable_clients / command
            client.write_text(f"#!/bin/sh\nprintf '%s\\n' '{version}'\n")
            client.chmod(0o755)
        self.env["PATH"] = str(stable_clients) + os.pathsep + self.env.get("PATH", "")

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.project, env=self.env, capture_output=True, text=True, timeout=30,
        )


class TestDoctorJson(_IsolatedHome):
    def test_json_flag_emits_valid_json_with_expected_keys(self):
        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(
            set(payload.keys()),
            {"errors", "warnings", "tier", "tier_name", "commit", "dirty"},
        )
        # Empty project is missing every managed file -> real errors expected.
        self.assertGreater(len(payload["errors"]), 0)

    def test_json_exit_code_matches_error_presence(self):
        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        expected = 1 if payload["errors"] else 0
        self.assertEqual(result.returncode, expected)

    def test_default_output_is_still_human_text_not_json(self):
        result = self.run_cli("doctor", "--path", str(self.project))
        self.assertIn("Doctor:", result.stdout)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(result.stdout)

    def test_json_and_text_report_the_same_facts(self):
        """The real regression this guards against: the print-vs-json branch
        in doctor_project() silently drifting apart (e.g. a future edit adds
        an error to one branch but not the other). Runs both modes against
        the identical fixture and cross-checks the counts/tier line, rather
        than diffing against a brittle stored golden-text baseline."""
        json_result = self.run_cli("doctor", "--path", str(self.project), "--json")
        text_result = self.run_cli("doctor", "--path", str(self.project))
        payload = json.loads(json_result.stdout)
        self.assertIn(
            f"Doctor: {len(payload['errors'])} error(s), {len(payload['warnings'])} warning(s).",
            text_result.stdout,
        )
        if payload["tier"]:
            self.assertIn(f"Tier: {payload['tier']} ({payload['tier_name']})", text_result.stdout)
        self.assertEqual(json_result.returncode, text_result.returncode)

    def test_provenance_is_null_outside_a_git_repository(self):
        """doctor must stay runnable where there is no Git at all -- the
        provenance fields degrade to null instead of failing the run."""
        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["dirty"])

    def test_provenance_records_the_commit_the_verdict_describes(self):
        """A doctor result with no commit attached says a tree was healthy but
        never which tree; this is what makes a stored CI result re-checkable."""
        git = self._git_fixture()
        if git is None:
            self.skipTest("git not available")
        result = self.run_cli("doctor", "--path", str(git), "--json")
        payload = json.loads(result.stdout)
        self.assertRegex(payload["commit"] or "", r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
        self.assertFalse(payload["dirty"])

    def test_provenance_flags_a_dirty_worktree(self):
        git = self._git_fixture()
        if git is None:
            self.skipTest("git not available")
        (git / "scratch.txt").write_text("uncommitted\n")
        result = self.run_cli("doctor", "--path", str(git), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dirty"])

    def _git_fixture(self) -> Path | None:
        """A throwaway repo with one commit, or None when git is unavailable."""
        repo = self.tmp / "gitrepo"
        repo.mkdir()
        env = dict(self.env)
        env.update({
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
        })
        steps = [
            ["git", "init", "-q"],
            [
                "git",
                "-c",
                "commit.gpgSign=false",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "init",
            ],
        ]
        for step in steps:
            try:
                done = subprocess.run(step, cwd=repo, env=env, capture_output=True, text=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                return None
            if done.returncode != 0:
                return None
        return repo

    def test_doctor_does_not_create_profile_state_in_a_fresh_project(self):
        before = sorted(str(p.relative_to(self.project)) for p in self.project.rglob("*"))
        self.run_cli("doctor", "--path", str(self.project), "--json")
        after = sorted(str(p.relative_to(self.project)) for p in self.project.rglob("*"))
        self.assertEqual(after, before)

    def test_doctor_stops_before_reading_through_managed_parent_symlink(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        sentinel = outside / "state/task-policy.json"
        sentinel.parent.mkdir()
        sentinel.write_text('{"prompt": "must-not-be-read-or-changed"}\n')
        (self.project / ".agents").symlink_to(outside, target_is_directory=True)

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(".agents must not be a symlink" in e for e in payload["errors"]))
        self.assertIsNone(payload["tier"])
        self.assertEqual(sentinel.read_text(), '{"prompt": "must-not-be-read-or-changed"}\n')


class TestTierJson(_IsolatedHome):
    def test_json_flag_emits_valid_json_with_expected_keys(self):
        result = self.run_cli("tier", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        for key in (
            "effective_tier", "computed_tier", "criticality_score",
            "complexity_score", "active_agents", "risk_answers_recorded",
        ):
            self.assertIn(key, payload)
        self.assertFalse(payload["risk_answers_recorded"])
        self.assertEqual(result.returncode, 0)

    def test_default_output_is_still_human_text_not_json(self):
        result = self.run_cli("tier", "--path", str(self.project))
        self.assertIn("Effective tier:", result.stdout)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(result.stdout)

    def test_json_and_text_report_the_same_facts(self):
        """Same regression guard as TestDoctorJson.test_json_and_text_report_the_same_facts,
        for the tier dispatch branch. Runs --json first, then text -- tier
        writes state, but re-running on the same fixture recomputes the same
        tier deterministically, so the printed facts must still match."""
        json_result = self.run_cli("tier", "--path", str(self.project), "--json")
        text_result = self.run_cli("tier", "--path", str(self.project))
        payload = json.loads(json_result.stdout)
        self.assertIn(
            f"Effective tier: {payload['effective_tier']} ({payload['tier_name']})",
            text_result.stdout,
        )
        self.assertIn(
            f"Computed this run: {payload['computed_tier']}  |  criticality "
            f"{payload['criticality_score']}/15  complexity {payload['complexity_score']}/8",
            text_result.stdout,
        )
        self.assertIn(
            f"Active agents for this tier: {', '.join(payload['active_agents'])}",
            text_result.stdout,
        )


class TestDoctorSecurityRegressions(_IsolatedHome):
    """Security regressions an independent review found missing from the
    earlier test suite."""

    def install_secure_fixture(self):
        for rel in ["AGENTS.md", "CLAUDE.md"]:
            (self.project / rel).write_text("fixture\n")
        docs = self.project / "docs"
        docs.mkdir()
        (docs / "PROJECT_CONTEXT.md").write_text("# Context\n")
        (docs / "COMMANDS.md").write_text(
            "<!-- agent-workspace:v8:commands:start -->\n"
            "<!-- agent-workspace:v8:commands:end -->\n"
        )
        claude = self.project / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text(
            (ROOT / "assets/project/.claude/settings.json").read_text()
        )
        codex = self.project / ".codex"
        codex.mkdir()
        (codex / "config.toml").write_text(
            (ROOT / "assets/project/.codex/config.base.toml").read_text()
        )
        (codex / "hooks.json").write_text(
            (ROOT / "assets/project/.codex/hooks.json").read_text()
        )
        runtime = self.project / ".agents/runtime"
        runtime.mkdir(parents=True)
        (runtime / "agent_workspace.py").write_bytes(
            (ROOT / "lib/hook_runtime.py").read_bytes()
        )
        risk_state = self.project / ".agents/state"
        risk_state.mkdir(parents=True, exist_ok=True)
        (risk_state / "risk-answers.json").write_text(
            json.dumps(aw.ae.DEFAULT_RISK_ANSWERS)
        )
        tier_result = self.run_cli("tier", "--path", str(self.project), "--json")
        self.assertEqual(tier_result.returncode, 0, tier_result.stderr)
        state = self.project / ".agents/state"
        project_id = (state / "project-id").read_text().strip()
        (state / "ownership.json").write_text(json.dumps({"project_id": project_id}))

    def assert_secure_fixture(self):
        result = self.run_cli("doctor", "--path", str(self.project), "--deep", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"], [], payload)

    def test_complete_security_fixture_passes(self):
        self.install_secure_fixture()
        self.assert_secure_fixture()

    def test_missing_baseline_agent_is_rejected_even_at_t0(self):
        self.install_secure_fixture()
        (self.project / ".claude/agents/reviewer.md").unlink()

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(
            any("requires Claude agent 'reviewer'" in item for item in payload["errors"]),
            payload,
        )

    def _raise_to_t2(self):
        """handles_payments is a hard floor -> T2, whose required_docs include
        docs/decisions/ (absent from the fixture)."""
        (self.project / ".agents/state/risk-answers.json").write_text(
            json.dumps({**aw.ae.DEFAULT_RISK_ANSWERS, "handles_payments": True})
        )
        tier_result = self.run_cli("tier", "--path", str(self.project), "--json")
        self.assertEqual(tier_result.returncode, 0, tier_result.stderr)
        self.assertEqual(json.loads(tier_result.stdout)["effective_tier"], "T2")

    def test_missing_tier_required_doc_is_an_error_not_a_warning(self):
        """`required_docs` used to only warn while required_agents/skills were
        errors, so a T2/T3 project could run indefinitely without the ADR trail
        its own recorded tier asks for -- a requirement that never blocks is
        governance theatre."""
        self.install_secure_fixture()
        self._raise_to_t2()

        payload = json.loads(self.run_cli("doctor", "--path", str(self.project), "--json").stdout)

        self.assertTrue(
            any("requires docs/decisions/" in item for item in payload["errors"]), payload
        )
        self.assertFalse(
            any("docs/decisions/" in item for item in payload["warnings"]), payload
        )

    def test_present_tier_required_doc_clears_the_error(self):
        self.install_secure_fixture()
        self._raise_to_t2()
        (self.project / "docs/decisions").mkdir(parents=True, exist_ok=True)

        payload = json.loads(self.run_cli("doctor", "--path", str(self.project), "--json").stdout)

        self.assertFalse(
            any("docs/decisions/" in item for item in payload["errors"]), payload
        )

    def test_managed_required_doc_is_not_reported_twice(self):
        """docs/PROJECT_CONTEXT.md is both a managed file and a tier
        requirement; one missing file must produce one error."""
        self.install_secure_fixture()
        (self.project / "docs/PROJECT_CONTEXT.md").unlink()

        payload = json.loads(self.run_cli("doctor", "--path", str(self.project), "--json").stdout)

        matches = [item for item in payload["errors"] if "PROJECT_CONTEXT.md" in item]
        self.assertEqual(len(matches), 1, payload)

    def test_symlinked_active_agent_is_rejected(self):
        self.install_secure_fixture()
        agent = self.project / ".codex/agents/developer.toml"
        outside = self.project.parent / "outside-agent.toml"
        outside.write_text('name = "replacement"\n')
        agent.unlink()
        agent.symlink_to(outside)

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(
            any("requires Codex agent 'developer'" in item for item in payload["errors"]),
            payload,
        )

    def test_unreviewed_default_risk_answers_block_doctor(self):
        self.install_secure_fixture()
        (self.project / ".agents/state/risk-answers.json").unlink()

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(any("risk answers have not been reviewed" in item for item in payload["errors"]), payload)

    def test_removed_claude_pretool_binding_is_rejected(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["hooks"].pop("PreToolUse")
        settings_path.write_text(json.dumps(settings))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("Claude PreToolUse hook" in item for item in payload["errors"]), payload)

    def test_noop_commands_cannot_impersonate_managed_hooks(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = (
            "true # .agents/runtime/agent_workspace.py"
        )
        settings_path.write_text(json.dumps(settings))
        hooks_path = self.project / ".codex/hooks.json"
        hooks = json.loads(hooks_path.read_text())
        hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = (
            "true # .agents/runtime/agent_workspace.py"
        )
        hooks_path.write_text(json.dumps(hooks))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("Claude PreToolUse hook" in item for item in payload["errors"]), payload)
        self.assertTrue(any("Codex PreToolUse hook" in item for item in payload["errors"]), payload)

    def test_claude_hook_must_cover_multiedit(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["hooks"]["PreToolUse"][0]["matcher"] = "Bash|Read|Write|Edit"
        settings_path.write_text(json.dumps(settings))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("Claude PreToolUse hook" in item for item in payload["errors"]), payload)

    def test_disabled_exact_hook_is_not_accepted(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["hooks"]["PreToolUse"][0]["hooks"][0]["enabled"] = False
        settings_path.write_text(json.dumps(settings))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("Claude PreToolUse hook" in item for item in payload["errors"]), payload)

    def test_removed_claude_deny_layers_are_rejected(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["permissions"]["deny"] = []
        settings["sandbox"]["filesystem"]["denyRead"] = []
        settings["sandbox"]["credentials"]["files"] = []
        settings["sandbox"]["credentials"]["envVars"] = []
        settings_path.write_text(json.dumps(settings))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        for fragment in ["permissions.deny", "filesystem.denyRead", "credentials.files", "credentials.envVars"]:
            self.assertTrue(any(fragment in item for item in payload["errors"]), payload)

    def test_project_local_package_credentials_are_required_in_primary_layers(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["permissions"]["deny"].remove("Read(./**/.npmrc)")
        settings["sandbox"]["filesystem"]["denyRead"].remove("**/.npmrc")
        settings["sandbox"]["credentials"]["files"].remove(
            {"path": "./.npmrc", "mode": "deny"}
        )
        settings_path.write_text(json.dumps(settings))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        for fragment in ["permissions.deny", "filesystem.denyRead", "credentials.files"]:
            self.assertTrue(any(fragment in item for item in payload["errors"]), payload)

    def test_codex_project_local_package_credentials_are_required(self):
        self.install_secure_fixture()
        config_path = self.project / ".codex/config.toml"
        config_path.write_text(
            config_path.read_text().replace('"**/.npmrc" = "deny"\n', "")
        )

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(
            any("workspace filesystem deny" in item for item in payload["errors"]),
            payload,
        )

    def test_removed_claude_bypass_and_mcp_approval_guards_are_rejected(self):
        self.install_secure_fixture()
        settings_path = self.project / ".claude/settings.json"
        settings = json.loads(settings_path.read_text())
        settings["permissions"].pop("disableBypassPermissionsMode")
        settings["permissions"]["ask"] = []
        settings_path.write_text(json.dumps(settings))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertIn("Claude bypass-permissions mode is not disabled", payload["errors"])
        self.assertIn(
            "Claude permissions.ask is missing required managed MCP approval rules",
            payload["errors"],
        )

    def test_removed_codex_pretool_binding_is_rejected(self):
        self.install_secure_fixture()
        hooks_path = self.project / ".codex/hooks.json"
        hooks = json.loads(hooks_path.read_text())
        hooks["hooks"].pop("PreToolUse")
        hooks_path.write_text(json.dumps(hooks))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("Codex PreToolUse hook" in item for item in payload["errors"]), payload)

    def test_required_agents_are_checked_for_both_clients_and_skills_block(self):
        self.install_secure_fixture()
        answers_path = self.project / ".agents/state/risk-answers.json"
        answers = dict(aw.ae.DEFAULT_RISK_ANSWERS, handles_payments=True)
        answers_path.write_text(json.dumps(answers))
        tier_result = self.run_cli("tier", "--path", str(self.project), "--json")
        self.assertEqual(tier_result.returncode, 0, tier_result.stderr)
        (self.project / ".codex/agents/architect.toml").unlink()

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(any("requires Codex agent 'architect'" in item for item in payload["errors"]), payload)
        self.assertTrue(any("requires skill 'security-scan'" in item for item in payload["errors"]), payload)

    @unittest.skipUnless(sys.version_info >= (3, 11), "TOML validation requires tomllib")
    def test_removed_codex_workspace_deny_and_hooks_feature_are_rejected(self):
        self.install_secure_fixture()
        config_path = self.project / ".codex/config.toml"
        lines = config_path.read_text().splitlines()
        removed_workspace_entry = False
        for index, line in enumerate(lines):
            if line.startswith('"**/') and not removed_workspace_entry:
                lines.pop(index)
                removed_workspace_entry = True
                break
        lines = ["hooks = false" if line == "hooks = true" else line for line in lines]
        config_path.write_text("\n".join(lines) + "\n")

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("workspace filesystem deny" in item for item in payload["errors"]), payload)
        self.assertIn("Codex hooks feature is not enabled", payload["errors"])

    def test_nonnumeric_session_end_timeout_is_reported_as_json_error(self):
        self.install_secure_fixture()
        hooks_path = self.project / ".codex/hooks.json"
        hooks = json.loads(hooks_path.read_text())
        hooks["hooks"]["SessionEnd"] = [{
            "hooks": [{
                "type": "command",
                "command": "python3 .agents/runtime/agent_workspace.py",
                "timeout": "never",
            }],
        }]
        hooks_path.write_text(json.dumps(hooks))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertIn("Codex SessionEnd hook timeout must be numeric", payload["errors"])

    def test_forged_derived_tier_fields_are_rejected(self):
        self.install_secure_fixture()
        tier_path = self.project / ".agents/state/tier.json"
        tier = json.loads(tier_path.read_text())
        tier["effective_tier"] = "T3"
        tier["tier_name"] = "forged"
        tier["requirements"] = {}
        tier_path.write_text(json.dumps(tier))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        for field in ["effective_tier", "tier_name", "requirements"]:
            self.assertTrue(any(field in item for item in payload["errors"]), payload)

    def test_empty_tier_object_is_not_accepted_as_current_state(self):
        self.install_secure_fixture()
        (self.project / ".agents/state/tier.json").write_text("{}\n")

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(any("computed_tier" in item for item in payload["errors"]), payload)

    def test_missing_current_state_is_a_warning_not_an_error(self):
        """docs/CURRENT_STATE.md is durable *local* project memory, not a
        security/governance invariant like the rest of `required` -- some
        maintainers deliberately .gitignore their own copy (this repo does,
        see CONTRIBUTING.md). A fresh clone missing it must not fail doctor."""
        required_minus_current_state = [
            "AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/config.toml",
            ".codex/hooks.json", ".agents/runtime/agent_workspace.py",
            "docs/PROJECT_CONTEXT.md", "docs/COMMANDS.md",
        ]
        for rel in required_minus_current_state:
            target = self.project / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("")
        (self.project / ".codex" / "hooks.json").write_text("{}")
        (self.project / "docs" / "COMMANDS.md").write_text(
            "<!-- agent-workspace:v8:commands:start -->\n<!-- agent-workspace:v8:commands:end -->\n"
        )
        state = self.project / ".agents" / "state"
        state.mkdir(parents=True)
        (state / "ownership.json").write_text(json.dumps({"project_id": "x"}))
        (state / "project-id").write_text("x")
        (state / "tier.json").write_text(json.dumps({"computed_tier": "T0"}))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertFalse(any("CURRENT_STATE" in e for e in payload["errors"]), payload["errors"])
        self.assertTrue(any("CURRENT_STATE" in w for w in payload["warnings"]), payload["warnings"])

    def test_deliberately_ignored_current_state_has_no_warning(self):
        self.install_secure_fixture()
        (self.project / ".gitignore").write_text("docs/CURRENT_STATE.md\n")

        payload = json.loads(
            self.run_cli("doctor", "--path", str(self.project), "--json").stdout
        )

        self.assertFalse(
            any("CURRENT_STATE" in item for item in payload["errors"]), payload
        )
        self.assertFalse(
            any("CURRENT_STATE" in item for item in payload["warnings"]), payload
        )

    def test_deep_probe_never_executes_a_modified_target_hook(self):
        """Finding 1: `doctor --deep` used to execute the *target's* copy of
        .agents/runtime/agent_workspace.py directly. In the CI-gate use case
        (action.yml) that target is an untrusted checked-out repository, so a
        crafted pull request could run arbitrary code on the runner."""
        runtime_dir = self.project / ".agents" / "runtime"
        runtime_dir.mkdir(parents=True)
        sentinel = self.project / "PWNED"
        malicious = (
            "import sys\n"
            "sys.stdin.read()\n"
            f"open({str(sentinel)!r}, 'w').write('pwned')\n"
            "print('{\"decision\": \"deny\"}')\n"
        )
        (runtime_dir / "agent_workspace.py").write_text(malicious)

        result = self.run_cli("doctor", "--path", str(self.project), "--deep", "--json")
        payload = json.loads(result.stdout)

        self.assertFalse(sentinel.exists(), "the target's hook file must never be executed")
        self.assertTrue(
            any("does not match the framework's shipped hook_runtime.py" in e for e in payload["errors"]),
            payload["errors"],
        )

    def test_deep_probe_runs_the_bundled_hook_when_target_copy_is_unmodified(self):
        runtime_dir = self.project / ".agents" / "runtime"
        runtime_dir.mkdir(parents=True)
        bundled = SCRIPT.parent / "hook_runtime.py"
        (runtime_dir / "agent_workspace.py").write_bytes(bundled.read_bytes())

        result = self.run_cli("doctor", "--path", str(self.project), "--deep", "--json")
        payload = json.loads(result.stdout)

        self.assertFalse(any("does not match" in e for e in payload["errors"]), payload["errors"])
        self.assertFalse(any("Deep security probe failed" in e for e in payload["errors"]), payload["errors"])

    def test_deep_probe_does_not_create_state_for_pretool_event(self):
        runtime_dir = self.project / ".agents" / "runtime"
        runtime_dir.mkdir(parents=True)
        bundled = SCRIPT.parent / "hook_runtime.py"
        (runtime_dir / "agent_workspace.py").write_bytes(bundled.read_bytes())
        state = self.project / ".agents/state"
        self.assertFalse(state.exists())

        self.run_cli("doctor", "--path", str(self.project), "--deep", "--json")

        self.assertFalse(state.exists(), "a diagnostic PreToolUse probe must be read-only")

    def test_empty_claude_settings_does_not_bypass_sandbox_checks(self):
        """Finding 2: doctor_project() gated its Claude sandbox invariant checks
        on `if claude:` (the parsed dict being truthy), so a valid-but-empty
        `{}` silently skipped every check -- a project could remove its entire
        sandbox config and still pass doctor clean."""
        (self.project / ".claude").mkdir()
        (self.project / ".claude" / "settings.json").write_text("{}")

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        for expected in [
            "Claude subprocess credential scrub is not enabled",
            "Claude sandbox is not enabled",
            "Claude sandbox is not configured to fail closed when unavailable",
            "Claude unsandboxed retry escape hatch is not disabled",
        ]:
            self.assertIn(expected, payload["errors"])

    def test_non_object_json_settings_is_rejected_not_silently_treated_as_empty(self):
        (self.project / ".claude").mkdir()
        (self.project / ".claude" / "settings.json").write_text("[1, 2, 3]")

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(any("must be a JSON object" in e for e in payload["errors"]), payload["errors"])

    def test_stale_recorded_tier_is_detected_against_current_risk_answers(self):
        """Finding 4: doctor only ever read the recorded tier.json, never
        recomputed it -- risk-answers.json could be edited (e.g. flipping
        life_safety to true) without re-running `tier`, and doctor stayed
        green reporting the stale, lower tier."""
        state = self.project / ".agents" / "state"
        state.mkdir(parents=True)
        (state / "project-profile.json").write_text(json.dumps({
            "size": "small", "monorepo": False, "package_roots": [], "source_files": 1, "source_lines": 10,
        }))
        (state / "risk-answers.json").write_text(json.dumps({
            "users": "internal", "data_sensitivity": "internal", "handles_pii": False,
            "life_safety": False, "regulated": False, "handles_payments": False,
            "external_exposure": False, "maturity": "prototype",
        }))
        tier_result = self.run_cli("tier", "--path", str(self.project), "--json")
        self.assertEqual(tier_result.returncode, 0, tier_result.stderr)
        recorded = json.loads(tier_result.stdout)
        self.assertEqual(recorded["computed_tier"], "T0")

        # Diverge: flip a hard-floor risk fact without re-running `tier`.
        answers = json.loads((state / "risk-answers.json").read_text())
        answers["life_safety"] = True
        (state / "risk-answers.json").write_text(json.dumps(answers))

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)
        self.assertTrue(
            any("tier.json computed_tier does not match" in e for e in payload["errors"]),
            payload["errors"],
        )

    def test_invalid_risk_answers_still_emit_doctor_json(self):
        self.install_secure_fixture()
        (self.project / ".agents/state/risk-answers.json").write_text("{not-json}\n")

        result = self.run_cli("doctor", "--path", str(self.project), "--deep", "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIsNone(payload["tier"])
        self.assertTrue(any("Invalid risk answers" in item for item in payload["errors"]), payload)

    def test_invalid_tier_history_still_emits_doctor_json(self):
        self.install_secure_fixture()
        history = self.project / ".agents/state/tier-history.jsonl"
        with history.open("a") as stream:
            stream.write("{not-json}\n")

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIsNone(payload["tier"])
        self.assertTrue(any("Invalid tier history" in item for item in payload["errors"]), payload)

    def test_tier_rescans_instead_of_trusting_cached_profile(self):
        config = self.home / ".config/ratchery/config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({
            "version": aw.VERSION,
            "vault_path": None,
            "projects_root": str(self.home / "Projects"),
            "project_layout": "flat",
            "external_tools": "none",
            "thresholds": {
                "medium_files": 0,
                "medium_lines": 999999,
                "large_files": 999999,
                "large_lines": 999999,
                "large_packages": 999999,
            },
        }))
        state = self.project / ".agents/state"
        state.mkdir(parents=True)
        (state / "project-profile.json").write_text(json.dumps({
            "size": "small", "monorepo": False, "package_roots": [],
            "source_files": 0, "source_lines": 0,
        }))
        (self.project / "app.py").write_text("value = 1\n")

        result = self.run_cli("tier", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["computed_tier"], "T1")
        refreshed = json.loads((state / "project-profile.json").read_text())
        self.assertEqual(refreshed["size"], "medium")

    def test_external_source_symlink_is_not_profiled(self):
        external = self.tmp / "external.py"
        external.write_text("secret = 1\n")
        linked = self.project / "linked.py"
        try:
            linked.symlink_to(external)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        inspected = aw.inspect_project(self.project)

        self.assertEqual(inspected["source_files"], 0)
        self.assertEqual(inspected["source_lines"], 0)

    def test_notebook_activates_data_and_ai_profiles_without_reading_notebook_json(self):
        (self.project / "analysis.ipynb").write_text('{"cells": ["large notebook payload"]}\n')

        inspected = aw.inspect_project(self.project)

        self.assertTrue(inspected["capabilities"]["data"])
        self.assertTrue(inspected["capabilities"]["ai_ml"])
        self.assertEqual(inspected["source_files"], 0)
        self.assertEqual(inspected["source_lines"], 0)

    def test_nested_container_and_iac_files_activate_cloud_profile(self):
        infra = self.project / "deploy/k8s"
        infra.mkdir(parents=True)
        (infra / "service.yaml").write_text("kind: Service\n")

        inspected = aw.inspect_project(self.project)

        self.assertTrue(inspected["capabilities"]["cloud_infra"])

    def test_old_installed_codex_is_rejected_by_project_doctor(self):
        self.install_secure_fixture()
        fake_bin = self.tmp / "bin"
        fake_bin.mkdir()
        codex = fake_bin / "codex"
        codex.write_text("#!/bin/sh\nprintf 'codex-cli 0.137.0\\n'\n")
        codex.chmod(0o755)
        self.env["PATH"] = str(fake_bin) + os.pathsep + self.env.get("PATH", "")

        result = self.run_cli("doctor", "--path", str(self.project), "--deep", "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(any("Codex CLI 0.137.0 is below" in item for item in payload["errors"]), payload)

    def test_recorded_mcp_opt_in_requires_both_client_configs(self):
        self.install_secure_fixture()
        enabled = self.run_cli("mcp", "enable", "context7", "--path", str(self.project))
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        config_path = self.project / ".codex/config.toml"
        start, end = aw.codex_mcp_markers("context7")
        config, removed = aw.remove_text_block(config_path.read_text(), start, end)
        self.assertTrue(removed)
        config_path.write_text(config)

        result = self.run_cli("doctor", "--path", str(self.project), "--json")
        payload = json.loads(result.stdout)

        self.assertTrue(any(
            "Recorded MCP opt-in 'context7' is missing or changed in .codex/config.toml" in item
            for item in payload["errors"]
        ), payload)


class TestMinimumCliVersions(unittest.TestCase):
    """A security gate must separate a verdict from a failed measurement.

    `command_version` swallowed every exception, so a probe that timed out on a
    loaded machine was indistinguishable from a genuinely unusable CLI and both
    were reported as the same hard error. A gate that fails for reasons
    unrelated to security is the fastest way to teach a team to ignore it."""

    def probe(self, raw, failure):
        return mock.patch.object(aw, "command_version_probe", return_value=(raw, failure))

    def test_old_installed_cli_is_rejected_as_an_error(self):
        with self.probe("tool 0.137.0", None):
            severity, message = aw.cli_security_version_issue(
                "codex", "Codex CLI", aw.CODEX_MIN_SECURITY
            )
        self.assertEqual(severity, "error")
        self.assertIn("below", message)

    def test_missing_cli_remains_supported(self):
        with self.probe(None, "absent"):
            issue = aw.cli_security_version_issue("codex", "Codex CLI", aw.CODEX_MIN_SECURITY)
        self.assertIsNone(issue)

    def test_current_cli_reports_nothing(self):
        with self.probe("tool 999.0.0", None):
            issue = aw.cli_security_version_issue("codex", "Codex CLI", aw.CODEX_MIN_SECURITY)
        self.assertIsNone(issue)

    def test_incomplete_probe_is_a_warning_not_an_error(self):
        """The regression: a timeout says nothing about the installed version,
        so it must not be reported as a violated security floor."""
        with self.probe(None, "transient"):
            severity, message = aw.cli_security_version_issue(
                "codex", "Codex CLI", aw.CODEX_MIN_SECURITY
            )
        self.assertEqual(severity, "warning")
        self.assertIn("did not complete", message)
        self.assertNotIn("below", message)

    def test_cli_that_answers_unusably_is_still_an_error(self):
        """A CLI that ran and returned garbage is a real defect, unlike a probe
        that never ran -- this is the half that must keep failing."""
        with self.probe(None, "unreadable"):
            severity, message = aw.cli_security_version_issue(
                "codex", "Codex CLI", aw.CODEX_MIN_SECURITY
            )
        self.assertEqual(severity, "error")
        self.assertIn("could not be verified", message)


class TestCommandVersionProbe(unittest.TestCase):
    def test_timeout_is_classified_transient(self):
        with mock.patch.object(aw, "exists", return_value=True), mock.patch.object(
            aw, "run", side_effect=subprocess.TimeoutExpired("claude", 4)
        ):
            self.assertEqual(aw.command_version_probe("claude"), (None, "transient"))

    def test_spawn_failure_is_classified_transient(self):
        with mock.patch.object(aw, "exists", return_value=True), mock.patch.object(
            aw, "run", side_effect=OSError("no fork")
        ):
            self.assertEqual(aw.command_version_probe("claude"), (None, "transient"))

    def test_nonzero_exit_is_classified_unreadable(self):
        broken = subprocess.CompletedProcess(["claude", "--version"], 1, "", "boom")
        with mock.patch.object(aw, "exists", return_value=True), mock.patch.object(
            aw, "run", return_value=broken
        ):
            self.assertEqual(aw.command_version_probe("claude"), (None, "unreadable"))

    def test_absent_command_is_classified_absent(self):
        with mock.patch.object(aw, "exists", return_value=False):
            self.assertEqual(aw.command_version_probe("claude"), (None, "absent"))

    def test_successful_probe_returns_the_version_line(self):
        ok = subprocess.CompletedProcess(["claude", "--version"], 0, "2.1.266 (Claude Code)\n", "")
        with mock.patch.object(aw, "exists", return_value=True), mock.patch.object(
            aw, "run", return_value=ok
        ):
            self.assertEqual(
                aw.command_version_probe("claude"), ("2.1.266 (Claude Code)", None)
            )

    def test_wrapper_keeps_its_original_contract(self):
        """command_version() has many callers that only want the string; the
        split must not change what they see."""
        ok = subprocess.CompletedProcess(["claude", "--version"], 0, "2.1.266\n", "")
        with mock.patch.object(aw, "exists", return_value=True), mock.patch.object(
            aw, "run", return_value=ok
        ):
            self.assertEqual(aw.command_version("claude"), "2.1.266")
        with mock.patch.object(aw, "exists", return_value=True), mock.patch.object(
            aw, "run", side_effect=subprocess.TimeoutExpired("claude", 4)
        ):
            self.assertIsNone(aw.command_version("claude"))


if __name__ == "__main__":
    unittest.main()
