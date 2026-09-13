#!/usr/bin/env python3
"""Unit tests for lib/adaptive_engine.py. Stdlib unittest only, no deps.

Run: python3 tests/test_adaptive_engine.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import adaptive_engine as ae  # noqa: E402


def small_profile(**overrides):
    data = {"size": "small", "monorepo": False, "package_roots": []}
    data.update(overrides)
    return data


def large_profile(**overrides):
    data = {"size": "large", "monorepo": True, "package_roots": ["a/package.json", "b/package.json", "c/package.json"]}
    data.update(overrides)
    return data


class TestScoring(unittest.TestCase):
    def test_default_answers_are_lowest_risk(self):
        crit = ae.criticality_score(ae.DEFAULT_RISK_ANSWERS)
        self.assertEqual(crit, ae._USERS_WEIGHTS["internal"] + ae._SENSITIVITY_WEIGHTS["internal"])

    def test_complexity_score_scales_with_size(self):
        self.assertLess(
            ae.complexity_score(small_profile()),
            ae.complexity_score(large_profile()),
        )

    def test_tiny_prototype_is_t0(self):
        result = ae.compute_tier(small_profile(), ae.DEFAULT_RISK_ANSWERS)
        self.assertEqual(result["computed_tier"], "T0")

    def test_large_internal_repo_is_not_automatically_t3(self):
        # Big codebase, but zero risk flags -> should not hit the top tier
        # just from size. Complexity alone must not fake criticality.
        result = ae.compute_tier(large_profile(), ae.DEFAULT_RISK_ANSWERS)
        self.assertNotEqual(result["computed_tier"], "T3")

    def test_payments_plus_public_forces_high_tier(self):
        answers = dict(ae.DEFAULT_RISK_ANSWERS, handles_payments=True, users="public", external_exposure=True)
        result = ae.compute_tier(small_profile(), answers)
        self.assertIn(result["computed_tier"], ("T2", "T3"))

    def test_payments_alone_forces_at_least_t2(self):
        # Regression test (found via independent Codex cross-review,
        # 2026-08-30): a small, purely internal project that merely
        # handles_payments must not compute T1 just because no other risk
        # flag or complexity signal is present -- handling payment data is a
        # hard floor by itself, not only combined with external_exposure.
        answers = dict(ae.DEFAULT_RISK_ANSWERS, handles_payments=True)
        result = ae.compute_tier(small_profile(), answers)
        self.assertEqual(result["computed_tier"], "T2")
        self.assertTrue(any("handles_payments" in r for r in result["floor_reasons"]))

    def test_life_safety_always_forces_t3(self):
        answers = dict(ae.DEFAULT_RISK_ANSWERS, life_safety=True)
        result = ae.compute_tier(small_profile(), answers)
        self.assertEqual(result["computed_tier"], "T3")
        self.assertTrue(any("life_safety" in r for r in result["floor_reasons"]))

    def test_regulated_forces_at_least_t2(self):
        answers = dict(ae.DEFAULT_RISK_ANSWERS, regulated=True)
        result = ae.compute_tier(small_profile(), answers)
        self.assertIn(result["computed_tier"], ("T2", "T3"))


class TestRatchet(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_classification_has_no_ratchet(self):
        out = ae.classify(self.root, small_profile())
        self.assertEqual(out["effective_tier"], out["computed_tier"])
        self.assertFalse(out["ratcheted"])

    def test_evaluate_tier_applies_ratchet_without_writing(self):
        ae.save_risk_answers(self.root, dict(ae.DEFAULT_RISK_ANSWERS, life_safety=True))
        ae.classify(self.root, small_profile())
        ae.save_risk_answers(self.root, ae.DEFAULT_RISK_ANSWERS)
        history_before = ae.history_path(self.root).read_text()
        tier_before = ae.tier_state_path(self.root).read_text()

        out = ae.evaluate_tier(self.root, small_profile())

        self.assertEqual(out["computed_tier"], "T0")
        self.assertEqual(out["effective_tier"], "T3")
        self.assertTrue(out["ratcheted"])
        self.assertEqual(ae.history_path(self.root).read_text(), history_before)
        self.assertEqual(ae.tier_state_path(self.root).read_text(), tier_before)

    def test_downgrade_is_blocked_without_acknowledgement(self):
        ae.save_risk_answers(self.root, dict(ae.DEFAULT_RISK_ANSWERS, life_safety=True))
        first = ae.classify(self.root, small_profile())
        self.assertEqual(first["effective_tier"], "T3")

        ae.save_risk_answers(self.root, ae.DEFAULT_RISK_ANSWERS)
        second = ae.classify(self.root, small_profile())
        self.assertEqual(second["computed_tier"], "T0")
        self.assertEqual(second["effective_tier"], "T3", "rigor must not silently decrease")
        self.assertTrue(second["ratcheted"])

    def test_downgrade_with_explicit_acknowledgement_is_allowed_and_logged(self):
        ae.save_risk_answers(self.root, dict(ae.DEFAULT_RISK_ANSWERS, life_safety=True))
        ae.classify(self.root, small_profile())

        ae.save_risk_answers(self.root, ae.DEFAULT_RISK_ANSWERS)
        out = ae.classify(self.root, small_profile(), acknowledge_downgrade="feature descoped, no longer safety-critical")
        self.assertEqual(out["effective_tier"], "T0")
        self.assertTrue(out["downgrade_acknowledged"])

        history = ae.read_history(self.root)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["downgrade_reason"], "feature descoped, no longer safety-critical")

    def test_acknowledged_downgrade_persists_across_subsequent_ordinary_runs(self):
        """An acknowledged downgrade previously only applied to the run that made
        it -- the very next ordinary run (no acknowledgement) silently ratcheted
        back up to the old, higher tier still sitting in the append-only history."""
        ae.save_risk_answers(self.root, dict(ae.DEFAULT_RISK_ANSWERS, life_safety=True))
        ae.classify(self.root, small_profile())  # T3

        ae.save_risk_answers(self.root, ae.DEFAULT_RISK_ANSWERS)
        acked = ae.classify(self.root, small_profile(), acknowledge_downgrade="descoped")
        self.assertEqual(acked["effective_tier"], "T0")

        # No acknowledgement this time -- must stay at the new floor, not the old T3.
        ordinary = ae.classify(self.root, small_profile())
        self.assertEqual(ordinary["effective_tier"], "T0")
        self.assertFalse(ordinary["ratcheted"])

        # And a second ordinary run after that, to rule out a one-run fluke.
        ordinary_again = ae.classify(self.root, small_profile())
        self.assertEqual(ordinary_again["effective_tier"], "T0")
        self.assertFalse(ordinary_again["ratcheted"])

    def test_history_is_append_only_jsonl(self):
        ae.classify(self.root, small_profile())
        ae.classify(self.root, small_profile())
        raw = ae.history_path(self.root).read_text().splitlines()
        self.assertEqual(len(raw), 2)
        for line in raw:
            json.loads(line)  # must be valid JSON per line

    def test_corrupt_history_blocks_evaluation(self):
        ae.history_path(self.root).parent.mkdir(parents=True)
        ae.history_path(self.root).write_text("{not-json}\n")

        with self.assertRaisesRegex(ValueError, "Invalid tier history at line 1"):
            ae.evaluate_tier(self.root, small_profile())

    def test_acknowledged_downgrade_requires_a_rationale(self):
        ae.history_path(self.root).parent.mkdir(parents=True)
        ae.history_path(self.root).write_text(json.dumps({
            "computed_tier": "T0",
            "effective_tier": "T0",
            "ratcheted": False,
            "downgrade_acknowledged": True,
            "downgrade_reason": "",
        }) + "\n")

        with self.assertRaisesRegex(ValueError, "requires a rationale"):
            ae.read_history(self.root)

    def test_classification_uses_one_ratchet_snapshot(self):
        with mock.patch.object(ae, "highest_recorded_tier", return_value=None) as highest:
            out = ae.classify(self.root, small_profile())

        self.assertEqual(out["effective_tier"], "T0")
        highest.assert_called_once_with(self.root)

    def test_tier_state_files_are_written(self):
        ae.classify(self.root, small_profile())
        self.assertTrue(ae.tier_state_path(self.root).exists())
        self.assertTrue((self.root / ".agents/state/tier.md").exists())
        state = json.loads(ae.tier_state_path(self.root).read_text())
        self.assertIn("effective_tier", state)
        self.assertIn("requirements", state)


class TestActiveAgents(unittest.TestCase):
    REGISTRY = {
        "agents": {
            "developer": {"activation": "tier-gated", "activates_at_tier": "T0"},
            "architect": {"activation": "tier-gated", "activates_at_tier": "T2", "enforced": True},
            "qa": {"activation": "tier-gated", "activates_at_tier": "T3", "enforced": True},
            "backend-engineer": {"activation": "conditional", "trigger_capability": "api"},
            "frontend-engineer": {"activation": "conditional", "trigger_capability": "frontend"},
            "cost-optimizer": {"activation": "on-demand"},
        }
    }

    def test_t0_activates_only_the_t0_floor_agent(self):
        active = ae.resolve_active_agents(self.REGISTRY, "T0", {})
        self.assertIn("developer", active)
        self.assertNotIn("architect", active)
        self.assertNotIn("qa", active)

    def test_t2_activates_t0_and_t2_agents_but_not_t3(self):
        active = ae.resolve_active_agents(self.REGISTRY, "T2", {})
        self.assertIn("developer", active)
        self.assertIn("architect", active)
        self.assertNotIn("qa", active)

    def test_t3_activates_everything_tier_gated(self):
        active = ae.resolve_active_agents(self.REGISTRY, "T3", {})
        self.assertIn("developer", active)
        self.assertIn("architect", active)
        self.assertIn("qa", active)

    def test_conditional_agent_needs_matching_capability(self):
        active = ae.resolve_active_agents(self.REGISTRY, "T0", {"api": True, "frontend": False})
        self.assertIn("backend-engineer", active)
        self.assertNotIn("frontend-engineer", active)

    def test_on_demand_is_never_auto_activated(self):
        active = ae.resolve_active_agents(self.REGISTRY, "T3", {"api": True, "frontend": True})
        self.assertNotIn("cost-optimizer", active)

    def test_real_shipped_registry_is_well_formed_for_this_function(self):
        # Guards against the registry.json shipped in assets/ drifting out of
        # sync with what this function expects (activation/trigger_capability keys).
        import json
        registry_path = Path(__file__).resolve().parents[1] / "assets/global/skills/registry.json"
        registry = json.loads(registry_path.read_text())
        active = ae.resolve_active_agents(registry, "T3", {"api": True, "frontend": True, "data": True, "database": True, "cloud_infra": True, "ai_ml": True})
        for name in ("architect", "security-reviewer", "qa"):
            self.assertIn(name, active, f"{name} must activate by T3 per tier_requirements()")
        for name in ("security-engineer", "context-optimizer", "cost-optimizer", "architecture-auditor", "release-manager", "migration-agent", "embedded-engineer", "performance-engineer"):
            self.assertNotIn(name, active, f"{name} is on-demand and must never auto-activate")

        registered_skills = registry["skills"]["available"]
        skills_root = registry_path.parent
        on_disk = sorted(
            path.parent.name for path in skills_root.glob("*/SKILL.md")
        )
        self.assertEqual(sorted(registered_skills), on_disk)


class TestRequirements(unittest.TestCase):
    def test_t0_has_minimal_requirements(self):
        req = ae.tier_requirements("T0")
        self.assertEqual(req["required_agents"], [])
        self.assertEqual(req["spec_mode"], "none")

    def test_t3_requires_security_reviewer_and_full_spec_mode(self):
        req = ae.tier_requirements("T3")
        self.assertIn("security-reviewer", req["required_agents"])
        self.assertEqual(req["spec_mode"], "speckit-full")

    def test_every_tier_has_requirements(self):
        for tier in ae.TIERS:
            req = ae.tier_requirements(tier)
            self.assertIn("testing_bar", req)
            self.assertIn("security_bar", req)


class TestRiskAnswerValidation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.path = ae.default_answers_path(self.root)
        self.path.parent.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_malformed_existing_file_does_not_fall_back_to_low_risk_defaults(self):
        self.path.write_text("{not-json}")
        with self.assertRaisesRegex(ValueError, "Invalid risk answers"):
            ae.load_risk_answers(self.root)

    def test_unknown_enum_is_rejected(self):
        self.path.write_text(json.dumps({"users": "pubic"}))
        with self.assertRaisesRegex(ValueError, "users must be one of"):
            ae.load_risk_answers(self.root)

    def test_integer_zero_is_not_accepted_as_false(self):
        self.path.write_text(json.dumps({"life_safety": 0}))
        with self.assertRaisesRegex(ValueError, "life_safety must be true or false"):
            ae.load_risk_answers(self.root)


class TestStandingDowngrade(unittest.TestCase):
    """An acknowledged downgrade must stay visible after the run that made it.

    `highest_recorded_tier` intentionally forgets history before the last
    acknowledgement so the ratchet floor resets. That made the acknowledgement
    itself invisible to every later run: a project downgraded from T3 reported
    as an ordinary T1 forever, with nothing in `tier.md` or `doctor` to say a
    human had lowered the bar."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".agents/state").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write_history(self, *entries):
        ae.history_path(self.root).write_text(
            "".join(json.dumps(e) + "\n" for e in entries)
        )

    @staticmethod
    def entry(computed, effective, *, acknowledged=False, reason=None, timestamp="2026-03-14T10:00:00+00:00"):
        return {
            "timestamp": timestamp,
            "computed_tier": computed,
            "effective_tier": effective,
            "criticality_score": 0,
            "complexity_score": 0,
            "floor_reasons": [],
            "ratcheted": ae.TIERS.index(effective) > ae.TIERS.index(computed),
            "downgrade_acknowledged": acknowledged,
            "downgrade_reason": reason,
        }

    def test_no_history_has_no_acknowledgement(self):
        self.assertIsNone(ae.acknowledged_downgrade(self.root))
        self.assertIsNone(ae.downgrade_notice(self.root, "T1"))

    def test_history_without_acknowledgement_is_silent(self):
        self.write_history(self.entry("T2", "T2"), self.entry("T1", "T2"))
        self.assertIsNone(ae.acknowledged_downgrade(self.root))
        self.assertIsNone(ae.downgrade_notice(self.root, "T2"))

    def test_acknowledged_downgrade_is_reported_with_origin_and_reason(self):
        self.write_history(
            self.entry("T3", "T3"),
            self.entry("T1", "T1", acknowledged=True, reason="payments moved to a separate service"),
        )
        ack = ae.acknowledged_downgrade(self.root)
        self.assertEqual(ack["from_tier"], "T3")
        self.assertEqual(ack["to_tier"], "T1")
        self.assertEqual(ack["reason"], "payments moved to a separate service")

    def test_notice_still_fires_on_runs_long_after_the_acknowledgement(self):
        """The regression: ordinary runs recorded after the acknowledgement
        must not bury it."""
        self.write_history(
            self.entry("T3", "T3"),
            self.entry("T1", "T1", acknowledged=True, reason="scope reduced"),
            self.entry("T1", "T1"),
            self.entry("T1", "T1"),
        )
        notice = ae.downgrade_notice(self.root, "T1")
        self.assertIsNotNone(notice)
        self.assertIn("T3", notice)
        self.assertIn("scope reduced", notice)
        self.assertIn("2026-03-14", notice)

    def test_notice_stops_once_the_project_climbs_back(self):
        """A project reclassified back up to its old tier is no longer
        operating below its history, so the notice must go away on its own
        rather than nagging forever."""
        self.write_history(
            self.entry("T3", "T3"),
            self.entry("T1", "T1", acknowledged=True, reason="scope reduced"),
        )
        self.assertIsNone(ae.downgrade_notice(self.root, "T3"))
        # Partway back up is still below T3, so the notice must persist.
        self.assertIsNotNone(ae.downgrade_notice(self.root, "T2"))

    def test_only_the_most_recent_acknowledgement_counts(self):
        self.write_history(
            self.entry("T3", "T3"),
            self.entry("T2", "T2", acknowledged=True, reason="first"),
            self.entry("T1", "T1", acknowledged=True, reason="second"),
        )
        ack = ae.acknowledged_downgrade(self.root)
        self.assertEqual(ack["reason"], "second")
        self.assertEqual(ack["from_tier"], "T3")

    def test_tier_md_carries_the_standing_downgrade(self):
        self.write_history(
            self.entry("T3", "T3"),
            self.entry("T1", "T1", acknowledged=True, reason="scope reduced"),
        )
        ae.write_tier_state(self.root, {
            "effective_tier": "T1",
            "computed_tier": "T1",
            "tier_name": ae.TIER_NAMES["T1"],
            "criticality_score": 0,
            "complexity_score": 0,
            "floor_reasons": [],
            "ratcheted": False,
            "requirements": ae.tier_requirements("T1"),
        })
        rendered = (self.root / ".agents/state/tier.md").read_text()
        self.assertIn("previously recorded T3", rendered)
        self.assertIn("scope reduced", rendered)


if __name__ == "__main__":
    unittest.main()
