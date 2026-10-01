#!/usr/bin/env python3
"""Contracts for capability provenance, routing, workflows, and radar."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import capability_system as cs  # noqa: E402

SCRIPT = LIB / "agent_workspace.py"


class CapabilitySystemTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=45,
        )

    def test_shipped_capability_catalogs_validate(self) -> None:
        for kind, expected_count in (("skill", 16), ("agent", 24)):
            with self.subTest(kind=kind):
                result = cs.validate_capabilities(ROOT, kind)
                self.assertTrue(result["ok"], result["errors"])
                self.assertEqual(result["counts"][kind], expected_count)

    def test_resolved_contract_includes_provenance_and_client_parity(self) -> None:
        skill = cs.capability_detail(ROOT, "skill", "security-hardening")
        self.assertRegex(skill["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(set(skill["clients"]), {"claude", "codex"})
        self.assertEqual(skill["permission_ceiling"], "security-gated")
        self.assertIn("SKILL.md", skill["resources"][0])

        agent = cs.capability_detail(ROOT, "agent", "security-reviewer")
        self.assertEqual(agent["client_contracts"]["claude"]["permission_mode"], "plan")
        self.assertEqual(
            agent["client_contracts"]["codex"]["default_permissions"],
            ":read-only",
        )

    def test_malformed_catalog_validation_fails_closed_without_traceback(self) -> None:
        with mock.patch.object(
            cs, "_registry", side_effect=cs.CapabilityError("malformed registry")
        ):
            result = cs.validate_capabilities(ROOT, "skill")
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"], {})
        self.assertEqual(result["errors"], ["malformed registry"])

    def test_behavior_evals_cover_every_capability(self) -> None:
        for kind in ("skill", "agent"):
            with self.subTest(kind=kind):
                result = cs.run_capability_evals(ROOT, kind)
                self.assertTrue(result["passed"], result["results"])
                selected = {
                    name
                    for case in result["results"]
                    for name in case["selected"]
                }
                self.assertTrue(set(cs.capability_names(ROOT, kind)) <= selected)

    def test_negative_routing_cases_fail_closed(self) -> None:
        typo = cs.recommend_capabilities(
            ROOT, "skill", "Fix a typo in a single file edit."
        )
        self.assertNotIn("architecture-map", [item["name"] for item in typo])

        scan_only = cs.recommend_capabilities(
            ROOT, "skill", "Perform a security review only and scan only."
        )
        self.assertNotIn("security-hardening", [item["name"] for item in scan_only])

    def test_workflows_validate_and_recommend_by_outcome(self) -> None:
        validation = cs.validate_workflows(ROOT)
        self.assertTrue(validation["ok"], validation["errors"])
        self.assertEqual(validation["count"], 7)

        matches = cs.recommend_workflows(
            ROOT, "Quero implementar funcionalidade com segurança"
        )
        self.assertEqual(matches[0]["id"], "implement-feature")

    def test_security_hardening_has_findings_gate_and_independent_review(self) -> None:
        workflow = cs.workflow_detail(ROOT, "security-hardening")
        step_ids = [step["id"] for step in workflow["steps"]]
        self.assertLess(step_ids.index("approve-findings"), step_ids.index("remediate"))
        approval = next(
            step for step in workflow["steps"] if step["id"] == "approve-findings"
        )
        self.assertEqual(approval["type"], "approval")
        self.assertIn("agent:security-reviewer", workflow["steps"][-1]["capabilities"])
        self.assertEqual(
            set(workflow["finding_contract"]["required"]),
            {
                "id",
                "severity",
                "asset",
                "evidence",
                "scenario",
                "remediation",
                "closure_test",
                "status",
            },
        )

    def test_radar_is_offline_valid_and_date_driven(self) -> None:
        current = cs.validate_radar(ROOT, dt.date(2026, 9, 28))
        self.assertTrue(current["ok"], current["errors"])
        self.assertEqual(current["stale"], [])
        summary = cs.radar_summary(ROOT, dt.date(2026, 9, 28))
        self.assertEqual(summary["network_access"], "none")
        self.assertEqual(summary["count"], 11)

        future = cs.validate_radar(ROOT, dt.date(2027, 4, 1))
        self.assertEqual(len(future["stale"]), 11)

    def test_cli_json_contracts(self) -> None:
        commands = (
            ("skills", "show", "security-hardening", "--json"),
            ("agents", "show", "security-reviewer", "--json"),
            ("workflows", "recommend", "--goal", "security audit", "--json"),
            ("radar", "status", "--json"),
        )
        for command in commands:
            with self.subTest(command=command):
                result = self.run_cli(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsNotNone(json.loads(result.stdout))

    def test_validation_commands_are_read_only(self) -> None:
        tracked = [
            ROOT / "assets/global/skills/registry.json",
            ROOT / "assets/global/evals/capability-routing.json",
            ROOT / "assets/global/workflows/registry.json",
            ROOT / "assets/global/technology-radar.json",
        ]
        before = {path: path.read_bytes() for path in tracked}
        for command in (
            ("skills", "validate"),
            ("agents", "validate"),
            ("workflows", "validate"),
            ("radar", "validate"),
        ):
            result = self.run_cli(*command)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({path: path.read_bytes() for path in tracked}, before)


if __name__ == "__main__":
    unittest.main()
