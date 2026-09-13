#!/usr/bin/env python3
"""Unit tests for lib/tool_router.py. Stdlib unittest only, no deps."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import tool_router as tr  # noqa: E402


class TestRouting(unittest.TestCase):
    def test_locate_string_always_routes_to_plain_search(self):
        # The brief's explicit requirement: a string search must never be
        # escalated to Graphify/Serena/QMD, regardless of repo size or what's
        # installed.
        for size in ("small", "medium", "large"):
            result = tr.route("locate_string", {"size": size}, {"graphify": True, "serena": True, "qmd": True})
            self.assertEqual(len(result), 1)
            self.assertIn("grep", result[0]["tool"].lower())

    def test_understand_architecture_only_suggests_graphify_if_installed_and_large(self):
        small_result = tr.route("understand_architecture", {"size": "small"}, {"graphify": True})
        self.assertFalse(any("Graphify" in r["tool"] for r in small_result))

        large_not_installed = tr.route("understand_architecture", {"size": "large"}, {"graphify": False})
        self.assertFalse(any("Graphify" in r["tool"] for r in large_not_installed))

        large_installed = tr.route("understand_architecture", {"size": "large"}, {"graphify": True})
        self.assertTrue(any("Graphify" in r["tool"] for r in large_installed))
        self.assertNotIn("Graphify", large_installed[0]["tool"])

    def test_navigate_symbols_prefers_native_first(self):
        result = tr.route("navigate_symbols", {"size": "large"}, {"serena": True})
        self.assertIn("native", result[0]["tool"].lower())

    def test_unknown_tools_are_never_assumed_installed(self):
        # Omitting the `installed` dict entirely must not silently enable
        # every optional tool.
        result = tr.route("third_party_docs", {"size": "large"}, None)
        self.assertFalse(any("Context7" in r["tool"] for r in result))

    def test_vault_retrieval_falls_back_when_qmd_absent(self):
        result = tr.route("vault_retrieval", {}, {"qmd": False})
        self.assertTrue(any("fallback" in r["tool"].lower() for r in result))

    def test_experimental_rtk_never_displaces_the_raw_default(self):
        result = tr.route("verbose_output", {}, {"rtk": True})
        self.assertIn("raw", result[0]["tool"].lower())
        self.assertTrue(any("A/B" in item["rationale"] for item in result))

    def test_unrecognized_task_kind_degrades_gracefully(self):
        result = tr.route("not-a-real-task-kind")
        self.assertEqual(len(result), 1)

    def test_recommend_for_profile_covers_every_task_kind(self):
        out = tr.recommend_for_profile({"size": "large"}, {"graphify": True, "qmd": True})
        self.assertEqual(set(out.keys()), set(tr.TASK_KINDS))
        for recs in out.values():
            self.assertGreaterEqual(len(recs), 1)


if __name__ == "__main__":
    unittest.main()
