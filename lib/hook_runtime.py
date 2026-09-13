#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

VERSION = "1.0.0-rc.1"

GIT_LOCAL_ENVIRONMENT = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_EXEC_PATH",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_INTERNAL_SUPER_PREFIX",
    "GIT_NAMESPACE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}

DESTRUCTIVE_PATTERNS = [
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[^\n]*\b[fdxX]",
    r"\bgit\s+push\b[^\n]*(?:--force(?:-with-lease)?|-f)\b",
    r"\brm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)",
    r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sh|bash|zsh)\b",
]

# Paths that an agent should never retrieve through shell/file tools.  This is a
# secondary deterministic guard.  Claude sandbox credentials and Codex
# filesystem denies are the primary enforcement boundaries.
SENSITIVE_PATH_PATTERNS = [
    r"(?<![A-Za-z0-9_.-])\.env(?!\.(?:example|sample|template)(?:\b|\.))(?:\.[A-Za-z0-9_.-]+)?(?:\b|$)",
    r"(?:^|[/\\])\.ssh(?:[/\\]|$)",
    r"(?:^|[/\\])id_(?:rsa|ed25519)(?:\.pub)?(?:\b|$)",
    r"(?:^|[/\\])\.aws[/\\]credentials(?:\b|$)",
    r"(?:^|[/\\])\.config[/\\]gcloud[/\\]application_default_credentials\.json(?:\b|$)",
    r"(?:^|[/\\])credentials(?:\.json)?(?:\b|$)",
    r"(?:^|[/\\])[^/\\\s]+\.pem(?:\b|$)",
    r"(?:^|[/\\])\.netrc(?:\b|$)",
    r"(?:^|[/\\])\.npmrc(?:\b|$)",
    r"(?:^|[/\\])\.pypirc(?:\b|$)",
]

# Shell environment dumps are disproportionately likely to expose unrelated
# credentials.  They are easy for the user to run manually when truly needed.
# `env`/`printenv` are flagged whenever invoked (with or without arguments);
# `set` is only flagged bare (no flags/arguments), since `set -e`/`set -eu`/
# `set -o pipefail` are common, safe shell-hardening idioms that print
# nothing -- only a bare `set` dumps every shell variable, including
# exported secrets. Found via independent Codex cross-review (2026-08-30):
# the prior pattern flagged `set -eu` as a false positive.
ENV_DUMP_PATTERN = re.compile(r"(^|[;&|]\s*)(?:(?:env|printenv)(?:\s|$)|set\s*(?:[;&|]|$))", re.I)
SECRET_ENV_REFERENCE = re.compile(
    r"\$(?:\{)?[A-Za-z_][A-Za-z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)[A-Za-z0-9_]*(?:\})?",
    re.I,
)


def clean_git_environment() -> dict[str, str]:
    """Remove caller-controlled Git routing/configuration from hook probes."""
    return {
        key: value
        for key, value in os.environ.items()
        if key not in GIT_LOCAL_ENVIRONMENT
        and not key.startswith("GIT_CONFIG_KEY_")
        and not key.startswith("GIT_CONFIG_VALUE_")
    }


def safe_state_directory(project: Path) -> tuple[Path, tuple[int, int]] | None:
    """Return an existing, non-symlinked state directory anchored in project."""
    root = project.resolve()
    agents = root / ".agents"
    state_dir = agents / "state"
    for directory in (agents, state_dir):
        try:
            mode = directory.lstat().st_mode
        except OSError:
            return None
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            return None
    try:
        if state_dir.resolve() != state_dir:
            return None
        state_stat = state_dir.stat()
    except OSError:
        return None
    return state_dir, (state_stat.st_dev, state_stat.st_ino)


def atomic_json(path: Path, data: Any, parent_identity: tuple[int, int]) -> None:
    """Replace a state file through a verified directory descriptor."""
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(path.parent, directory_flags)
    temp_name = f".{path.name}.aw-{secrets.token_hex(12)}"
    created = False
    try:
        directory_stat = os.fstat(directory_fd)
        if (directory_stat.st_dev, directory_stat.st_ino) != parent_identity:
            raise OSError("managed state directory changed during hook execution")
        file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        file_flags |= getattr(os, "O_NOFOLLOW", 0)
        file_fd = os.open(temp_name, file_flags, 0o600, dir_fd=directory_fd)
        created = True
        with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        os.replace(
            temp_name,
            path.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        created = False
    finally:
        if created:
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except OSError:
                pass
        os.close(directory_fd)


def run(cmd: list[str], cwd: Path, timeout: float = 1.0) -> str:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=clean_git_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:
        return ""


def classify(prompt: str) -> tuple[str, str, list[str]]:
    text = prompt.lower()
    complex_words = (
        "architecture",
        "arquitetura",
        "migration",
        "migração",
        "authentication",
        "autenticação",
        "authorization",
        "security",
        "segurança",
        "database schema",
        "breaking change",
        "production",
        "deploy",
        "multi-agent",
        "refactor across",
        "monorepo",
    )
    medium_words = (
        "refactor",
        "implement",
        "implemente",
        "feature",
        "bug",
        "test",
        "review",
        "endpoint",
        "api",
        "database",
        "sql",
    )
    reasons: list[str] = []
    if any(word in text for word in complex_words) or len(prompt) > 2200:
        reasons.append("high-risk or cross-cutting task signal")
        return "complex", "high", reasons
    if any(word in text for word in medium_words) or len(prompt) > 700:
        reasons.append("multi-step implementation or review signal")
        return "standard", "medium", reasons
    reasons.append("small/local task signal")
    return "trivial", "low", reasons


def deny(reason: str) -> dict[str, Any]:
    # Current Claude Code and Codex both accept this PreToolUse shape.
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def sensitive_reference(text: str) -> bool:
    if not text:
        return False
    return any(re.search(pattern, text, re.I) for pattern in SENSITIVE_PATH_PATTERNS)


def patch_target_paths(serialized_input: str) -> str:
    """Extract file targets from apply_patch metadata, excluding patch bodies."""
    return " ".join(
        match.group(1).strip()
        for match in re.finditer(
            r"^\*\*\* (?:Add|Delete|Update) File:\s*(.+)$",
            serialized_input,
            re.MULTILINE,
        )
    )


def unsafe_shell(command: str) -> str | None:
    if not command:
        return None
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.I):
            return "Blocked destructive or unreviewed remote-script command."
    if sensitive_reference(command):
        return "Blocked shell access to a sensitive credential path. Use an example/template file instead."
    if ENV_DUMP_PATTERN.search(command):
        return "Blocked broad environment dump because it can expose credentials. Inspect a known non-secret variable explicitly instead."
    if SECRET_ENV_REFERENCE.search(command):
        return "Blocked direct shell expansion of a likely secret environment variable."
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Known, accepted failure mode: a malformed/unparseable stdin payload
        # makes this hook a silent no-op (fail-open) rather than blocking the
        # calling CLI. This is deliberate, not an oversight -- this hook is a
        # secondary deterministic guard (see the SENSITIVE_PATH_PATTERNS
        # comment above); the real enforcement boundary is Claude's sandbox
        # config / Codex's filesystem denies (Layer 1), which do not depend
        # on this process parsing anything. Do not turn this into a hard
        # failure without re-checking that boundary first.
        return

    event = str(payload.get("hook_event_name") or "")
    cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
    root_text = run(["git", "rev-parse", "--show-toplevel"], cwd, 0.8)
    candidate = Path(root_text).resolve() if root_text else None
    project = (
        candidate
        if candidate is not None
        and candidate.is_dir()
        and (candidate == cwd or candidate in cwd.parents)
        else cwd
    )

    if event == "UserPromptSubmit":
        prompt = str(payload.get("prompt") or "")
        level, risk, reasons = classify(prompt)
        # Never persist the raw prompt. Hash is enough to correlate duplicate hook
        # events without turning local state or the Vault into a prompt archive.
        policy = {
            "version": VERSION,
            "level": level,
            "risk": risk,
            "reasons": reasons,
            "updated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()[:24],
        }
        state = safe_state_directory(project)
        if state is None:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": (
                                "Ratchetry did not persist task policy because "
                                ".agents/state is missing or unsafe. Run `ratchery "
                                "refresh` and inspect managed-path symlinks."
                            ),
                        }
                    }
                )
            )
            return
        state_dir, state_identity = state
        try:
            atomic_json(state_dir / "task-policy.json", policy, state_identity)
        except OSError:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": (
                                "Ratchetry could not safely persist task policy. "
                                "Run `ratchery doctor` before continuing."
                            ),
                        }
                    }
                )
            )
            return
        if level == "complex":
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": (
                                "Ratchetry classified this task as complex/high-risk. "
                                "Read the task policy, identify contracts and validation before editing, "
                                "and use a work plan when the change is cross-cutting."
                            ),
                        }
                    }
                )
            )
        return

    if event == "PreToolUse":
        tool_name = re.sub(
            r"[^a-z]", "", str(payload.get("tool_name") or "").lower()
        )
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        command = str(tool_input.get("command") or "")
        path_text = " ".join(
            str(tool_input.get(key) or "")
            for key in ("file_path", "path", "notebook_path")
        )
        # apply_patch and some local function tools carry paths inside command/input.
        serialized = json.dumps(tool_input, ensure_ascii=False)
        patch_payload = command if "*** Begin Patch" in command else serialized
        is_patch_input = (
            tool_name.endswith("applypatch") and "*** Begin Patch" in patch_payload
        )

        reason = None if is_patch_input else unsafe_shell(command)
        if reason:
            print(json.dumps(deny(reason)))
            return
        patch_paths = patch_target_paths(patch_payload) if is_patch_input else ""
        non_shell_paths = patch_paths or path_text
        if sensitive_reference(non_shell_paths) or (
            not command
            and not is_patch_input
            and sensitive_reference(serialized)
        ):
            print(json.dumps(deny("Blocked access to a sensitive credential file.")))
            return
        return

if __name__ == "__main__":
    main()
