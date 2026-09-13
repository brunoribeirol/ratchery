#!/usr/bin/env python3
"""Contract tests for the optional-tool catalog and non-automation policy."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import agent_workspace as aw  # noqa: E402
import hook_runtime as hook  # noqa: E402


class TestToolCatalog(unittest.TestCase):
    def test_hook_runtime_reports_the_current_product_version(self):
        self.assertEqual(hook.VERSION, aw.VERSION)

    def test_shipped_catalog_is_valid_and_has_no_external_always_mode(self):
        self.assertEqual(aw.tool_catalog_issues(), [])
        catalog = aw.load_tool_catalog()
        self.assertTrue(catalog)
        self.assertNotIn("_schema_version", catalog)
        self.assertNotIn("always", {entry["activation"] for entry in catalog.values()})

    def test_cost_security_and_heavy_tool_modes_are_explicit(self):
        catalog = aw.load_tool_catalog()
        self.assertEqual(catalog["ccusage"]["family"], "cost-observability")
        self.assertEqual(catalog["gitleaks"]["activation"], "profile")
        self.assertEqual(catalog["trivy"]["activation"], "profile")
        self.assertEqual(catalog["rtk"]["activation"], "experimental")
        self.assertEqual(catalog["context-mode"]["activation"], "experimental")
        self.assertEqual(catalog["agent-scan"]["activation"], "on-demand")
        self.assertEqual(catalog["ai-jail"]["activation"], "experimental")
        self.assertEqual(catalog["ai-jail"]["family"], "outer-agent-sandbox")
        self.assertEqual(catalog["ai-memory"]["activation"], "experimental")
        self.assertEqual(catalog["ai-memory"]["family"], "team-durable-memory")
        self.assertEqual(catalog["serena"]["commit_seen"], aw.SERENA_V1_7_0_COMMIT)
        for entry in catalog.values():
            self.assertTrue(entry["network"])
            self.assertTrue(entry["benchmark"])

    def test_invalid_schema_and_unsafe_command_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tools.lock.json"
            path.write_text(
                json.dumps(
                    {
                        "_schema_version": 99,
                        "bad": {
                            "family": "x",
                            "activation": "magic",
                            "commands": ["--inject"],
                            "network": "none",
                            "benchmark": "required",
                            "source": "http://example.com",
                            "policy": "manual",
                            "commit_seen": "short",
                        },
                    }
                )
            )
            issues = aw.tool_catalog_issues(path)
        joined = "\n".join(issues)
        self.assertIn("_schema_version 1", joined)
        self.assertIn("unsupported mode", joined)
        self.assertIn("safe executable names", joined)
        self.assertIn("must use https", joined)
        self.assertIn("full lowercase Git SHA", joined)

    def test_every_entry_requires_valid_recheck_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tools.lock.json"
            path.write_text(
                json.dumps(
                    {
                        "_schema_version": 1,
                        "demo": {
                            "family": "test",
                            "activation": "experimental",
                            "commands": ["demo"],
                            "network": "none",
                            "benchmark": "required",
                            "source": "https://example.invalid/demo",
                            "policy": "manual",
                            "version_seen": "1.0.0",
                        },
                    }
                )
            )
            issues = aw.tool_catalog_issues(path)
        joined = "\n".join(issues)
        self.assertIn("checked_at must be an ISO date", joined)
        self.assertIn("recheck_by must be an ISO date", joined)

    def test_tools_status_does_not_execute_discovered_binaries_by_default(self):
        paths = {
            "claude": "/tmp/claude",
            "codex": None,
            "uv": None,
            "uvx": None,
            **{name: None for name in aw.load_tool_catalog()},
            "gitleaks": "/tmp/gitleaks",
        }
        with (
            mock.patch.object(aw, "tool_paths", return_value=paths),
            mock.patch.object(
                aw, "command_version", side_effect=AssertionError("unexpected execution")
            ),
            mock.patch.object(
                aw, "qmd_security_state", side_effect=AssertionError("unexpected execution")
            ),
            redirect_stdout(io.StringIO()),
        ):
            aw.tools_status()

    def test_install_guidance_does_not_execute_discovered_binaries(self):
        def discovered(command: str):
            return f"/tmp/{command}" if command in {"qmd", "rtk"} else None

        with (
            mock.patch.object(aw.shutil, "which", side_effect=discovered),
            mock.patch.object(
                aw, "command_version", side_effect=AssertionError("unexpected execution")
            ),
            mock.patch.object(
                aw, "qmd_security_state", side_effect=AssertionError("unexpected execution")
            ),
            redirect_stdout(io.StringIO()),
        ):
            aw.tools_install()
            self.assertEqual(aw.tools_install_named("rtk"), 0)

    def test_tools_recommend_is_read_only_and_honors_mcp_opt_in(self):
        profile = {
            "size": "small",
            "source_files": 1,
            "capabilities": {"cloud_infra": False},
        }
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(aw, "git_root", return_value=Path(tmp)),
                mock.patch.object(aw, "inspect_project", return_value=profile),
                mock.patch.object(
                    aw, "profile", side_effect=AssertionError("must not write")
                ),
                mock.patch.object(aw, "tool_paths", return_value={}),
                mock.patch.object(aw, "mcp_opted_in", return_value={"context7"}),
                mock.patch.object(
                    aw, "qmd_configured", side_effect=AssertionError("must not probe")
                ),
                redirect_stdout(stdout),
            ):
                aw.tools_recommend(Path(tmp))
        self.assertIn("Context7", stdout.getvalue())

    def test_tools_recommend_does_not_route_blocked_qmd(self):
        profile = {
            "size": "small",
            "source_files": 1,
            "capabilities": {"cloud_infra": False},
        }
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(aw, "git_root", return_value=Path(tmp)),
                mock.patch.object(aw, "inspect_project", return_value=profile),
                mock.patch.object(aw, "tool_paths", return_value={"qmd": "/tmp/qmd"}),
                mock.patch.object(aw, "mcp_opted_in", return_value=set()),
                mock.patch.object(
                    aw,
                    "qmd_security_state",
                    return_value=("blocked", "QMD fixture is blocked"),
                ),
                mock.patch.object(aw, "qmd_configured", return_value=True),
                redirect_stdout(stdout),
            ):
                aw.tools_recommend(Path(tmp), probe=True)
        self.assertIn("QMD fixture is blocked", stdout.getvalue())
        self.assertNotIn("QMD (via search-vault skill)", stdout.getvalue())

    def test_serena_is_not_reported_installed_merely_because_uvx_exists(self):
        real_which = aw.shutil.which

        def only_uvx(command: str):
            return "/tmp/uvx" if command == "uvx" else None

        with mock.patch.object(aw.shutil, "which", side_effect=only_uvx):
            paths = aw.tool_paths()
        self.assertEqual(paths["uvx"], "/tmp/uvx")
        self.assertIsNone(paths["serena"])
        self.assertIsNotNone(real_which)

    def test_failed_version_probe_is_not_reported_as_a_version(self):
        failed = type("Result", (), {"returncode": 2, "stdout": "", "stderr": "unknown --version"})()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "run", return_value=failed),
        ):
            self.assertIsNone(aw.command_version("graphify"))


class TestRtkGuidance(unittest.TestCase):
    def test_guidance_separates_claude_and_codex_and_runs_nothing(self):
        stdout = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=False),
            mock.patch.object(aw.subprocess, "run") as runner,
            redirect_stdout(stdout),
        ):
            rc = aw.tools_install_named("rtk")
        text = stdout.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("--rev FULL_40_CHAR_COMMIT_SHA --locked", text)
        self.assertIn("mutable Git tag is not an immutable pin", text)
        self.assertIn("rtk init -g --dry-run -v", text)
        self.assertIn("rtk init -g --codex --dry-run -v", text)
        self.assertIn("Claude uses a PreToolUse hook", text)
        runner.assert_not_called()


class TestHookRuntimeSecurity(unittest.TestCase):
    def invoke(self, payload: dict) -> str:
        stdout = io.StringIO()
        with (
            mock.patch.object(hook.sys, "stdin", io.StringIO(json.dumps(payload))),
            redirect_stdout(stdout),
        ):
            hook.main()
        return stdout.getvalue()

    def test_patch_policy_text_is_not_mistaken_for_a_sensitive_target(self):
        output = self.invoke({
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: docs/policy.md\n"
                    "+Block .npmrc and credentials.json.\n"
                    "*** End Patch"
                )
            },
        })
        self.assertEqual(output, "")

    def test_patch_to_sensitive_target_is_denied(self):
        output = self.invoke({
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: .npmrc\n"
                    "+registry=https://example.invalid\n"
                    "*** End Patch"
                )
            },
        })
        self.assertIn("deny", output)

    def test_bash_cannot_impersonate_a_patch_to_skip_destructive_checks(self):
        output = self.invoke({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {
                "command": (
                    "*** Begin Patch\n"
                    "git reset --hard\n"
                    "*** End Patch"
                )
            },
        })
        self.assertIn("deny", output)

    def test_prompt_state_refuses_symlinked_agents_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            outside = Path(tmp) / "outside"
            root.mkdir()
            (outside / "state").mkdir(parents=True)
            (root / ".agents").symlink_to(outside, target_is_directory=True)
            output = self.invoke({
                "hook_event_name": "UserPromptSubmit",
                "cwd": str(root),
                "prompt": "implement feature",
            })
            self.assertIn("missing or unsafe", output)
            self.assertFalse((outside / "state/task-policy.json").exists())

    def test_prompt_state_is_private_and_contains_no_raw_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".agents/state"
            state.mkdir(parents=True)
            prompt = "implement feature with private business details"
            self.invoke({
                "hook_event_name": "UserPromptSubmit",
                "cwd": str(root),
                "prompt": prompt,
            })
            policy_path = state / "task-policy.json"
            policy = json.loads(policy_path.read_text())
            self.assertNotIn(prompt, policy_path.read_text())
            self.assertNotIn("prompt", policy)
            self.assertEqual(policy_path.stat().st_mode & 0o777, 0o600)

    def test_git_probe_ignores_external_git_directory(self):
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real"
            attacker = Path(tmp) / "attacker"
            real.mkdir(); attacker.mkdir()
            for repo in (real, attacker):
                subprocess.run(
                    ["git", "init", "-q"], cwd=repo, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
            with mock.patch.dict(os.environ, {"GIT_DIR": str(attacker / ".git")}):
                root = hook.run(["git", "rev-parse", "--show-toplevel"], real)
            self.assertEqual(Path(root).resolve(), real.resolve())


class TestHookTemplateContracts(unittest.TestCase):
    def test_claude_uses_exec_form_and_project_directory(self):
        settings = json.loads(
            (Path(__file__).resolve().parents[1] / "assets/project/.claude/settings.json").read_text()
        )
        for groups in settings["hooks"].values():
            for group in groups:
                for command in group["hooks"]:
                    self.assertEqual(command["command"], "python3")
                    self.assertEqual(
                        command["args"],
                        ["${CLAUDE_PROJECT_DIR}/.agents/runtime/agent_workspace.py"],
                    )

    def test_codex_git_discovery_uses_a_clean_minimal_environment(self):
        hooks = json.loads(
            (Path(__file__).resolve().parents[1] / "assets/project/.codex/hooks.json").read_text()
        )
        for groups in hooks["hooks"].values():
            for group in groups:
                for command in group["hooks"]:
                    text = command["command"]
                    self.assertIn("PATH=/usr/bin:/bin", text)
                    self.assertIn("git -C . rev-parse --show-toplevel", text)
                    self.assertIn("$ROOT/.agents/runtime/agent_workspace.py", text)


if __name__ == "__main__":
    unittest.main()
