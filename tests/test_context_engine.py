#!/usr/bin/env python3
"""Unit tests for lib/context_engine.py. Stdlib unittest only, no deps."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import context_engine as ce  # noqa: E402


class TestClaudeignore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_generates_file_with_baseline_patterns(self):
        path = ce.generate_claudeignore(self.root)
        self.assertTrue(path.exists())
        text = path.read_text()
        self.assertIn("node_modules/", text)
        self.assertIn(".env", text)
        self.assertIn("!.env.example", text, "must not blanket-exclude the safe example file")

    def test_preserves_custom_tail_on_regeneration(self):
        ce.generate_claudeignore(self.root)
        path = ce.claudeignore_path(self.root)
        with path.open("a") as fh:
            fh.write("\nmy-custom-generated-dir/\n")
        ce.generate_claudeignore(self.root)
        text = path.read_text()
        self.assertIn("my-custom-generated-dir/", text)
        self.assertIn("node_modules/", text)

    def test_baseline_is_idempotent(self):
        ce.generate_claudeignore(self.root)
        first = ce.claudeignore_path(self.root).read_text()
        ce.generate_claudeignore(self.root)
        second = ce.claudeignore_path(self.root).read_text()
        self.assertEqual(first, second)


class TestSteeringFiles(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.profile = {"size": "medium", "monorepo": False, "package_roots": [], "languages": {".py": 10}, "capabilities": {"api": True, "frontend": False}, "source_files": 10, "source_lines": 500}

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_three_files(self):
        written = ce.generate_steering_files(self.root, self.profile)
        names = {p.name for p in written}
        self.assertEqual(names, {"product.md", "structure.md", "tech.md"})
        for p in written:
            self.assertTrue(p.exists())

    def test_never_overwrites_human_edited_content(self):
        ce.generate_steering_files(self.root, self.profile)
        product = ce.steering_dir(self.root) / "product.md"
        product.write_text("# Product\n\nHUMAN-WROTE-THIS\n")
        ce.generate_steering_files(self.root, self.profile)
        self.assertIn("HUMAN-WROTE-THIS", product.read_text())

    def test_steering_points_to_refreshable_profile_instead_of_freezing_counts(self):
        ce.generate_steering_files(self.root, self.profile)
        text = (ce.steering_dir(self.root) / "tech.md").read_text()
        structure = (ce.steering_dir(self.root) / "structure.md").read_text()
        self.assertIn(".agents/state/project-profile.md", text)
        self.assertIn(".agents/state/project-profile.md", structure)
        self.assertNotIn("`.py`: 10 files", text)
        self.assertNotIn("10 source files", structure)

    def test_import_block_references_all_three_files(self):
        block = ce.steering_import_block()
        for name in ("product.md", "structure.md", "tech.md"):
            self.assertIn(name, block)


if __name__ == "__main__":
    unittest.main()
