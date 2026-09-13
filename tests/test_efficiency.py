#!/usr/bin/env python3
"""Tests for aggregate usage parsing and benchmark CLI behavior."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import agent_workspace as aw  # noqa: E402
import efficiency as ef  # noqa: E402


def ccusage_report(*, cost: float = 2.5, multiplier: int = 1) -> str:
    return json.dumps(
        {
            "daily": [{"sessionId": "must-not-be-persisted"}],
            "totals": {
                "inputTokens": 100 * multiplier,
                "outputTokens": 20 * multiplier,
                "cacheCreationTokens": 5 * multiplier,
                "cacheReadTokens": 50 * multiplier,
                "totalTokens": 175 * multiplier,
                "totalCost": cost,
                "modelBreakdowns": [{"model": "private-model-detail"}],
            },
        }
    )


def snapshot(
    name: str,
    *,
    cost: float,
    tokens: int,
    successful: int = 2,
    configuration: str | None = None,
    configuration_digest: str = "b" * 64,
) -> dict:
    metrics = {
        "input_tokens": tokens,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "total_tokens": tokens,
        "estimated_cost_usd": cost,
    }
    return ef.make_snapshot(
        name=name,
        metrics=metrics,
        filters={
            "source": "codex",
            "project": ef.project_fingerprint("demo"),
            "period": "daily",
            "selection": "date-window",
            "since": "20260901",
            "until": "20260901",
            "offline": True,
        },
        provenance={
            "git_commit": "a" * 40,
            "task_set": "core-suite-v1",
            "model": "gpt-5.6-codex",
            "client_version": "codex-0.153.3",
            "environment_id": "macos-arm64-sandboxed",
            "configuration": configuration or name,
            "configuration_digest": configuration_digest,
        },
        attempted_tasks=2,
        successful_tasks=successful,
        captured_at="2026-09-08T00:00:00+00:00",
        ccusage_version="ccusage 99.0.0",
    )


class TestCcusageParsing(unittest.TestCase):
    def test_extracts_only_aggregate_totals(self):
        metrics = ef.parse_ccusage_json(ccusage_report())
        self.assertEqual(metrics["total_tokens"], 175)
        self.assertEqual(metrics["estimated_cost_usd"], 2.5)
        self.assertNotIn("daily", metrics)
        self.assertNotIn("modelBreakdowns", metrics)

    def test_legacy_rows_are_summed_without_being_returned(self):
        rows = [
            {
                "inputTokens": 2,
                "outputTokens": 3,
                "cacheCreationTokens": 4,
                "cacheReadTokens": 5,
                "totalCost": 0.1,
                "sessionId": "private",
            },
            {
                "inputTokens": 7,
                "outputTokens": 11,
                "cacheCreationTokens": 13,
                "cacheReadTokens": 17,
                "totalCost": 0.2,
            },
        ]
        metrics = ef.parse_ccusage_json(json.dumps(rows))
        self.assertEqual(metrics["total_tokens"], 62)
        self.assertAlmostEqual(metrics["estimated_cost_usd"], 0.3)

    def test_exact_session_entries_are_aggregated_without_session_id(self):
        report = {
            "sessionId": "private-session-id",
            "totalCost": 0.5,
            "totalTokens": 10,
            "entries": [
                {
                    "inputTokens": 4,
                    "outputTokens": 2,
                    "cacheCreationTokens": 1,
                    "cacheReadTokens": 3,
                    "costUSD": 0.5,
                    "model": "private-model",
                }
            ],
        }
        metrics = ef.parse_ccusage_json(json.dumps(report))
        self.assertEqual(metrics["total_tokens"], 10)
        self.assertNotIn("sessionId", metrics)

    def test_rejects_empty_malformed_negative_and_inconsistent_reports(self):
        invalid = [
            "not-json",
            "[]",
            "{}",
            ccusage_report().replace('"totalCost": 2.5', '"totalCost": NaN'),
            ccusage_report().replace('"inputTokens": 100', '"inputTokens": -1'),
            ccusage_report().replace('"totalTokens": 175', '"totalTokens": 999'),
        ]
        for report in invalid:
            with self.subTest(report=report[:30]), self.assertRaises(ef.BenchmarkError):
                ef.parse_ccusage_json(report)


class TestBenchmarkSnapshots(unittest.TestCase):
    def test_cost_per_success_and_zero_success_are_explicit(self):
        successful = snapshot("ok", cost=4.0, tokens=10, successful=2)
        failed = snapshot("failed", cost=4.0, tokens=10, successful=0)
        self.assertEqual(successful["metrics"]["cost_per_successful_task"], 2.0)
        self.assertIsNone(failed["metrics"]["cost_per_successful_task"])

    def test_compare_reports_deltas_and_handles_zero_baseline(self):
        compared = ef._delta(0, 100)
        self.assertEqual(compared["absolute_delta"], 100)
        self.assertIsNone(compared["percent_delta"])

    def test_compare_never_emits_non_standard_infinite_percentages(self):
        baseline = snapshot("baseline", cost=1e-300, tokens=1)
        candidate = snapshot("candidate", cost=1e300, tokens=2)
        compared = ef.compare_snapshots(baseline, candidate)
        self.assertIsNone(
            compared["metrics"]["estimated_cost_usd"]["percent_delta"]
        )
        json.dumps(compared, allow_nan=False)

    def test_compare_rejects_different_source_or_project_scope(self):
        baseline = snapshot("baseline", cost=1.0, tokens=10)
        candidate = snapshot("candidate", cost=1.0, tokens=10)
        candidate["filters"]["project"] = ef.project_fingerprint("other")
        with self.assertRaisesRegex(ef.BenchmarkError, "scopes differ"):
            ef.compare_snapshots(baseline, candidate)

    def test_compare_rejects_different_tool_version_attempt_count_or_window_size(self):
        baseline = snapshot("baseline", cost=1.0, tokens=10)

        version_changed = snapshot("candidate", cost=1.0, tokens=10)
        version_changed["ccusage_version"] = "ccusage 100.0.0"
        with self.assertRaisesRegex(ef.BenchmarkError, "versions differ"):
            ef.compare_snapshots(baseline, version_changed)

        attempts_changed = snapshot("candidate", cost=1.0, tokens=10)
        attempts_changed["metrics"]["attempted_tasks"] = 3
        attempts_changed["metrics"]["successful_tasks"] = 2
        attempts_changed["metrics"]["success_rate"] = 2 / 3
        with self.assertRaisesRegex(ef.BenchmarkError, "task counts differ"):
            ef.compare_snapshots(baseline, attempts_changed)

        duration_changed = snapshot("candidate", cost=1.0, tokens=10)
        duration_changed["filters"]["until"] = "20260902"
        with self.assertRaisesRegex(ef.BenchmarkError, "durations differ"):
            ef.compare_snapshots(baseline, duration_changed)

    def test_compare_rejects_different_reproducibility_provenance(self):
        baseline = snapshot("baseline", cost=1.0, tokens=10)
        candidate = snapshot("candidate", cost=1.0, tokens=10)
        candidate["provenance"]["model"] = "different-model"
        with self.assertRaisesRegex(ef.BenchmarkError, "provenance differs for: model"):
            ef.compare_snapshots(baseline, candidate)

    def test_rejects_unsafe_names_and_impossible_task_counts(self):
        for name in ("../escape", "--option", "a" * 65):
            with self.subTest(name=name), self.assertRaises(ef.BenchmarkError):
                ef.validate_benchmark_name(name)
        with self.assertRaisesRegex(ef.BenchmarkError, "cannot exceed"):
            ef.make_snapshot(
                name="bad-counts",
                metrics={
                    "input_tokens": 1,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_tokens": 1,
                    "estimated_cost_usd": 0.1,
                },
                filters={
                    "source": "all",
                    "project": None,
                    "period": "daily",
                    "selection": "date-window",
                    "since": "20260901",
                    "until": "20260901",
                    "offline": True,
                },
                provenance={
                    "git_commit": "a" * 40,
                    "task_set": "core-suite-v1",
                    "model": "gpt-5.6-codex",
                    "client_version": "codex-0.153.3",
                    "environment_id": "macos-arm64-sandboxed",
                    "configuration": "native",
                    "configuration_digest": "b" * 64,
                },
                attempted_tasks=1,
                successful_tasks=2,
                captured_at="now",
                ccusage_version="ccusage 99.0.0",
            )
        with self.assertRaisesRegex(ef.BenchmarkError, "measured token usage"):
            snapshot("empty-window", cost=0.0, tokens=0)

    def test_rejects_untrusted_filter_and_metadata_content(self):
        valid = snapshot("valid", cost=1.0, tokens=10)
        invalid_values = []
        with_extra_filter = json.loads(json.dumps(valid))
        with_extra_filter["filters"]["raw_rows"] = ["private"]
        invalid_values.append(with_extra_filter)
        with_terminal_control = json.loads(json.dumps(valid))
        with_terminal_control["filters"]["project"] = "safe\nforged output"
        invalid_values.append(with_terminal_control)
        without_offline_boundary = json.loads(json.dumps(valid))
        without_offline_boundary["filters"]["offline"] = False
        invalid_values.append(without_offline_boundary)
        with_bad_version = json.loads(json.dumps(valid))
        with_bad_version["ccusage_version"] = "ccusage\x1b[2J"
        invalid_values.append(with_bad_version)
        with_path_label = json.loads(json.dumps(valid))
        with_path_label["provenance"]["environment_id"] = "Users/alice/private"
        invalid_values.append(with_path_label)

        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ef.BenchmarkError):
                ef.validate_snapshot(value)

    def test_task_set_validation_is_deterministic_and_rejects_unsafe_contracts(self):
        suite_path = Path(__file__).resolve().parents[1] / "benchmarks/core-suite-v1.json"
        suite = json.loads(suite_path.read_text())
        checked = ef.validate_task_set(suite)
        self.assertEqual(len(checked["tasks"]), 6)
        self.assertEqual(ef.task_set_digest(suite), ef.task_set_digest(checked))
        tasks = {task["id"]: task for task in checked["tasks"]}
        for task_id in ("T1-onboarding", "T5-decision-retrieval", "T6-log-analysis"):
            self.assertIn('test -z "$(git status --porcelain', tasks[task_id]["verification"][0])
        for task_id in ("T2-bug-fix", "T3-feature", "T4-test-repair"):
            self.assertTrue(
                any("tests/test_app.py" in command for command in tasks[task_id]["verification"])
            )

        traversal = json.loads(json.dumps(suite))
        traversal["protocol"]["fixture"] = "../private"
        with self.assertRaisesRegex(ef.BenchmarkError, "safe repository-relative"):
            ef.validate_task_set(traversal)

        duplicate = json.loads(json.dumps(suite))
        duplicate["tasks"][1]["id"] = duplicate["tasks"][0]["id"]
        with self.assertRaisesRegex(ef.BenchmarkError, "duplicate task id"):
            ef.validate_task_set(duplicate)

    def test_bundled_task_set_validation_failure_is_never_treated_as_a_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "broken.json"
            for payload in ({"id": "broken"}, {"title": "missing id"}):
                broken.write_text(json.dumps(payload))
                with (
                    self.subTest(payload=payload),
                    mock.patch.object(aw, "_shipped_task_set_paths", return_value=[broken]),
                    self.assertRaises(ef.BenchmarkError),
                ):
                    aw.benchmark_task_set_identity("broken")

    def test_repeated_report_requires_samples_and_preserves_quality_floor(self):
        baseline = [
            snapshot(f"base-{index}", cost=3.0 + index / 10, tokens=300 + index, configuration="native")
            for index in range(3)
        ]
        candidate = [
            snapshot(f"candidate-{index}", cost=2.0 + index / 10, tokens=200 + index, configuration="rtk")
            for index in range(3)
        ]

        report = ef.report_snapshots(baseline, candidate)

        self.assertEqual(report["result"]["status"], "manual-review-candidate")
        self.assertFalse(report["result"]["automated_adoption_decision"])
        self.assertTrue(report["samples"]["enough"])
        self.assertEqual(report["metrics"]["total_tokens"]["baseline"]["median"], 301)

        one_sample = ef.report_snapshots(baseline[:1], candidate[:1])
        self.assertEqual(one_sample["result"]["status"], "insufficient-samples")

        regression = [
            snapshot(f"bad-{index}", cost=1.0, tokens=100, successful=1, configuration="bad")
            for index in range(3)
        ]
        quality_report = ef.report_snapshots(baseline, regression)
        self.assertEqual(quality_report["result"]["status"], "quality-regression")

    def test_repeated_report_rejects_mixed_arm_configuration(self):
        baseline = [snapshot("b1", cost=1, tokens=10, configuration="native")]
        baseline.append(snapshot("b2", cost=1, tokens=10, configuration="other"))
        candidate = [snapshot("c1", cost=1, tokens=10, configuration="rtk")]
        with self.assertRaisesRegex(ef.BenchmarkError, "different configurations"):
            ef.report_snapshots(baseline, candidate)

    def test_repeated_report_rejects_configuration_drift_within_an_arm(self):
        baseline = [
            snapshot(
                f"b{index}",
                cost=2,
                tokens=20,
                configuration="native",
                configuration_digest="a" * 64,
            )
            for index in range(3)
        ]
        candidate = [
            snapshot(
                f"c{index}",
                cost=1,
                tokens=10,
                configuration="rtk",
                configuration_digest=("c" if index == 2 else "b") * 64,
            )
            for index in range(3)
        ]
        with self.assertRaisesRegex(ef.BenchmarkError, "configuration digests"):
            ef.report_snapshots(baseline, candidate)

    def test_repeated_report_rejects_duplicate_trials(self):
        baseline = snapshot("baseline", cost=2, tokens=20, configuration="native")
        candidate = snapshot("candidate", cost=1, tokens=10, configuration="rtk")
        with self.assertRaisesRegex(ef.BenchmarkError, "distinct trials"):
            ef.report_snapshots([baseline, baseline, baseline], [candidate])

    def test_budget_evaluation_is_explicit_and_never_claims_billing_accuracy(self):
        result = ef.evaluate_budget(
            {"total_tokens": 2100, "estimated_cost_usd": 1.25},
            max_cost_usd=2.0,
            max_tokens=2000,
            spike_baseline_tokens=200,
            spike_multiplier=10,
        )
        self.assertEqual(result["status"], "exceeded")
        self.assertTrue(result["estimated"])
        self.assertEqual(
            {item["kind"]: item["status"] for item in result["checks"]},
            {"cost": "ok", "tokens": "exceeded", "token-spike": "warning"},
        )
        with self.assertRaisesRegex(ef.BenchmarkError, "at least one"):
            ef.evaluate_budget(
                {"total_tokens": 1, "estimated_cost_usd": 0},
                max_cost_usd=None,
                max_tokens=None,
                spike_baseline_tokens=None,
                spike_multiplier=10,
            )


class TestBenchmarkCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.root = self.base / "project"
        (self.root / ".agents/state").mkdir(parents=True)
        (self.root / ".agents/state/project-id").write_text(
            "12345678-1234-4234-8234-123456789abc\n"
        )
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "add", ".agents/state/project-id"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Benchmark Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "-c",
                "commit.gpgSign=false",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            check=True,
        )
        self._xdg_state = mock.patch.dict(
            os.environ, {"XDG_STATE_HOME": str(self.base / "state")}
        )
        self._xdg_state.start()

    def tearDown(self):
        self._xdg_state.stop()
        self._tmp.cleanup()

    def test_ccusage_argv_is_validated_and_never_shell_text(self):
        command = aw.ccusage_command(
            period="daily",
            source="codex",
            since="20260901",
            until="20260902",
            project="my project; touch nope",
            session_id=None,
            json_output=True,
            offline=True,
        )
        self.assertEqual(command[0:3], ["ccusage", "codex", "daily"])
        self.assertIn("my project; touch nope", command)
        self.assertNotIn("shell=True", command)
        with self.assertRaises(ef.BenchmarkError):
            aw.ccusage_command(period="daily", source="--bad")
        with self.assertRaises(ef.BenchmarkError):
            aw.ccusage_command(period="daily", since="20260230")
        with self.assertRaises(ef.BenchmarkError):
            aw.ccusage_command(period="daily", since="20260902", until="20260901")

    def test_usage_json_normalizes_machine_readable_stdout(self):
        stdout = io.StringIO()
        completed = subprocess.CompletedProcess(
            ["ccusage"], 0, stdout='{"totals":{"totalTokens":1}}', stderr=""
        )
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "run", return_value=completed) as runner,
            redirect_stdout(stdout),
        ):
            rc = aw.usage(
                period="daily",
                source="codex",
                since=None,
                until=None,
                project=None,
                session_id=None,
                json_output=True,
                offline=True,
            )
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"totals": {"totalTokens": 1}})
        command = runner.call_args.args[0]
        self.assertEqual(command, ["ccusage", "codex", "daily", "--json", "--offline"])

    def test_usage_json_rejects_stray_stdout_instead_of_leaking_invalid_json(self):
        completed = subprocess.CompletedProcess(
            ["ccusage"], 0, stdout='NOTICE\n{"totals":{}}', stderr=""
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "run", return_value=completed),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            rc = aw.usage(
                period="daily",
                source="codex",
                since=None,
                until=None,
                project=None,
                session_id=None,
                json_output=True,
                offline=True,
            )
        self.assertEqual(rc, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("invalid JSON", stderr.getvalue())

    def test_capture_persists_aggregates_not_raw_rows(self):
        result = subprocess.CompletedProcess(
            ["ccusage"], 0, stdout=ccusage_report(), stderr=""
        )
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "git_root", return_value=self.root),
            mock.patch.object(aw, "run", return_value=result),
            mock.patch.object(aw, "command_version", return_value="ccusage 99.0.0"),
            redirect_stdout(io.StringIO()),
        ):
            rc = aw.benchmark_capture(
                path=self.root,
                name="candidate",
                source="codex",
                since="20260901",
                until="20260901",
                project="demo",
                session_id=None,
                task_set="core-suite-v1",
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="candidate",
                attempted_tasks=3,
                successful_tasks=2,
                replace=False,
            )
        self.assertEqual(rc, 0)
        stored_text = aw.benchmark_snapshot_path(
            self.root, "candidate", create_dir=False
        ).read_text()
        stored = json.loads(stored_text)
        self.assertEqual(stored["metrics"]["total_tokens"], 175)
        self.assertEqual(stored["filters"]["project"], ef.project_fingerprint("demo"))
        self.assertRegex(
            stored["provenance"]["task_set"],
            r"^core-suite-v1@sha256:[0-9a-f]{64}$",
        )
        self.assertRegex(stored["provenance"]["configuration_digest"], r"^[0-9a-f]{64}$")
        self.assertNotIn("demo", stored_text)
        self.assertNotIn("must-not-be-persisted", stored_text)
        self.assertNotIn("private-model-detail", stored_text)

    def test_capture_does_not_overwrite_without_explicit_replace(self):
        directory = aw.benchmark_directory(self.root, create=True)
        target = directory / "existing.json"
        target.write_text("keep me")
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "git_root", return_value=self.root),
            mock.patch.object(aw, "run") as runner,
            redirect_stderr(stderr),
        ):
            rc = aw.benchmark_capture(
                path=self.root,
                name="existing",
                source=None,
                since="20260901",
                until="20260901",
                project=None,
                session_id=None,
                task_set="core-suite-v1",
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="native",
                attempted_tasks=1,
                successful_tasks=1,
                replace=False,
            )
        self.assertEqual(rc, 2)
        self.assertEqual(target.read_text(), "keep me")
        runner.assert_not_called()

    def test_capture_reports_ccusage_failure_without_writing_snapshot(self):
        result = subprocess.CompletedProcess(
            ["ccusage"], 3, stdout="", stderr="unsupported source"
        )
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "git_root", return_value=self.root),
            mock.patch.object(aw, "run", return_value=result),
            redirect_stderr(stderr),
        ):
            rc = aw.benchmark_capture(
                path=self.root,
                name="failed",
                source="codex",
                since="20260901",
                until="20260901",
                project=None,
                session_id=None,
                task_set="core-suite-v1",
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="native",
                attempted_tasks=1,
                successful_tasks=0,
                replace=False,
            )
        self.assertEqual(rc, 3)
        self.assertIn("ccusage failed with exit 3", stderr.getvalue())
        self.assertNotIn("unsupported source", stderr.getvalue())
        self.assertFalse((aw.state_root() / "benchmarks").exists())

    def test_capture_handles_ccusage_timeout_without_traceback(self):
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "git_root", return_value=self.root),
            mock.patch.object(aw, "run", side_effect=subprocess.TimeoutExpired(["ccusage"], 120)),
            redirect_stderr(stderr),
        ):
            rc = aw.benchmark_capture(
                path=self.root,
                name="timeout",
                source="codex",
                since="20260901",
                until="20260901",
                project=None,
                session_id=None,
                task_set="core-suite-v1",
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="native",
                attempted_tasks=1,
                successful_tasks=0,
                replace=False,
            )
        self.assertEqual(rc, 1)
        self.assertIn("timed out", stderr.getvalue())

    def test_session_capture_does_not_persist_session_id(self):
        session_id = "abc:def-123"
        session_report = json.dumps(
            {
                "sessionId": session_id,
                "totalCost": 0.1,
                "totalTokens": 3,
                "entries": [
                    {
                        "inputTokens": 1,
                        "outputTokens": 2,
                        "cacheCreationTokens": 0,
                        "cacheReadTokens": 0,
                        "costUSD": 0.1,
                    }
                ],
            }
        )
        result = subprocess.CompletedProcess(
            ["ccusage"], 0, stdout=session_report, stderr=""
        )
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "git_root", return_value=self.root),
            mock.patch.object(aw, "run", return_value=result) as runner,
            mock.patch.object(aw, "command_version", return_value="ccusage 99.0.0"),
            redirect_stdout(io.StringIO()),
        ):
            rc = aw.benchmark_capture(
                path=self.root,
                name="one-session",
                source="codex",
                since=None,
                until=None,
                project=None,
                session_id=session_id,
                task_set="core-suite-v1",
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="native",
                attempted_tasks=1,
                successful_tasks=1,
                replace=False,
            )
        self.assertEqual(rc, 0)
        command = runner.call_args.args[0]
        self.assertEqual(
            command,
            ["ccusage", "codex", "session", "--id", session_id, "--json", "--offline"],
        )
        stored_text = aw.benchmark_snapshot_path(
            self.root, "one-session", create_dir=False
        ).read_text()
        self.assertNotIn(session_id, stored_text)
        self.assertEqual(json.loads(stored_text)["filters"]["selection"], "session")

    def test_compare_json_stdout_is_machine_readable_only(self):
        directory = aw.benchmark_directory(self.root, create=True)
        (directory / "base.json").write_text(json.dumps(snapshot("base", cost=2, tokens=20)))
        (directory / "candidate.json").write_text(
            json.dumps(snapshot("candidate", cost=1, tokens=10))
        )
        stdout = io.StringIO()
        with mock.patch.object(aw, "git_root", return_value=self.root), redirect_stdout(stdout):
            rc = aw.benchmark_compare(
                path=self.root,
                baseline_name="base",
                candidate_name="candidate",
                json_output=True,
            )
        self.assertEqual(rc, 0)
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(parsed["metrics"]["total_tokens"]["percent_delta"], -50.0)

    def test_benchmark_paths_reject_symlinked_agents_parent(self):
        outside = self.root / "outside"
        (self.root / ".agents").rename(outside)
        (self.root / ".agents").symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(ef.BenchmarkError, "real .agents directory"):
            aw.benchmark_snapshot_path(self.root, "baseline", create_dir=False)

    def test_benchmark_paths_require_a_real_valid_project_id(self):
        project_id = self.root / ".agents/state/project-id"
        project_id.write_text("not-a-uuid\n")
        with self.assertRaisesRegex(ef.BenchmarkError, "valid project UUID"):
            aw.benchmark_snapshot_path(self.root, "baseline", create_dir=False)

    def test_configuration_digest_tracks_managed_inputs_not_prompt_state(self):
        facts = {
            "task_set": "core-suite-v1@sha256:" + "a" * 64,
            "model": "gpt-5.6-codex",
            "client_version": "codex-0.153.3",
            "environment_id": "macos-arm64-sandboxed",
            "configuration": "native",
            "ccusage_version": "ccusage-99.0.0",
        }
        original = aw.benchmark_configuration_digest(self.root, **facts)
        settings = self.root / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_text('{"sandbox": true}\n')
        configured = aw.benchmark_configuration_digest(self.root, **facts)
        self.assertNotEqual(original, configured)

        task_policy = self.root / ".agents/state/task-policy.json"
        task_policy.write_text('{"prompt_hash": "volatile"}\n')
        self.assertEqual(
            configured, aw.benchmark_configuration_digest(self.root, **facts)
        )

    def test_configuration_digest_ignores_refresh_timestamp_not_semantic_state(self):
        facts = {
            "task_set": "core-suite-v1@sha256:" + "a" * 64,
            "model": "gpt-5.6-codex",
            "client_version": "codex-0.153.3",
            "environment_id": "macos-arm64-sandboxed",
            "configuration": "native",
            "ccusage_version": "ccusage-99.0.0",
        }
        active_path = self.root / ".agents/state/active-agents.json"
        active_path.write_text(
            json.dumps({"generated_at": "first", "tier": "T1", "active": {"reviewer": "T1"}})
        )
        first = aw.benchmark_configuration_digest(self.root, **facts)
        active_path.write_text(
            json.dumps({"generated_at": "second", "tier": "T1", "active": {"reviewer": "T1"}})
        )
        self.assertEqual(first, aw.benchmark_configuration_digest(self.root, **facts))
        active_path.write_text(
            json.dumps({"generated_at": "second", "tier": "T2", "active": {"reviewer": "T2"}})
        )
        self.assertNotEqual(first, aw.benchmark_configuration_digest(self.root, **facts))

    def test_configuration_digest_rejects_symlinked_agent_inventory(self):
        outside = self.base / "outside-agents"
        outside.mkdir()
        claude = self.root / ".claude"
        claude.mkdir()
        (claude / "agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ef.BenchmarkError, "non-symlinked"):
            aw.benchmark_configuration_digest(
                self.root,
                task_set="core-suite-v1@sha256:" + "a" * 64,
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="native",
                ccusage_version="ccusage-99.0.0",
            )

    def test_configuration_digest_rejects_symlinked_managed_parent(self):
        outside = self.base / "outside-claude"
        outside.mkdir()
        (outside / "settings.json").write_text('{"outside": true}\n')
        (self.root / ".claude").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ef.BenchmarkError, "parent.*non-symlinked"):
            aw.benchmark_configuration_digest(
                self.root,
                task_set="core-suite-v1@sha256:" + "a" * 64,
                model="gpt-5.6-codex",
                client_version="codex-0.153.3",
                environment_id="macos-arm64-sandboxed",
                configuration="native",
                ccusage_version="ccusage-99.0.0",
            )

    def test_benchmark_namespace_binds_uuid_to_canonical_project_path(self):
        other = self.base / "other-project"
        (other / ".agents/state").mkdir(parents=True)
        (other / ".agents/state/project-id").write_text(
            "12345678-1234-4234-8234-123456789abc\n"
        )
        first = aw.benchmark_directory(self.root, create=False)
        second = aw.benchmark_directory(other, create=False)
        self.assertNotEqual(first, second)

    def test_relative_xdg_state_home_is_ignored(self):
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": "relative-state"}):
            state = aw.state_root()
        self.assertTrue(state.is_absolute())
        self.assertNotEqual(state, Path("relative-state/ratchery"))

    def test_relative_xdg_config_home_is_ignored(self):
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "relative-config"}):
            config = aw.config_path()
        self.assertTrue(config.is_absolute())
        self.assertNotEqual(config, Path("relative-config/ratchery/config.json"))

    def test_regular_legacy_config_is_read_then_new_saves_use_ratchery(self):
        config_root = self.base / "config"
        legacy = config_root / "agent-workspace/config.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text(
            json.dumps(
                {
                    "version": "1.0.1",
                    "vault_path": "/legacy-vault",
                    "projects_root": "/legacy-projects",
                    "project_layout": "flat",
                    "external_tools": "none",
                }
            )
        )
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_root)}):
            self.assertEqual(aw.config_read_path(), legacy)
            migrated = aw.cfg()
            self.assertEqual(migrated["vault_path"], "/legacy-vault")
            aw.save_cfg(migrated)
            self.assertTrue((config_root / "ratchery/config.json").is_file())
            self.assertEqual(aw.config_read_path(), config_root / "ratchery/config.json")

    def test_symlinked_legacy_config_is_not_used_for_migration(self):
        config_root = self.base / "config-symlink"
        legacy = config_root / "agent-workspace/config.json"
        legacy.parent.mkdir(parents=True)
        target = self.base / "untrusted-config.json"
        target.write_text('{"vault_path":"/must-not-load"}\n')
        legacy.symlink_to(target)
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config_root)}):
            self.assertEqual(aw.config_read_path(), config_root / "ratchery/config.json")
            self.assertIsNone(aw.cfg()["vault_path"])

    def test_benchmark_state_cannot_resolve_inside_project(self):
        inside = self.root / ".local-state"
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(inside)}):
            with self.assertRaisesRegex(ef.BenchmarkError, "outside the project"):
                aw.benchmark_directory(self.root, create=False)

    def test_benchmark_state_symlink_cannot_redirect_inside_project(self):
        inside = self.root / ".local-state"
        inside.mkdir()
        state_link = self.base / "state-link"
        state_link.symlink_to(inside, target_is_directory=True)
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(state_link)}):
            with self.assertRaisesRegex(ef.BenchmarkError, "outside the project"):
                aw.benchmark_directory(self.root, create=False)

    def test_benchmark_provenance_rejects_a_dirty_worktree(self):
        (self.root / "untracked.py").write_text("print('dirty')\n")
        with self.assertRaisesRegex(ef.BenchmarkError, "clean worktree"):
            aw.clean_git_commit(self.root)

    def test_benchmark_provenance_ignores_git_environment_redirection(self):
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str(self.base / "attacker-git-dir"),
                "GIT_WORK_TREE": str(self.base / "attacker-work-tree"),
                "GIT_INDEX_FILE": str(self.base / "attacker-index"),
                "GIT_OBJECT_DIRECTORY": str(self.base / "attacker-objects"),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(self.base / "attacker-alternates"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.fsmonitor",
                "GIT_CONFIG_VALUE_0": str(self.base / "attacker-monitor"),
            },
        ):
            commit = aw.clean_git_commit(self.root)
            diagnostic = aw.git_provenance(self.root)
        expected = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        self.assertEqual(commit, expected)
        self.assertEqual(diagnostic, {"commit": expected, "dirty": False})

    def test_git_provenance_disables_repository_fsmonitor_command(self):
        sentinel = self.base / "fsmonitor-executed"
        monitor = self.base / "fsmonitor"
        monitor.write_text(f"#!/bin/sh\n: > '{sentinel}'\n")
        monitor.chmod(0o755)
        subprocess.run(
            ["git", "config", "core.fsmonitor", str(monitor)],
            cwd=self.root,
            check=True,
        )

        commit = aw.clean_git_commit(self.root)
        diagnostic = aw.git_provenance(self.root)

        self.assertEqual(diagnostic["commit"], commit)
        self.assertFalse(diagnostic["dirty"])
        self.assertFalse(sentinel.exists())

    def test_git_root_ignores_git_environment_redirection(self):
        attacker = self.base / "attacker"
        subprocess.run(["git", "init", "-q", str(attacker)], check=True)
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str(attacker / ".git"),
                "GIT_WORK_TREE": str(attacker),
            },
        ):
            root = aw.git_root(self.root)
        self.assertEqual(root.resolve(), self.root.resolve())

    def test_clean_git_environment_removes_config_and_discovery_overrides(self):
        with mock.patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": str(self.base / "attacker-config"),
                "GIT_CEILING_DIRECTORIES": str(self.base),
                "GIT_NAMESPACE": "attacker",
                "SAFE_CONTROL": "preserved",
            },
        ):
            cleaned = aw.clean_git_environment()
        self.assertNotIn("GIT_CONFIG_GLOBAL", cleaned)
        self.assertNotIn("GIT_CEILING_DIRECTORIES", cleaned)
        self.assertNotIn("GIT_NAMESPACE", cleaned)
        self.assertEqual(cleaned["SAFE_CONTROL"], "preserved")

    def test_exclusive_snapshot_write_never_overwrites_existing_file(self):
        directory = aw.benchmark_directory(self.root, create=True)
        target = directory / "baseline.json"
        target.write_text("keep me")
        with self.assertRaisesRegex(ef.BenchmarkError, "already exists"):
            aw.write_benchmark_snapshot(target, {"new": True}, replace=False)
        self.assertEqual(target.read_text(), "keep me")

    def test_black_box_capture_uses_fake_ccusage_and_never_real_usage(self):
        fake_bin = self.base / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "ccusage"
        fake.write_text(
            "#!/bin/sh\n"
            "if [ \"${1:-}\" = \"--version\" ]; then printf 'ccusage 99.0.0\\n'; exit 0; fi\n"
            "printf '%s\\n' '{\"sessionId\":\"private-session\",\"totalCost\":0.25,"
            "\"totalTokens\":10,\"entries\":[{\"inputTokens\":4,\"outputTokens\":2,"
            "\"cacheCreationTokens\":1,\"cacheReadTokens\":3,\"costUSD\":0.25}]}'\n"
        )
        fake.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        script = Path(__file__).resolve().parents[1] / "lib/agent_workspace.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "benchmark",
                "capture",
                "black-box",
                "--path",
                str(self.root),
                "--source",
                "codex",
                "--session-id",
                "private-session",
                "--task-set",
                "core-suite-v1",
                "--model",
                "gpt-5.6-codex",
                "--client-version",
                "codex-0.153.3",
                "--environment-id",
                "macos-arm64-sandboxed",
                "--configuration",
                "native",
                "--attempted-tasks",
                "1",
                "--successful-tasks",
                "1",
            ],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        stored_text = aw.benchmark_snapshot_path(
            self.root, "black-box", create_dir=False
        ).read_text()
        self.assertNotIn("private-session", stored_text)
        self.assertEqual(json.loads(stored_text)["metrics"]["total_tokens"], 10)

    def test_suite_commands_emit_valid_json_without_starting_an_agent(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = aw.benchmark_suites(json_output=True)
        self.assertEqual(rc, 0)
        suites = json.loads(stdout.getvalue())["suites"]
        self.assertEqual([item["id"] for item in suites], ["core-suite-v1"])

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = aw.benchmark_show(target="core-suite-v1", json_output=True)
        self.assertEqual(rc, 0)
        shown = json.loads(stdout.getvalue())
        self.assertEqual(len(shown["tasks"]), 6)
        self.assertRegex(shown["sha256"], r"^[0-9a-f]{64}$")

    def test_report_cli_returns_machine_readable_repeated_statistics(self):
        directory = aw.benchmark_directory(self.root, create=True)
        baseline_names = []
        candidate_names = []
        for index in range(3):
            baseline_name = f"base-{index}"
            candidate_name = f"candidate-{index}"
            baseline_names.append(baseline_name)
            candidate_names.append(candidate_name)
            (directory / f"{baseline_name}.json").write_text(
                json.dumps(snapshot(baseline_name, cost=2, tokens=20, configuration="native"))
            )
            (directory / f"{candidate_name}.json").write_text(
                json.dumps(snapshot(candidate_name, cost=1, tokens=10, configuration="rtk"))
            )
        stdout = io.StringIO()
        with mock.patch.object(aw, "git_root", return_value=self.root), redirect_stdout(stdout):
            rc = aw.benchmark_report(
                path=self.root,
                baseline_names=baseline_names,
                candidate_names=candidate_names,
                minimum_trials=3,
                minimum_success_rate=1.0,
                json_output=True,
            )
        self.assertEqual(rc, 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["result"]["status"], "manual-review-candidate")
        self.assertFalse(report["result"]["automated_adoption_decision"])

    def test_report_cli_cannot_count_one_snapshot_three_times(self):
        directory = aw.benchmark_directory(self.root, create=True)
        (directory / "base.json").write_text(
            json.dumps(snapshot("base", cost=2, tokens=20, configuration="native"))
        )
        (directory / "candidate.json").write_text(
            json.dumps(snapshot("candidate", cost=1, tokens=10, configuration="rtk"))
        )
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "git_root", return_value=self.root),
            redirect_stderr(stderr),
        ):
            rc = aw.benchmark_report(
                path=self.root,
                baseline_names=["base", "base", "base"],
                candidate_names=["candidate", "candidate", "candidate"],
                minimum_trials=3,
                minimum_success_rate=1.0,
                json_output=True,
            )
        self.assertEqual(rc, 2)
        self.assertIn("distinct trials", stderr.getvalue())

    def test_budget_check_is_offline_read_only_and_enforcement_is_opt_in(self):
        completed = subprocess.CompletedProcess(
            ["ccusage"], 0, stdout=ccusage_report(cost=2.5), stderr=""
        )
        stdout = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "run", return_value=completed) as runner,
            redirect_stdout(stdout),
        ):
            rc = aw.budget_check(
                period="daily",
                source="codex",
                since="20260901",
                until="20260901",
                project="private-project-label",
                session_id=None,
                max_cost_usd=1.0,
                max_tokens=None,
                spike_baseline_tokens=None,
                spike_multiplier=10,
                enforce=False,
                json_output=True,
            )
        self.assertEqual(rc, 0)
        payload_text = stdout.getvalue()
        payload = json.loads(payload_text)
        self.assertEqual(payload["status"], "exceeded")
        self.assertNotIn("private-project-label", payload_text)
        self.assertIn("--offline", runner.call_args.args[0])
        self.assertFalse((aw.state_root() / "budgets").exists())

        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "run", return_value=completed),
            redirect_stdout(io.StringIO()),
        ):
            enforced = aw.budget_check(
                period="daily",
                source="codex",
                since="20260901",
                until="20260901",
                project=None,
                session_id=None,
                max_cost_usd=1.0,
                max_tokens=None,
                spike_baseline_tokens=None,
                spike_multiplier=10,
                enforce=True,
                json_output=True,
            )
        self.assertEqual(enforced, 3)

    def test_budget_rejects_missing_threshold_before_running_ccusage(self):
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=True),
            mock.patch.object(aw, "run") as runner,
            redirect_stderr(stderr),
        ):
            rc = aw.budget_check(
                period="daily",
                source=None,
                since="20260901",
                until="20260901",
                project=None,
                session_id=None,
                max_cost_usd=None,
                max_tokens=None,
                spike_baseline_tokens=None,
                spike_multiplier=10,
                enforce=False,
                json_output=True,
            )
        self.assertEqual(rc, 2)
        runner.assert_not_called()
        self.assertIn("at least one", stderr.getvalue())

    def test_budget_validates_arguments_before_checking_for_ccusage(self):
        stderr = io.StringIO()
        with (
            mock.patch.object(aw, "exists", return_value=False),
            redirect_stderr(stderr),
        ):
            rc = aw.budget_check(
                period="daily",
                source="codex",
                since="20260230",
                until="20260230",
                project=None,
                session_id=None,
                max_cost_usd=1.0,
                max_tokens=None,
                spike_baseline_tokens=None,
                spike_multiplier=10,
                enforce=False,
                json_output=True,
            )
        self.assertEqual(rc, 2)
        self.assertIn("valid calendar date", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
