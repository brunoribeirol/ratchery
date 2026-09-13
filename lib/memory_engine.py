#!/usr/bin/env python3
"""Bounded, provider-neutral handoff records for curated project memory.

The module deliberately owns only validation and rendering.  Vault discovery,
Git provenance, backups, and CLI dispatch remain in ``agent_workspace.py`` so
this data format cannot silently grow into a session-capture or orchestration
runtime.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from pathlib import PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 64 * 1024
MAX_STORED_BYTES = 64 * 1024
MAX_LIST_ITEMS = 32
MAX_CHANGED_FILES = 128

INPUT_KEYS = {
    "source_client",
    "target_client",
    "objective",
    "completed",
    "changed_files",
    "checks",
    "open_risks",
    "next_action",
}
REQUIRED_INPUT_KEYS = INPUT_KEYS - {"target_client"}
STORED_KEYS = INPUT_KEYS | {
    "schema_version",
    "created_at",
    "project_id",
    "project_slug",
    "git",
}
CHECK_KEYS = {"command", "status", "summary"}
CHECK_STATUSES = {"passed", "failed", "skipped", "not-run"}
CLIENT_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
PROJECT_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
PROJECT_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

# This is a narrow tripwire, not a DLP claim.  It catches common credential
# forms before durable storage while the written policy still requires a human
# to review every handoff.  Error messages never include the matching value.
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.I),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.I),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|secret)"
        r"\s*[:=]\s*[\"']?[^\s\"',]{8,}",
        re.I,
    ),
)


class HandoffError(ValueError):
    """Raised when a handoff is unsafe, malformed, or outside its contract."""


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HandoffError("handoff JSON contains a duplicate key")
        result[key] = value
    return result


def parse_input(data: bytes) -> dict[str, Any]:
    """Decode and validate an untrusted handoff payload from stdin."""
    if len(data) > MAX_INPUT_BYTES:
        raise HandoffError(f"handoff input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HandoffError("handoff input must be valid UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs_object)
    except HandoffError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise HandoffError("handoff input must be one valid JSON object") from exc
    return validate_input(value)


def _plain_text(value: Any, label: str, maximum: int, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise HandoffError(f"{label} must be a string")
    if not value.strip() and required:
        raise HandoffError(f"{label} must not be empty")
    if len(value) > maximum:
        raise HandoffError(f"{label} exceeds {maximum} characters")
    if value == "" and not required:
        return ""
    if len(value.splitlines()) != 1 or any(
        unicodedata.category(character).startswith("C") for character in value
    ):
        raise HandoffError(f"{label} contains a control or format character")
    return value.strip()


def _client(value: Any, label: str) -> str:
    checked = _plain_text(value, label, 64)
    if not CLIENT_RE.fullmatch(checked):
        raise HandoffError(
            f"{label} must be a lowercase client identifier using letters, numbers, '.', '_' or '-'"
        )
    return checked


def _text_list(value: Any, label: str, *, maximum_items: int = MAX_LIST_ITEMS) -> list[str]:
    if not isinstance(value, list):
        raise HandoffError(f"{label} must be an array")
    if len(value) > maximum_items:
        raise HandoffError(f"{label} exceeds {maximum_items} items")
    return [
        _plain_text(item, f"{label}[{index}]", 500)
        for index, item in enumerate(value)
    ]


def _changed_files(value: Any) -> list[str]:
    items = _text_list(value, "changed_files", maximum_items=MAX_CHANGED_FILES)
    checked: list[str] = []
    for index, item in enumerate(items):
        if len(item) > 512 or "\\" in item:
            raise HandoffError(
                f"changed_files[{index}] must be a repository-relative POSIX path"
            )
        path = PurePosixPath(item)
        if path.is_absolute() or item in {".", ".."} or ".." in path.parts:
            raise HandoffError(
                f"changed_files[{index}] must be a repository-relative POSIX path"
            )
        checked.append(item)
    return checked


def _checks(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise HandoffError("checks must be an array")
    if len(value) > MAX_LIST_ITEMS:
        raise HandoffError(f"checks exceeds {MAX_LIST_ITEMS} items")
    checked: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != CHECK_KEYS:
            raise HandoffError(
                f"checks[{index}] must contain exactly command, status, and summary"
            )
        status = item.get("status")
        if status not in CHECK_STATUSES:
            raise HandoffError(
                f"checks[{index}].status must be one of: {', '.join(sorted(CHECK_STATUSES))}"
            )
        checked.append(
            {
                "command": _plain_text(item.get("command"), f"checks[{index}].command", 300),
                "status": status,
                "summary": _plain_text(
                    item.get("summary"), f"checks[{index}].summary", 500, required=False
                ),
            }
        )
    return checked


def _contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SECRET_PATTERNS)
    if isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_secret(item) for item in value.values())
    return False


def validate_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HandoffError("handoff input must be a JSON object")
    unknown = set(value) - INPUT_KEYS
    missing = REQUIRED_INPUT_KEYS - set(value)
    if unknown:
        raise HandoffError("handoff input contains unsupported fields")
    if missing:
        raise HandoffError("handoff input is missing required fields")
    normalized: dict[str, Any] = {
        "source_client": _client(value.get("source_client"), "source_client"),
        "target_client": _client(value.get("target_client", "any"), "target_client"),
        "objective": _plain_text(value.get("objective"), "objective", 1000),
        "completed": _text_list(value.get("completed"), "completed"),
        "changed_files": _changed_files(value.get("changed_files")),
        "checks": _checks(value.get("checks")),
        "open_risks": _text_list(value.get("open_risks"), "open_risks"),
        "next_action": _plain_text(value.get("next_action"), "next_action", 1000),
    }
    if _contains_secret(normalized):
        raise HandoffError(
            "handoff rejected because it contains secret-like material; remove or redact it"
        )
    return normalized


def build_record(
    value: Any,
    *,
    project_id: str,
    project_slug: str,
    created_at: str,
    commit: str | None,
    dirty: bool | None,
) -> dict[str, Any]:
    payload = validate_input(value)
    record = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "project_id": project_id,
        "project_slug": project_slug,
        "git": {"commit": commit, "dirty": dirty},
        **payload,
    }
    return validate_record(record)


def validate_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != STORED_KEYS:
        raise HandoffError("stored handoff has an unsupported schema")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise HandoffError("stored handoff has an unsupported schema version")
    created_at = value.get("created_at")
    if not isinstance(created_at, str):
        raise HandoffError("stored handoff created_at must be an ISO timestamp")
    try:
        parsed_time = dt.datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise HandoffError("stored handoff created_at must be an ISO timestamp") from exc
    if parsed_time.tzinfo is None:
        raise HandoffError("stored handoff created_at must include a timezone")
    if not isinstance(value.get("project_id"), str) or not PROJECT_ID_RE.fullmatch(
        value["project_id"]
    ):
        raise HandoffError("stored handoff project_id is invalid")
    if not isinstance(value.get("project_slug"), str) or not PROJECT_SLUG_RE.fullmatch(
        value["project_slug"]
    ):
        raise HandoffError("stored handoff project_slug is invalid")
    git = value.get("git")
    if not isinstance(git, dict) or set(git) != {"commit", "dirty"}:
        raise HandoffError("stored handoff git provenance is invalid")
    commit = git.get("commit")
    dirty = git.get("dirty")
    if commit is not None and (not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit)):
        raise HandoffError("stored handoff git commit is invalid")
    if dirty is not None and not isinstance(dirty, bool):
        raise HandoffError("stored handoff git dirty state is invalid")

    normalized_input = validate_input({key: value[key] for key in INPUT_KEYS})
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "project_id": value["project_id"],
        "project_slug": value["project_slug"],
        "git": {"commit": commit, "dirty": dirty},
        **normalized_input,
    }
    encoded = json.dumps(normalized, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_STORED_BYTES:
        raise HandoffError(f"stored handoff exceeds {MAX_STORED_BYTES} bytes")
    return normalized


def parse_record(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_STORED_BYTES:
        raise HandoffError(f"stored handoff exceeds {MAX_STORED_BYTES} bytes")
    try:
        text = data.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_pairs_object)
    except HandoffError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise HandoffError("stored handoff is not valid UTF-8 JSON") from exc
    return validate_record(value)


def render_text(record: dict[str, Any]) -> str:
    value = validate_record(record)
    commit = value["git"]["commit"]
    dirty = value["git"]["dirty"]
    lines = [
        f"Handoff: {value['source_client']} -> {value['target_client']}",
        f"Created: {value['created_at']}",
        f"Git: {commit or 'unknown'}; dirty={str(dirty).lower() if dirty is not None else 'unknown'}",
        f"Objective: {value['objective']}",
        "Completed:",
    ]
    lines.extend(f"  - {item}" for item in value["completed"])
    if not value["completed"]:
        lines.append("  - none recorded")
    lines.append("Changed files:")
    lines.extend(f"  - {item}" for item in value["changed_files"])
    if not value["changed_files"]:
        lines.append("  - none")
    lines.append("Checks:")
    for check in value["checks"]:
        detail = f" -- {check['summary']}" if check["summary"] else ""
        lines.append(f"  - [{check['status']}] {check['command']}{detail}")
    if not value["checks"]:
        lines.append("  - none recorded")
    lines.append("Open risks:")
    lines.extend(f"  - {item}" for item in value["open_risks"])
    if not value["open_risks"]:
        lines.append("  - none recorded")
    lines.append(f"Next action: {value['next_action']}")
    return "\n".join(lines) + "\n"
