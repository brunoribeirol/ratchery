#!/usr/bin/env python3
"""Unit tests for the per-project session-log layout and migration path in
lib/agent_workspace.py (plan_session_log_migration / migrate_session_logs /
recent_session_logs). Stdlib unittest only, no deps.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import agent_workspace as aw  # noqa: E402


def write_log(path: Path, project: str | None, name: str = "log.md") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    file = path / name
    frontmatter = f'project: "{project}"\n' if project else ""
    file.write_text(f"---\ntitle: \"test\"\n{frontmatter}---\n\n# Test session\n")
    return file


class TestPlanSessionLogMigration(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        (self.vault / "projects/demo-project").mkdir(parents=True)  # existing project Home dir
        (self.vault / "projects/demo-project/Home.md").write_text("# Demo\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_matches_log_to_its_project_by_frontmatter(self):
        write_log(self.vault / "session-logs", "demo-project", "2026-01-01-demo.md")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(len(plan["moves"]), 1)
        self.assertEqual(plan["moves"][0]["to"], "projects/demo-project/session-logs/2026-01-01-demo.md")
        self.assertEqual(plan["skipped"], [])

    def test_skips_log_with_no_project_field(self):
        write_log(self.vault / "session-logs", None, "orphan.md")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertEqual(len(plan["skipped"]), 1)
        self.assertIn("no 'project' frontmatter field", plan["skipped"][0]["reason"])

    def test_skips_log_whose_project_has_no_home(self):
        write_log(self.vault / "session-logs", "ghost-project", "ghost.md")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertIn("no projects/ghost-project", plan["skipped"][0]["reason"])

    def test_skips_when_destination_already_exists(self):
        write_log(self.vault / "session-logs", "demo-project", "dup.md")
        write_log(self.vault / "projects/demo-project/session-logs", "demo-project", "dup.md")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertIn("already exists", plan["skipped"][0]["reason"])

    def test_no_global_folder_is_a_no_op(self):
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertEqual(plan["skipped"], [])

    def test_ignores_readme_in_global_folder(self):
        (self.vault / "session-logs").mkdir()
        (self.vault / "session-logs/README.md").write_text("# notes\n")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertEqual(plan["skipped"], [])

    def test_rejects_path_traversal_in_project_field(self):
        # Regression test: a `project:` value like "../../escape" must never
        # be treated as a real slug, even if that directory happens to exist
        # relative to vault/projects/.
        escape_dir = self.vault.parent / "escape"
        escape_dir.mkdir(exist_ok=True)
        write_log(self.vault / "session-logs", "../../escape", "traversal.md")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertIn("unsafe project slug", plan["skipped"][0]["reason"])

    def test_ignores_project_looking_text_outside_real_frontmatter(self):
        # Regression test: parse_frontmatter_field must only read the actual
        # YAML frontmatter block, not any "project:"-looking line anywhere in
        # the file body.
        note = self.vault / "session-logs" / "malformed.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("this file has no real frontmatter\nproject: demo-project\n")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertIn("no 'project' frontmatter field", plan["skipped"][0]["reason"])

    def test_requires_an_actual_home_md_not_just_a_directory(self):
        (self.vault / "projects/no-home-dir").mkdir(parents=True)  # directory exists, no Home.md
        write_log(self.vault / "session-logs", "no-home-dir", "orphan.md")
        plan = aw.plan_session_log_migration(self.vault)
        self.assertEqual(plan["moves"], [])
        self.assertIn("no projects/no-home-dir/Home.md found", plan["skipped"][0]["reason"])


class TestSafeVaultSlug(unittest.TestCase):
    def test_accepts_plain_slugs(self):
        for slug in ["demo-project", "demo_project", "demo.project", "a1"]:
            self.assertTrue(aw.is_safe_vault_slug(slug), slug)

    def test_rejects_traversal_and_separators(self):
        for slug in ["../escape", "..", ".", "a/b", "a\\b", "/etc/passwd", ""]:
            self.assertFalse(aw.is_safe_vault_slug(slug), slug)


class TestMigrateSessionLogsApply(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name) / "vault"
        (self.vault / "projects/demo-project").mkdir(parents=True)
        (self.vault / "projects/demo-project/Home.md").write_text("# Demo\n")
        self.home = Path(self._tmp.name) / "home"
        self.home.mkdir()
        self._orig_env = dict(os.environ)
        os.environ["XDG_STATE_HOME"] = str(self.home / ".local/state")
        os.environ["HOME"] = str(self.home)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)
        self._tmp.cleanup()

    def test_dry_run_moves_nothing(self):
        note = write_log(self.vault / "session-logs", "demo-project", "keep.md")
        aw.migrate_session_logs(self.vault, apply=False)
        self.assertTrue(note.exists())
        self.assertFalse((self.vault / "projects/demo-project/session-logs/keep.md").exists())

    def test_apply_moves_the_file_and_backs_it_up(self):
        note = write_log(self.vault / "session-logs", "demo-project", "move-me.md")
        result = aw.migrate_session_logs(self.vault, apply=True)
        self.assertFalse(note.exists())
        dest = self.vault / "projects/demo-project/session-logs/move-me.md"
        self.assertTrue(dest.exists())
        self.assertIn("backup", result)
        backup_path = Path(result["backup"])
        self.assertTrue((backup_path / "vault/session-logs/move-me.md").exists(), "original content must be backed up before the move")

    def test_apply_with_nothing_to_move_is_a_no_op(self):
        result = aw.migrate_session_logs(self.vault, apply=True)
        self.assertEqual(result["moves"], [])
        self.assertNotIn("backup", result)


class TestRecentSessionLogsAggregation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_aggregates_across_multiple_projects(self):
        write_log(self.vault / "projects/alpha/session-logs", "alpha", "a.md")
        write_log(self.vault / "projects/beta/session-logs", "beta", "b.md")
        notes = aw.recent_session_logs(self.vault)
        names = {p.name for p in notes}
        self.assertEqual(names, {"a.md", "b.md"})

    def test_ignores_old_global_flat_folder(self):
        # The old global vault/session-logs/ bucket must not leak into the
        # per-project aggregation -- that's the whole point of the migration.
        write_log(self.vault / "session-logs", "alpha", "old.md")
        notes = aw.recent_session_logs(self.vault)
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
