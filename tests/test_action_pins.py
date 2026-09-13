#!/usr/bin/env python3
"""Regression tests for mutable GitHub Action and Docker references."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_action_pins", ROOT / "scripts/verify-action-pins.py"
)
assert SPEC and SPEC.loader
verify_action_pins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_action_pins)


class TestActionPins(unittest.TestCase):
    def test_mutable_docker_tag_is_rejected_but_digest_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            workflow = workflows / "ci.yml"
            workflow.write_text("steps:\n  - uses: docker://alpine:latest\n")
            self.assertEqual(
                verify_action_pins.unpinned_references(root),
                [".github/workflows/ci.yml:2: docker://alpine:latest"],
            )

            workflow.write_text(
                "steps:\n  - uses: docker://alpine@sha256:" + "a" * 64 + "\n"
            )
            self.assertEqual(verify_action_pins.unpinned_references(root), [])


if __name__ == "__main__":
    unittest.main()
