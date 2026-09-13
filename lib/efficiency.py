#!/usr/bin/env python3
"""Pure helpers for privacy-preserving cost/quality benchmark snapshots.

The module deliberately knows nothing about subprocesses, agent prompts, or local
session files.  It accepts ccusage's aggregate JSON, validates the small totals
contract we rely on, and returns a snapshot containing aggregates only.  Raw rows,
session identifiers, model breakdowns, paths, and prompts never cross the snapshot
boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

SNAPSHOT_SCHEMA_VERSION = 2
TASK_SET_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 2
SAFE_BENCHMARK_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
SAFE_SOURCE_NAME = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}$")
SAFE_EVIDENCE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,127}$")

_CCUSAGE_FIELDS = {
    "input_tokens": "inputTokens",
    "output_tokens": "outputTokens",
    "cache_creation_tokens": "cacheCreationTokens",
    "cache_read_tokens": "cacheReadTokens",
}
_COMPARISON_METRICS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "success_rate",
    "cost_per_successful_task",
)
_FILTER_KEYS = {"source", "project", "period", "selection", "since", "until", "offline"}
_PROVENANCE_KEYS = {
    "git_commit",
    "task_set",
    "model",
    "client_version",
    "environment_id",
    "configuration",
    "configuration_digest",
}
_TASK_SET_KEYS = {
    "schema_version",
    "id",
    "title",
    "description",
    "minimum_trials_per_arm",
    "protocol",
    "tasks",
}
_PROTOCOL_KEYS = {
    "execution",
    "fixture",
    "reset_between_tasks",
    "network",
    "secrets",
    "requirements",
}
_TASK_KEYS = {"id", "category", "prompt", "success_criteria", "verification"}


class BenchmarkError(ValueError):
    """Raised when usage input or a stored snapshot is unsafe or incomparable."""


def _plain_text(value: Any, label: str, *, maximum: int = 4000) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise BenchmarkError(
            f"{label} must be a non-empty string of at most {maximum} characters without controls"
        )
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise BenchmarkError(f"{label} must be a non-empty array of strings")
    return [
        _plain_text(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    ]


def _safe_relative_path(value: Any, label: str) -> str:
    text = _plain_text(value, label, maximum=512)
    if "\\" in text:
        raise BenchmarkError(f"{label} must use a repository-relative POSIX path")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BenchmarkError(f"{label} must be a safe repository-relative path")
    return text


def validate_task_set(value: Any) -> dict[str, Any]:
    """Validate and normalize a versioned, non-executing benchmark protocol."""
    if not isinstance(value, dict) or set(value) != _TASK_SET_KEYS:
        raise BenchmarkError(
            "benchmark task set requires exactly: " + ", ".join(sorted(_TASK_SET_KEYS))
        )
    if value.get("schema_version") != TASK_SET_SCHEMA_VERSION:
        raise BenchmarkError(
            f"unsupported task-set schema_version: {value.get('schema_version')!r}"
        )
    task_set_id = value.get("id")
    if not isinstance(task_set_id, str) or not SAFE_EVIDENCE_LABEL.fullmatch(task_set_id):
        raise BenchmarkError("task-set id must be a safe evidence identifier")
    minimum_trials = _number(
        value.get("minimum_trials_per_arm"),
        "minimum_trials_per_arm",
        integer=True,
    )
    if minimum_trials < 2:
        raise BenchmarkError("minimum_trials_per_arm must be at least 2")

    protocol = value.get("protocol")
    if not isinstance(protocol, dict) or set(protocol) != _PROTOCOL_KEYS:
        raise BenchmarkError(
            "task-set protocol requires exactly: " + ", ".join(sorted(_PROTOCOL_KEYS))
        )
    if protocol.get("execution") != "manual":
        raise BenchmarkError("task-set protocol.execution must be 'manual'")
    if protocol.get("reset_between_tasks") is not True:
        raise BenchmarkError("task-set protocol must reset between tasks")
    if protocol.get("network") != "disabled" or protocol.get("secrets") != "none":
        raise BenchmarkError("task-set protocol must disable network and require no secrets")

    tasks = value.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise BenchmarkError("task-set tasks must be a non-empty array")
    normalized_tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or set(task) != _TASK_KEYS:
            raise BenchmarkError(
                f"task {index} requires exactly: " + ", ".join(sorted(_TASK_KEYS))
            )
        task_id = task.get("id")
        if not isinstance(task_id, str) or not SAFE_EVIDENCE_LABEL.fullmatch(task_id):
            raise BenchmarkError(f"task {index}.id must be a safe evidence identifier")
        if task_id in seen:
            raise BenchmarkError(f"duplicate task id: {task_id}")
        seen.add(task_id)
        normalized_tasks.append(
            {
                "id": task_id,
                "category": _plain_text(task.get("category"), f"task {index}.category", maximum=100),
                "prompt": _plain_text(task.get("prompt"), f"task {index}.prompt"),
                "success_criteria": _string_list(
                    task.get("success_criteria"), f"task {index}.success_criteria"
                ),
                "verification": _string_list(
                    task.get("verification"), f"task {index}.verification"
                ),
            }
        )

    return {
        "schema_version": TASK_SET_SCHEMA_VERSION,
        "id": task_set_id,
        "title": _plain_text(value.get("title"), "task-set title", maximum=200),
        "description": _plain_text(value.get("description"), "task-set description"),
        "minimum_trials_per_arm": minimum_trials,
        "protocol": {
            "execution": "manual",
            "fixture": _safe_relative_path(protocol.get("fixture"), "protocol.fixture"),
            "reset_between_tasks": True,
            "network": "disabled",
            "secrets": "none",
            "requirements": _string_list(protocol.get("requirements"), "protocol.requirements"),
        },
        "tasks": normalized_tasks,
    }


def task_set_digest(value: Any) -> str:
    checked = validate_task_set(value)
    canonical = json.dumps(
        checked, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_benchmark_name(value: str) -> str:
    if value in {".", ".."} or not SAFE_BENCHMARK_NAME.fullmatch(value):
        raise BenchmarkError(
            "benchmark name must be 1-64 characters using letters, digits, '.', '_', or '-'"
        )
    return value


def validate_source_name(value: str | None) -> str | None:
    if value is None:
        return None
    if not SAFE_SOURCE_NAME.fullmatch(value):
        raise BenchmarkError(
            "ccusage source must start with a lowercase letter and contain only lowercase letters, digits, or '-'"
        )
    return value


def validate_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    if not SAFE_SESSION_ID.fullmatch(value):
        raise BenchmarkError(
            "ccusage session ID must be 1-200 characters without whitespace or option syntax"
        )
    return value


def project_fingerprint(value: str | None) -> str | None:
    """Return a stable comparison key without retaining a project label/path."""
    if value is None:
        return None
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _number(value: Any, label: str, *, integer: bool) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkError(f"{label} must be a non-negative number")
    if not math.isfinite(value) or value < 0:
        raise BenchmarkError(f"{label} must be finite and non-negative")
    if integer:
        if not float(value).is_integer():
            raise BenchmarkError(f"{label} must be a whole token count")
        return int(value)
    return float(value)


def _date(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{8}", value):
        raise BenchmarkError(f"filters.{label} must use YYYYMMDD")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise BenchmarkError(f"filters.{label} is not a valid calendar date") from exc
    return value


def _validated_filters(filters: Any) -> dict[str, Any]:
    if not isinstance(filters, dict):
        raise BenchmarkError("benchmark snapshot filters must be an object")
    extra = sorted(set(filters) - _FILTER_KEYS)
    if extra:
        raise BenchmarkError("unsupported benchmark filter(s): " + ", ".join(extra))

    source = filters.get("source")
    if source != "all":
        source = validate_source_name(source)
    if source is None:
        raise BenchmarkError("filters.source must be 'all' or a valid ccusage source")

    project = filters.get("project")
    if project is not None and not (
        isinstance(project, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", project)
    ):
        raise BenchmarkError(
            "filters.project must be null or a SHA-256 project fingerprint"
        )

    period = filters.get("period")
    selection = filters.get("selection")
    offline = filters.get("offline")
    since = filters.get("since")
    until = filters.get("until")
    if offline is not True:
        raise BenchmarkError("benchmark snapshots must record offline=true")
    if selection == "session":
        if period != "session" or source == "all":
            raise BenchmarkError(
                "session snapshots require period=session and one explicit source"
            )
        if any(value is not None for value in (project, since, until)):
            raise BenchmarkError(
                "session snapshots cannot contain project or date-window filters"
            )
    elif selection == "date-window":
        if period != "daily":
            raise BenchmarkError("date-window snapshots require period=daily")
        since = _date(since, "since")
        until = _date(until, "until")
        if since > until:
            raise BenchmarkError("filters.since cannot be later than filters.until")
    else:
        raise BenchmarkError("filters.selection must be 'session' or 'date-window'")

    return {
        "source": source,
        "project": project,
        "period": period,
        "selection": selection,
        "since": since,
        "until": until,
        "offline": True,
    }


def _safe_metadata(value: Any, label: str, *, required: bool) -> str | None:
    if value is None and not required:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 200
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        requirement = "a non-empty" if required else "null or a"
        raise BenchmarkError(
            f"{label} must be {requirement} string of at most 200 characters without controls"
        )
    return value


def _validated_provenance(provenance: Any) -> dict[str, str]:
    if not isinstance(provenance, dict) or set(provenance) != _PROVENANCE_KEYS:
        raise BenchmarkError(
            "benchmark provenance requires exactly: "
            + ", ".join(sorted(_PROVENANCE_KEYS))
        )
    commit = provenance.get("git_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise BenchmarkError("provenance.git_commit must be a full Git object ID")
    checked = {"git_commit": commit}
    configuration_digest = provenance.get("configuration_digest")
    if not isinstance(configuration_digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", configuration_digest
    ):
        raise BenchmarkError(
            "provenance.configuration_digest must be a lowercase SHA-256 digest"
        )
    checked["configuration_digest"] = configuration_digest
    for key in sorted(
        _PROVENANCE_KEYS - {"git_commit", "configuration_digest"}
    ):
        value = provenance.get(key)
        if not isinstance(value, str) or not SAFE_EVIDENCE_LABEL.fullmatch(value):
            raise BenchmarkError(
                f"provenance.{key} must be a 1-128 character evidence identifier "
                "without whitespace or path separators"
            )
        checked[key] = value
    return {key: checked[key] for key in sorted(checked)}


def _aggregate_ccusage_rows(rows: list[Any]) -> dict[str, Any]:
    if not rows:
        raise BenchmarkError("ccusage returned no usage data for this benchmark window")
    totals = {field: 0 for field in _CCUSAGE_FIELDS.values()}
    totals["totalCost"] = 0.0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BenchmarkError(f"ccusage row {index} is not an object")
        for camel in _CCUSAGE_FIELDS.values():
            totals[camel] += _number(row.get(camel), f"row {index}.{camel}", integer=True)
        cost = row.get("totalCost", row.get("costUSD"))
        totals["totalCost"] += _number(cost, f"row {index}.cost", integer=False)
    return totals


def parse_ccusage_json(text: str) -> dict[str, int | float]:
    """Return validated aggregate metrics from ccusage JSON output.

    Current ccusage emits ``{"totals": ...}``; legacy report versions may emit
    a top-level list, which is summed after validating every row.  No row-level
    data is returned to the caller.
    """
    try:
        report = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise BenchmarkError(f"ccusage did not emit valid JSON: {exc}") from exc

    if isinstance(report, list):
        totals = _aggregate_ccusage_rows(report)
    elif isinstance(report, dict) and isinstance(report.get("totals"), dict):
        totals = report["totals"]
    elif isinstance(report, dict) and isinstance(report.get("entries"), list):
        totals = _aggregate_ccusage_rows(report["entries"])
    else:
        raise BenchmarkError("ccusage JSON must contain an aggregate 'totals' object")

    metrics: dict[str, int | float] = {}
    for field, camel in _CCUSAGE_FIELDS.items():
        metrics[field] = _number(totals.get(camel), f"totals.{camel}", integer=True)
    metrics["total_tokens"] = sum(int(metrics[field]) for field in _CCUSAGE_FIELDS)
    metrics["estimated_cost_usd"] = _number(
        totals.get("totalCost"), "totals.totalCost", integer=False
    )

    reported_total = totals.get("totalTokens")
    if reported_total is not None:
        checked_total = _number(reported_total, "totals.totalTokens", integer=True)
        if checked_total != metrics["total_tokens"]:
            raise BenchmarkError(
                "ccusage totalTokens does not match the sum of its token categories"
            )
    return metrics


def make_snapshot(
    *,
    name: str,
    metrics: dict[str, Any],
    filters: dict[str, Any],
    provenance: dict[str, Any],
    attempted_tasks: int,
    successful_tasks: int,
    captured_at: str,
    ccusage_version: str,
) -> dict[str, Any]:
    validate_benchmark_name(name)
    checked_filters = _validated_filters(filters)
    checked_provenance = _validated_provenance(provenance)
    checked_captured_at = _safe_metadata(captured_at, "captured_at", required=True)
    checked_version = _safe_metadata(ccusage_version, "ccusage_version", required=True)
    attempted = _number(attempted_tasks, "attempted_tasks", integer=True)
    successful = _number(successful_tasks, "successful_tasks", integer=True)
    if attempted < 1:
        raise BenchmarkError("attempted_tasks must be at least 1")
    if successful > attempted:
        raise BenchmarkError("successful_tasks cannot exceed attempted_tasks")

    normalized = {
        field: _number(
            metrics.get(field),
            field,
            integer=field != "estimated_cost_usd",
        )
        for field in (*_CCUSAGE_FIELDS, "total_tokens", "estimated_cost_usd")
    }
    expected_total = sum(int(normalized[field]) for field in _CCUSAGE_FIELDS)
    if normalized["total_tokens"] != expected_total:
        raise BenchmarkError("total_tokens does not match the token category sum")
    if normalized["total_tokens"] == 0:
        raise BenchmarkError(
            "benchmark snapshots require measured token usage; the selected window is empty"
        )

    success_rate = successful / attempted
    cost_per_success = (
        float(normalized["estimated_cost_usd"]) / successful if successful else None
    )
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "name": name,
        "captured_at": checked_captured_at,
        "source": "ccusage",
        "ccusage_version": checked_version,
        "filters": checked_filters,
        "provenance": checked_provenance,
        "metrics": {
            **normalized,
            "attempted_tasks": attempted,
            "successful_tasks": successful,
            "success_rate": success_rate,
            "cost_per_successful_task": cost_per_success,
        },
    }


def validate_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BenchmarkError("benchmark snapshot must be a JSON object")
    if value.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise BenchmarkError(
            f"unsupported benchmark schema_version: {value.get('schema_version')!r}"
        )
    if value.get("source") != "ccusage":
        raise BenchmarkError("benchmark snapshot source must be 'ccusage'")
    filters = value.get("filters")
    provenance = value.get("provenance")
    metrics = value.get("metrics")
    if not isinstance(filters, dict) or not isinstance(metrics, dict):
        raise BenchmarkError("benchmark snapshot requires object filters and metrics")
    rebuilt = make_snapshot(
        name=value.get("name", ""),
        metrics=metrics,
        filters=filters,
        provenance=provenance,
        attempted_tasks=metrics.get("attempted_tasks"),
        successful_tasks=metrics.get("successful_tasks"),
        captured_at=value.get("captured_at", ""),
        ccusage_version=value.get("ccusage_version"),
    )
    if metrics.get("success_rate") != rebuilt["metrics"]["success_rate"]:
        raise BenchmarkError("stored success_rate does not match task counts")
    if metrics.get("cost_per_successful_task") != rebuilt["metrics"]["cost_per_successful_task"]:
        raise BenchmarkError("stored cost_per_successful_task does not match cost/task counts")
    return rebuilt


def _delta(baseline: int | float | None, candidate: int | float | None) -> dict[str, Any]:
    if baseline is None or candidate is None:
        return {
            "baseline": baseline,
            "candidate": candidate,
            "absolute_delta": None,
            "percent_delta": None,
        }
    absolute = candidate - baseline
    percent = None
    if baseline != 0:
        try:
            candidate_percent = absolute / baseline * 100.0
        except OverflowError:
            candidate_percent = math.inf
        if math.isfinite(candidate_percent):
            percent = candidate_percent
    return {
        "baseline": baseline,
        "candidate": candidate,
        "absolute_delta": absolute,
        "percent_delta": percent,
    }


def compare_snapshots(baseline_value: Any, candidate_value: Any) -> dict[str, Any]:
    baseline = validate_snapshot(baseline_value)
    candidate = validate_snapshot(candidate_value)
    if baseline["ccusage_version"] != candidate["ccusage_version"]:
        raise BenchmarkError("benchmark ccusage versions differ")
    scope_keys = ("source", "project", "period", "selection", "offline")
    mismatches = [
        key
        for key in scope_keys
        if baseline["filters"].get(key) != candidate["filters"].get(key)
    ]
    if mismatches:
        raise BenchmarkError(
            "benchmark scopes differ for: " + ", ".join(mismatches)
        )
    provenance_keys = (
        "git_commit",
        "task_set",
        "model",
        "client_version",
        "environment_id",
    )
    provenance_mismatches = [
        key
        for key in provenance_keys
        if baseline["provenance"][key] != candidate["provenance"][key]
    ]
    if provenance_mismatches:
        raise BenchmarkError(
            "benchmark provenance differs for: " + ", ".join(provenance_mismatches)
        )

    b_metrics = baseline["metrics"]
    c_metrics = candidate["metrics"]
    if b_metrics["attempted_tasks"] != c_metrics["attempted_tasks"]:
        raise BenchmarkError("benchmark attempted task counts differ")
    if baseline["filters"]["selection"] == "date-window":
        b_start = datetime.strptime(baseline["filters"]["since"], "%Y%m%d")
        b_end = datetime.strptime(baseline["filters"]["until"], "%Y%m%d")
        c_start = datetime.strptime(candidate["filters"]["since"], "%Y%m%d")
        c_end = datetime.strptime(candidate["filters"]["until"], "%Y%m%d")
        if b_end - b_start != c_end - c_start:
            raise BenchmarkError("benchmark date-window durations differ")
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "baseline": baseline["name"],
        "candidate": candidate["name"],
        "scope": {
            **{key: baseline["filters"].get(key) for key in scope_keys},
            "ccusage_version": baseline["ccusage_version"],
        },
        "provenance": {
            **{key: baseline["provenance"][key] for key in provenance_keys},
            "baseline_configuration": baseline["provenance"]["configuration"],
            "candidate_configuration": candidate["provenance"]["configuration"],
            "baseline_configuration_digest": baseline["provenance"][
                "configuration_digest"
            ],
            "candidate_configuration_digest": candidate["provenance"][
                "configuration_digest"
            ],
        },
        "metrics": {
            field: _delta(b_metrics[field], c_metrics[field])
            for field in _COMPARISON_METRICS
        },
        "sample": {
            "baseline_attempted_tasks": b_metrics["attempted_tasks"],
            "candidate_attempted_tasks": c_metrics["attempted_tasks"],
            "baseline_successful_tasks": b_metrics["successful_tasks"],
            "candidate_successful_tasks": c_metrics["successful_tasks"],
        },
    }


def _metric_distribution(snapshots: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [item["metrics"][field] for item in snapshots]
    if any(value is None for value in values):
        return {"median": None, "minimum": None, "maximum": None}
    numeric = [float(value) for value in values]
    return {
        "median": statistics.median(numeric),
        "minimum": min(numeric),
        "maximum": max(numeric),
    }


def report_snapshots(
    baseline_values: list[Any],
    candidate_values: list[Any],
    *,
    minimum_trials: int = 3,
    minimum_success_rate: float = 1.0,
) -> dict[str, Any]:
    """Summarize repeated compatible arms without making an adoption decision."""
    if isinstance(minimum_trials, bool) or not isinstance(minimum_trials, int) or minimum_trials < 2:
        raise BenchmarkError("minimum_trials must be an integer of at least 2")
    if (
        isinstance(minimum_success_rate, bool)
        or not isinstance(minimum_success_rate, (int, float))
        or not math.isfinite(minimum_success_rate)
        or not 0 <= minimum_success_rate <= 1
    ):
        raise BenchmarkError("minimum_success_rate must be between 0 and 1")
    if not baseline_values or not candidate_values:
        raise BenchmarkError("benchmark report requires at least one snapshot in each arm")

    baseline = [validate_snapshot(item) for item in baseline_values]
    candidate = [validate_snapshot(item) for item in candidate_values]
    if len({item["name"] for item in baseline}) != len(baseline):
        raise BenchmarkError("baseline snapshots must be distinct trials")
    if len({item["name"] for item in candidate}) != len(candidate):
        raise BenchmarkError("candidate snapshots must be distinct trials")
    baseline_configuration = baseline[0]["provenance"]["configuration"]
    candidate_configuration = candidate[0]["provenance"]["configuration"]
    if any(
        item["provenance"]["configuration"] != baseline_configuration
        for item in baseline
    ):
        raise BenchmarkError("baseline snapshots contain different configurations")
    if any(
        item["provenance"]["configuration"] != candidate_configuration
        for item in candidate
    ):
        raise BenchmarkError("candidate snapshots contain different configurations")
    if baseline_configuration == candidate_configuration:
        raise BenchmarkError("baseline and candidate configurations must differ")
    baseline_digest = baseline[0]["provenance"]["configuration_digest"]
    candidate_digest = candidate[0]["provenance"]["configuration_digest"]
    if any(
        item["provenance"]["configuration_digest"] != baseline_digest
        for item in baseline
    ):
        raise BenchmarkError(
            "baseline snapshots contain different configuration digests"
        )
    if any(
        item["provenance"]["configuration_digest"] != candidate_digest
        for item in candidate
    ):
        raise BenchmarkError(
            "candidate snapshots contain different configuration digests"
        )

    reference = baseline[0]
    for item in [*baseline[1:], *candidate]:
        compare_snapshots(reference, item)

    fields = _COMPARISON_METRICS
    baseline_summary = {
        field: _metric_distribution(baseline, field) for field in fields
    }
    candidate_summary = {
        field: _metric_distribution(candidate, field) for field in fields
    }
    median_deltas = {
        field: _delta(
            baseline_summary[field]["median"],
            candidate_summary[field]["median"],
        )
        for field in fields
    }
    baseline_success = baseline_summary["success_rate"]["median"]
    candidate_success = candidate_summary["success_rate"]["median"]
    candidate_floor_met = all(
        item["metrics"]["success_rate"] >= minimum_success_rate
        for item in candidate
    )
    relative_quality_preserved = (
        candidate_success is not None
        and baseline_success is not None
        and candidate_success >= baseline_success
    )
    enough_samples = (
        len(baseline) >= minimum_trials and len(candidate) >= minimum_trials
    )
    cost_delta = median_deltas["cost_per_successful_task"]["absolute_delta"]
    token_delta = median_deltas["total_tokens"]["absolute_delta"]
    measured_savings = (
        cost_delta is not None
        and token_delta is not None
        and cost_delta < 0
        and token_delta < 0
    )
    if not enough_samples:
        status = "insufficient-samples"
    elif not candidate_floor_met or not relative_quality_preserved:
        status = "quality-regression"
    elif measured_savings:
        status = "manual-review-candidate"
    else:
        status = "no-measured-savings"

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "baseline_configuration": baseline_configuration,
        "candidate_configuration": candidate_configuration,
        "baseline_configuration_digest": baseline_digest,
        "candidate_configuration_digest": candidate_digest,
        "provenance": {
            key: reference["provenance"][key]
            for key in (
                "git_commit",
                "task_set",
                "model",
                "client_version",
                "environment_id",
            )
        },
        "scope": {
            key: reference["filters"].get(key)
            for key in ("source", "project", "period", "selection", "offline")
        },
        "samples": {
            "baseline": len(baseline),
            "candidate": len(candidate),
            "minimum_trials_per_arm": minimum_trials,
            "enough": enough_samples,
        },
        "quality": {
            "minimum_success_rate": float(minimum_success_rate),
            "candidate_floor_met": candidate_floor_met,
            "relative_quality_preserved": relative_quality_preserved,
        },
        "metrics": {
            field: {
                "baseline": baseline_summary[field],
                "candidate": candidate_summary[field],
                "median_delta": median_deltas[field],
            }
            for field in fields
        },
        "result": {
            "status": status,
            "measured_savings": measured_savings,
            "automated_adoption_decision": False,
        },
    }


def evaluate_budget(
    metrics: dict[str, Any],
    *,
    max_cost_usd: float | None,
    max_tokens: int | None,
    spike_baseline_tokens: int | None,
    spike_multiplier: float,
) -> dict[str, Any]:
    """Evaluate aggregate usage locally; this is an estimate, not a billing control."""
    total_tokens = _number(metrics.get("total_tokens"), "total_tokens", integer=True)
    cost = _number(metrics.get("estimated_cost_usd"), "estimated_cost_usd", integer=False)
    if max_cost_usd is not None:
        max_cost_usd = float(_number(max_cost_usd, "max_cost_usd", integer=False))
        if max_cost_usd == 0:
            raise BenchmarkError("max_cost_usd must be greater than zero")
    if max_tokens is not None:
        max_tokens = int(_number(max_tokens, "max_tokens", integer=True))
        if max_tokens == 0:
            raise BenchmarkError("max_tokens must be greater than zero")
    if spike_baseline_tokens is not None:
        spike_baseline_tokens = int(
            _number(spike_baseline_tokens, "spike_baseline_tokens", integer=True)
        )
        if spike_baseline_tokens == 0:
            raise BenchmarkError("spike_baseline_tokens must be greater than zero")
    if (
        isinstance(spike_multiplier, bool)
        or not isinstance(spike_multiplier, (int, float))
        or not math.isfinite(spike_multiplier)
        or spike_multiplier <= 1
    ):
        raise BenchmarkError("spike_multiplier must be greater than 1")
    if max_cost_usd is None and max_tokens is None and spike_baseline_tokens is None:
        raise BenchmarkError("at least one budget or spike threshold is required")

    checks: list[dict[str, Any]] = []
    if max_cost_usd is not None:
        checks.append(
            {
                "kind": "cost",
                "actual": float(cost),
                "limit": max_cost_usd,
                "status": "exceeded" if cost > max_cost_usd else "ok",
            }
        )
    if max_tokens is not None:
        checks.append(
            {
                "kind": "tokens",
                "actual": int(total_tokens),
                "limit": max_tokens,
                "status": "exceeded" if total_tokens > max_tokens else "ok",
            }
        )
    if spike_baseline_tokens is not None:
        spike_limit = float(spike_baseline_tokens) * float(spike_multiplier)
        checks.append(
            {
                "kind": "token-spike",
                "actual": int(total_tokens),
                "baseline": spike_baseline_tokens,
                "multiplier": float(spike_multiplier),
                "limit": spike_limit,
                "status": "warning" if total_tokens >= spike_limit else "ok",
            }
        )
    if any(item["status"] == "exceeded" for item in checks):
        status = "exceeded"
    elif any(item["status"] == "warning" for item in checks):
        status = "warning"
    else:
        status = "ok"
    return {
        "schema_version": 1,
        "status": status,
        "estimated": True,
        "metrics": {
            "total_tokens": int(total_tokens),
            "estimated_cost_usd": float(cost),
        },
        "checks": checks,
    }
