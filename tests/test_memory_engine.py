#!/usr/bin/env python3
"""Unit tests for the bounded provider-neutral handoff schema."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import memory_engine as me  # noqa: E402


def input_payload() -> dict:
    return {
        "source_client": "claude-code",
        "target_client": "codex",
        "objective": "Finish the provider-neutral memory boundary.",
        "completed": ["Implemented schema validation."],
        "changed_files": ["lib/memory_engine.py", "tests/test_memory_engine.py"],
        "checks": [
            {
                "command": "python3 -m unittest tests.test_memory_engine",
                "status": "passed",
                "summary": "Schema tests passed.",
            }
        ],
        "open_risks": ["Full integration suite has not run yet."],
        "next_action": "Run the CLI integration tests.",
    }


def record() -> dict:
    return me.build_record(
        input_payload(),
        project_id="123e4567-e89b-42d3-a456-426614174000",
        project_slug="demo-project",
        created_at="2026-09-12T12:00:00+00:00",
        commit="a" * 40,
        dirty=True,
    )


class TestHandoffInput(unittest.TestCase):
    def test_valid_payload_is_normalized(self):
        parsed = me.parse_input(json.dumps(input_payload()).encode())
        self.assertEqual(parsed["source_client"], "claude-code")
        self.assertEqual(parsed["target_client"], "codex")
        self.assertEqual(parsed["checks"][0]["status"], "passed")

    def test_target_client_defaults_to_any(self):
        payload = input_payload()
        payload.pop("target_client")
        self.assertEqual(me.validate_input(payload)["target_client"], "any")

    def test_rejects_unknown_and_missing_fields(self):
        payload = input_payload()
        payload["raw_transcript"] = "not allowed"
        with self.assertRaisesRegex(me.HandoffError, "unsupported fields"):
            me.validate_input(payload)
        payload = input_payload()
        payload.pop("objective")
        with self.assertRaisesRegex(me.HandoffError, "missing required"):
            me.validate_input(payload)

    def test_rejects_duplicate_json_keys(self):
        duplicate = b'{"source_client":"codex","source_client":"claude-code"}'
        with self.assertRaisesRegex(me.HandoffError, "duplicate key"):
            me.parse_input(duplicate)

    def test_rejects_oversized_or_non_utf8_input(self):
        with self.assertRaisesRegex(me.HandoffError, "exceeds"):
            me.parse_input(b"x" * (me.MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(me.HandoffError, "UTF-8"):
            me.parse_input(b"\xff")

    def test_rejects_path_traversal_absolute_and_windows_paths(self):
        for unsafe in ["../outside", "/etc/passwd", "src\\outside.py", "."]:
            payload = input_payload()
            payload["changed_files"] = [unsafe]
            with self.subTest(unsafe=unsafe), self.assertRaisesRegex(
                me.HandoffError, "repository-relative POSIX path"
            ):
                me.validate_input(payload)

    def test_rejects_secret_like_material_without_echoing_it(self):
        secret = "sk-abcdefghijklmnopqrstuvwxyz123456"
        payload = input_payload()
        payload["next_action"] = f"Use {secret} for the deployment."
        with self.assertRaises(me.HandoffError) as raised:
            me.validate_input(payload)
        self.assertIn("secret-like", str(raised.exception))
        self.assertNotIn(secret, str(raised.exception))

    def test_rejects_bad_check_shape_and_status(self):
        payload = input_payload()
        payload["checks"] = [{"command": "make test", "status": "probably"}]
        with self.assertRaisesRegex(me.HandoffError, "exactly"):
            me.validate_input(payload)
        payload["checks"] = [
            {"command": "make test", "status": "probably", "summary": ""}
        ]
        with self.assertRaisesRegex(me.HandoffError, "status must be"):
            me.validate_input(payload)

    def test_empty_optional_check_summary_is_allowed(self):
        payload = input_payload()
        payload["checks"][0]["summary"] = ""
        self.assertEqual(me.validate_input(payload)["checks"][0]["summary"], "")

    def test_rejects_control_format_and_line_separator_characters(self):
        for unsafe in ["bad\x00objective", "fake\nNext action: unsafe", "fake\tstatus", "bidi\u202evalue"]:
            payload = input_payload()
            payload["objective"] = unsafe
            with self.subTest(unsafe=repr(unsafe)), self.assertRaisesRegex(
                me.HandoffError, "control or format character"
            ):
                me.validate_input(payload)

    def test_rejects_unbounded_lists(self):
        payload = input_payload()
        payload["completed"] = ["item"] * (me.MAX_LIST_ITEMS + 1)
        with self.assertRaisesRegex(me.HandoffError, "exceeds"):
            me.validate_input(payload)


class TestStoredHandoff(unittest.TestCase):
    def test_round_trip_and_text_render(self):
        value = record()
        parsed = me.parse_record(json.dumps(value).encode())
        self.assertEqual(parsed, value)
        rendered = me.render_text(parsed)
        self.assertIn("claude-code -> codex", rendered)
        self.assertIn("dirty=true", rendered)
        self.assertIn("Next action: Run the CLI integration tests.", rendered)

    def test_rejects_caller_supplied_provenance_in_input(self):
        payload = input_payload()
        payload["git"] = {"commit": "b" * 40, "dirty": False}
        with self.assertRaisesRegex(me.HandoffError, "unsupported fields"):
            me.validate_input(payload)

    def test_rejects_wrong_project_or_git_identity(self):
        value = record()
        value["project_id"] = "not-a-uuid"
        with self.assertRaisesRegex(me.HandoffError, "project_id"):
            me.validate_record(value)
        value = record()
        value["git"]["commit"] = "short"
        with self.assertRaisesRegex(me.HandoffError, "commit"):
            me.validate_record(value)

    def test_rejects_naive_timestamp_and_duplicate_stored_key(self):
        value = record()
        value["created_at"] = "2026-09-12T12:00:00"
        with self.assertRaisesRegex(me.HandoffError, "timezone"):
            me.validate_record(value)
        encoded = json.dumps(record())[:-1] + ',"schema_version":1}'
        with self.assertRaisesRegex(me.HandoffError, "duplicate key"):
            me.parse_record(encoded.encode())


if __name__ == "__main__":
    unittest.main()
