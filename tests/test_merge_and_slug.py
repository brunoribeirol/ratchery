#!/usr/bin/env python3
"""Unit tests for merge/slug/frontmatter logic in lib/agent_workspace.py that
previously had only indirect coverage via tests/run-tests.sh's black-box CLI
assertions: merge_project_json, merge_codex_hooks (managed-block/hook merge
engine), frontmatter_issues (Vault YAML validation), and choose_vault_slug
(project<->Vault identity resolution). Stdlib unittest only, no deps.
"""
from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import agent_workspace as aw  # noqa: E402


class _HomeRedirected(unittest.TestCase):
    """Shared setUp: merge_project_json/merge_codex_hooks call backup_file(),
    which writes under state_root() -- redirect HOME/XDG_STATE_HOME to a
    throwaway dir so tests never touch the real machine's state."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self._orig_env = dict(os.environ)
        os.environ["XDG_STATE_HOME"] = str(self.home / ".local/state")
        os.environ["HOME"] = str(self.home)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)
        self._tmp.cleanup()


class TestMergeHookMaps(unittest.TestCase):
    def test_owned_group_replaced_user_group_preserved(self):
        existing = {
            "PreToolUse": [
                {"hooks": [{"type": "command", "command": f"python3 {aw.RUNTIME_MARKER}"}]},
                {"hooks": [{"type": "command", "command": "my-own-hook.sh"}]},
            ]
        }
        managed = {"PreToolUse": [{"hooks": [{"type": "command", "command": f"python3 {aw.RUNTIME_MARKER} --v2"}]}]}
        result = aw.merge_hook_maps(existing, managed)
        commands = [h["hooks"][0]["command"] for h in result["PreToolUse"]]
        self.assertIn("my-own-hook.sh", commands)  # user-owned group survives
        self.assertIn(f"python3 {aw.RUNTIME_MARKER} --v2", commands)  # replaced with new managed version
        self.assertNotIn(f"python3 {aw.RUNTIME_MARKER}", commands)  # old managed version gone, not duplicated

    def test_event_with_only_removed_owned_group_disappears(self):
        existing = {"SessionEnd": [{"hooks": [{"type": "command", "command": f"python3 {aw.RUNTIME_MARKER}"}]}]}
        result = aw.merge_hook_maps(existing, {})
        self.assertNotIn("SessionEnd", result)  # no owned + no managed replacement = event key dropped, not left empty

    def test_event_present_only_in_managed_is_added(self):
        result = aw.merge_hook_maps({}, {"UserPromptSubmit": [{"hooks": []}]})
        self.assertIn("UserPromptSubmit", result)


class TestManagedTextBlocks(unittest.TestCase):
    def test_pre_rebrand_vault_index_is_recognized_for_safe_replacement(self):
        old = (
            "# Vault Index\n\n"
            "This block is maintained by Agent Workspace v8.\n\n"
            "## Active projects\n\n## Main areas\n\n## Navigation\n"
        )
        self.assertTrue(aw.looks_like_legacy_canonical_index(old))

    def test_rejects_missing_reversed_or_duplicate_markers(self):
        for text in ["START\nbody", "END\nbody\nSTART", "START\nbody\nEND\nSTART"]:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "Malformed managed block"):
                aw.replace_managed_block(text, "replacement", "START", "END")


class TestMergeProjectJson(_HomeRedirected):
    def test_user_owned_top_level_key_untouched(self):
        path = self.tmp / "settings.json"
        path.write_text(json.dumps({"userSetting": "keep-me", "sandbox": {"enabled": False}}))
        aw.merge_project_json(path, {"sandbox": {"enabled": True}}, self.tmp, "settings-update")
        merged = json.loads(path.read_text())
        self.assertEqual(merged["userSetting"], "keep-me")
        self.assertTrue(merged["sandbox"]["enabled"])

    def test_arrays_are_additive_and_deduplicated(self):
        path = self.tmp / "settings.json"
        marker_a, marker_b = "rule-alpha", "rule-beta"
        path.write_text(json.dumps({"permissions": {"deny": [marker_a]}}))
        aw.merge_project_json(path, {"permissions": {"deny": [marker_a, marker_b]}}, self.tmp, "x")
        merged = json.loads(path.read_text())
        deny = merged["permissions"]["deny"]
        self.assertEqual(deny.count(marker_a), 1)  # not duplicated
        self.assertIn(marker_b, deny)

    def test_backup_created_only_when_content_actually_changes(self):
        path = self.tmp / "settings.json"
        path.write_text(json.dumps({"a": 1}))
        aw.merge_project_json(path, {"a": 1}, self.tmp, "noop")  # patch == existing already
        backups_dir = aw.state_root() / "project-backups"
        self.assertFalse(backups_dir.exists())
        aw.merge_project_json(path, {"a": 2}, self.tmp, "real-change")
        self.assertTrue(backups_dir.exists())

    def test_nested_dict_merges_recursively_not_wholesale_replace(self):
        path = self.tmp / "settings.json"
        path.write_text(json.dumps({"sandbox": {"enabled": True, "userField": "keep"}}))
        aw.merge_project_json(path, {"sandbox": {"failIfUnavailable": True}}, self.tmp, "x")
        merged = json.loads(path.read_text())
        self.assertEqual(merged["sandbox"], {"enabled": True, "userField": "keep", "failIfUnavailable": True})


class TestMergeCodexHooks(_HomeRedirected):
    def test_description_and_hooks_merged(self):
        path = self.tmp / "hooks.json"
        path.write_text(json.dumps({"description": "old", "hooks": {"PreToolUse": [{"hooks": [{"command": "keep-mine"}]}]}}))
        aw.merge_codex_hooks(path, {"description": "new", "hooks": {}}, self.tmp)
        result = json.loads(path.read_text())
        self.assertEqual(result["description"], "new")
        self.assertEqual(result["hooks"]["PreToolUse"][0]["hooks"][0]["command"], "keep-mine")

    def test_no_write_when_nothing_changes(self):
        path = self.tmp / "hooks.json"
        path.write_text(json.dumps({"description": "d", "hooks": {}}))
        mtime_before = path.stat().st_mtime_ns
        aw.merge_codex_hooks(path, {"description": "d", "hooks": {}}, self.tmp)
        self.assertEqual(path.stat().st_mtime_ns, mtime_before)


class TestMcpOptIn(_HomeRedirected):
    def _project(self, name: str = "project") -> Path:
        project = self.tmp / name
        (project / ".codex").mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "assets/project/.codex/config.base.toml"
        (project / ".codex/config.toml").write_text(source.read_text())
        return project

    def test_committed_opt_in_survives_refresh_in_a_fresh_checkout(self):
        original = self._project("original")
        aw.mcp_enable(original, "context7")

        clone = self._project("clone")
        (clone / ".agents/state").mkdir(parents=True)
        (clone / ".mcp.json").write_bytes((original / ".mcp.json").read_bytes())
        (clone / ".codex/config.toml").write_bytes(
            (original / ".codex/config.toml").read_bytes()
        )
        marker = aw.mcp_opt_in_path(original)
        aw.mcp_opt_in_path(clone).write_bytes(marker.read_bytes())

        aw.remove_legacy_auto_mcp(clone / ".mcp.json")

        status = aw.mcp_status(clone)["context7"]
        self.assertTrue(status["claude"])
        self.assertTrue(status["codex"])

    def test_generated_gitignore_commits_the_opt_in_marker(self):
        block = (Path(__file__).resolve().parents[1] / "assets/project/gitignore.block").read_text()
        self.assertIn("!.agents/state/mcp-enabled.json", block)

    def test_enable_and_disable_are_dual_client_and_reversible(self):
        project = self._project()

        aw.mcp_enable(project, "serena")

        status = aw.mcp_status(project)["serena"]
        self.assertEqual(status, {"claude": True, "codex": True})
        self.assertIn("--context\", \"codex", (project / ".codex/config.toml").read_text())
        self.assertIn(aw.SERENA_V1_7_0_COMMIT, (project / ".mcp.json").read_text())
        codex_config = tomllib.loads((project / ".codex/config.toml").read_text())
        serena = codex_config["mcp_servers"]["serena"]
        self.assertIn(aw.SERENA_V1_7_0_COMMIT, serena["args"][1])
        self.assertEqual(
            serena["enabled_tools"],
            ["get_symbols_overview", "find_symbol", "find_referencing_symbols"],
        )
        self.assertEqual(serena["default_tools_approval_mode"], "prompt")
        self.assertEqual(serena["tools"]["find_symbol"]["output_token_limit"], 8000)
        self.assertTrue(aw.mcp_disable(project, "serena"))
        self.assertEqual(
            aw.mcp_status(project)["serena"],
            {"claude": False, "codex": False},
        )
        self.assertFalse(aw.mcp_opt_in_path(project).exists())

    def test_enable_rolls_back_all_project_files_when_a_replace_fails(self):
        project = self._project()
        codex = project / ".codex/config.toml"
        codex_before = codex.read_bytes()
        original_write = aw.atomic_write_bytes
        project_writes = 0

        def fail_second_project_write(path: Path, data: bytes) -> None:
            nonlocal project_writes
            if Path(path).is_relative_to(project):
                project_writes += 1
                if project_writes == 2:
                    raise OSError("simulated replacement failure")
            original_write(path, data)

        with mock.patch.object(aw, "atomic_write_bytes", side_effect=fail_second_project_write):
            with self.assertRaisesRegex(OSError, "simulated replacement failure"):
                aw.mcp_enable(project, "context7")

        self.assertFalse(aw.mcp_opt_in_path(project).exists())
        self.assertFalse((project / ".mcp.json").exists())
        self.assertEqual(codex.read_bytes(), codex_before)

    def test_backups_are_private_and_do_not_disclose_absolute_source_path(self):
        project = self._project()
        source = project / ".codex/config.toml"
        backup = aw.backup_file(source, project, "test")
        self.assertIsNotNone(backup)
        assert backup is not None
        manifest_path = backup / "manifest.json"
        backup_path = backup / source.name
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["source"], ".codex/config.toml")
        self.assertNotIn(str(project), manifest_path.read_text())
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(backup_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(manifest_path.stat().st_mode), 0o600)

    def test_managed_parent_symlink_is_rejected_before_write(self):
        project = self.tmp / "symlink-project"
        outside = self.tmp / "outside"
        project.mkdir(); outside.mkdir()
        (project / ".claude").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Managed directory .claude"):
            aw.project_files(project, {"capabilities": {}}, None)
        self.assertEqual(list(outside.iterdir()), [])

    def test_enable_refuses_to_overwrite_user_owned_claude_server(self):
        project = self._project()
        custom = {"mcpServers": {"context7": {"command": "custom"}}}
        (project / ".mcp.json").write_text(json.dumps(custom))

        with self.assertRaisesRegex(ValueError, "Refusing to overwrite user-owned"):
            aw.mcp_enable(project, "context7")

        self.assertEqual(json.loads((project / ".mcp.json").read_text()), custom)
        self.assertNotIn("agent-workspace:mcp:context7", (project / ".codex/config.toml").read_text())

    def test_enable_refuses_to_overwrite_user_owned_codex_server(self):
        project = self._project()
        config = project / ".codex/config.toml"
        config.write_text(config.read_text() + '\n[mcp_servers.context7]\nurl = "https://custom.invalid"\n')

        with self.assertRaisesRegex(ValueError, "user-owned Codex MCP server"):
            aw.mcp_enable(project, "context7")

        self.assertFalse((project / ".mcp.json").exists())

    def test_enable_refuses_to_repair_a_modified_managed_codex_block(self):
        project = self._project()
        aw.mcp_enable(project, "context7")
        claude_before = (project / ".mcp.json").read_text()
        codex = project / ".codex/config.toml"
        codex.write_text(codex.read_text().replace("enabled = true", "enabled = false"))

        with self.assertRaisesRegex(ValueError, "modified/user-owned Codex"):
            aw.mcp_enable(project, "context7")

        self.assertEqual((project / ".mcp.json").read_text(), claude_before)
        self.assertIn("enabled = false", codex.read_text())

    def test_malformed_shared_marker_blocks_before_configuration_changes(self):
        project = self._project()
        marker = aw.mcp_opt_in_path(project)
        marker.parent.mkdir(parents=True)
        marker.write_text("{not-json}")
        codex_before = (project / ".codex/config.toml").read_text()

        with self.assertRaisesRegex(ValueError, "Invalid MCP opt-in state"):
            aw.mcp_enable(project, "context7")

        self.assertFalse((project / ".mcp.json").exists())
        self.assertEqual((project / ".codex/config.toml").read_text(), codex_before)

    def test_disable_preserves_both_clients_when_codex_block_was_modified(self):
        project = self._project()
        aw.mcp_enable(project, "context7")
        claude_before = (project / ".mcp.json").read_text()
        marker_before = aw.mcp_opt_in_path(project).read_text()
        codex = project / ".codex/config.toml"
        codex.write_text(codex.read_text().replace("enabled = true", "enabled = false"))

        with self.assertRaisesRegex(ValueError, "modified/user-owned Codex"):
            aw.mcp_disable(project, "context7")

        self.assertEqual((project / ".mcp.json").read_text(), claude_before)
        self.assertEqual(aw.mcp_opt_in_path(project).read_text(), marker_before)
        self.assertIn("enabled = false", codex.read_text())

    def test_disable_preserves_claude_when_codex_markers_are_malformed(self):
        project = self._project()
        aw.mcp_enable(project, "serena")
        claude_before = (project / ".mcp.json").read_text()
        codex = project / ".codex/config.toml"
        start, _end = aw.codex_mcp_markers("serena")
        codex.write_text(codex.read_text().replace(start, "# missing-start"))

        with self.assertRaisesRegex(ValueError, "Malformed managed block"):
            aw.mcp_disable(project, "serena")

        self.assertEqual((project / ".mcp.json").read_text(), claude_before)
        self.assertTrue(aw.mcp_opt_in_path(project).exists())


class TestGlobalSkillIntegrity(_HomeRedirected):
    def test_legacy_owned_skill_is_upgraded_to_ratchery_marker(self):
        legacy = self.home / ".agents/skills/security-scan"
        legacy.mkdir(parents=True)
        (legacy / "MANAGED_BY_AGENT_WORKSPACE").write_text("1.0.1\n")
        (legacy / "SKILL.md").write_text("legacy managed content\n")

        aw.global_guidance()

        self.assertFalse((legacy / "MANAGED_BY_AGENT_WORKSPACE").exists())
        self.assertEqual(
            (legacy / "MANAGED_BY_RATCHERY").read_text(), aw.VERSION + "\n"
        )
        self.assertEqual(
            (legacy / "SKILL.md").read_bytes(),
            (
                aw.package_root()
                / "assets/global/skills/security-scan/SKILL.md"
            ).read_bytes(),
        )

    def test_install_refuses_user_owned_same_name_skill_without_partial_guidance_write(self):
        collision = self.home / ".agents/skills/security-scan"
        collision.mkdir(parents=True)
        (collision / "SKILL.md").write_text("user content\n")

        with self.assertRaisesRegex(ValueError, "user-owned global Skill"):
            aw.global_guidance()

        self.assertEqual((collision / "SKILL.md").read_text(), "user content\n")
        self.assertFalse((self.home / ".claude/CLAUDE.md").exists())

    def test_global_doctor_rejects_tampered_managed_skill(self):
        aw.global_guidance()
        skill = self.home / ".agents/skills/security-scan/SKILL.md"
        skill.write_text("tampered\n")
        config = self.home / ".config/ratchery/config.json"
        config.parent.mkdir(parents=True)
        vault = self.tmp / "vault"
        projects = self.tmp / "projects"
        vault.mkdir()
        projects.mkdir()
        config.write_text(
            json.dumps({"vault_path": str(vault), "projects_root": str(projects)})
        )

        stdout = io.StringIO()
        with mock.patch.object(aw, "exists", return_value=False), redirect_stdout(stdout):
            output = aw.global_doctor()

        self.assertEqual(output, 1)
        self.assertIn("Global Skill content drifted", stdout.getvalue())


class TestFrontmatterIssues(unittest.TestCase):
    def _write(self, body: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
        tmp.close()
        Path(tmp.name).write_text(body)
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_no_frontmatter_is_not_an_issue(self):
        self.assertEqual(aw.frontmatter_issues(self._write("# just a note\n")), [])

    def test_unclosed_frontmatter_flagged(self):
        issues = aw.frontmatter_issues(self._write("---\ntitle: x\n\n# body\n"))
        self.assertEqual(issues, ["frontmatter is not closed"])

    def test_missing_colon_flagged(self):
        issues = aw.frontmatter_issues(self._write("---\nthis has no colon\n---\n"))
        self.assertTrue(any("missing colon" in i for i in issues))

    def test_unquoted_colon_in_value_flagged(self):
        issues = aw.frontmatter_issues(self._write('---\ntitle: Session: something\n---\n'))
        self.assertTrue(any("quote scalar" in i for i in issues))

    def test_properly_quoted_value_not_flagged(self):
        issues = aw.frontmatter_issues(self._write('---\ntitle: "Session: something"\n---\n'))
        self.assertEqual(issues, [])

    def test_valid_frontmatter_no_issues(self):
        issues = aw.frontmatter_issues(self._write("---\ntitle: clean\nstatus: active\n---\n\n# Body\n"))
        self.assertEqual(issues, [])


class TestChooseVaultSlug(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name) / "vault"
        (self.vault / "projects").mkdir(parents=True)
        self.project_path = Path(self._tmp.name) / "repo"
        self.project_path.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _profile(self, project_id="abc12345-def6-4789-a123-456789abcdef", slug="myproj", name="myproj"):
        return {"project_id": project_id, "slug": slug, "project": name}

    def test_no_existing_home_uses_base_slug(self):
        slug = aw.choose_vault_slug(self.vault, self.project_path, self._profile())
        self.assertEqual(slug, "myproj")

    def test_reconnects_by_project_id_even_under_different_slug(self):
        home_dir = self.vault / "projects" / "renamed-slug"
        home_dir.mkdir(parents=True)
        (home_dir / "Home.md").write_text('---\nproject_id: "abc12345-def6-4789-a123-456789abcdef"\n---\n# Renamed\n')
        slug = aw.choose_vault_slug(self.vault, self.project_path, self._profile())
        self.assertEqual(slug, "renamed-slug")  # found via project_id, not the (different) base slug

    def test_project_id_in_note_body_does_not_reconnect(self):
        home_dir = self.vault / "projects" / "unrelated"
        home_dir.mkdir(parents=True)
        (home_dir / "Home.md").write_text(
            "# Unrelated\n\n"
            "```yaml\n"
            'project_id: "abc12345-def6-4789-a123-456789abcdef"\n'
            "```\n"
        )
        slug = aw.choose_vault_slug(self.vault, self.project_path, self._profile())
        self.assertEqual(slug, "myproj")

    def test_collision_with_unrelated_project_gets_suffixed(self):
        home_dir = self.vault / "projects" / "myproj"
        home_dir.mkdir(parents=True)
        (home_dir / "Home.md").write_text("# Someone else's project, no matching path or title\n")
        slug = aw.choose_vault_slug(self.vault, self.project_path, self._profile())
        self.assertEqual(slug, "myproj-abc12345")  # suffixed with the project_id's first segment, not overwritten

    def test_legacy_home_adopted_when_title_matches(self):
        home_dir = self.vault / "projects" / "myproj"
        home_dir.mkdir(parents=True)
        (home_dir / "Home.md").write_text("# myproj\nNo project_id here (pre-v8.2 layout).\n")
        slug = aw.choose_vault_slug(self.vault, self.project_path, self._profile())
        self.assertEqual(slug, "myproj")  # adopted, not suffixed, because the title affirmatively matches


class TestStaleToolsLockEntries(unittest.TestCase):
    def _write_lock(self, entries: dict) -> Path:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        json.dump(entries, tmp)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_entry_without_recheck_by_is_silent(self):
        path = self._write_lock({"context7": {"source": "https://example.com"}})
        self.assertEqual(aw.stale_tools_lock_entries(path), [])

    def test_future_recheck_by_is_silent(self):
        path = self._write_lock({"graphify": {"version_seen": "1.0", "recheck_by": "2099-01-01"}})
        self.assertEqual(aw.stale_tools_lock_entries(path), [])

    def test_past_recheck_by_is_flagged(self):
        path = self._write_lock({"graphify": {"version_seen": "1.0", "recheck_by": "2000-01-01"}})
        overdue = aw.stale_tools_lock_entries(path)
        self.assertEqual(len(overdue), 1)
        self.assertIn("graphify", overdue[0])

    def test_malformed_date_is_flagged_not_crashed(self):
        path = self._write_lock({"rtk": {"version_seen": "1.0", "recheck_by": "not-a-date"}})
        overdue = aw.stale_tools_lock_entries(path)
        self.assertEqual(len(overdue), 1)
        self.assertIn("not a valid date", overdue[0])

    def test_missing_file_is_silent_not_crashed(self):
        self.assertEqual(aw.stale_tools_lock_entries(Path("/nonexistent/tools.lock.json")), [])


if __name__ == "__main__":
    unittest.main()
