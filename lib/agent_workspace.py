#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

try:
    import fcntl  # POSIX advisory locks for the Vault handoff mutation boundary
except ImportError:  # pragma: no cover - memory mutations fail closed off POSIX
    fcntl = None

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - preflight reports this runtime as unsupported
    tomllib = None

# Sibling modules in the same lib/ directory. Python puts the running
# script's own directory at sys.path[0], so this resolves regardless of cwd
# or how ratchery was invoked (bin shim, direct python3 call, etc.).
import adaptive_engine as ae
import context_engine as ce
import efficiency as ef
import memory_engine as me
import tool_router as tr

VERSION = "1.0.0"
# The "v8" embedded below is the managed-block MERGE-FORMAT version, not the
# software's VERSION above -- it identifies the marker syntax merge_project_json()/
# managed()/replace_managed_block() use to find and update their own content inside
# a human-owned file (AGENTS.md, CLAUDE.md, docs/COMMANDS.md, VAULT-INDEX.md).
# Frozen deliberately, not a stale leftover: bumping this string would make
# `ratchery refresh` unable to find the managed block in any project
# already installed under the current format, silently leaving stale content in
# place instead of updating it. Only bump it alongside an explicit migration path
# that recognizes both old and new markers during a transition window -- never
# as a routine version bump. Ratchetry keeps this internal pre-rebrand marker
# unchanged throughout the 1.x compatibility window.
MSTART = "<!-- agent-workspace:v8:start -->"
MEND = "<!-- agent-workspace:v8:end -->"
TSTART = "# agent-workspace:v8:start"
TEND = "# agent-workspace:v8:end"
INDEX_START = "<!-- agent-workspace:v8:index:start -->"
INDEX_END = "<!-- agent-workspace:v8:index:end -->"
COMMANDS_START = "<!-- agent-workspace:v8:commands:start -->"
COMMANDS_END = "<!-- agent-workspace:v8:commands:end -->"
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
RUNTIME_MARKER = ".agents/runtime/agent_workspace.py"
QMD_INDEX = "ratchery-vault"
QMD_COLLECTION = "vault"
QMD_MIN_SAFE = (2, 6, 4)
QMD_LAST_KNOWN_VULNERABLE = (2, 6, 3)
CLAUDE_MIN_SECURITY = (2, 1, 187)
CODEX_MIN_SECURITY = (0, 138, 0)
PROFILE_MAX_SOURCE_BYTES = 32 * 1024 * 1024
BENCHMARK_CONFIGURATION_MAX_FILE_BYTES = 1024 * 1024
BENCHMARK_CONFIGURATION_MAX_TOTAL_BYTES = 8 * 1024 * 1024
BENCHMARK_CONFIGURATION_MAX_FILES = 512
BENCHMARK_CONFIGURATION_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".claudeignore",
    ".claude/settings.json",
    ".codex/config.toml",
    ".codex/hooks.json",
    ".mcp.json",
    ".agents/state/active-agents.json",
    ".agents/state/mcp-enabled.json",
    ".agents/state/ownership.json",
    ".agents/state/project-profile.json",
    ".agents/state/risk-answers.json",
    ".agents/state/tier.json",
)
BENCHMARK_CONFIGURATION_VOLATILE_JSON_KEYS = {
    ".agents/state/active-agents.json": {"generated_at"},
    ".agents/state/ownership.json": {"updated_at"},
    ".agents/state/project-profile.json": {"generated_at"},
    ".agents/state/tier.json": {"timestamp"},
}
BENCHMARK_CONFIGURATION_DIRECTORIES = (
    ".agents/skills",
    ".agents/steering",
    ".claude/agents",
    ".claude/rules",
    ".claude/skills",
    ".codex/agents",
    ".codex/skills",
)
BENCHMARK_CONFIGURATION_PARENTS = (
    ".agents",
    ".agents/state",
    ".claude",
    ".codex",
)

SOURCE_EXT = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts",
    ".go", ".rs", ".rb", ".php", ".cs", ".c", ".h", ".cpp", ".hpp",
    ".swift", ".scala", ".ex", ".exs", ".sql", ".sh", ".bash", ".zsh",
    ".vue", ".svelte", ".dart", ".tf", ".hcl",
}
IGNORE = {
    ".git", ".hg", ".svn", ".agents", ".claude", ".codex", ".idea", ".vscode",
    "node_modules", "vendor", ".venv", "venv", "env", "dist", "build", "target",
    "coverage", ".next", ".nuxt", ".cache", ".turbo", "__pycache__", "graphify-out",
}
MONO = {
    "pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json", "rush.json",
    "WORKSPACE", "WORKSPACE.bazel", "pants.toml",
}
PKG = {
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "mix.exs",
}
CATEGORIES = ["personal", "academic", "learning", "work", "experiments", "archived"]

MANAGED_PROJECT_DIRECTORIES = (
    ".agents",
    ".agents/runtime",
    ".agents/skills",
    ".agents/state",
    ".claude",
    ".claude/agents",
    ".claude/rules",
    ".claude/skills",
    ".codex",
    ".codex/agents",
    "docs",
    "docs/decisions",
    "docs/specs",
    "docs/work",
)
MANAGED_PROJECT_FILES = (
    ".agents/runtime/agent_workspace.py",
    ".agents/state/active-agents.json",
    ".agents/state/mcp-enabled.json",
    ".agents/state/ownership.json",
    ".agents/state/project-id",
    ".agents/state/project-profile.json",
    ".agents/state/project-profile.md",
    ".agents/state/risk-answers.json",
    ".agents/state/task-policy.json",
    ".agents/state/tier-history.jsonl",
    ".agents/state/tier.json",
    ".agents/state/tier.md",
    ".claude/settings.json",
    ".claudeignore",
    ".codex/config.toml",
    ".codex/hooks.json",
    ".gitignore",
    ".gitignore.ratchery",
    ".mcp.json",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/COMMANDS.md",
    "docs/CURRENT_STATE.md",
    "docs/MONOREPO_MAP.md",
    "docs/PROJECT_CONTEXT.md",
    "docs/TOOL_POLICY.md",
    "docs/WORKFLOW.md",
    "docs/decisions/ADR_TEMPLATE.md",
    "docs/specs/DELTA_SPEC_TEMPLATE.md",
    "docs/specs/FULL_SPEC_TEMPLATE.md",
    "docs/work/TASK_TEMPLATE.md",
)
MANAGED_DIRECTORY_MARKERS = (
    "MANAGED_BY_RATCHERY",
    "MANAGED_BY_AGENT_WORKSPACE",  # recognized only for safe legacy migration
)


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def xdg_base(variable: str, fallback: Path) -> Path:
    """Return an absolute XDG base, ignoring spec-invalid relative values."""
    configured = os.environ.get(variable)
    base = Path(configured).expanduser() if configured else fallback
    return base if base.is_absolute() else fallback


def config_path() -> Path:
    return (
        xdg_base("XDG_CONFIG_HOME", Path.home() / ".config")
        / "ratchery"
        / "config.json"
    )


def legacy_config_path() -> Path:
    """Previous private-development config location, read-only for migration."""
    return (
        xdg_base("XDG_CONFIG_HOME", Path.home() / ".config")
        / "agent-workspace"
        / "config.json"
    )


def config_read_path() -> Path:
    """Prefer Ratchetry config; accept one regular legacy config if needed."""
    current = config_path()
    if current.exists() or current.is_symlink():
        return current
    legacy = legacy_config_path()
    if legacy.is_file() and not legacy.is_symlink():
        return legacy
    return current


def state_root() -> Path:
    return xdg_base("XDG_STATE_HOME", Path.home() / ".local/state") / "ratchery"


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "project"


def exists(command: str) -> bool:
    return shutil.which(command) is not None


def command_version_probe(command: str, timeout: float = 4) -> tuple[str | None, str | None]:
    """Probe a CLI's version, reporting *why* the probe came back empty.

    Returns ``(version_text, failure)``. ``failure`` is None on success,
    otherwise one of:

    - ``"absent"``   -- the command is not installed at all;
    - ``"transient"`` -- the probe itself never completed (timeout, spawn
      error). This says nothing about the CLI's actual version;
    - ``"unreadable"`` -- the CLI ran and answered unusably (non-zero exit,
      empty output). That is a real defect in the installed tool.

    The distinction exists because callers gate on it: a probe that timed out
    on a loaded CI runner is not evidence that a security-policy floor was
    violated, and reporting it as one makes the gate flaky. Only a version that
    was actually read and found wanting is a hard failure.
    """
    if not exists(command):
        return None, "absent"
    transient = False
    for args in ([command, "--version"], [command, "version"]):
        try:
            result = run(args, cwd=Path.home(), timeout=timeout)
        except (subprocess.TimeoutExpired, OSError):
            transient = True
            continue
        except Exception:
            transient = True
            continue
        if result.returncode != 0:
            continue
        text = (result.stdout + " " + result.stderr).strip()
        if text:
            return text.splitlines()[0][:200], None
    return None, "transient" if transient else "unreadable"


def command_version(command: str, timeout: float = 4) -> str | None:
    """The version string, or None for any reason. Callers that must tell an
    unmeasurable probe from a bad answer use :func:`command_version_probe`."""
    return command_version_probe(command, timeout=timeout)[0]


def parse_semver(text: str | None) -> tuple[int, int, int] | None:
    if not text:
        return None
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", text)
    if not match:
        return None
    return tuple(int(x) for x in match.groups())


def qmd_security_state() -> tuple[str, str]:
    if not exists("qmd"):
        return "missing", "QMD is not installed"
    raw = command_version("qmd") or "unknown version"
    version = parse_semver(raw)
    if version is None:
        return "unknown", f"QMD version could not be verified ({raw})"
    if version <= QMD_LAST_KNOWN_VULNERABLE:
        return "blocked", f"QMD {'.'.join(map(str, version))} is blocked by Ratchetry because <=2.6.3 has project-local trust issues"
    if version < QMD_MIN_SAFE:
        return "blocked", f"QMD {'.'.join(map(str, version))} is below the minimum accepted safe version 2.6.4"
    return "safe", f"QMD {'.'.join(map(str, version))} passes the Ratchetry version gate"


def cli_security_version_issue(
    command: str, label: str, minimum: tuple[int, int, int]
) -> tuple[str, str] | None:
    """Check an installed CLI against the supported policy floor.

    Returns ``(severity, message)`` with severity ``"error"`` or ``"warning"``,
    or None when the CLI is absent or new enough.

    Severity separates a *verdict* from a *failed measurement*. A version that
    was read and is below the floor is an error: the check ran and the answer
    is bad. A probe that never completed -- a timeout on a busy CI runner, a
    spawn failure -- is a warning: it reports that the floor is unverified, not
    that it was violated. Reporting the second as the first makes a security
    gate fail for reasons that have nothing to do with security, which is the
    fastest way to teach a team to ignore it.
    """
    raw, failure = command_version_probe(command)
    minimum_text = ".".join(map(str, minimum))
    if failure == "absent":
        return None
    if failure == "transient":
        return (
            "warning",
            f"{label} version could not be verified (the version probe did not complete); "
            f"require >= {minimum_text}. This is an unverified check, not a known-bad "
            "version -- re-run `doctor` on an idle machine to confirm.",
        )
    version = parse_semver(raw)
    if version is None:
        return (
            "error",
            f"{label} version could not be verified ({raw or 'no version output'}); "
            f"require >= {minimum_text}",
        )
    if version < minimum:
        return (
            "error",
            f"{label} {'.'.join(map(str, version))} is below Ratchetry's supported "
            f"security-policy floor; require >= {minimum_text}",
        )
    return None


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.aw-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def managed_project_layout_issues(project_root: Path) -> list[str]:
    """Reject managed paths that can escape the selected project via symlinks."""
    root = project_root.resolve()
    issues: list[str] = []
    blocked_parents: set[str] = set()

    def below_blocked_parent(rel: str) -> bool:
        return any(rel == parent or rel.startswith(parent + "/") for parent in blocked_parents)

    for rel in MANAGED_PROJECT_DIRECTORIES:
        if below_blocked_parent(rel):
            continue
        target = root / rel
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            issues.append(f"Cannot inspect managed directory {rel}: {exc}")
            continue
        if stat.S_ISLNK(mode):
            issues.append(f"Managed directory {rel} must not be a symlink")
            blocked_parents.add(rel)
        elif not stat.S_ISDIR(mode):
            issues.append(f"Managed directory {rel} must be a real directory")
            blocked_parents.add(rel)
    for rel in MANAGED_PROJECT_FILES:
        if below_blocked_parent(rel):
            continue
        target = root / rel
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            issues.append(f"Cannot inspect managed file {rel}: {exc}")
            continue
        if stat.S_ISLNK(mode):
            issues.append(f"Managed file {rel} must not be a symlink")
        elif not stat.S_ISREG(mode):
            issues.append(f"Managed file {rel} must be a regular file")
    return issues


def require_safe_project_layout(project_root: Path) -> None:
    issues = managed_project_layout_issues(project_root)
    if issues:
        raise ValueError("Unsafe project layout: " + "; ".join(issues))


def transactional_file_update(changes: list[tuple[Path, bytes | None]]) -> None:
    """Apply prepared file replacements with process-level rollback on failure."""
    snapshots: list[tuple[Path, bytes | None]] = []
    for path, _data in changes:
        if path.is_symlink():
            raise ValueError(f"Refusing to update symlinked file: {path}")
        snapshots.append((path, path.read_bytes() if path.exists() else None))
    try:
        for path, data in changes:
            if data is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write_bytes(path, data)
    except Exception as exc:
        rollback_failures: list[str] = []
        for path, data in reversed(snapshots):
            try:
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write_bytes(path, data)
            except Exception as rollback_exc:
                rollback_failures.append(f"{path}: {rollback_exc}")
        if rollback_failures:
            raise RuntimeError(
                f"configuration update failed ({exc}); rollback also failed: "
                + "; ".join(rollback_failures)
            ) from exc
        raise


def write_benchmark_snapshot(path: Path, data: Any, *, replace: bool) -> None:
    """Write one snapshot without a check-then-overwrite race."""
    payload = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.aw-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        if replace:
            os.replace(tmp_name, path)
        else:
            try:
                os.link(tmp_name, path)
            except FileExistsError as exc:
                raise ef.BenchmarkError(
                    f"benchmark '{path.stem}' already exists; pass --replace to overwrite it"
                ) from exc
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def run(
    cmd: list[str],
    cwd: Path | None = None,
    timeout: float = 120,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def clean_git_environment() -> dict[str, str]:
    """Return an environment without caller-controlled Git repository routing."""
    environment = os.environ.copy()
    for variable in list(environment):
        if (
            variable in GIT_LOCAL_ENVIRONMENT
            or variable.startswith("GIT_CONFIG_")
        ):
            environment.pop(variable, None)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return environment


def safe_git_read_command(*arguments: str) -> list[str]:
    """Build a read-only Git command that cannot invoke repository fsmonitor hooks."""
    return [
        "git",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "submodule.recurse=false",
        *arguments,
    ]


def cfg() -> dict[str, Any]:
    return load_json(
        config_read_path(),
        {
            "version": VERSION,
            "vault_path": None,
            "projects_root": str(Path.home() / "Projects"),
            "project_layout": "flat",
            "external_tools": "none",
            "thresholds": {
                "medium_files": 150,
                "medium_lines": 25000,
                "large_files": 800,
                "large_lines": 120000,
                "large_packages": 5,
            },
        },
    )


def save_cfg(data: dict[str, Any]) -> None:
    data["version"] = VERSION
    write_json(config_path(), data)


def configured_vault_path(override: str | Path | None = None) -> Path:
    """Return an explicit/configured Vault path or fail with setup guidance."""
    raw = override if override is not None else cfg().get("vault_path")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise ValueError(
            "Vault memory is not configured. Run `ratchery setup --vault <path>` "
            "to enable it."
        )
    return Path(raw).expanduser()


def setup_vault_path(vault: str | None, no_vault: bool) -> Path | None:
    """Resolve setup's explicit enable/disable/preserve memory selection."""
    if no_vault:
        return None
    if vault:
        return Path(vault)
    configured = cfg().get("vault_path")
    if configured is None or configured == "":
        return None
    if not isinstance(configured, str):
        raise ValueError("Configured Vault path must be a string or null")
    return Path(configured)


def git_root(path: Path) -> Path:
    resolved_path = path.resolve()
    if exists("git"):
        try:
            result = run(
                safe_git_read_command("rev-parse", "--show-toplevel"),
                path,
                5,
                env=clean_git_environment(),
            )
            if result.returncode == 0 and result.stdout.strip():
                candidate = Path(result.stdout.strip()).resolve()
                if candidate.is_dir() and (
                    candidate == resolved_path or candidate in resolved_path.parents
                ):
                    return candidate
        except Exception:
            pass
    return resolved_path


def backup_file(path: Path, project_root: Path | None = None, reason: str = "project-update") -> Path | None:
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Refusing to back up non-regular managed file: {path}")
    if project_root is not None:
        require_safe_project_layout(project_root)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    root_label = hashlib.sha256(str((project_root or path.parent).resolve()).encode()).hexdigest()[:12]
    target = state_root() / "project-backups" / root_label / stamp / path.name
    private_root = state_root() / "project-backups"
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    for directory in (private_root, private_root / root_label, target.parent):
        directory.chmod(0o700)
    shutil.copy2(path, target, follow_symlinks=False)
    target.chmod(0o600)
    try:
        source = path.resolve().relative_to(
            (project_root or path.parent).resolve()
        ).as_posix()
    except ValueError:
        source = path.name
    manifest_path = target.parent / "manifest.json"
    write_json(
        manifest_path,
        {"version": VERSION, "created_at": now(), "reason": reason, "source": source},
    )
    manifest_path.chmod(0o600)
    return target.parent


def replace_managed_block(old: str, body: str, start: str, end: str) -> str:
    block = f"{start}\n{body.strip()}\n{end}"
    existing_body = text_block_body(old, start, end)
    if existing_body is not None:
        a = old.index(start)
        z = old.index(end, a) + len(end)
        return (old[:a] + block + old[z:]).rstrip() + "\n"
    return (old.rstrip() + ("\n\n" if old.strip() else "") + block).rstrip() + "\n"


def read_managed_text(path: Path) -> str:
    """Read an existing managed file without following its final symlink."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise ValueError(f"Cannot safely read managed file {path}: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"Managed path must be a regular file: {path}")
        with os.fdopen(descriptor, "r", encoding="utf-8", errors="replace") as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def managed(path: Path, body: str, start: str = MSTART, end: str = MEND) -> None:
    old = read_managed_text(path)
    new = replace_managed_block(old, body, start, end)
    if new != old:
        atomic_write_text(path, new)


def copy_if_missing(src: Path, dst: Path) -> None:
    if dst.is_symlink():
        raise ValueError(f"Refusing to write through symlinked file: {dst}")
    if dst.exists():
        if not dst.is_file():
            raise ValueError(f"Expected a regular file: {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def managed_directory_marker(path: Path) -> Path | None:
    """Return a real ownership sentinel, accepting the pre-rebrand name."""
    for name in MANAGED_DIRECTORY_MARKERS:
        marker = path / name
        if marker.is_file() and not marker.is_symlink():
            return marker
    return None


def copy_managed_dir(src: Path, dst: Path) -> None:
    """Update only directories previously marked as Ratchetry-managed."""
    if dst.exists() and managed_directory_marker(dst) is None:
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    (dst / "MANAGED_BY_RATCHERY").write_text(VERSION + "\n")


def unique_list(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def hook_runtime_reference(hook: dict[str, Any]) -> str:
    """Search command and exec-form arguments for our immutable ownership marker."""
    return str(hook.get("command", "")) + "\n" + json.dumps(
        hook.get("args", []), ensure_ascii=False
    )


def is_owned_hook_group(group: Any) -> bool:
    if not isinstance(group, dict):
        return False
    hooks = group.get("hooks") or []
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(h, dict) and RUNTIME_MARKER in hook_runtime_reference(h)
        for h in hooks
    )


def merge_hook_maps(existing: dict[str, Any], managed_hooks: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    all_events = list(dict.fromkeys([*existing.keys(), *managed_hooks.keys()]))
    for event in all_events:
        old_groups = existing.get(event, []) if isinstance(existing.get(event, []), list) else []
        kept = [g for g in old_groups if not is_owned_hook_group(g)]
        new_groups = managed_hooks.get(event, []) if isinstance(managed_hooks.get(event, []), list) else []
        combined = kept + new_groups
        if combined:
            result[event] = combined
    return result


def merge_project_json(path: Path, patch: dict[str, Any], project_root: Path, kind: str) -> None:
    existing = load_json(path, {})
    if not isinstance(existing, dict):
        existing = {}
    # Deep copy, not dict(existing): a shallow copy shares nested dict/list
    # objects with `existing`, and recursive() below mutates dst[key] for a
    # nested dict *in place* rather than reassigning it -- with a shallow
    # copy that mutation also lands on `existing`, so the `merged != existing`
    # check below can never detect a nested-field change and silently skips
    # the write. Found via a unit test that merges into an already-present
    # nested key (e.g. sandbox.enabled) and asserts the file actually changed.
    merged = copy.deepcopy(existing)

    def recursive(dst: dict[str, Any], src: dict[str, Any], prefix: tuple[str, ...] = ()) -> None:
        for key, value in src.items():
            pfx = prefix + (key,)
            if key == "hooks" and isinstance(value, dict):
                dst[key] = merge_hook_maps(dst.get(key, {}) if isinstance(dst.get(key), dict) else {}, value)
            elif isinstance(value, dict) and isinstance(dst.get(key), dict):
                recursive(dst[key], value, pfx)
            elif isinstance(value, list) and isinstance(dst.get(key), list):
                # Security and deny arrays are additive. Other user arrays are preserved
                # with Ratchetry entries appended rather than replaced.
                dst[key] = unique_list(dst[key] + value)
            else:
                dst[key] = value

    recursive(merged, patch)
    if merged != existing:
        backup_file(path, project_root, kind)
        write_json(path, merged)


def merge_codex_hooks(path: Path, patch: dict[str, Any], project_root: Path) -> None:
    existing = load_json(path, {})
    if not isinstance(existing, dict):
        existing = {}
    existing_hooks = existing.get("hooks", {}) if isinstance(existing.get("hooks", {}), dict) else {}
    patch_hooks = patch.get("hooks", {}) if isinstance(patch.get("hooks", {}), dict) else {}
    result = dict(existing)
    result["description"] = patch.get("description", existing.get("description", ""))
    result["hooks"] = merge_hook_maps(existing_hooks, patch_hooks)
    if result != existing:
        backup_file(path, project_root, "codex-hooks-update")
        write_json(path, result)


def mcp_opt_in_path(project_root: Path) -> Path:
    return project_root / ".agents/state/mcp-enabled.json"


def mcp_opted_in(project_root: Path) -> set[str]:
    marker = mcp_opt_in_path(project_root)
    if not marker.exists():
        return set()
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("MCP opt-in state must be a regular file")
    try:
        data = json.loads(marker.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Invalid MCP opt-in state: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(name, str) for name in data):
        raise ValueError("Invalid MCP opt-in state: expected a JSON array of server names")
    unknown = sorted(set(data) - set(KNOWN_MCP_SERVERS))
    if unknown:
        raise ValueError(f"Invalid MCP opt-in state: unknown server(s): {', '.join(unknown)}")
    return set(data)


def remove_legacy_auto_mcp(path: Path) -> None:
    """Remove only the exact MCP definitions v8.1 auto-injected when policy is
    none -- but never a server the user explicitly opted into via
    `ratchery mcp enable`. Bug found via independent Codex
    cross-review (2026-08-30): this used to run unconditionally on every
    init/refresh, so it silently deleted an explicit `mcp enable` opt-in the
    very next time the project was refreshed, which is exactly the kind of
    "your decision doesn't stick" behavior the risk ratchet exists to
    prevent elsewhere in this codebase."""
    if not path.exists():
        return
    data = load_json(path, {})
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return
    opted_in = mcp_opted_in(path.parent)
    known_context7 = {"type": "http", "url": "https://mcp.context7.com/mcp"}
    known_serena_claude = {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/oraios/serena@v1.6.0", "serena", "start-mcp-server", "--context", "claude-code"],
    }
    changed = False
    if servers.get("context7") == known_context7 and "context7" not in opted_in:
        servers.pop("context7", None); changed = True
    if servers.get("serena") == known_serena_claude and "serena" not in opted_in:
        servers.pop("serena", None); changed = True
    if changed:
        if not servers:
            data.pop("mcpServers", None)
        write_json(path, data)


SERENA_V1_7_0_COMMIT = "949a27ef1e5fda1a6e7b561e777bcece345c6ffd"

KNOWN_MCP_SERVERS: dict[str, dict[str, Any]] = {
    "context7": {"type": "http", "url": "https://mcp.context7.com/mcp"},
    "serena": {
        "command": "uvx",
        "args": [
            "--from",
            f"git+https://github.com/oraios/serena@{SERENA_V1_7_0_COMMIT}",
            "serena",
            "start-mcp-server",
            "--context",
            "claude-code",
            "--project-from-cwd",
            "--open-web-dashboard",
            "false",
        ],
    },
}

CODEX_MCP_BLOCKS = {
    "context7": """[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"
enabled = true
required = false
enabled_tools = ["resolve-library-id", "query-docs"]
startup_timeout_sec = 10
tool_timeout_sec = 30
default_tools_approval_mode = "prompt"

[mcp_servers.context7.tools."resolve-library-id"]
approval_mode = "prompt"
output_token_limit = 2000

[mcp_servers.context7.tools."query-docs"]
approval_mode = "prompt"
output_token_limit = 6000""",
    "serena": f"""[mcp_servers.serena]
command = "uvx"
args = ["--from", "git+https://github.com/oraios/serena@{SERENA_V1_7_0_COMMIT}", "serena", "start-mcp-server", "--context", "codex", "--project-from-cwd", "--open-web-dashboard", "false"]
enabled = true
required = false
enabled_tools = ["get_symbols_overview", "find_symbol", "find_referencing_symbols"]
startup_timeout_sec = 30
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"

[mcp_servers.serena.tools.get_symbols_overview]
approval_mode = "prompt"
output_token_limit = 4000

[mcp_servers.serena.tools.find_symbol]
approval_mode = "prompt"
output_token_limit = 8000

[mcp_servers.serena.tools.find_referencing_symbols]
approval_mode = "prompt"
output_token_limit = 6000""",
}


def codex_mcp_markers(name: str) -> tuple[str, str]:
    return (
        f"# agent-workspace:mcp:{name}:start",
        f"# agent-workspace:mcp:{name}:end",
    )


def text_block_body(text: str, start: str, end: str) -> str | None:
    """Return one managed block's body, rejecting ambiguous/corrupt markers."""
    start_count = text.count(start)
    end_count = text.count(end)
    if start_count == end_count == 0:
        return None
    if start_count != 1 or end_count != 1:
        raise ValueError(f"Malformed managed block: expected exactly one {start!r} and {end!r}")
    begin = text.index(start)
    finish = text.find(end, begin + len(start))
    if finish < 0:
        raise ValueError(f"Malformed managed block: {end!r} must follow {start!r}")
    return text[begin + len(start) : finish].strip()


def remove_text_block(text: str, start: str, end: str) -> tuple[str, bool]:
    if text_block_body(text, start, end) is None:
        return text, False
    begin = text.index(start)
    finish = text.index(end, begin) + len(end)
    return (text[:begin] + text[finish:]).strip() + "\n", True


def read_codex_config(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing regular .codex/config.toml; run `ratchery init` first")
    try:
        return path.read_text()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Invalid .codex/config.toml: {exc}") from exc


def read_mcp_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{path.name} must be a regular file")
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Invalid {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {path.name}: expected a JSON object")
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError(f"Invalid {path.name}: mcpServers must be a JSON object")
    return data


def mcp_enable(path: Path, name: str) -> None:
    """Explicit, one-at-a-time opt-in for an optional MCP integration. Never
    called automatically -- the framework's own security posture (see
    docs/decision-matrix.md section D) is that MCP schemas stay out of a
    project's context until a human deliberately asks for them. The command
    writes static, reviewable Claude and Codex definitions and a shared marker
    so refresh remains reversible and team-durable."""
    if not tomllib:
        raise ValueError("MCP configuration requires Python 3.11+")
    require_safe_project_layout(path)
    opted_in = mcp_opted_in(path)
    mcp_path = path / ".mcp.json"
    data = read_mcp_json(mcp_path)
    servers = data.setdefault("mcpServers", {})
    existing_server = servers.get(name)
    if existing_server is not None and existing_server != KNOWN_MCP_SERVERS[name]:
        raise ValueError(
            f"Refusing to overwrite user-owned MCP server '{name}' in {mcp_path.name}"
        )

    codex_path = path / ".codex/config.toml"
    codex_text = read_codex_config(codex_path)
    start, end = codex_mcp_markers(name)
    managed_codex_body = text_block_body(codex_text, start, end)
    if tomllib:
        try:
            parsed_codex = tomllib.loads(codex_text)
        except Exception as exc:
            raise ValueError(f"Invalid .codex/config.toml: {exc}") from exc
        existing_codex = parsed_codex.get("mcp_servers", {})
        if isinstance(existing_codex, dict) and name in existing_codex:
            if managed_codex_body is None:
                raise ValueError(
                    f"Refusing to overwrite user-owned Codex MCP server '{name}'"
                )
            if managed_codex_body != CODEX_MCP_BLOCKS[name].strip():
                raise ValueError(
                    f"Refusing to overwrite modified/user-owned Codex MCP server '{name}'"
                )
    new_codex = replace_managed_block(codex_text, CODEX_MCP_BLOCKS[name], start, end)
    if tomllib:
        try:
            tomllib.loads(new_codex)
        except Exception as exc:
            raise ValueError(f"Generated Codex MCP config is invalid: {exc}") from exc

    claude_changed = existing_server is None
    servers[name] = KNOWN_MCP_SERVERS[name]
    opt_in_data = (
        json.dumps(sorted(opted_in | {name}), indent=2, ensure_ascii=False) + "\n"
    ).encode()
    changes: list[tuple[Path, bytes | None]] = [(mcp_opt_in_path(path), opt_in_data)]
    if new_codex != codex_text:
        backup_file(codex_path, path, f"mcp-enable-{name}")
        changes.append((codex_path, new_codex.encode()))
    if claude_changed:
        backup_file(mcp_path, path, f"mcp-enable-{name}")
        changes.append(
            (
                mcp_path,
                (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode(),
            )
        )
    # Enable records intent first. If the process is interrupted between
    # replacements, doctor sees the missing client side and fails closed.
    transactional_file_update(changes)


def mcp_disable(path: Path, name: str) -> bool:
    require_safe_project_layout(path)
    mcp_path = path / ".mcp.json"
    opted_in = mcp_opted_in(path)
    if name not in opted_in:
        return False
    data = read_mcp_json(mcp_path)
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if isinstance(servers, dict) and name in servers and servers[name] != KNOWN_MCP_SERVERS[name]:
        raise ValueError(
            f"Refusing to remove modified/user-owned MCP server '{name}' from {mcp_path.name}"
        )
    codex_path = path / ".codex/config.toml"
    codex_text = read_codex_config(codex_path)
    start, end = codex_mcp_markers(name)
    codex_body = text_block_body(codex_text, start, end)
    if codex_body is not None and codex_body != CODEX_MCP_BLOCKS[name].strip():
        raise ValueError(
            f"Refusing to remove modified/user-owned Codex MCP server '{name}'"
        )
    new_codex, removed_codex = remove_text_block(codex_text, start, end)

    # Both client configurations are validated before either is mutated.
    removed_claude = isinstance(servers, dict) and name in servers
    if removed_claude:
        servers.pop(name, None)
        if not servers:
            data.pop("mcpServers", None)
        backup_file(mcp_path, path, f"mcp-disable-{name}")
    if removed_codex:
        backup_file(codex_path, path, f"mcp-disable-{name}")

    opted_in = opted_in - {name}
    opt_in_path = mcp_opt_in_path(path)
    changes: list[tuple[Path, bytes | None]] = []
    if removed_claude:
        changes.append(
            (
                mcp_path,
                (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode(),
            )
        )
    if removed_codex:
        changes.append((codex_path, new_codex.encode()))
    marker_data = (
        (json.dumps(sorted(opted_in), indent=2, ensure_ascii=False) + "\n").encode()
        if opted_in
        else None
    )
    changes.append((opt_in_path, marker_data))
    # Disable removes executable definitions before clearing intent. An
    # interrupted process therefore remains visibly inconsistent to doctor.
    transactional_file_update(changes)
    return removed_claude or removed_codex


def mcp_status(path: Path) -> dict[str, dict[str, bool]]:
    require_safe_project_layout(path)
    data = read_mcp_json(path / ".mcp.json")
    servers = data.get("mcpServers", {}) if isinstance(data, dict) else {}
    codex_text = read_codex_config(path / ".codex/config.toml")
    return {
        name: {
            "claude": name in servers,
            "codex": all(marker in codex_text for marker in codex_mcp_markers(name)),
        }
        for name in KNOWN_MCP_SERVERS
    }


def ensure_project_id(path: Path) -> str:
    require_safe_project_layout(path)
    id_path = path / ".agents/state/project-id"
    value = read_text(id_path).strip()
    if not re.fullmatch(r"[0-9a-f-]{36}", value):
        value = str(uuid.uuid4())
        atomic_write_text(id_path, value + "\n")
    return value


def inspect_project(path: Path) -> dict[str, Any]:
    """Return project facts without creating IDs or writing profile state."""
    conf = cfg(); th = conf["thresholds"]
    files: list[Path] = []; lines = 0; bytes_scanned = 0
    langs: dict[str, int] = {}; packages: list[str] = []
    filenames: set[str] = set()
    for dirpath, dirs, names in os.walk(path):
        dp = Path(dirpath)
        dirs[:] = [d for d in dirs if d not in IGNORE and not (dp / d).is_symlink()]
        for name in names:
            file = dp / name
            # Profiling must stay inside the inspected project. os.walk does not
            # follow symlinked directories by default, but it still returns
            # symlinked files; opening one could read or block on an arbitrary
            # target outside the repository.
            if file.is_symlink() or not file.is_file():
                continue
            filenames.add(str(file.relative_to(path)).lower())
            if name in PKG:
                packages.append(str(file.relative_to(path)))
            if file.suffix.lower() in SOURCE_EXT:
                files.append(file)
                langs[file.suffix.lower()] = langs.get(file.suffix.lower(), 0) + 1
                # Exact line totals are useful only until the repository is
                # already known to be large. Bound total bytes read so a huge
                # generated/sparse source file in an untrusted checkout cannot
                # turn `doctor` into a memory or I/O denial of service.
                if lines > th["large_lines"]:
                    continue
                try:
                    size = file.stat().st_size
                    if bytes_scanned + size > PROFILE_MAX_SOURCE_BYTES:
                        lines = th["large_lines"] + 1
                        continue
                    bytes_scanned += size
                    with file.open(errors="ignore") as fh:
                        lines += sum(1 for _ in fh)
                except OSError:
                    pass
    mono = any((path / marker).exists() for marker in MONO)
    size = "small"
    if mono or len(files) > th["large_files"] or lines > th["large_lines"] or len(packages) >= th["large_packages"]:
        size = "large"
    elif len(files) > th["medium_files"] or lines > th["medium_lines"] or len(packages) >= 2:
        size = "medium"

    package_json_path = path / "package.json"
    package_json = (
        load_json(package_json_path, {})
        if package_json_path.is_file() and not package_json_path.is_symlink()
        else {}
    )
    if not isinstance(package_json, dict):
        package_json = {}
    dependency_groups = [package_json.get("dependencies"), package_json.get("devDependencies")]
    deps = " ".join(
        name
        for group in dependency_groups
        if isinstance(group, dict)
        for name in group
        if isinstance(name, str)
    ).lower()
    pyproject_path = path / "pyproject.toml"
    pyproject = (
        read_text(pyproject_path).lower()
        if pyproject_path.is_file() and not pyproject_path.is_symlink()
        else ""
    )
    code_probe = " ".join(filenames) + " " + deps + " " + pyproject
    has_notebook = any(filename.endswith(".ipynb") for filename in filenames)
    has_cloud_files = any(
        filename.endswith(".tf")
        or Path(filename).name.startswith("dockerfile")
        or Path(filename).name in {"compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"}
        or any(part in {"terraform", "cloudformation", "pulumi", "helm", "k8s", "kubernetes"} for part in Path(filename).parts)
        for filename in filenames
    )
    ai_markers = [
        "torch", "tensorflow", "transformers", "scikit-learn", "sklearn",
        "anthropic", "openai", "langchain", "llamaindex", "litellm",
    ]
    capabilities = {
        "data": has_notebook or any(x in code_probe for x in ["dbt", "airflow", "spark", "dagster", "prefect"]) or langs.get(".sql", 0) >= 8,
        "frontend": any(x in deps for x in ["react", "next", "vue", "svelte", "angular", "vite"]),
        "database": any((path / x).exists() for x in ["alembic.ini", "migrations", "prisma", "dbt_project.yml"]) or langs.get(".sql", 0) >= 3,
        "api": any(x in code_probe for x in ["fastapi", "flask", "django", "express", "nestjs", "openapi", "swagger"]),
        "cloud_infra": has_cloud_files or any(x in code_probe for x in ["serverless.yml", "serverless.yaml", "cdk.json", "aws-cdk"]),
        "ai_ml": has_notebook or any(x in code_probe for x in ai_markers),
    }
    return {
        "project": path.name,
        "slug": slug(path.name),
        "size": size,
        "source_files": len(files),
        "source_lines": lines,
        "package_roots": sorted(packages),
        "monorepo": mono,
        "languages": langs,
        "capabilities": capabilities,
        "initial_file_budget": 3 if size == "small" else 6 if size == "medium" else 4,
    }


def profile(path: Path) -> dict[str, Any]:
    require_safe_project_layout(path)
    data = {
        **inspect_project(path),
        "version": VERSION,
        "generated_at": now(),
        "project_id": ensure_project_id(path),
    }
    write_json(path / ".agents/state/project-profile.json", data)
    md = (
        "# Project Profile\n\n"
        f"- Size: **{data['size']}**\n"
        f"- Source files: {data['source_files']}\n"
        f"- Source lines: {data['source_lines']}\n"
        f"- Packages: {len(data['package_roots'])}\n"
        f"- Monorepo: {str(data['monorepo']).lower()}\n"
        f"- Initial file budget: {data['initial_file_budget']}\n"
        f"- Capabilities: {', '.join(k for k,v in data['capabilities'].items() if v) or 'generic'}\n"
    )
    atomic_write_text(path / ".agents/state/project-profile.md", md)
    return data


def detect_commands_body(path: Path) -> str:
    out: list[str] = []
    if (path / "Makefile").exists():
        out += ["### Make", "```bash", "make help", "make test", "```", ""]
    if (path / "pyproject.toml").exists():
        prefix = "uv run " if (path / "uv.lock").exists() else "poetry run " if (path / "poetry.lock").exists() else ""
        install = "uv sync" if (path / "uv.lock").exists() else "python -m pip install -e ."
        out += ["### Python", "```bash", install, f"{prefix}pytest -q", f"{prefix}ruff check .", f"{prefix}mypy .", "```", ""]
    if (path / "package.json").exists():
        pm = "pnpm" if (path / "pnpm-lock.yaml").exists() else "yarn" if (path / "yarn.lock").exists() else "bun" if any((path / x).exists() for x in ["bun.lock", "bun.lockb"]) else "npm"
        install = {"pnpm": "pnpm install", "yarn": "yarn install", "bun": "bun install", "npm": "npm install"}[pm]
        runp = "" if pm in ["yarn", "bun"] else " run"
        scripts = (load_json(path / "package.json", {}) or {}).get("scripts", {}) or {}
        cmds = [install] + [f"{pm}{runp} {x}" for x in ["test", "lint", "typecheck", "build"] if x in scripts]
        out += ["### JavaScript / TypeScript", "```bash", *cmds, "```", ""]
    if (path / "Cargo.toml").exists():
        out += ["### Rust", "```bash", "cargo test", "cargo clippy --all-targets --all-features", "cargo fmt --check", "```", ""]
    if (path / "go.mod").exists():
        out += ["### Go", "```bash", "go test ./...", "go vet ./...", "```", ""]
    if (path / "pom.xml").exists():
        out += ["### Java / Maven", "```bash", "./mvnw verify", "```", ""]
    if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
        out += ["### Java / Gradle", "```bash", "./gradlew test", "```", ""]
    if not out:
        out = ["No commands were detected from supported manifests. Add confirmed project-specific commands below.", ""]
    return "\n".join(out).rstrip()


def update_commands_doc(path: Path) -> None:
    doc = path / "docs/COMMANDS.md"
    old = read_text(doc)
    if not old:
        old = (
            "# Project Commands\n\n"
            "Automatically detected commands are managed by Ratchetry. "
            "Keep human notes outside the managed block.\n\n"
            "## Automatically detected\n\n"
            "## Project-specific notes\n\n"
            "Add confirmed commands, caveats, environment setup, and deployment notes here.\n"
        )
    new = replace_managed_block(old, detect_commands_body(path), COMMANDS_START, COMMANDS_END)
    if new != old:
        atomic_write_text(doc, new)


def install_conditional_skills(path: Path, profile_data: dict[str, Any]) -> None:
    assets = package_root() / "assets/project/conditional-skills"
    mapping = {
        "data": "data-pipeline-review",
        "frontend": "frontend-a11y-review",
        "database": "database-migration-review",
        "api": "api-contract-review",
    }
    for capability, skill in mapping.items():
        enabled = bool(profile_data.get("capabilities", {}).get(capability))
        for target in [path / ".agents/skills" / skill, path / ".claude/skills" / skill]:
            if enabled and (assets / skill).exists():
                copy_managed_dir(assets / skill, target)
            elif not enabled and target.exists() and managed_directory_marker(target):
                shutil.rmtree(target)


def write_ownership_manifest(path: Path, profile_data: dict[str, Any]) -> None:
    data = {
        "version": VERSION,
        "updated_at": now(),
        "project_id": profile_data["project_id"],
        "managed_markers": [MSTART, TSTART, COMMANDS_START],
        "owned_hook_command_contains": RUNTIME_MARKER,
        "runtime": ".agents/runtime/agent_workspace.py",
        "conditional_skills": [k for k,v in profile_data.get("capabilities", {}).items() if v],
    }
    write_json(path / ".agents/state/ownership.json", data)


# The four compatibility-baseline agents. Always installed regardless of
# tier/capability -- preserved for backward compatibility and because the
# decision matrix explicitly KEEPs this set unconditionally.
ALWAYS_ON_AGENTS = {"explorer", "reviewer", "security-reviewer", "test-runner"}


def agent_registry() -> dict[str, Any]:
    return load_json(package_root() / "assets/global/skills/registry.json", {"agents": {}})


def registered_global_skills() -> list[str]:
    """Return the exact global Skill inventory or fail on registry/disk drift."""
    registry = agent_registry()
    skills = registry.get("skills") if isinstance(registry, dict) else None
    available = skills.get("available") if isinstance(skills, dict) else None
    if (
        not isinstance(available, list)
        or not all(isinstance(name, str) and name for name in available)
        or len(available) != len(set(available))
    ):
        raise ValueError("Global Skill registry must contain unique skills.available names")
    assets = package_root() / "assets/global/skills"
    on_disk = {
        item.name
        for item in assets.iterdir()
        if item.is_dir() and (item / "SKILL.md").is_file()
    }
    if set(available) != on_disk:
        missing = sorted(set(available) - on_disk)
        unregistered = sorted(on_disk - set(available))
        raise ValueError(
            "Global Skill registry/disk mismatch"
            f" (missing={missing or 'none'}, unregistered={unregistered or 'none'})"
        )
    return available


def active_agent_names(p: dict[str, Any], tier_state: dict[str, Any] | None) -> dict[str, str]:
    """Which agent names should be installed into this project right now, and why.
    Combines the always-on baseline 4 with the registry-driven tier/capability
    resolution -- see adaptive_engine.resolve_active_agents()."""
    effective_tier = (tier_state or {}).get("effective_tier", "T0")
    active = ae.resolve_active_agents(agent_registry(), effective_tier, p.get("capabilities", {}))
    for name in ALWAYS_ON_AGENTS:
        active.setdefault(name, "baseline agent, always installed")
    return active


def install_agents(path: Path, p: dict[str, Any], tier_state: dict[str, Any] | None) -> dict[str, str]:
    """Copy only the currently-active agent set into .claude/agents/ and
    .codex/agents/ (mirrored pair per name). Never deletes an already-copied
    agent file -- activation can only add, matching the framework's
    never-destroy-without-explicit-action policy; `ratchery
    agents-status` surfaces anything that's present but no longer implied by
    the current tier/capabilities so a human can decide whether to remove it."""
    require_safe_project_layout(path)
    assets = package_root() / "assets/project"
    active = active_agent_names(p, tier_state)
    for name in active:
        md = assets / ".claude/agents" / f"{name}.md"
        if md.exists():
            copy_if_missing(md, path / ".claude/agents" / md.name)
        toml = assets / ".codex/agents" / f"{name.replace('-', '_')}.toml"
        if toml.exists():
            copy_if_missing(toml, path / ".codex/agents" / toml.name)
    write_json(path / ".agents/state/active-agents.json", {"generated_at": now(), "tier": (tier_state or {}).get("effective_tier"), "active": active})
    return active


def project_files(path: Path, p: dict[str, Any], tier_state: dict[str, Any] | None = None) -> None:
    require_safe_project_layout(path)
    assets = package_root() / "assets/project"
    managed(path / "AGENTS.md", (assets / "AGENTS.block.md").read_text())
    managed(path / "CLAUDE.md", (assets / "CLAUDE.block.md").read_text())
    for filename in ["PROJECT_CONTEXT.md", "CURRENT_STATE.md", "WORKFLOW.md", "TOOL_POLICY.md"]:
        copy_if_missing(assets / "docs" / filename, path / "docs" / filename)
    copy_if_missing(assets / "docs/decisions/ADR_TEMPLATE.md", path / "docs/decisions/ADR_TEMPLATE.md")
    copy_if_missing(assets / "docs/specs/DELTA_SPEC_TEMPLATE.md", path / "docs/specs/DELTA_SPEC_TEMPLATE.md")
    copy_if_missing(assets / "docs/specs/FULL_SPEC_TEMPLATE.md", path / "docs/specs/FULL_SPEC_TEMPLATE.md")
    copy_if_missing(assets / "docs/work/TASK_TEMPLATE.md", path / "docs/work/TASK_TEMPLATE.md")
    update_commands_doc(path)
    copy_if_missing(assets / "gitignore.block", path / ".gitignore.ratchery")
    managed(path / ".gitignore", (assets / "gitignore.block").read_text(), TSTART, TEND)
    ce.generate_claudeignore(path)
    ce.generate_steering_files(path, p, tier_state)

    runtime = path / ".agents/runtime/agent_workspace.py"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package_root() / "lib/hook_runtime.py", runtime)

    claude_patch = load_json(assets / ".claude/settings.json", {})
    merge_project_json(path / ".claude/settings.json", claude_patch, path, "claude-settings-update")
    for file in (assets / ".claude/rules").glob("*.md"):
        copy_if_missing(file, path / ".claude/rules" / file.name)

    # Legacy releases injected Context7/Serena automatically. This keeps MCP schemas
    # out of every medium/large session unless the user explicitly enables them.
    codex = (assets / ".codex/config.base.toml").read_text()
    managed(path / ".codex/config.toml", codex, TSTART, TEND)
    merge_codex_hooks(path / ".codex/hooks.json", load_json(assets / ".codex/hooks.json", {}), path)

    install_agents(path, p, tier_state)

    if cfg().get("external_tools") == "none":
        remove_legacy_auto_mcp(path / ".mcp.json")

    install_conditional_skills(path, p)

    if p["size"] == "large":
        lines = ["# Monorepo Map", "", "Generated package roots:", ""] + [f"- `{x}`" for x in p["package_roots"]]
        atomic_write_text(path / "docs/MONOREPO_MAP.md", "\n".join(lines) + "\n")
        for marker in p["package_roots"]:
            directory = (path / marker).parent
            if directory == path:
                continue
            managed(
                directory / "AGENTS.md",
                f"# Package scope\n- Work only inside `{directory.relative_to(path)}` unless cross-package impact is proven.\n"
                "- Read the nearest package manifest and tests before editing.\n"
                "- Return concise evidence to the parent task.",
            )
            managed(directory / "CLAUDE.md", "@AGENTS.md")

    write_ownership_manifest(path, p)


def legacy_kit_detected(vault: Path) -> bool:
    readme = vault / "README.md"
    installer = vault / "install.sh"
    index = vault / "VAULT-INDEX.md"
    return (
        not readme.is_symlink()
        and readme.is_file()
        and "Vault Agent Memory Kit v1.0" in read_text(readme)
    ) or (
        not installer.is_symlink()
        and installer.is_file()
        and ".vault-agent-kit-backups" in read_text(installer)
    ) or (
        not index.is_symlink()
        and index.is_file()
        and "vault-agent-kit:" in read_text(index)
    )


def legacy_owned(vault: Path, rel: str) -> bool:
    p = vault / rel
    if p.is_symlink() or not p.is_file():
        return False
    text = read_text(p)
    checks = {
        "README.md": ["Vault Agent Memory Kit v1.0"],
        "install.sh": [".vault-agent-kit-backups", "Vault agent memory kit installed"],
        "AGENTS.md": ["# Vault Operating Contract", "Detailed multi-step workflows belong in Skills"],
        "CLAUDE.md": ["# Claude Code Vault Adapter", "@AGENTS.md"],
        "VAULT-INDEX.md": ["vault-agent-kit:active-projects:start", "vault-agent-kit:section:start"],
        "templates/README.md": ["# Vault templates", "project-note.md"],
        "templates/project-home.md": ["vault-agent-kit:current-state:start"],
        "templates/project-note.md": ["{{project_home_link}}"],
        "templates/session-log.md": ["# {{session_title}}", "## Unresolved risks"],
        "templates/bug.md": ["# Bug: {{title}}", "## Reusable lesson"],
        "templates/decision.md": ["# Decision: {{title}}", "## Review trigger"],
        "templates/command.md": ["# Command: {{title}}", "## Variations"],
        "templates/reference.md": ["# {{title}}", "## Reliability and limitations"],
    }
    return p.exists() and all(x in text for x in checks.get(rel, []))


def touched_vault_paths(vault: Path) -> list[str]:
    rels = ["AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md", "README.md", "install.sh", "related-note.md"]
    rels += [f"templates/{x}" for x in ["README.md", "project-home.md", "project-note.md", "session-log.md", "bug.md", "decision.md", "command.md", "reference.md"]]
    rels += [f"templates/ratchery/{x}" for x in ["project-home.md", "session-log.md", "bug.md", "decision.md", "command.md", "reference.md"]]
    return [
        x
        for x in rels
        if (vault / x).exists()
        or (vault / x).is_symlink()
        or x in ("AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md")
    ]


def backup_vault(vault: Path, rels: list[str], reason: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    base = state_root() / "backups" / stamp
    target_root = base / "vault"
    for rel in rels:
        src = vault / rel
        if not src.exists() and not src.is_symlink():
            continue
        dst = target_root / rel; dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
    write_json(base / "manifest.json", {"version": VERSION, "created_at": now(), "reason": reason, "vault_path": str(vault), "paths": rels})
    return base


def clean_macos_metadata(vault: Path) -> list[str]:
    removed: list[str] = []
    for p in list(vault.rglob(".DS_Store")):
        try: p.unlink(); removed.append(str(p.relative_to(vault)))
        except OSError: pass
    for p in sorted(vault.rglob("__MACOSX"), reverse=True):
        if p.is_dir():
            try: shutil.rmtree(p); removed.append(str(p.relative_to(vault)))
            except OSError: pass
    return removed


def wikilink(vault: Path, path: Path, label: str | None = None) -> str:
    rel = path.relative_to(vault).with_suffix("").as_posix()
    label = label or path.stem
    return f"[[{rel}|{label}]]"


def first_heading(path: Path) -> str:
    match = re.search(r"^#\s+(.+)$", read_text(path), re.M)
    return match.group(1).strip() if match else path.stem.replace("-", " ").title()


def recent_notes(vault: Path, rel_dir: str, limit: int = 5) -> list[Path]:
    root = vault / rel_dir
    if not root.exists(): return []
    files = [p for p in root.rglob("*.md") if p.name != "README.md"]
    return sorted(files, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:limit]


def recent_session_logs(vault: Path, limit: int = 5) -> list[Path]:
    """Session logs live per-project (projects/<slug>/session-logs/), not in
    one global bucket -- aggregate across every project for the dashboard's
    'recent activity' view instead of scanning a single flat folder."""
    files = [p for p in vault.glob("projects/*/session-logs/*.md") if p.name != "README.md"]
    return sorted(files, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:limit]


def render_vault_dashboard(vault: Path) -> str:
    lines: list[str] = ["## Active projects", ""]
    homes = list((vault / "projects").glob("*/Home.md")) if (vault / "projects").exists() else []
    homes = sorted(homes, key=lambda p: p.stat().st_mtime, reverse=True)
    if homes:
        for home in homes[:12]:
            lines.append(f"- {wikilink(vault, home, first_heading(home))}")
    else:
        lines.append("- No project Home notes found yet.")

    lines += ["", "## Recent sessions", ""]
    session_notes = recent_session_logs(vault)
    if session_notes:
        lines += [f"- {wikilink(vault, p, first_heading(p))}" for p in session_notes]
    else:
        lines.append("- None yet.")

    for title, directory in [
        ("Recent decisions", "decisions"),
        ("Recent reusable bugs", "bugs-solved"),
    ]:
        lines += ["", f"## {title}", ""]
        notes = recent_notes(vault, directory)
        if notes:
            lines += [f"- {wikilink(vault, p, first_heading(p))}" for p in notes]
        else:
            lines.append("- None yet.")

    lines += ["", "## Main areas", ""]
    if (vault / "tcc/CONTEXT.md").exists():
        lines.append("- [[tcc/CONTEXT|TCC]]")
    for directory in ["projects", "academic", "career", "decisions", "bugs-solved", "commands", "references", "session-logs", "graphify", "templates/ratchery"]:
        if (vault / directory).exists():
            lines.append(f"- `{directory}/`")
    lines += [
        "", "## Retrieval order", "",
        "1. Open the relevant project `Home.md`.",
        "2. Search project-specific session logs.",
        "3. Retrieve only relevant decisions, bugs, commands, or references.",
        "4. Use `ratchery vault-search` (QMD when configured) before broad scans.",
        "5. Keep source code in repositories outside the Vault.",
    ]
    return "\n".join(lines)


def looks_like_legacy_canonical_index(text: str) -> bool:
    ownership_banner = (
        "This block is maintained by Ratchetry v8." in text
        or "This block is maintained by Agent Workspace v8." in text
    )
    return (
        text.startswith("# Vault Index")
        and "## Active projects" in text
        and "## Main areas" in text
        and "## Navigation" in text
        and ownership_banner
    )


def vault_refresh(vault: Path | None = None) -> None:
    if vault is None:
        vault = configured_vault_path()
    vault = validate_vault_install_targets(vault)
    path = vault / "VAULT-INDEX.md"
    old = read_text(path)
    if not old or looks_like_legacy_canonical_index(old):
        old = "# Vault Index\n\nThis file is a human-editable dashboard. Ratchetry only owns the marked activity block.\n"
    new = replace_managed_block(old, render_vault_dashboard(vault), INDEX_START, INDEX_END)
    if new != old:
        atomic_write_text(path, new)
    print("Vault index refreshed:", path)


def vault_plan(vault: Path, migration: str = "safe") -> dict[str, Any]:
    vault = validate_vault_install_targets(vault); legacy = legacy_kit_detected(vault); actions: list[dict[str, Any]] = []; warnings: list[str] = []
    if legacy and migration == "safe":
        for rel in ["README.md", "install.sh", "AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md", "templates/README.md", "templates/project-home.md", "templates/project-note.md", "templates/session-log.md", "templates/bug.md", "templates/decision.md", "templates/command.md", "templates/reference.md"]:
            if legacy_owned(vault, rel):
                actions.append({"action": "backup-and-replace" if rel in ("AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md") else "backup-and-remove", "path": rel})
    if (vault / "related-note.md").exists() and (vault / "related-note.md").stat().st_size == 0:
        actions.append({"action": "backup-and-remove", "path": "related-note.md"})
    ds = sum(1 for _ in vault.rglob(".DS_Store")); mac = sum(1 for _ in vault.rglob("__MACOSX"))
    if ds: actions.append({"action": "remove-macos-metadata", "count": ds, "path": ".DS_Store"})
    if mac: actions.append({"action": "remove-macos-metadata", "count": mac, "path": "__MACOSX"})
    for rel in ["AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md"]:
        actions.append({"action": "create-or-update", "path": rel})
    actions.append({"action": "create-or-update", "path": "templates/ratchery/"})
    if (vault / "Clippings/ChatGPT.md").exists():
        warnings.append("Clippings/ChatGPT.md is preserved. Review it manually because it appears to be a raw transcript.")
    return {"version": VERSION, "vault": str(vault), "migration": migration, "legacy_kit_detected": legacy, "actions": actions, "warnings": warnings}


def print_vault_plan(plan: dict[str, Any]) -> None:
    print(f"Vault plan for: {plan['vault']}")
    print(f"Legacy kit detected: {str(plan['legacy_kit_detected']).lower()}")
    for action in plan["actions"]:
        suffix = f" ({action['count']})" if "count" in action else ""
        print(f"- {action['action']}: {action['path']}{suffix}")
    for warning in plan["warnings"]:
        print("WARN:", warning)


def validate_vault_root(vault: Path) -> Path:
    """Resolve one real Vault root without following a caller-selected link."""
    vault = vault.expanduser()
    if vault.is_symlink():
        raise ValueError("Vault path must not be a symlink")
    try:
        vault = vault.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Vault path is unavailable") from exc
    if not vault.is_dir():
        raise ValueError("Vault path must be an existing directory")
    return vault


def validate_vault_install_targets(vault: Path) -> Path:
    """Reject Vault roots/managed targets that could redirect setup writes."""
    vault = validate_vault_root(vault)

    for relative in (
        "projects",
        "session-logs",
        "decisions",
        "bugs-solved",
        "commands",
        "references",
        "graphify",
        "templates",
        "templates/ratchery",
    ):
        directory = vault / relative
        if directory.is_symlink():
            raise ValueError(f"Vault managed directory must not be a symlink: {relative}")
        if directory.exists() and not directory.is_dir():
            raise ValueError(f"Vault managed directory must be a real directory: {relative}")
    for relative in touched_vault_paths(vault):
        target = vault / relative
        if target.is_symlink():
            raise ValueError(f"Vault managed file must not be a symlink: {relative}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Vault managed file must be regular: {relative}")
    return vault


def vault_install(migration: str = "safe") -> Path | None:
    vault = validate_vault_install_targets(configured_vault_path()); assets = package_root() / "assets/vault"
    plan = vault_plan(vault, migration); print_vault_plan(plan)
    rels = touched_vault_paths(vault); backup = backup_vault(vault, rels, "vault-install") if rels else None
    if migration == "safe" and plan["legacy_kit_detected"]:
        for rel in ["README.md", "install.sh", "templates/README.md", "templates/project-home.md", "templates/project-note.md", "templates/session-log.md", "templates/bug.md", "templates/decision.md", "templates/command.md", "templates/reference.md", "AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md"]:
            if legacy_owned(vault, rel):
                p = vault / rel
                if p.exists(): p.unlink()
    if (vault / "related-note.md").exists() and (vault / "related-note.md").stat().st_size == 0:
        (vault / "related-note.md").unlink()
    clean_macos_metadata(vault)
    for directory in ["projects", "session-logs", "decisions", "bugs-solved", "commands", "references", "graphify", "templates/ratchery"]:
        (vault / directory).mkdir(parents=True, exist_ok=True)
    managed(vault / "AGENTS.md", (assets / "AGENTS.block.md").read_text())
    managed(vault / "CLAUDE.md", (assets / "CLAUDE.block.md").read_text())
    for file in (assets / "templates").glob("*.md"):
        atomic_write_bytes(vault / "templates/ratchery" / file.name, file.read_bytes())
    vault_refresh(vault)
    print("Vault backup:", backup or "not required")
    return backup


def frontmatter_issues(path: Path) -> list[str]:
    text = read_text(path); issues: list[str] = []
    if not text.startswith("---\n"): return issues
    end = text.find("\n---\n", 4)
    if end < 0: return ["frontmatter is not closed"]
    for index, line in enumerate(text[4:end].splitlines(), start=2):
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "-")): continue
        if ":" not in line: issues.append(f"line {index}: missing colon"); continue
        _, value = line.split(":", 1); value = value.strip()
        if ": " in value and not value.startswith(('"', "'", "[", "{", "|", ">")):
            issues.append(f"line {index}: quote scalar containing colon")
    return issues


def fix_frontmatter_yaml(vault: Path | None = None, apply: bool = False) -> int:
    if vault is None: vault = configured_vault_path()
    vault = validate_vault_root(vault); changes: list[tuple[Path, str]] = []
    for path in sorted(vault.rglob("*.md")):
        if path.is_symlink() or not path.is_file():
            continue
        text = read_text(path)
        if not text.startswith("---\n"): continue
        end = text.find("\n---\n", 4)
        if end < 0: continue
        out: list[str] = []; changed = False
        for line in text[4:end].splitlines():
            if line.startswith((" ", "-")) or ":" not in line:
                out.append(line); continue
            key, value = line.split(":", 1); raw = value.strip()
            if ": " in raw and not raw.startswith(('"', "'", "[", "{", "|", ">")):
                escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
                out.append(f'{key}: "{escaped}"'); changed = True
            else: out.append(line)
        if changed:
            changes.append((path, "---\n" + "\n".join(out) + text[end:]))
    print(f"Frontmatter YAML fixes: {len(changes)} file(s).")
    for path, _ in changes: print("-", path.relative_to(vault))
    if not apply:
        print("Dry run only. Re-run with --apply to write changes."); return 0
    if not changes: return 0
    backup = backup_vault(vault, [str(path.relative_to(vault)) for path, _ in changes], "vault-fix-yaml")
    for path, new in changes: atomic_write_text(path, new)
    print("Applied fixes. Backup:", backup)
    return 0


def vault_audit(vault: Path | None = None) -> int:
    if vault is None: vault = configured_vault_path()
    vault = validate_vault_root(vault); errors: list[str] = []; warnings: list[str] = []
    index = ""
    for filename in ["AGENTS.md", "CLAUDE.md", "VAULT-INDEX.md"]:
        path = vault / filename
        if path.is_symlink() or (path.exists() and not path.is_file()):
            errors.append(f"{filename} must be a regular non-symlink file")
        elif not path.exists():
            errors.append(f"Missing {filename}")
        elif filename == "VAULT-INDEX.md":
            index = read_text(path)
    if index.count(INDEX_START) != 1 or index.count(INDEX_END) != 1:
        errors.append("VAULT-INDEX.md must contain exactly one managed activity block")
    if legacy_kit_detected(vault): warnings.append("Legacy vault-agent-kit artifacts are still present")
    for path in vault.rglob("*"):
        if path.is_symlink():
            warnings.append(f"Symlink in Vault was not inspected: {path.relative_to(vault)}")
            continue
        if path.is_file():
            try:
                if os.access(path, os.X_OK) and path.suffix in (".sh", ".py"):
                    warnings.append(f"Executable in Vault: {path.relative_to(vault)}")
            except OSError: pass
        if path.suffix.lower() == ".md":
            for issue in frontmatter_issues(path): errors.append(f"{path.relative_to(vault)}: {issue}")
    for path in vault.rglob(".DS_Store"): warnings.append(f"macOS metadata: {path.relative_to(vault)}")
    for item in errors: print("ERROR:", item)
    for item in warnings: print("WARN:", item)
    print(f"Vault doctor: {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


def rollback_vault(backup_dir: Path) -> int:
    backup_dir = backup_dir.expanduser().resolve(); manifest = load_json(backup_dir / "manifest.json", {})
    src = backup_dir / "vault"; target_raw = manifest.get("vault_path")
    if not src.exists() or not target_raw:
        print(f"Invalid backup directory: {backup_dir} (expected a 'vault/' subdirectory and manifest.json with a vault_path). Pass the backup directory printed by the vault-install/vault-fix-yaml run that created it.", file=sys.stderr); return 2
    target = Path(target_raw).expanduser()
    for path in sorted(src.rglob("*")):
        if path.is_dir(): continue
        rel = path.relative_to(src); dst = target / rel; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst, follow_symlinks=False)
    print("Restored backed-up files to:", target); return 0


def validate_projects_workspace_targets(root: Path, layout: str) -> Path:
    """Reject final-component symlinks in the package-manager workspace plan."""
    root = root.expanduser()
    if root.is_symlink():
        raise ValueError("Projects root must not be a symlink")
    root = root.resolve()
    if root.exists() and not root.is_dir():
        raise ValueError("Projects root must be a directory")
    if layout != "categorized":
        return root
    readme = root / "README.md"
    if readme.is_symlink() or (readme.exists() and not readme.is_file()):
        raise ValueError("Projects workspace README must be a regular file")
    for category in CATEGORIES:
        directory = root / category
        if directory.is_symlink():
            raise ValueError(f"Projects category must not be a symlink: {category}")
        if directory.exists() and not directory.is_dir():
            raise ValueError(f"Projects category must be a directory: {category}")
        category_readme = directory / "README.md"
        if category_readme.is_symlink() or (
            category_readme.exists() and not category_readme.is_file()
        ):
            raise ValueError(
                f"Projects category README must be a regular file: {category}"
            )
    return root


def setup_projects_workspace(root: Path, layout: str = "flat") -> None:
    root = validate_projects_workspace_targets(root, layout)
    root.mkdir(parents=True, exist_ok=True)
    if layout != "categorized": return
    assets = package_root() / "assets/projects-workspace"
    copy_if_missing(assets / "README.md", root / "README.md")
    for category in CATEGORIES:
        (root / category).mkdir(parents=True, exist_ok=True)
        copy_if_missing(assets / "categories" / f"{category}.md", root / category / "README.md")


def setup_workspace(
    *,
    vault: Path | None,
    projects_root: Path,
    project_layout: str = "flat",
    vault_migration: str = "safe",
    external_tools: str = "none",
    dry_run: bool = False,
    assume_yes: bool = False,
) -> int:
    """Configure user-owned state after a package manager installs Ratchetry.

    Package managers own the immutable runtime; this command owns only the
    explicit, user-scoped configuration step. It deliberately reuses the same
    managed merge and backup paths as the source installer and never installs
    third-party tools.
    """
    try:
        if vault is not None:
            vault = validate_vault_install_targets(vault)
        projects_root = validate_projects_workspace_targets(projects_root, project_layout)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if preflight() != 0:
        return 1

    plan = vault_plan(vault, vault_migration) if vault is not None else None
    # Surface deterministic ownership collisions before confirmation or any
    # write. global_guidance() revalidates at the mutation boundary to close
    # the ordinary check/use gap as far as this local process can.
    validate_global_guidance_targets()
    if plan is not None:
        print_vault_plan(plan)
    print()
    print("Ratchetry setup")
    print(f"  Vault memory:    {vault if vault is not None else 'not configured (optional)'}")
    print(f"  Projects root:   {projects_root}")
    print(f"  Project layout:  {project_layout}")
    print(f"  Vault migration: {vault_migration}")
    print(f"  External tools:  {external_tools}")

    if dry_run:
        print("\nDry run only. No files were changed.")
        print("No third-party tool is installed by this command.")
        return 0

    if not assume_yes:
        try:
            answer = input("\nConfigure this user account? [y/N] ")
        except EOFError:
            print("Setup cancelled: confirmation input was unavailable.", file=sys.stderr)
            return 1
        if answer.strip().lower() not in {"y", "yes"}:
            print("Setup cancelled.")
            return 1

    data = {
        "version": VERSION,
        "vault_path": str(vault) if vault is not None else None,
        "projects_root": str(projects_root),
        "project_layout": project_layout,
        "external_tools": external_tools,
        "thresholds": {
            "medium_files": 150,
            "medium_lines": 25000,
            "large_files": 800,
            "large_lines": 120000,
            "large_packages": 5,
        },
    }
    save_cfg(data)
    setup_projects_workspace(projects_root, project_layout)
    global_guidance()
    if vault is not None:
        vault_install(vault_migration)
    if external_tools == "recommended":
        tools_install()

    doctor_result = global_doctor()
    if doctor_result != 0:
        print(
            "Setup completed, but doctor found configuration issues. Review the "
            "errors and rerun doctor-global.",
            file=sys.stderr,
        )
        return doctor_result

    print("\nRatchetry setup completed successfully.")
    print("Next: initialize a repository with `ratchery init`.")
    return 0


def _frontmatter_field_from_text(text: str, key: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    frontmatter = text[4:end]
    matches = re.findall(
        rf'^{re.escape(key)}:\s*"?([^"\n]+?)"?\s*$', frontmatter, re.M
    )
    return matches[0] if len(matches) == 1 else None


def parse_home_project_id(path: Path) -> str | None:
    return _frontmatter_field_from_text(read_text(path), "project_id")


def parse_frontmatter_field(path: Path, key: str) -> str | None:
    """Read one field from the YAML frontmatter block only (between the first
    pair of `---` delimiters) -- never from the note body. A prior version of
    this function searched the whole file text, so a `project:`-looking line
    anywhere in the body (including inside a code block, or attacker-supplied
    content) could be picked up as if it were real frontmatter."""
    return _frontmatter_field_from_text(read_text(path), key)


_SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def is_safe_vault_slug(slug: str) -> bool:
    """A vault project slug must be a single, unremarkable path component --
    never an absolute path, `..` traversal, or anything containing a path
    separator. Rejects anything a filesystem could interpret as escaping
    `vault/projects/`."""
    return bool(_SAFE_SLUG.match(slug)) and "/" not in slug and "\\" not in slug and slug not in (".", "..")


def plan_session_log_migration(vault: Path) -> dict[str, Any]:
    """Session logs used to land in one flat vault/session-logs/ bucket shared
    by every project, which becomes unreadable with more than a couple of
    active projects. Each log's `project:` frontmatter field (written by
    assets/vault/templates/session-log.md) tells us which
    projects/<slug>/session-logs/ folder it actually belongs in. Read-only:
    returns the plan, moves nothing. See migrate_session_logs() for the
    write path."""
    global_dir = vault / "session-logs"
    moves: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    if global_dir.exists():
        for note in sorted(global_dir.glob("*.md")):
            if note.name == "README.md":
                continue
            slug = parse_frontmatter_field(note, "project")
            if not slug:
                skipped.append({"path": str(note.relative_to(vault)), "reason": "no 'project' frontmatter field"}); continue
            if not is_safe_vault_slug(slug):
                skipped.append({"path": str(note.relative_to(vault)), "reason": f"unsafe project slug {slug!r} (rejected, not a plain path component)"}); continue
            project_dir = vault / "projects" / slug
            if not (project_dir / "Home.md").exists():
                skipped.append({"path": str(note.relative_to(vault)), "reason": f"no projects/{slug}/Home.md found"}); continue
            dest = project_dir / "session-logs" / note.name
            # Defense in depth beyond the slug check above: confirm the
            # resolved destination is actually still inside the vault before
            # trusting it (Path.relative_to on unresolved paths would not
            # catch a "projects/../../escape" style slug on its own).
            try:
                dest.resolve().relative_to(vault.resolve())
            except ValueError:
                skipped.append({"path": str(note.relative_to(vault)), "reason": "destination resolves outside the vault"}); continue
            if dest.exists():
                skipped.append({"path": str(note.relative_to(vault)), "reason": f"destination already exists: {dest.relative_to(vault)}"}); continue
            moves.append({"from": str(note.relative_to(vault)), "to": str(dest.relative_to(vault))})
    return {"moves": moves, "skipped": skipped}


def migrate_session_logs(vault: Path, apply: bool = False) -> dict[str, Any]:
    """Apply plan_session_log_migration(). Backs up every file it touches
    first (same backup_vault() mechanism as every other Vault mutation) and
    never overwrites or deletes anything it isn't confident about -- see
    'skipped' in the plan for what it left alone and why."""
    plan = plan_session_log_migration(vault)
    if not apply or not plan["moves"]:
        return plan
    backup = backup_vault(vault, [m["from"] for m in plan["moves"]], "migrate-session-logs")
    for move in plan["moves"]:
        src = vault / move["from"]; dest = vault / move["to"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
    vault_refresh(vault)
    plan["backup"] = str(backup)
    return plan


def choose_vault_slug(vault: Path, project_path: Path, p: dict[str, Any]) -> str:
    projects_dir = vault / "projects"
    project_id = p["project_id"]
    # Project ID is the durable identity.  If the repository is moved or renamed,
    # reconnect to its existing Vault memory tree before considering the new name.
    if projects_dir.exists():
        for candidate in projects_dir.glob("*/Home.md"):
            if parse_home_project_id(candidate) == project_id:
                return candidate.parent.name

    base = p["slug"]
    home = projects_dir / base / "Home.md"
    if not home.exists():
        return base
    existing_id = parse_home_project_id(home)
    if not existing_id:
        # Adopt a v8.1-era Home only when there is affirmative evidence that it
        # belongs to this repository. Otherwise avoid cross-project memory
        # collisions by allocating a stable project-id suffix.
        text = read_text(home)
        path_matches = str(project_path.resolve()) in text
        title_matches = bool(re.search(rf"^#\s+{re.escape(p['project'])}\s*$", text, re.I | re.M))
        if path_matches or title_matches:
            return base
    return f"{base}-{project_id.split('-')[0]}"


def update_home_metadata(home: Path, project_path: Path, p: dict[str, Any], vault_slug: str) -> None:
    old = read_text(home)
    if not old: return
    # Add project_id to frontmatter when absent.
    if old.startswith("---\n") and not re.search(r"^project_id:", old, re.M):
        end = old.find("\n---\n", 4)
        if end > 0:
            old = old[:end] + f'\nproject_id: "{p["project_id"]}"' + old[end:]
    body = (
        "## Workspace metadata\n"
        f"- Project ID: `{p['project_id']}`\n"
        f"- Repository path: `{project_path}`\n"
        f"- Vault slug: `{vault_slug}`\n"
        f"- Profile: `{p['size']}`\n"
        f"- Updated: `{today()}`"
    )
    new = replace_managed_block(old, body, MSTART, MEND)
    if new != read_text(home): atomic_write_text(home, new)


def vault_project(path: Path, p: dict[str, Any]) -> None:
    vp = cfg().get("vault_path")
    if not vp: return
    vault = Path(vp).expanduser().resolve(); vault_slug = choose_vault_slug(vault, path, p); p["vault_slug"] = vault_slug
    write_json(path / ".agents/state/project-profile.json", p)
    directory = vault / "projects" / vault_slug; directory.mkdir(parents=True, exist_ok=True)
    home = directory / "Home.md"
    if not home.exists():
        tpl = (package_root() / "assets/vault/templates/project-home.md").read_text()
        text = (tpl.replace("{{project_name}}", path.name).replace("{{project_slug}}", vault_slug)
                .replace("{{project_id}}", p["project_id"]).replace("{{date}}", today()).replace("{{repository_path}}", str(path)))
        atomic_write_text(home, text)
    update_home_metadata(home, path, p, vault_slug)
    # Each project owns its own session-logs -- not a single global bucket
    # shared by every project in the Vault, which is unreadable once you have
    # more than one or two active projects. See docs/decision-matrix.md.
    (directory / "session-logs").mkdir(exist_ok=True)
    if p["size"] == "medium":
        for name in ["Architecture", "Knowledge", "References"]: (directory / name).mkdir(exist_ok=True)
    if p["size"] == "large":
        for name in ["00 - Vision", "01 - Product", "02 - Modules", "03 - Integrations", "04 - Architecture", "05 - Security", "06 - AI Prompts", "07 - Decisions", "08 - References", "09 - Execution"]:
            (directory / name).mkdir(exist_ok=True)
    vault_refresh(vault)


def validate_global_guidance_targets() -> tuple[Path, Path, list[str]]:
    """Validate global Skill ownership and return the resolved install plan."""
    canonical = Path.home() / ".agents/skills"; claude = Path.home() / ".claude/skills"
    skill_names = registered_global_skills()

    directories = (
        Path.home() / ".agents",
        canonical,
        Path.home() / ".claude",
        claude,
        Path.home() / ".codex",
    )
    for directory in directories:
        if directory.is_symlink():
            raise ValueError(f"Refusing a symlinked global directory: {directory}")
        if directory.exists() and not directory.is_dir():
            raise ValueError(f"Global managed directory must be real: {directory}")
    for target in (
        Path.home() / ".claude/CLAUDE.md",
        Path.home() / ".codex/AGENTS.md",
    ):
        if target.is_symlink():
            raise ValueError(f"Refusing a symlinked global managed file: {target}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Global managed path must be a regular file: {target}")

    for name in skill_names:
        target = canonical / name
        if target.is_symlink() or (
            target.exists() and managed_directory_marker(target) is None
        ):
            raise ValueError(f"Refusing to overwrite user-owned global Skill {target}")
        link = claude / name
        if link.is_symlink():
            if link.resolve(strict=False) != target.resolve(strict=False):
                raise ValueError(f"Refusing to replace user-owned Claude Skill symlink {link}")
        elif link.exists():
            if managed_directory_marker(link) is None:
                raise ValueError(f"Refusing to overwrite user-owned Claude Skill {link}")
    return canonical, claude, skill_names


def global_guidance() -> None:
    assets = package_root() / "assets/global"

    # Validate every collision before writing any global guidance or Skill.
    # User-owned same-name directories/symlinks are preserved, but the install
    # must fail visibly rather than claiming the framework catalog is present.
    canonical, claude, skill_names = validate_global_guidance_targets()

    managed(Path.home() / ".claude/CLAUDE.md", (assets / "CLAUDE.block.md").read_text())
    managed(Path.home() / ".codex/AGENTS.md", (assets / "AGENTS.block.md").read_text())
    canonical.mkdir(parents=True, exist_ok=True); claude.mkdir(parents=True, exist_ok=True)
    for name in skill_names:
        skill = assets / "skills" / name
        target = canonical / skill.name
        copy_managed_dir(skill, target)
        link = claude / skill.name
        if link.is_symlink() and link.resolve(strict=False) == target.resolve(strict=False):
            continue
        if link.exists() or link.is_symlink():
            if link.is_symlink(): link.unlink()
            elif managed_directory_marker(link): shutil.rmtree(link)
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            shutil.copytree(target, link)


def init_project(path: Path) -> dict[str, Any]:
    path = git_root(path.resolve()); path.mkdir(parents=True, exist_ok=True)
    require_safe_project_layout(path)
    risk_answers_recorded = ae.default_answers_path(path).is_file()
    p = profile(path)
    # Classify before generating project files: steering files and agent
    # activation both depend on knowing the tier, not just the raw profile.
    tier = ae.classify(path, p)
    project_files(path, p, tier); vault_project(path, p)
    note = " [ratcheted]" if tier.get("ratcheted") else ""
    print(f"Initialized {path} ({p['size']}, {p['source_files']} source files, tier {tier['effective_tier']}{note}).")
    if not risk_answers_recorded:
        print(
            "ACTION REQUIRED: tier is provisional because project risk answers have not "
            "been reviewed. Run `ratchery tier-set --path .` (with any needed risk "
            "flags) before relying on doctor/CI."
        )
    return p


def parse_json_file(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        errors.append(f"Invalid JSON {path.name}: {exc}"); return {}
    if not isinstance(data, dict):
        errors.append(f"{path.name} must be a JSON object, found {type(data).__name__}"); return {}
    return data


def missing_list_entries(actual: Any, required: Any) -> list[Any]:
    """Return required JSON-like list entries not present in ``actual``."""
    if not isinstance(actual, list) or not isinstance(required, list):
        return list(required) if isinstance(required, list) else []
    actual_keys = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in actual}
    return [item for item in required if json.dumps(item, sort_keys=True, ensure_ascii=False) not in actual_keys]


def has_managed_pretool_hook(
    config: dict[str, Any], expected: dict[str, Any], required_tools: set[str]
) -> bool:
    """Whether PreToolUse invokes the exact shipped runtime command safely."""
    hooks = config.get("hooks", {}) if isinstance(config, dict) else {}
    groups = hooks.get("PreToolUse", []) if isinstance(hooks, dict) else []
    expected_hooks = expected.get("hooks", {}) if isinstance(expected, dict) else {}
    expected_groups = expected_hooks.get("PreToolUse", []) if isinstance(expected_hooks, dict) else []
    if not isinstance(groups, list) or not isinstance(expected_groups, list):
        return False
    expected_specs: set[tuple[Any, Any, str, Any]] = set()
    for group in expected_groups:
        for hook in group.get("hooks", []) if isinstance(group, dict) else []:
            if isinstance(hook, dict):
                expected_specs.add((
                    hook.get("type"),
                    hook.get("command"),
                    json.dumps(hook.get("args", []), ensure_ascii=False),
                    hook.get("timeout"),
                ))
    if not expected_specs:
        return False
    for group in groups:
        if not isinstance(group, dict):
            continue
        if group.get("enabled") is False or group.get("disabled") is True:
            continue
        matcher = group.get("matcher")
        matcher_covers = matcher in (None, "", "*") or (
            isinstance(matcher, str) and required_tools.issubset(set(matcher.split("|")))
        )
        if not matcher_covers:
            continue
        for hook in group.get("hooks", []) if isinstance(group.get("hooks"), list) else []:
            if not isinstance(hook, dict):
                continue
            if hook.get("enabled") is False or hook.get("disabled") is True:
                continue
            actual_spec = (
                hook.get("type"),
                hook.get("command"),
                json.dumps(hook.get("args", []), ensure_ascii=False),
                hook.get("timeout"),
            )
            if actual_spec in expected_specs:
                return True
    return False


def validate_claude_security(config: dict[str, Any], errors: list[str]) -> None:
    """Require the shipped Claude security invariants while allowing additions."""
    expected = load_json(package_root() / "assets/project/.claude/settings.json", {})
    expected_permissions = expected.get("permissions") if isinstance(expected, dict) else None
    expected_sandbox = expected.get("sandbox") if isinstance(expected, dict) else None
    expected_fs = expected_sandbox.get("filesystem") if isinstance(expected_sandbox, dict) else None
    expected_credentials = expected_sandbox.get("credentials") if isinstance(expected_sandbox, dict) else None
    expected_hooks = expected.get("hooks") if isinstance(expected, dict) else None
    template_valid = (
        isinstance(expected_permissions, dict)
        and expected_permissions.get("disableBypassPermissionsMode") == "disable"
        and isinstance(expected_permissions.get("ask"), list)
        and isinstance(expected_permissions.get("deny"), list)
        and isinstance(expected_fs, dict)
        and isinstance(expected_fs.get("denyRead"), list)
        and isinstance(expected_credentials, dict)
        and isinstance(expected_credentials.get("files"), list)
        and isinstance(expected_credentials.get("envVars"), list)
        and isinstance(expected_hooks, dict)
        and isinstance(expected_hooks.get("PreToolUse"), list)
    )
    if not template_valid:
        errors.append("Bundled Claude security template is missing or invalid; cannot verify project policy")
        return
    actual_permissions = config.get("permissions", {}) if isinstance(config.get("permissions"), dict) else {}
    if actual_permissions.get("disableBypassPermissionsMode") != "disable":
        errors.append("Claude bypass-permissions mode is not disabled")
    if missing_list_entries(actual_permissions.get("ask"), expected_permissions.get("ask")):
        errors.append("Claude permissions.ask is missing required managed MCP approval rules")
    if missing_list_entries(actual_permissions.get("deny"), expected_permissions.get("deny")):
        errors.append("Claude permissions.deny is missing required sensitive-file protections")

    sandbox = config.get("sandbox", {}) if isinstance(config.get("sandbox"), dict) else {}
    actual_fs = sandbox.get("filesystem", {}) if isinstance(sandbox.get("filesystem"), dict) else {}
    if missing_list_entries(actual_fs.get("denyRead"), expected_fs.get("denyRead")):
        errors.append("Claude sandbox.filesystem.denyRead is missing required protections")

    actual_credentials = sandbox.get("credentials", {}) if isinstance(sandbox.get("credentials"), dict) else {}
    if missing_list_entries(actual_credentials.get("files"), expected_credentials.get("files")):
        errors.append("Claude sandbox.credentials.files is missing required deny entries")
    if missing_list_entries(actual_credentials.get("envVars"), expected_credentials.get("envVars")):
        errors.append("Claude sandbox.credentials.envVars is missing required deny entries")

    if not has_managed_pretool_hook(config, expected, {"Bash", "Read", "Write", "Edit", "MultiEdit"}):
        errors.append("Claude PreToolUse hook is not bound to the Ratchetry runtime for protected tools")


def validate_codex_security(config: dict[str, Any], hooks: dict[str, Any], errors: list[str]) -> None:
    """Require the shipped Codex security invariants while allowing additions."""
    if not tomllib:
        return
    try:
        expected = tomllib.loads((package_root() / "assets/project/.codex/config.base.toml").read_text())
    except Exception as exc:
        errors.append(f"Bundled Codex security template is missing or invalid; cannot verify project policy: {exc}")
        return
    expected_permissions = expected.get("permissions") if isinstance(expected, dict) else None
    expected_profile = expected_permissions.get("project-edit") if isinstance(expected_permissions, dict) else None
    expected_fs = expected_profile.get("filesystem") if isinstance(expected_profile, dict) else None
    expected_workspace = expected_fs.get(":workspace_roots") if isinstance(expected_fs, dict) else None
    expected_shell_policy = expected.get("shell_environment_policy") if isinstance(expected, dict) else None
    expected_filters = expected_shell_policy.get("filters") if isinstance(expected_shell_policy, dict) else None
    expected_agents = expected.get("agents") if isinstance(expected, dict) else None
    if not (
        isinstance(expected_profile, dict)
        and isinstance(expected_fs, dict)
        and isinstance(expected_workspace, dict)
        and isinstance(expected_filters, dict)
        and expected.get("max_threads") == 4
        and expected.get("interrupt_message") is False
        and isinstance(expected_agents, dict)
        and all(isinstance(role, dict) for role in expected_agents.values())
    ):
        errors.append("Bundled Codex security template is missing or invalid; cannot verify project policy")
        return
    permissions = config.get("permissions", {}) if isinstance(config.get("permissions"), dict) else {}
    actual_profile = permissions.get("project-edit", {}) if isinstance(permissions.get("project-edit"), dict) else {}
    if actual_profile.get("extends") != expected_profile.get("extends"):
        errors.append("Codex project-edit profile does not extend the restricted workspace profile")

    actual_fs = actual_profile.get("filesystem", {}) if isinstance(actual_profile.get("filesystem"), dict) else {}
    actual_workspace = actual_fs.get(":workspace_roots", {}) if isinstance(actual_fs.get(":workspace_roots"), dict) else {}
    for pattern, value in expected_workspace.items():
        if actual_workspace.get(pattern) != value:
            errors.append("Codex project-edit profile is missing a required workspace filesystem deny")
            break
    for pattern, value in expected_fs.items():
        if pattern != ":workspace_roots" and actual_fs.get(pattern) != value:
            errors.append("Codex project-edit profile is missing a required global filesystem deny")
            break

    shell_policy = config.get("shell_environment_policy", {}) if isinstance(config.get("shell_environment_policy"), dict) else {}
    actual_filters = shell_policy.get("filters", {}) if isinstance(shell_policy.get("filters"), dict) else {}
    if any(actual_filters.get(name) != value for name, value in expected_filters.items()):
        errors.append("Codex shell environment policy is missing required secret filters")
    if config.get("max_threads") != expected.get("max_threads"):
        errors.append("Codex max_threads does not retain the managed four-thread cost cap")
    if config.get("interrupt_message") is not expected.get("interrupt_message"):
        errors.append("Codex interrupt_message does not match the managed agent policy")
    actual_agents = config.get("agents")
    if not isinstance(actual_agents, dict) or any(
        not isinstance(role, dict) for role in actual_agents.values()
    ):
        errors.append(
            "Codex [agents] must contain only named role tables for minimum-client compatibility"
        )
    features = config.get("features", {}) if isinstance(config.get("features"), dict) else {}
    if features.get("hooks") is not True:
        errors.append("Codex hooks feature is not enabled")
    expected_hooks = load_json(package_root() / "assets/project/.codex/hooks.json", {})
    if not isinstance(expected_hooks, dict) or not expected_hooks.get("hooks"):
        errors.append("Bundled Codex hook template is missing or invalid; cannot verify project policy")
        return
    if not has_managed_pretool_hook(hooks, expected_hooks, {"Bash", "apply_patch", "Edit", "Write"}):
        errors.append("Codex PreToolUse hook is not bound to the Ratchetry runtime for protected tools")


def git_provenance(path: Path) -> dict[str, Any]:
    """Which commit a diagnostic result actually describes.

    `doctor --json` is the payload of this project's reusable CI action, and a
    verdict with no commit attached is not auditable evidence: it says a tree
    was healthy, never which tree. Recording the commit (and whether the
    worktree was dirty when the check ran) makes a stored result re-checkable
    against the exact revision it was produced from.

    Unlike :func:`clean_git_commit`, which *requires* a pristine worktree
    because a benchmark measured on uncommitted code is meaningless, this
    reports what it finds and never fails the caller: `doctor` must stay
    runnable in a dirty tree, on a shallow checkout, and outside Git entirely.
    Every field is None when the fact could not be established.
    """
    git_env = clean_git_environment()

    def run(argv: list[str], timeout: float) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                argv, cwd=str(path), env=git_env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
            )
        except (OSError, UnicodeError, subprocess.TimeoutExpired):
            return None

    commit = None
    commit_result = run(safe_git_read_command("rev-parse", "--verify", "HEAD"), 5)
    if commit_result is not None and commit_result.returncode == 0:
        candidate = commit_result.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", candidate):
            commit = candidate

    dirty = None
    status_result = run(
        safe_git_read_command(
            "status", "--porcelain=v1", "--untracked-files=normal"
        ),
        10,
    )
    if status_result is not None and status_result.returncode == 0:
        dirty = bool(status_result.stdout.strip())

    return {"commit": commit, "dirty": dirty}


def emit_doctor_result(
    path: Path,
    errors: list[str],
    warnings: list[str],
    tier_reported: str | None,
    tier_name_reported: str | None,
    json_output: bool,
) -> int:
    """Render the single doctor result contract for normal and early exits."""
    provenance = git_provenance(path)
    if json_output:
        print(json.dumps({
            "errors": errors,
            "warnings": warnings,
            "tier": tier_reported,
            "tier_name": tier_name_reported,
            "commit": provenance["commit"],
            "dirty": provenance["dirty"],
        }, ensure_ascii=False))
    else:
        for item in errors:
            print("ERROR:", item)
        for item in warnings:
            print("WARN:", item)
        if provenance["commit"]:
            suffix = " (worktree dirty)" if provenance["dirty"] else ""
            print(f"Commit: {provenance['commit']}{suffix}")
        print(f"Doctor: {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors else 0


def doctor_project(path: Path, deep: bool = False, json_output: bool = False) -> int:
    path = git_root(path.resolve()); errors: list[str] = []; warnings: list[str] = []
    tier_reported = None; tier_name_reported = None
    # Stop before reading any project-owned content when a managed parent can
    # redirect access outside the selected repository. Merely reporting the
    # symlink and continuing would still follow it in the checks below.
    errors.extend(managed_project_layout_issues(path))
    if errors:
        return emit_doctor_result(
            path, errors, warnings, tier_reported, tier_name_reported, json_output
        )
    required = ["AGENTS.md", "CLAUDE.md", ".claude/settings.json", ".codex/config.toml", ".codex/hooks.json", ".agents/runtime/agent_workspace.py", ".agents/state/ownership.json", ".agents/state/project-id", "docs/PROJECT_CONTEXT.md", "docs/COMMANDS.md", ".agents/state/tier.json"]
    for rel in required:
        target = path / rel
        if not target.exists():
            errors.append(f"Missing {rel}")
        elif target.is_symlink():
            errors.append(f"Managed file {rel} must not be a symlink")
    for issue in [
        cli_security_version_issue("claude", "Claude Code", CLAUDE_MIN_SECURITY),
        cli_security_version_issue("codex", "Codex CLI", CODEX_MIN_SECURITY),
    ]:
        if issue:
            severity, message = issue
            (errors if severity == "error" else warnings).append(message)
    # Soft check, not hard-required: docs/CURRENT_STATE.md is durable *local*
    # project memory (AGENTS.md asks agents to keep it updated), but unlike
    # everything in `required` above it carries no security/governance
    # invariant -- some maintainers deliberately keep it .gitignore'd (session
    # notes, not something downstream users/contributors need to see; see
    # CONTRIBUTING.md "This repo runs its own tooling on itself" for this
    # repo's own example). A fresh clone missing it is a recommendation, not
    # a failure the way a missing sandbox config or tier record is.
    current_state_ignored = "docs/CURRENT_STATE.md" in {
        line.strip()
        for line in read_text(path / ".gitignore").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if not (path / "docs/CURRENT_STATE.md").exists() and not current_state_ignored:
        warnings.append("docs/CURRENT_STATE.md not found -- recommended for durable project memory across sessions, not required (safe to .gitignore deliberately, see CONTRIBUTING.md)")

    risk_answers_path = ae.default_answers_path(path)
    if not risk_answers_path.exists():
        errors.append(
            "Project risk answers have not been reviewed; run `ratchery tier-set "
            "--path .` with the project's real risk facts before relying on this tier"
        )

    try:
        mcp_opt_ins = mcp_opted_in(path)
        mcp_data = read_mcp_json(path / ".mcp.json")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        mcp_opt_ins = set()
        mcp_data = {}
    mcp_servers = mcp_data.get("mcpServers", {}) if isinstance(mcp_data, dict) else {}
    for name in sorted(mcp_opt_ins):
        if not isinstance(mcp_servers, dict) or mcp_servers.get(name) != KNOWN_MCP_SERVERS[name]:
            errors.append(
                f"Recorded MCP opt-in '{name}' is missing or changed in .mcp.json"
            )

    tier_path = path / ".agents/state/tier.json"
    tier_state = parse_json_file(tier_path, errors) if tier_path.exists() and not tier_path.is_symlink() else {}
    # Always scan through the pure path: loading a cached project profile here
    # would let codebase growth change the expected tier without doctor seeing
    # it, while calling profile() would violate the read-only CI contract.
    current_profile: dict[str, Any] | None = None
    try:
        current_profile = inspect_project(path)
        expected_tier = ae.evaluate_tier(path, current_profile)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        expected_tier = None
    derived_fields = [
        "computed_tier", "effective_tier", "criticality_score",
        "complexity_score", "floor_reasons", "ratcheted", "tier_name",
        "requirements",
    ]
    if expected_tier is not None:
        if tier_path.exists() and not tier_path.is_symlink():
            for field in derived_fields:
                if tier_state.get(field) != expected_tier.get(field):
                    errors.append(
                        f"Recorded tier.json {field} does not match the value derived from "
                        "current project facts, risk answers, and ratchet history -- run "
                        "`ratchery tier` to refresh reviewed tier state"
                    )

        tier = expected_tier["effective_tier"]
        tier_reported = tier
        tier_name_reported = expected_tier["tier_name"]
        if not json_output:
            print(f"Tier: {tier} ({tier_name_reported})")
        try:
            notice = ae.downgrade_notice(path, tier)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
        else:
            if notice:
                warnings.append(notice)
        # `required_docs` is reported at the same severity as required agents
        # and skills. A requirement that only ever warns is governance theatre:
        # it lets a T2/T3 project run indefinitely without the ADR trail or
        # security review its own recorded tier asks for, which is the same
        # "green by absence" failure the tier derivation below guards against.
        # Docs already covered by the managed `required` list above are skipped
        # so a single missing file is not reported twice.
        for doc in expected_tier["requirements"]["required_docs"]:
            if doc in required or (path / doc).exists():
                continue
            errors.append(
                f"Tier {tier} requires {doc}, not found -- create it, or lower the tier "
                "deliberately with `ratchery tier --acknowledge-downgrade \"<reason>\"`"
            )
        expected_agents = active_agent_names(current_profile or {}, expected_tier)
        for agent_name in sorted(expected_agents):
            claude_agent = path / ".claude/agents" / f"{agent_name}.md"
            codex_agent = path / ".codex/agents" / f"{agent_name.replace('-', '_')}.toml"
            if claude_agent.is_symlink() or not claude_agent.is_file():
                errors.append(
                    f"Tier/capability policy requires Claude agent '{agent_name}', not installed -- "
                    "run `ratchery refresh`"
                )
            if codex_agent.is_symlink() or not codex_agent.is_file():
                errors.append(
                    f"Tier/capability policy requires Codex agent '{agent_name}', not installed -- "
                    "run `ratchery refresh`"
                )
        for skill_name in expected_tier["requirements"]["required_skills"]:
            locations = [path / ".agents/skills" / skill_name, path / ".claude/skills" / skill_name, Path.home() / ".agents/skills" / skill_name, Path.home() / ".claude/skills" / skill_name]
            if not any(loc.exists() for loc in locations):
                errors.append(
                    f"Tier {tier} requires skill '{skill_name}', not found locally or globally -- "
                    "run `ratchery install-global`"
                )

    claude_settings_path = path / ".claude/settings.json"
    claude = parse_json_file(claude_settings_path, errors) if claude_settings_path.exists() and not claude_settings_path.is_symlink() else {}
    codex_hooks_path = path / ".codex/hooks.json"
    codex_hooks = parse_json_file(codex_hooks_path, errors) if codex_hooks_path.exists() and not codex_hooks_path.is_symlink() else {}
    # Gate on the file existing, not on the parsed dict being truthy -- an empty
    # `{}` (or any non-dict JSON, now caught by parse_json_file above) must still
    # be checked, not silently skip every sandbox invariant below.
    if claude_settings_path.exists() and not claude_settings_path.is_symlink():
        env = claude.get("env", {}) if isinstance(claude.get("env"), dict) else {}
        if env.get("CLAUDE_CODE_SUBPROCESS_ENV_SCRUB") != "1": errors.append("Claude subprocess credential scrub is not enabled")
        sandbox = claude.get("sandbox", {}) if isinstance(claude.get("sandbox"), dict) else {}
        if not sandbox.get("enabled"): errors.append("Claude sandbox is not enabled")
        if sandbox.get("failIfUnavailable") is not True: errors.append("Claude sandbox is not configured to fail closed when unavailable")
        if sandbox.get("allowUnsandboxedCommands") is not False: errors.append("Claude unsandboxed retry escape hatch is not disabled")
        validate_claude_security(claude, errors)
    codex_hook_map = codex_hooks.get("hooks", {}) if isinstance(codex_hooks.get("hooks"), dict) else {}
    for group in codex_hook_map.get("SessionEnd", []):
        for hook in group.get("hooks", []) if isinstance(group, dict) else []:
            if isinstance(hook, dict) and RUNTIME_MARKER in hook_runtime_reference(hook):
                try:
                    timeout = float(hook.get("timeout", 1))
                except (TypeError, ValueError):
                    errors.append("Codex SessionEnd hook timeout must be numeric")
                else:
                    if timeout > 3:
                        errors.append("Codex SessionEnd hook timeout exceeds 3 seconds")

    policy_path = path / ".agents/state/task-policy.json"
    if policy_path.is_symlink():
        errors.append("Managed file .agents/state/task-policy.json must not be a symlink")
        policy = {}
    else:
        policy = load_json(policy_path, {})
    if isinstance(policy, dict) and "prompt" in policy: errors.append("Raw user prompt is persisted in task-policy.json")
    commands_path = path / "docs/COMMANDS.md"
    commands_text = read_text(commands_path) if not commands_path.is_symlink() else ""
    if commands_text.count(COMMANDS_START) != 1 or commands_text.count(COMMANDS_END) != 1:
        errors.append("docs/COMMANDS.md must contain exactly one managed commands block")
    ownership_path = path / ".agents/state/ownership.json"
    project_id_path = path / ".agents/state/project-id"
    ownership = load_json(ownership_path, {}) if not ownership_path.is_symlink() else {}
    project_id = read_text(project_id_path).strip() if not project_id_path.is_symlink() else ""
    if not isinstance(ownership, dict) or ownership.get("project_id") != project_id:
        errors.append("Project ownership manifest/project-id mismatch")

    codex_config_path = path / ".codex/config.toml"
    if tomllib and codex_config_path.exists() and not codex_config_path.is_symlink():
        try:
            codex_cfg = tomllib.loads(codex_config_path.read_text())
        except Exception as exc:
            errors.append(f"Invalid TOML .codex/config.toml: {exc}")
        else:
            # Semantic validation, not just syntax -- found missing via
            # independent Codex cross-review (2026-08-30): a prior version of
            # this check only confirmed the TOML parsed, so replacing
            # default_permissions with an unrestricted built-in preset (e.g.
            # ":danger-full-access") reported 0 errors even though it removes
            # both the filesystem denies and the network restriction below.
            profile_name = codex_cfg.get("default_permissions")
            if profile_name != "project-edit":
                errors.append(f"Codex default_permissions is {profile_name!r}, expected the hardened 'project-edit' profile")
            # Named codex_edit_profile, not `profile` -- doctor_project() also calls
            # the module-level profile() (project size/capability scanner) elsewhere
            # in this same function, and a local `profile` would shadow it for the
            # whole function body (Python scoping), breaking that unrelated call.
            permissions = codex_cfg.get("permissions", {}) if isinstance(codex_cfg.get("permissions"), dict) else {}
            codex_edit_profile = permissions.get("project-edit", {}) if isinstance(permissions.get("project-edit"), dict) else {}
            codex_network = codex_edit_profile.get("network", {}) if isinstance(codex_edit_profile.get("network"), dict) else {}
            if codex_network.get("enabled") is not False:
                errors.append("Codex project-edit profile does not disable network access")
            codex_filesystem = codex_edit_profile.get("filesystem", {}) if isinstance(codex_edit_profile.get("filesystem"), dict) else {}
            workspace_denies = codex_filesystem.get(":workspace_roots", {}) if isinstance(codex_filesystem.get(":workspace_roots"), dict) else {}
            for pattern in ["**/*.env", "**/*.pem", "**/id_rsa", "**/id_ed25519", "**/credentials.json"]:
                if workspace_denies.get(pattern) != "deny":
                    errors.append(f"Codex project-edit profile is missing filesystem deny for {pattern!r}")
            global_denies = codex_filesystem
            for pattern in ["~/.ssh", "~/.aws/credentials"]:
                if global_denies.get(pattern) != "deny":
                    errors.append(f"Codex project-edit profile is missing filesystem deny for {pattern!r}")
            shell_policy = codex_cfg.get("shell_environment_policy", {}) if isinstance(codex_cfg.get("shell_environment_policy"), dict) else {}
            if shell_policy.get("ignore_default_excludes") is not False:
                errors.append("Codex shell_environment_policy.ignore_default_excludes is not disabled (should be false)")
            validate_codex_security(codex_cfg, codex_hooks, errors)
            codex_servers = codex_cfg.get("mcp_servers", {}) if isinstance(codex_cfg.get("mcp_servers"), dict) else {}
            codex_text = codex_config_path.read_text()
            for name in sorted(mcp_opt_ins):
                expected_server = tomllib.loads(CODEX_MCP_BLOCKS[name])["mcp_servers"][name]
                actual_server = codex_servers.get(name) if isinstance(codex_servers, dict) else None
                start, end = codex_mcp_markers(name)
                markers_present = start in codex_text and end in codex_text
                if not isinstance(actual_server, dict) or any(
                    actual_server.get(key) != value for key, value in expected_server.items()
                ) or not markers_present:
                    errors.append(
                        f"Recorded MCP opt-in '{name}' is missing or changed in .codex/config.toml"
                    )
    elif not tomllib and codex_config_path.exists():
        current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
        errors.append(
            f"Python {current_python} cannot verify the Codex TOML security contract; "
            "Ratchetry requires Python 3.11+"
        )

    if deep and (path / ".agents/runtime/agent_workspace.py").exists() and not (path / ".agents/runtime/agent_workspace.py").is_symlink():
        # Never execute the target's own copy of this file -- in the CI-gate
        # use case (action.yml) `path` is an untrusted checked-out repository,
        # and a crafted pull request could replace
        # .agents/runtime/agent_workspace.py with arbitrary code that would then
        # run on the Actions runner. Instead, hash-compare the target's copy
        # against this framework's own bundled lib/hook_runtime.py (copy2()'d
        # verbatim by install_runtime_hook(), so an unmodified deployment hashes
        # identically) and only ever run the bundled copy, only once the hashes
        # match.
        hook = path / ".agents/runtime/agent_workspace.py"
        bundled = package_root() / "lib/hook_runtime.py"
        try:
            target_hash = hashlib.sha256(hook.read_bytes()).hexdigest()
            bundled_hash = hashlib.sha256(bundled.read_bytes()).hexdigest()
        except Exception as exc:
            errors.append(f"Deep security probe failed: could not read hook runtime: {exc}")
        else:
            if target_hash != bundled_hash:
                errors.append("Deep security probe: .agents/runtime/agent_workspace.py does not match the framework's shipped hook_runtime.py -- run `ratchery refresh`. (Not run directly, to avoid executing unverified code from the target project.)")
            else:
                probe = json.dumps({"hook_event_name": "PreToolUse", "cwd": str(path), "tool_name": "Bash", "tool_input": {"command": "cat .env"}}) + "\n"
                try:
                    result = subprocess.run([sys.executable, str(bundled)], input=probe, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
                    if "deny" not in result.stdout: errors.append("Deep security probe: Bash 'cat .env' was not denied")
                except Exception as exc: errors.append(f"Deep security probe failed: {exc}")

    return emit_doctor_result(
        path, errors, warnings, tier_reported, tier_name_reported, json_output
    )


def preflight(strict: bool = False) -> int:
    errors: list[str] = []; warnings: list[str] = []
    if sys.version_info < (3, 11): errors.append(f"Python 3.11+ required; found {sys.version.split()[0]}")
    if not exists("git"): warnings.append("Git CLI not found; project Git initialization and Git-aware hooks will be limited")
    if sys.platform not in ("darwin", "linux"): warnings.append(f"Installer is primarily tested on macOS/Linux/WSL2; platform={sys.platform}")
    if not exists("claude"): warnings.append("Claude Code CLI not found")
    if not exists("codex"): warnings.append("Codex CLI not found")
    for issue in [
        cli_security_version_issue("claude", "Claude Code", CLAUDE_MIN_SECURITY),
        cli_security_version_issue("codex", "Codex CLI", CODEX_MIN_SECURITY),
    ]:
        if issue:
            severity, message = issue
            (errors if severity == "error" else warnings).append(message)
    qmd_state, qmd_message = qmd_security_state()
    if qmd_state in {"blocked", "unknown"}: warnings.append(qmd_message + "; QMD integration will stay disabled")
    if exists("qmd") and not (exists("node") or exists("bun")): warnings.append("QMD is present but Node/Bun runtime was not found")
    print(f"Python: {sys.version.split()[0]}")
    print("Git:", command_version("git") or shutil.which("git") or "not installed")
    print("Claude:", command_version("claude") or "not installed")
    print("Codex:", command_version("codex") or "not installed")
    print("QMD security:", qmd_message)
    for item in errors: print("ERROR:", item)
    for item in warnings: print("WARN:", item)
    print(f"Preflight: {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors or (strict and warnings) else 0


def qmd_base() -> list[str]:
    # Dedicated named index isolates Ratchetry from project-local .qmd files
    # and from unrelated QMD collections the user may maintain.
    return ["qmd", "--index", QMD_INDEX]


def qmd_run(args: list[str], timeout: float = 120, passthrough: bool = False) -> subprocess.CompletedProcess[str]:
    # Never execute QMD from inside an arbitrary repository. QMD <=2.6.3 can
    # auto-discover checked-in .qmd/index.yml files. Running from HOME plus the
    # dedicated --index keeps Ratchetry on its own configuration surface.
    cmd = qmd_base() + args
    if passthrough:
        return subprocess.run(cmd, cwd=str(Path.home()), text=True, timeout=timeout)
    return run(cmd, cwd=Path.home(), timeout=timeout)


def qmd_allowed(verbose: bool = False) -> bool:
    state, message = qmd_security_state()
    if state != "safe":
        if verbose:
            print("QMD integration disabled:", message, file=sys.stderr)
            print("Install a verified stable QMD release newer than 2.6.3, then rerun this command.", file=sys.stderr)
        return False
    return True


def qmd_collection_list() -> str:
    if not qmd_allowed():
        return ""
    try:
        result = qmd_run(["collection", "list"], timeout=15)
        return result.stdout + result.stderr
    except Exception:
        return ""


def qmd_context_list() -> str:
    if not qmd_allowed():
        return ""
    try:
        result = qmd_run(["context", "list"], timeout=15)
        return result.stdout + result.stderr
    except Exception:
        return ""


def qmd_configured() -> bool:
    return qmd_allowed() and QMD_COLLECTION in qmd_collection_list()


def qmd_context_configured() -> bool:
    return qmd_allowed() and f"qmd://{QMD_COLLECTION}" in qmd_context_list()


def qmd_plan() -> list[list[str]]:
    vault = configured_vault_path().resolve()
    commands: list[list[str]] = []
    if not qmd_configured():
        commands.append(qmd_base() + ["collection", "add", str(vault), "--name", QMD_COLLECTION, "--mask", "**/*.md"])
    if not qmd_context_configured():
        commands.append(qmd_base() + ["context", "add", f"qmd://{QMD_COLLECTION}", "Curated Obsidian knowledge for Ratchetry projects, decisions, bugs, commands, references, and session summaries."])
    commands.append(qmd_base() + ["embed", "-c", QMD_COLLECTION])
    return commands


def print_shell_command(command: list[str]) -> None:
    import shlex
    print("  " + " ".join(shlex.quote(x) for x in command))


def vault_qmd_setup(apply: bool = False) -> int:
    if not qmd_allowed(verbose=True):
        return 2
    print(f"QMD Vault setup plan for isolated index '{QMD_INDEX}'.")
    print("Safety: commands run from HOME with an explicit named index; no repository-local .qmd config is trusted.")
    commands = qmd_plan()
    for command in commands:
        print_shell_command(command)
    if not apply:
        print("Dry plan only. Re-run with --apply to execute these commands explicitly.")
        return 0
    for command in commands:
        print("Running:")
        print_shell_command(command)
        # command already contains the qmd base; execute from HOME to prevent local config discovery.
        result = subprocess.run(command, cwd=str(Path.home()), check=False)
        if result.returncode != 0:
            print("QMD setup stopped after a failed command.", file=sys.stderr)
            return result.returncode
    return 0


def vault_qmd_status() -> int:
    state, message = qmd_security_state()
    print("QMD security:", message)
    if state != "safe":
        return 1
    print("Ratchetry QMD index:", QMD_INDEX)
    print("Collection configured:", "yes" if qmd_configured() else "no")
    result = qmd_run(["status"], timeout=30, passthrough=True)
    return result.returncode


def vault_qmd_reindex(apply: bool = False) -> int:
    if not qmd_allowed(verbose=True):
        return 2
    if not qmd_configured():
        print("Ratchetry QMD index is not configured. Run vault-qmd-setup first.", file=sys.stderr)
        return 2
    # This named index is owned by Ratchetry and never receives an update
    # hook. Still run from HOME so checked-in project config cannot be discovered.
    commands = [qmd_base() + ["update"], qmd_base() + ["embed", "-c", QMD_COLLECTION]]
    print(f"QMD reindex plan for isolated index '{QMD_INDEX}':")
    for command in commands:
        print_shell_command(command)
    if not apply:
        print("Dry plan only. Re-run with --apply to execute.")
        return 0
    for command in commands:
        rc = subprocess.run(command, cwd=str(Path.home()), check=False).returncode
        if rc:
            return rc
    return 0


def fallback_vault_search(query: str, limit: int = 8) -> int:
    vault = validate_vault_root(configured_vault_path()); tokens = [t.lower() for t in re.findall(r"[A-Za-zÀ-ÿ0-9_-]{3,}", query)]
    scored: list[tuple[int, Path, str]] = []
    for path in vault.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(vault).parts): continue
        if path.is_symlink() or not path.is_file(): continue
        text = read_text(path); low = text.lower(); score = sum(low.count(t) for t in tokens)
        if score:
            first = next((line.strip() for line in text.splitlines() if line.strip() and not line.startswith("---")), "")
            scored.append((score, path, first[:180]))
    for score, path, snippet in sorted(scored, key=lambda x: (-x[0], str(x[1])))[:limit]:
        print(f"{path.relative_to(vault)}  score={score}\n  {snippet}")
    return 0 if scored else 1


def vault_search(query: str, limit: int = 8) -> int:
    if qmd_allowed() and qmd_configured():
        result = qmd_run(["query", "-c", QMD_COLLECTION, "--json", "-n", str(limit), query], passthrough=True)
        return result.returncode
    if exists("qmd") and not qmd_allowed():
        print("QMD is installed but blocked by the Ratchetry security gate; using lexical fallback.", file=sys.stderr)
    else:
        print("QMD not configured; using lightweight lexical Vault fallback.", file=sys.stderr)
    return fallback_vault_search(query, limit)


MEMORY_HANDOFF_NAME = "Handoff.json"
MEMORY_LOCK_NAME = ".Handoff.lock"
MEMORY_HOME_MAX_BYTES = 128 * 1024
MEMORY_MAX_PROJECTS = 4096


def _directory_flags() -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return flags


def _regular_read_at(
    directory_fd: int,
    name: str,
    *,
    maximum: int,
    missing_ok: bool = False,
    require_private: bool = False,
) -> tuple[bytes | None, tuple[int, int, int, int] | None]:
    """Read one regular file through an anchored directory descriptor.

    Returning the file identity lets a later mutation prove that the value it
    backed up is still the value being replaced or removed.  ``O_NOFOLLOW`` is
    the primary protection; the post-open ``fstat`` closes the wrong-type and
    oversized-file cases without ever following a repository/Vault symlink.
    """
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        if missing_ok:
            return None, None
        raise ValueError(f"Required memory file {name} was not found") from None
    except OSError as exc:
        raise ValueError(f"Cannot safely open memory file {name}: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"Memory file {name} must be a regular file")
        if require_private and stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError(
                f"Memory file {name} must not grant group or other permissions"
            )
        if metadata.st_size > maximum:
            raise ValueError(f"Memory file {name} exceeds {maximum} bytes")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > maximum:
            raise ValueError(f"Memory file {name} exceeds {maximum} bytes")
        identity = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
        )
        return data, identity
    finally:
        os.close(descriptor)


def _memory_project_id(project_root: Path) -> str:
    require_safe_project_layout(project_root)
    try:
        state_fd = os.open(project_root / ".agents/state", _directory_flags())
    except OSError as exc:
        raise ValueError("Project memory state directory is unavailable or unsafe") from exc
    try:
        data, _identity = _regular_read_at(
            state_fd, "project-id", maximum=128, missing_ok=False
        )
    finally:
        os.close(state_fd)
    assert data is not None
    try:
        value = data.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise ValueError("Project memory identity is not a valid UUID") from exc
    if not me.PROJECT_ID_RE.fullmatch(value):
        raise ValueError("Project memory identity is not a valid UUID")
    return value


def _home_project_id(data: bytes) -> str | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    value = _frontmatter_field_from_text(text, "project_id")
    return value if value and me.PROJECT_ID_RE.fullmatch(value) else None


def _configured_vault_root() -> Path:
    configured = cfg().get("vault_path")
    if not isinstance(configured, str) or not configured.strip():
        raise ValueError(
            "Vault memory is not configured; run `ratchery global-config` first"
        )
    configured_path = Path(configured).expanduser()
    try:
        if configured_path.is_symlink():
            raise ValueError("Configured Vault memory path must not be a symlink")
        vault = configured_path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Configured Vault memory path is unavailable") from exc
    if not vault.is_dir():
        raise ValueError("Configured Vault memory path is not a directory")
    return vault


def _locate_memory_project(project_root: Path) -> dict[str, str | Path]:
    """Resolve the exact Vault project by durable UUID, never by basename."""
    project_id = _memory_project_id(project_root)
    vault = _configured_vault_root()
    try:
        root_fd = os.open(vault, _directory_flags())
    except OSError as exc:
        raise ValueError("Configured Vault memory root is unavailable or unsafe") from exc
    try:
        try:
            projects_fd = os.open("projects", _directory_flags(), dir_fd=root_fd)
        except OSError as exc:
            raise ValueError("Configured Vault has no safe projects directory") from exc
        try:
            names = os.listdir(projects_fd)
            if len(names) > MEMORY_MAX_PROJECTS:
                raise ValueError(
                    f"Vault projects directory exceeds the {MEMORY_MAX_PROJECTS}-entry safety limit"
                )
            matches: list[str] = []
            for name in names:
                if not is_safe_vault_slug(name):
                    continue
                try:
                    project_fd = os.open(name, _directory_flags(), dir_fd=projects_fd)
                except OSError:
                    continue
                try:
                    home, _identity = _regular_read_at(
                        project_fd,
                        "Home.md",
                        maximum=MEMORY_HOME_MAX_BYTES,
                        missing_ok=True,
                    )
                except ValueError:
                    continue
                finally:
                    os.close(project_fd)
                if home is not None and _home_project_id(home) == project_id:
                    matches.append(name)
        finally:
            os.close(projects_fd)
    finally:
        os.close(root_fd)
    if not matches:
        raise ValueError(
            "No Vault project matches this repository's project UUID; run `ratchery refresh` "
            "after repairing any stale Vault Home metadata"
        )
    if len(matches) != 1:
        raise ValueError("Multiple Vault projects claim this repository's project UUID")
    return {"vault": vault, "project_id": project_id, "slug": matches[0]}


def _open_memory_project(location: dict[str, str | Path]) -> tuple[int, int, int]:
    """Open and re-verify the selected Vault directory through anchored fds."""
    vault = location["vault"]
    slug_value = location["slug"]
    project_id = location["project_id"]
    assert isinstance(vault, Path)
    assert isinstance(slug_value, str)
    assert isinstance(project_id, str)
    try:
        root_fd = os.open(vault, _directory_flags())
    except OSError as exc:
        raise ValueError("Configured Vault memory root is unavailable or unsafe") from exc
    try:
        projects_fd = os.open("projects", _directory_flags(), dir_fd=root_fd)
        try:
            project_fd = os.open(slug_value, _directory_flags(), dir_fd=projects_fd)
        except Exception:
            os.close(projects_fd)
            raise
    except Exception:
        os.close(root_fd)
        raise
    try:
        _verify_memory_project_identity(project_fd, project_id)
    except Exception:
        os.close(project_fd)
        os.close(projects_fd)
        os.close(root_fd)
        raise
    return root_fd, projects_fd, project_fd


def _close_memory_project(descriptors: tuple[int, int, int]) -> None:
    for descriptor in reversed(descriptors):
        os.close(descriptor)


def _verify_memory_project_identity(project_fd: int, project_id: str) -> None:
    home, _identity = _regular_read_at(
        project_fd, "Home.md", maximum=MEMORY_HOME_MAX_BYTES
    )
    if home is None or _home_project_id(home) != project_id:
        raise ValueError("Vault project identity changed during the memory operation")


def _open_or_create_private_directory(parent_fd: int, name: str) -> int:
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise ValueError("Memory backup directory is unavailable or unsafe") from exc
    descriptor = -1
    try:
        descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
        os.fchmod(descriptor, 0o700)
        return descriptor
    except OSError as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise ValueError("Memory backup directory is unavailable or unsafe") from exc


def _exclusive_write_at(directory_fd: int, name: str, data: bytes) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    except OSError as exc:
        raise ValueError("Memory backup file could not be created safely") from exc
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _memory_backup(project_id: str, data: bytes, reason: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    base = state_root()
    try:
        base.mkdir(mode=0o700, parents=True, exist_ok=True)
        base_fd = os.open(base, _directory_flags())
        os.fchmod(base_fd, 0o700)
    except OSError as exc:
        raise ValueError("Memory backup state root is unavailable or unsafe") from exc
    descriptors = [base_fd]
    try:
        for name in ("memory-backups", project_id, stamp):
            descriptors.append(_open_or_create_private_directory(descriptors[-1], name))
        destination_fd = descriptors[-1]
        _exclusive_write_at(destination_fd, MEMORY_HANDOFF_NAME, data)
        manifest = (
            json.dumps(
                {
                    "version": VERSION,
                    "created_at": now(),
                    "reason": reason,
                    "project_id": project_id,
                    "file": MEMORY_HANDOFF_NAME,
                },
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        _exclusive_write_at(destination_fd, "manifest.json", manifest)
        os.fsync(destination_fd)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    return base / "memory-backups" / project_id / stamp


def _acquire_memory_lock(project_fd: int) -> int:
    if fcntl is None:
        raise ValueError("Memory handoff mutations require a POSIX file-locking runtime")
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(MEMORY_LOCK_NAME, flags, 0o600, dir_fd=project_fd)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Memory handoff lock must be a regular file")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = os.stat(MEMORY_LOCK_NAME, dir_fd=project_fd, follow_symlinks=False)
        if not stat.S_ISREG(current.st_mode) or (
            current.st_dev,
            current.st_ino,
        ) != (metadata.st_dev, metadata.st_ino):
            raise ValueError("Memory handoff lock changed while opening")
        return descriptor
    except BlockingIOError as exc:
        if "descriptor" in locals():
            os.close(descriptor)
        raise ValueError("Another memory handoff mutation is already in progress") from exc
    except (OSError, ValueError) as exc:
        if "descriptor" in locals():
            os.close(descriptor)
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Memory handoff lock is unavailable or unsafe") from exc


def _release_memory_lock(descriptor: int) -> None:
    assert fcntl is not None
    try:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _identity_at(directory_fd: int, name: str) -> tuple[int, int, int, int] | None:
    try:
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"Memory file {name} must be a regular file")
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns


def _write_handoff_at(
    project_fd: int,
    data: bytes,
    *,
    expected_identity: tuple[int, int, int, int] | None,
) -> None:
    current_identity = _identity_at(project_fd, MEMORY_HANDOFF_NAME)
    if current_identity != expected_identity:
        raise ValueError("Pending handoff changed during update; retry after inspecting it")
    temporary = f".{MEMORY_HANDOFF_NAME}.aw-{uuid.uuid4().hex}"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open(temporary, flags, 0o600, dir_fd=project_fd)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        if expected_identity is None:
            try:
                os.link(
                    temporary,
                    MEMORY_HANDOFF_NAME,
                    src_dir_fd=project_fd,
                    dst_dir_fd=project_fd,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise ValueError(
                    "A pending handoff already exists; inspect it before using --replace"
                ) from exc
            os.unlink(temporary, dir_fd=project_fd)
        else:
            if _identity_at(project_fd, MEMORY_HANDOFF_NAME) != expected_identity:
                raise ValueError(
                    "Pending handoff changed during update; retry after inspecting it"
                )
            os.replace(
                temporary,
                MEMORY_HANDOFF_NAME,
                src_dir_fd=project_fd,
                dst_dir_fd=project_fd,
            )
        os.fsync(project_fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=project_fd)
        except FileNotFoundError:
            pass


def _read_pending_handoff(
    project_fd: int,
) -> tuple[dict[str, Any] | None, bytes | None, tuple[int, int, int, int] | None]:
    data, identity = _regular_read_at(
        project_fd,
        MEMORY_HANDOFF_NAME,
        maximum=me.MAX_STORED_BYTES,
        missing_ok=True,
        require_private=True,
    )
    if data is None:
        return None, None, None
    return me.parse_record(data), data, identity


def memory_backends(json_output: bool = False) -> int:
    payload = {
        "backends": [
            {
                "name": "curated-vault",
                "status": "built-in",
                "automatic_capture": False,
                "network": False,
                "role": "default explicit memory and provider-neutral handoff",
            },
            {
                "name": "ai-memory",
                "status": "experimental",
                "automatic_capture": True,
                "network": True,
                "role": "optional team/multi-machine trial after security review and benchmark",
            },
        ],
        "active": "curated-vault",
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print("Active memory backend: curated-vault (explicit, local, no automatic capture)")
        print("Available:")
        print("  curated-vault [built-in] -- provider-neutral handoffs and curated notes")
        print("  ai-memory [experimental] -- plan only; not installed, started, or configured")
    return 0


def memory_status(path: Path, json_output: bool = False) -> int:
    root = git_root(path.resolve())
    errors: list[str] = []
    warnings: list[str] = []
    handoff: dict[str, Any] | None = None
    try:
        location = _locate_memory_project(root)
        descriptors = _open_memory_project(location)
        try:
            handoff, _data, _identity = _read_pending_handoff(descriptors[2])
        finally:
            _close_memory_project(descriptors)
        if handoff and handoff["project_id"] != location["project_id"]:
            errors.append("Pending handoff belongs to a different project UUID")
            handoff = None
    except (OSError, ValueError, me.HandoffError) as exc:
        errors.append(str(exc))

    provenance = git_provenance(root)
    if handoff:
        handoff_commit = handoff["git"]["commit"]
        current_commit = provenance["commit"]
        if handoff_commit and current_commit and handoff_commit != current_commit:
            warnings.append(
                "Pending handoff was written at a different Git commit; verify it before continuing"
            )
    payload = {
        "backend": "curated-vault",
        "automatic_capture": False,
        "network": False,
        "pending_handoff": handoff is not None,
        "handoff_created_at": handoff.get("created_at") if handoff else None,
        "handoff_source": handoff.get("source_client") if handoff else None,
        "handoff_target": handoff.get("target_client") if handoff else None,
        "ai_memory": {
            "status": "experimental",
            "executable_present": exists("ai-memory"),
            "enabled": False,
        },
        "errors": errors,
        "warnings": warnings,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print("Memory backend: curated-vault")
        print("Automatic capture: disabled")
        print("Network required: no")
        print("Pending handoff:", "yes" if handoff else "no")
        if handoff:
            print(
                f"Handoff: {handoff['source_client']} -> {handoff['target_client']} "
                f"({handoff['created_at']})"
            )
        for item in errors:
            print("ERROR:", item)
        for item in warnings:
            print("WARNING:", item)
    return 1 if errors else 0


def memory_plan(backend: str, json_output: bool = False) -> int:
    if backend == "curated-vault":
        steps = [
            "Configure the Vault path with global-config.",
            "Initialize or refresh the project so its durable UUID matches one Vault Home.",
            "Use memory handoff write/show/clear only at explicit continuation boundaries.",
        ]
        payload = {
            "backend": backend,
            "activation": "built-in",
            "executes_external_tools": False,
            "steps": steps,
        }
    else:
        steps = [
            "Review and install a current, verified ai-memory release manually.",
            "Start loopback-only with bearer auth when exposure is not strictly local and keep LLM/embedding providers disabled.",
            "Configure native hooks in allowlist mode; disable Claude prompt and assistant capture for the baseline.",
            "Add a reviewed .ai-memory.toml marker with repository-specific capture exclusions.",
            "Verify capture policy locally, then benchmark against curated-vault on cost per successful task.",
            "Promote only after privacy, retention, recovery, latency, and context-injection evidence is acceptable.",
        ]
        payload = {
            "backend": backend,
            "activation": "experimental",
            "executes_external_tools": False,
            "steps": steps,
        }
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"Memory backend plan: {backend}")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print("Plan only: no external binary was executed and no configuration was changed.")
    return 0


def memory_handoff_write(
    path: Path,
    input_data: bytes,
    *,
    replace: bool,
    json_output: bool,
) -> int:
    root = git_root(path.resolve())
    location = _locate_memory_project(root)
    payload = me.parse_input(input_data)
    provenance = git_provenance(root)
    record = me.build_record(
        payload,
        project_id=str(location["project_id"]),
        project_slug=str(location["slug"]),
        created_at=now(),
        commit=provenance["commit"],
        dirty=provenance["dirty"],
    )
    encoded = (
        json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    descriptors = _open_memory_project(location)
    backup: Path | None = None
    lock_fd = -1
    try:
        lock_fd = _acquire_memory_lock(descriptors[2])
        _verify_memory_project_identity(
            descriptors[2], str(location["project_id"])
        )
        existing, existing_data, existing_identity = _read_pending_handoff(descriptors[2])
        if existing is not None and not replace:
            print(
                "A pending handoff already exists; inspect it before using --replace.",
                file=sys.stderr,
            )
            return 2
        if existing_data is not None:
            backup = _memory_backup(
                str(location["project_id"]), existing_data, "memory-handoff-replace"
            )
        _verify_memory_project_identity(
            descriptors[2], str(location["project_id"])
        )
        _write_handoff_at(
            descriptors[2], encoded, expected_identity=existing_identity
        )
    finally:
        if lock_fd >= 0:
            _release_memory_lock(lock_fd)
        _close_memory_project(descriptors)
    output = {
        "status": "written",
        "backend": "curated-vault",
        "created_at": record["created_at"],
        "source_client": record["source_client"],
        "target_client": record["target_client"],
        "replaced": backup is not None,
    }
    if json_output:
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(
            f"Stored provider-neutral handoff: {record['source_client']} -> "
            f"{record['target_client']}"
        )
        if backup:
            print("Previous handoff backed up before replacement.")
    return 0


def memory_handoff_show(path: Path, json_output: bool = False) -> int:
    root = git_root(path.resolve())
    location = _locate_memory_project(root)
    descriptors = _open_memory_project(location)
    try:
        record, _data, _identity = _read_pending_handoff(descriptors[2])
    finally:
        _close_memory_project(descriptors)
    if record is None:
        print("No pending handoff.", file=sys.stderr)
        return 1
    if record["project_id"] != location["project_id"]:
        raise ValueError("Pending handoff belongs to a different project UUID")
    if json_output:
        print(json.dumps(record, ensure_ascii=False))
    else:
        print(me.render_text(record), end="")
    return 0


def memory_handoff_clear(path: Path, *, apply: bool) -> int:
    root = git_root(path.resolve())
    location = _locate_memory_project(root)
    descriptors = _open_memory_project(location)
    lock_fd = -1
    try:
        lock_fd = _acquire_memory_lock(descriptors[2])
        _verify_memory_project_identity(
            descriptors[2], str(location["project_id"])
        )
        record, data, identity = _read_pending_handoff(descriptors[2])
        if record is None or data is None or identity is None:
            print("No pending handoff.")
            return 0
        if record["project_id"] != location["project_id"]:
            raise ValueError("Pending handoff belongs to a different project UUID")
        if not apply:
            print("Would clear the pending handoff after creating a private backup.")
            print("Dry run only. Re-run with --apply to clear it.")
            return 0
        backup = _memory_backup(
            str(location["project_id"]), data, "memory-handoff-clear"
        )
        _verify_memory_project_identity(
            descriptors[2], str(location["project_id"])
        )
        if _identity_at(descriptors[2], MEMORY_HANDOFF_NAME) != identity:
            raise ValueError("Pending handoff changed during clear; retry after inspecting it")
        os.unlink(MEMORY_HANDOFF_NAME, dir_fd=descriptors[2])
        os.fsync(descriptors[2])
    finally:
        if lock_fd >= 0:
            _release_memory_lock(lock_fd)
        _close_memory_project(descriptors)
    print("Cleared pending handoff after creating a private backup.")
    print("Backup:", backup)
    return 0


def dispatch_memory(args: argparse.Namespace) -> int:
    """Dispatch memory commands without exposing implementation tracebacks.

    Handoff input and Vault contents are untrusted data.  Expected validation
    and filesystem failures therefore become one concise stderr message while
    machine-readable success output remains uncontaminated on stdout.
    """
    try:
        if args.memory_cmd == "backends":
            return memory_backends(args.json)
        if args.memory_cmd in {"status", "doctor"}:
            return memory_status(Path(args.path), args.json)
        if args.memory_cmd == "plan":
            return memory_plan(args.backend, args.json)
        if args.handoff_cmd == "write":
            if not args.stdin or sys.stdin.isatty():
                print(
                    "Refusing to read an interactive terminal; pass --stdin and pipe one reviewed JSON object.",
                    file=sys.stderr,
                )
                return 2
            input_data = sys.stdin.buffer.read(me.MAX_INPUT_BYTES + 1)
            return memory_handoff_write(
                Path(args.path),
                input_data,
                replace=args.replace,
                json_output=args.json,
            )
        if args.handoff_cmd == "show":
            return memory_handoff_show(Path(args.path), args.json)
        return memory_handoff_clear(Path(args.path), apply=args.apply)
    except (OSError, ValueError, me.HandoffError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


TOOL_ACTIVATION_MODES = {"profile", "on-demand", "experimental", "disabled"}


def load_tool_catalog(lock_path: Path | None = None) -> dict[str, dict[str, Any]]:
    raw = load_json(lock_path or package_root() / "tools.lock.json", {})
    if not isinstance(raw, dict):
        return {}
    return {
        name: entry
        for name, entry in raw.items()
        if not name.startswith("_") and isinstance(entry, dict)
    }


def tool_catalog_issues(lock_path: Path | None = None) -> list[str]:
    path = lock_path or package_root() / "tools.lock.json"
    raw = load_json(path, {})
    if not isinstance(raw, dict):
        return ["tools.lock.json must be a JSON object"]
    issues: list[str] = []
    if raw.get("_schema_version") != 1:
        issues.append("tools.lock.json must declare _schema_version 1")
    entries = {name: value for name, value in raw.items() if not name.startswith("_")}
    if not entries:
        issues.append("tools.lock.json must contain at least one tool")
    for name, entry in entries.items():
        prefix = f"tools.lock.json: {name}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or not isinstance(entry, dict):
            issues.append(f"{prefix} must be a lowercase tool-name object")
            continue
        for field in ("family", "activation", "network", "benchmark", "source", "policy"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                issues.append(f"{prefix}.{field} must be a non-empty string")
        if entry.get("activation") not in TOOL_ACTIVATION_MODES:
            issues.append(f"{prefix}.activation has an unsupported mode")
        commands = entry.get("commands")
        if not isinstance(commands, list) or any(
            not isinstance(command, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", command)
            for command in commands
        ):
            issues.append(f"{prefix}.commands must be a list of safe executable names")
        source = entry.get("source")
        if isinstance(source, str) and not source.startswith("https://"):
            issues.append(f"{prefix}.source must use https")
        if "version_seen" in entry and (
            not isinstance(entry["version_seen"], str) or not entry["version_seen"].strip()
        ):
            issues.append(f"{prefix}.version_seen must be a non-empty string")
        if "commit_seen" in entry and (
            not isinstance(entry["commit_seen"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", entry["commit_seen"])
        ):
            issues.append(f"{prefix}.commit_seen must be a full lowercase Git SHA")
        checked_at = entry.get("checked_at")
        recheck_by = entry.get("recheck_by")
        for field, value in (("checked_at", checked_at), ("recheck_by", recheck_by)):
            try:
                if not isinstance(value, str):
                    raise ValueError
                dt.date.fromisoformat(value)
            except ValueError:
                issues.append(f"{prefix}.{field} must be an ISO date")
        if isinstance(checked_at, str) and isinstance(recheck_by, str):
            try:
                if dt.date.fromisoformat(recheck_by) <= dt.date.fromisoformat(checked_at):
                    issues.append(f"{prefix}.recheck_by must be later than checked_at")
            except ValueError:
                pass
    return issues


def tool_paths() -> dict[str, str | None]:
    paths: dict[str, str | None] = {}
    for name, entry in load_tool_catalog().items():
        paths[name] = next(
            (found for command in entry.get("commands", []) if (found := shutil.which(command))),
            None,
        )
    for name in ("uvx", "uv", "claude", "codex"):
        paths[name] = shutil.which(name)
    return paths


def tools_status(*, probe: bool = False) -> None:
    conf = cfg(); print("External tool policy:", conf.get("external_tools"))
    paths = tool_paths()
    print("Clients/runners:")
    for name in ("claude", "codex", "uv", "uvx"):
        path = paths.get(name)
        version = command_version(path) if path and probe else None
        print(f"- {name}:", (path + (f" | {version}" if version else "")) if path else "not installed")
    print("Optional-tool catalog (discovery runs no optional binary unless --probe is explicit):")
    for name, entry in load_tool_catalog().items():
        path = paths.get(name)
        commands = entry.get("commands", [])
        version = command_version(path) if path and probe else None
        if path:
            state = path + (f" | {version}" if version else "")
        elif commands:
            state = "not installed"
        else:
            state = "no standalone command probe"
        print(f"- {name} [{entry['activation']}/{entry['family']}]: {state}")
        print(f"    network: {entry['network']}")
    if probe:
        qmd_state, qmd_message = qmd_security_state()
        print("qmd security:", qmd_message)
        if qmd_state == "safe":
            print(
                f"qmd index {QMD_INDEX}:",
                "configured" if qmd_configured() else "not configured",
            )
    else:
        print("qmd security: not executed; use `tools-status --probe` for explicit probes")


def tools_recommend(path: Path | None = None, *, probe: bool = False) -> None:
    paths = tool_paths()
    qmd_probe = qmd_security_state() if probe else None
    if path and path.exists():
        root = git_root(path.resolve()); p = inspect_project(root)
        print(f"Project profile: {p['size']} | capabilities: {', '.join(k for k,v in p['capabilities'].items() if v) or 'generic'}")
        installed = {name: bool(found) for name, found in paths.items()}
        opted_in = mcp_opted_in(root)
        installed["serena"] = "serena" in opted_in
        installed["context7"] = "context7" in opted_in
        installed["qmd"] = bool(
            qmd_probe
            and qmd_probe[0] == "safe"
            and paths.get("qmd")
            and qmd_configured()
        )
        print("Tool Router recommendations by task kind (advisory; benchmark policy still applies):")
        for kind in tr.TASK_KINDS:
            recs = tr.route(kind, p, installed)
            print(f"- {kind}:")
            for rec in recs:
                print(f"    {rec['tool']} -- {rec['rationale']}")
        if p["source_files"] >= 40: print("- ast-grep [profile]: structural AST search for precise repeated code patterns")
        tier_state = load_json(root / ".agents/state/tier.json", {})
        effective_tier = tier_state.get("effective_tier", "T0")
        if effective_tier in {"T1", "T2", "T3"}:
            print("- gitleaks [profile]: explicit pre-commit/release secret scan")
        if p["capabilities"].get("cloud_infra"):
            print("- trivy [profile]: consolidated container/IaC/repository security scan")
            print("- checkov [on-demand]: add only for focused findings not covered by Trivy")
        if effective_tier in {"T2", "T3"} and p["source_files"]:
            print("- semgrep [profile]: explicit SAST for the stricter security bar")
    print("Global/observability:")
    if qmd_probe:
        print(f"- QMD: {qmd_probe[1]}")
    elif paths.get("qmd"):
        print("- QMD: command found; security/configuration not executed (use --probe)")
    else:
        print("- QMD: not installed")
    print("  Ratchetry never auto-installs QMD; after installing a verified safe stable release, use `vault-qmd-setup` then `--apply`.")
    print("- ccusage [profile]: local usage observability and Ratchetry benchmark input; not a runtime dependency")
    print("- RTK / Context Mode [experimental]: benchmark separately before enabling either broadly")


def tools_install() -> None:
    # Backward-compatible command name. Ratchetry deliberately performs no
    # third-party installation: QMD 2.6.3 has known project-local trust issues,
    # and the stable baseline should never silently mutate global developer tools.
    print("Ratchetry does not auto-install third-party tools.")
    qmd_path = shutil.which("qmd")
    print(
        "QMD:",
        f"command found at {qmd_path}; version/security not probed"
        if qmd_path
        else "not installed",
    )
    print("Review `ratchery tools-recommend` and install optional tools explicitly after reviewing their current releases.")


RTK_INSTALL_COMMAND = (
    "cargo install --git https://github.com/rtk-ai/rtk "
    "--rev FULL_40_CHAR_COMMIT_SHA --locked"
)
RTK_CLAUDE_PREVIEW_COMMAND = "rtk init -g --dry-run -v"
RTK_CLAUDE_INIT_COMMAND = "rtk init -g"
RTK_CODEX_PREVIEW_COMMAND = "rtk init -g --codex --dry-run -v"
RTK_CODEX_INIT_COMMAND = "rtk init -g --codex"


def tools_install_named(name: str) -> int:
    """Print, never run, the exact command to install one optional tool.
    Same non-automation policy as `vault-qmd-setup`: this only prints a
    reviewable command; the human runs it and pins a version themselves."""
    if name == "rtk":
        rtk_path = shutil.which("rtk")
        if rtk_path:
            print(f"RTK command found at {rtk_path}; version not executed or verified")
            return 0
        print("Ratchetry does not auto-install RTK. To install it yourself:")
        print(
            "  First verify the signed v0.48.0 release's full 40-character commit SHA "
            "(currently shown upstream with prefix fde0a8f)."
        )
        print(f"  {RTK_INSTALL_COMMAND}")
        print("  Replace the placeholder before running; a mutable Git tag is not an immutable pin.")
        print("Preview each client integration before allowing it to modify global configuration:")
        print(f"  # Claude Code preview: {RTK_CLAUDE_PREVIEW_COMMAND}")
        print(f"  # Claude Code apply:   {RTK_CLAUDE_INIT_COMMAND}")
        print(f"  # Codex preview:       {RTK_CODEX_PREVIEW_COMMAND}")
        print(f"  # Codex apply:         {RTK_CODEX_INIT_COMMAND}")
        print("Claude uses a PreToolUse hook; Codex uses AGENTS.md/RTK.md instructions, not that hook.")
        print("Keep RTK telemetry disabled and benchmark against raw output before broad activation.")
        return 0
    print(f"Unknown tool: {name}. Supported names: rtk.")
    return 1


def _ccusage_date(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not re.fullmatch(r"\d{8}", value):
        raise ef.BenchmarkError(f"{label} must use YYYYMMDD")
    try:
        dt.datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ef.BenchmarkError(f"{label} is not a valid calendar date") from exc
    return value


def _ccusage_project(value: str | None) -> str | None:
    if value is None:
        return None
    if not value or len(value) > 200 or any(ord(char) < 32 for char in value):
        raise ef.BenchmarkError(
            "ccusage project must be 1-200 characters without control characters"
        )
    return value


def ccusage_command(
    *,
    period: str,
    source: str | None = None,
    since: str | None = None,
    until: str | None = None,
    project: str | None = None,
    session_id: str | None = None,
    json_output: bool = False,
    offline: bool = False,
) -> list[str]:
    """Build a validated argv list for ccusage; never return shell syntax."""
    if period not in {"daily", "weekly", "monthly", "session"}:
        raise ef.BenchmarkError(f"unsupported ccusage period: {period}")
    source = ef.validate_source_name(source)
    since = _ccusage_date(since, "since")
    until = _ccusage_date(until, "until")
    project = _ccusage_project(project)
    session_id = ef.validate_session_id(session_id)
    if since and until and since > until:
        raise ef.BenchmarkError("since cannot be later than until")
    if project and period != "daily":
        raise ef.BenchmarkError("--project is currently supported only with --period daily")
    if session_id and period != "session":
        raise ef.BenchmarkError("--session-id requires --period session")

    command = ["ccusage"]
    if source:
        command.append(source)
    command.append(period)
    if since:
        command.extend(["--since", since])
    if until:
        command.extend(["--until", until])
    if project:
        command.extend(["--project", project])
    if session_id:
        command.extend(["--id", session_id])
    if json_output:
        command.append("--json")
    if offline:
        command.append("--offline")
    return command


def usage(
    *,
    period: str,
    source: str | None,
    since: str | None,
    until: str | None,
    project: str | None,
    session_id: str | None,
    json_output: bool,
    offline: bool,
) -> int:
    if not exists("ccusage"):
        print(
            "ccusage is not installed. It is optional observability, not an Ratchetry dependency.",
            file=sys.stderr,
        )
        print(
            "Review the current ccusage release before installing it, then rerun `ratchery usage`.",
            file=sys.stderr,
        )
        return 1
    try:
        command = ccusage_command(
            period=period,
            source=source,
            since=since,
            until=until,
            project=project,
            session_id=session_id,
            json_output=json_output,
            offline=offline,
        )
    except ef.BenchmarkError as exc:
        print(f"usage: {exc}", file=sys.stderr)
        return 2
    if not json_output:
        return subprocess.run(command, cwd=str(Path.home()), check=False).returncode
    try:
        result = run(command, cwd=Path.home(), timeout=120)
    except subprocess.TimeoutExpired:
        print("usage: ccusage timed out after 120 seconds", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"usage: could not run ccusage: {exc}", file=sys.stderr)
        return 1
    if result.returncode != 0:
        print(
            f"usage: ccusage failed with exit {result.returncode}; "
            "run the same ccusage command directly to inspect its diagnostic",
            file=sys.stderr,
        )
        return result.returncode or 1
    try:
        report = json.loads(
            result.stdout,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant {value}")
            ),
        )
        if not isinstance(report, (dict, list)):
            raise ValueError("top level must be an object or array")
        output = json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"usage: ccusage emitted invalid JSON: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


def benchmark_task_set_directory() -> Path:
    return package_root() / "benchmarks"


def _strict_json_file(path: Path, label: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ef.BenchmarkError(f"{label} must be a regular JSON file: {path}")
    try:
        return json.loads(
            path.read_text(),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant {value}")
            ),
        )
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ef.BenchmarkError(f"cannot read {label}: {exc}") from exc


def _shipped_task_set_paths() -> list[Path]:
    directory = benchmark_task_set_directory()
    if directory.is_symlink() or not directory.is_dir():
        raise ef.BenchmarkError("bundled benchmark task-set directory is missing or invalid")
    return sorted(
        path
        for path in directory.glob("*.json")
        if path.is_file() and not path.is_symlink()
    )


def load_benchmark_task_set(target: str, *, allow_path: bool = False) -> tuple[dict[str, Any], Path, str]:
    shipped_by_id: dict[str, Path] = {}
    for path in _shipped_task_set_paths():
        raw = _strict_json_file(path, "bundled benchmark task set")
        checked = ef.validate_task_set(raw)
        if checked["id"] in shipped_by_id:
            raise ef.BenchmarkError(f"duplicate bundled task-set id: {checked['id']}")
        shipped_by_id[checked["id"]] = path

    if target in shipped_by_id:
        path = shipped_by_id[target]
    elif allow_path:
        path = Path(target).expanduser().resolve()
    else:
        raise ef.BenchmarkError(
            f"unknown bundled task set {target!r}; run `ratchery benchmark suites`"
        )
    checked = ef.validate_task_set(_strict_json_file(path, "benchmark task set"))
    digest = ef.task_set_digest(checked)
    fixture = package_root() / checked["protocol"]["fixture"]
    if path in shipped_by_id.values() and (
        fixture.is_symlink() or not fixture.is_dir()
    ):
        raise ef.BenchmarkError(
            f"bundled task-set fixture is missing or invalid: {checked['protocol']['fixture']}"
        )
    return checked, path, digest


def benchmark_task_set_identity(value: str) -> str:
    bundled_selectors: set[str] = set()
    for path in _shipped_task_set_paths():
        bundled_selectors.add(path.stem)
        raw = _strict_json_file(path, "bundled benchmark task set")
        task_set_id = raw.get("id") if isinstance(raw, dict) else None
        if isinstance(task_set_id, str):
            bundled_selectors.add(task_set_id)

    if value in bundled_selectors:
        # A bundled suite name is authoritative. Do not silently downgrade a
        # broken bundled definition to an opaque user-supplied label.
        checked, _path, digest = load_benchmark_task_set(value)
        return f"{checked['id']}@sha256:{digest}"
    if not ef.SAFE_EVIDENCE_LABEL.fullmatch(value):
        raise ef.BenchmarkError(
            "task_set must be a bundled suite id or a short evidence label"
        )
    return value


def benchmark_suites(*, json_output: bool) -> int:
    try:
        suites = []
        for path in _shipped_task_set_paths():
            checked, _resolved, digest = load_benchmark_task_set(path.stem)
            suites.append(
                {
                    "id": checked["id"],
                    "title": checked["title"],
                    "tasks": len(checked["tasks"]),
                    "minimum_trials_per_arm": checked["minimum_trials_per_arm"],
                    "sha256": digest,
                }
            )
    except ef.BenchmarkError as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2
    if json_output:
        print(json.dumps({"schema_version": 1, "suites": suites}, sort_keys=True))
    else:
        for suite in suites:
            print(
                f"{suite['id']}: {suite['tasks']} tasks, "
                f"minimum {suite['minimum_trials_per_arm']} trials/arm, "
                f"sha256:{suite['sha256']}"
            )
            print(f"  {suite['title']}")
    return 0


def benchmark_show(*, target: str, json_output: bool) -> int:
    try:
        checked, _path, digest = load_benchmark_task_set(target)
    except ef.BenchmarkError as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2
    if json_output:
        print(
            json.dumps(
                {**checked, "sha256": digest},
                ensure_ascii=False,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 0
    print(f"{checked['id']}: {checked['title']}")
    print(checked["description"])
    print(
        f"Protocol: manual, network disabled, no secrets, "
        f"minimum {checked['minimum_trials_per_arm']} trials/arm"
    )
    print(f"Fixture: {checked['protocol']['fixture']}")
    print(f"Identity: {checked['id']}@sha256:{digest}")
    for task in checked["tasks"]:
        print(f"\n{task['id']} [{task['category']}]\n{task['prompt']}")
        for criterion in task["success_criteria"]:
            print(f"- {criterion}")
    return 0


def benchmark_validate(*, target: str, json_output: bool) -> int:
    try:
        checked, path, digest = load_benchmark_task_set(target, allow_path=True)
    except ef.BenchmarkError as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2
    result = {
        "valid": True,
        "id": checked["id"],
        "tasks": len(checked["tasks"]),
        "minimum_trials_per_arm": checked["minimum_trials_per_arm"],
        "sha256": digest,
    }
    if json_output:
        print(json.dumps(result, sort_keys=True))
    else:
        print(
            f"Valid task set {checked['id']} ({len(checked['tasks'])} tasks) at {path}"
        )
        print(f"Identity: {checked['id']}@sha256:{digest}")
    return 0


def benchmark_directory(project_root: Path, *, create: bool) -> Path:
    agents_dir = project_root / ".agents"
    if not agents_dir.is_dir() or agents_dir.is_symlink():
        raise ef.BenchmarkError(
            "project must be initialized and contain a real .agents directory"
        )
    project_id_path = agents_dir / "state" / "project-id"
    if project_id_path.is_symlink() or not project_id_path.is_file():
        raise ef.BenchmarkError(
            "project benchmark storage requires a real .agents/state/project-id; "
            "run `ratchery refresh`"
        )
    try:
        project_id = str(uuid.UUID(project_id_path.read_text().strip()))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ef.BenchmarkError("project benchmark storage requires a valid project UUID") from exc

    root_fingerprint = hashlib.sha256(str(project_root.resolve()).encode()).hexdigest()[:16]
    namespace = f"{project_id}-{root_fingerprint}"
    storage_root = state_root()
    directories = [
        storage_root,
        storage_root / "benchmarks",
        storage_root / "benchmarks" / namespace,
    ]
    resolved_project = project_root.resolve()
    for directory in directories:
        resolved_directory = directory.resolve(strict=False)
        if (
            resolved_directory == resolved_project
            or resolved_project in resolved_directory.parents
        ):
            raise ef.BenchmarkError(
                "benchmark state must resolve outside the project repository"
            )
        if directory.exists() and (directory.is_symlink() or not directory.is_dir()):
            raise ef.BenchmarkError(f"benchmark state path must be a real directory: {directory}")
        if create:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if directory.is_symlink() or directory.resolve() != resolved_directory:
                raise ef.BenchmarkError(
                    f"benchmark state path changed or became a symlink: {directory}"
                )
    return directories[-1]


def benchmark_snapshot_path(project_root: Path, name: str, *, create_dir: bool) -> Path:
    ef.validate_benchmark_name(name)
    directory = benchmark_directory(project_root, create=create_dir)
    return directory / f"{name}.json"


def clean_git_commit(project_root: Path) -> str:
    """Return HEAD only when the benchmark starts from a clean Git worktree."""
    git_env = clean_git_environment()
    try:
        commit_result = subprocess.run(
            safe_git_read_command("rev-parse", "--verify", "HEAD"),
            cwd=str(project_root),
            env=git_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        status_result = subprocess.run(
            safe_git_read_command(
                "status", "--porcelain=v1", "--untracked-files=normal"
            ),
            cwd=str(project_root),
            env=git_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ef.BenchmarkError(f"could not verify clean Git provenance: {exc}") from exc
    commit = commit_result.stdout.strip()
    if commit_result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise ef.BenchmarkError("benchmark capture requires a repository with a valid HEAD")
    if status_result.returncode != 0:
        raise ef.BenchmarkError("could not inspect the benchmark worktree status")
    if status_result.stdout:
        raise ef.BenchmarkError(
            "benchmark capture requires a clean worktree so both arms can reproduce the same code"
        )
    return commit


def _benchmark_configuration_file(
    path: Path,
    display: str,
    *,
    ignored_json_keys: set[str] | None = None,
) -> tuple[dict[str, str], int]:
    """Hash one known configuration file without following a replaced symlink."""
    try:
        before = path.lstat()
    except FileNotFoundError:
        return {"path": display, "state": "missing"}, 0
    except OSError as exc:
        raise ef.BenchmarkError(f"cannot inspect benchmark configuration {display}: {exc}") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ef.BenchmarkError(
            f"benchmark configuration must contain only regular, non-symlink files: {display}"
        )
    if before.st_size > BENCHMARK_CONFIGURATION_MAX_FILE_BYTES:
        raise ef.BenchmarkError(f"benchmark configuration file is too large: {display}")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ef.BenchmarkError(f"cannot open benchmark configuration {display}: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise ef.BenchmarkError(
                f"benchmark configuration changed while opening: {display}"
            )
        data = bytearray()
        while len(data) <= BENCHMARK_CONFIGURATION_MAX_FILE_BYTES:
            chunk = os.read(descriptor, min(65536, BENCHMARK_CONFIGURATION_MAX_FILE_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if len(data) > BENCHMARK_CONFIGURATION_MAX_FILE_BYTES:
        raise ef.BenchmarkError(f"benchmark configuration file is too large: {display}")
    if (
        (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        or after.st_size != len(data)
    ):
        raise ef.BenchmarkError(f"benchmark configuration changed while reading: {display}")
    digest_data = bytes(data)
    state = "file"
    if ignored_json_keys:
        try:
            parsed = json.loads(
                digest_data,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-standard JSON constant {value}")
                ),
            )
        except (UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ef.BenchmarkError(
                f"benchmark configuration JSON is invalid: {display}: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ef.BenchmarkError(
                f"benchmark configuration JSON must be an object: {display}"
            )
        for key in ignored_json_keys:
            parsed.pop(key, None)
        digest_data = json.dumps(
            parsed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        state = "normalized-json"
    return {
        "path": display,
        "state": state,
        "sha256": hashlib.sha256(digest_data).hexdigest(),
    }, len(data)


def benchmark_configuration_digest(
    project_root: Path,
    *,
    task_set: str,
    model: str,
    client_version: str,
    environment_id: str,
    configuration: str,
    ccusage_version: str,
) -> str:
    """Fingerprint bounded agent configuration without persisting its contents."""
    root = project_root.resolve()
    records: list[dict[str, str]] = []
    total_bytes = 0
    seen: set[str] = set()

    for relative in BENCHMARK_CONFIGURATION_PARENTS:
        parent = root / relative
        try:
            parent_stat = parent.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ef.BenchmarkError(
                f"cannot inspect benchmark configuration parent {relative}: {exc}"
            ) from exc
        if stat.S_ISLNK(parent_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
            raise ef.BenchmarkError(
                f"benchmark configuration parent must be real and non-symlinked: {relative}"
            )

    def add_file(
        path: Path,
        display: str,
        *,
        ignored_json_keys: set[str] | None = None,
    ) -> None:
        nonlocal total_bytes
        if display in seen:
            return
        record, size = _benchmark_configuration_file(
            path, display, ignored_json_keys=ignored_json_keys
        )
        seen.add(display)
        records.append(record)
        total_bytes += size
        if len(records) > BENCHMARK_CONFIGURATION_MAX_FILES:
            raise ef.BenchmarkError("benchmark configuration contains too many files")
        if total_bytes > BENCHMARK_CONFIGURATION_MAX_TOTAL_BYTES:
            raise ef.BenchmarkError("benchmark configuration exceeds the 8 MiB total limit")

    for relative in BENCHMARK_CONFIGURATION_FILES:
        add_file(
            root / relative,
            relative,
            ignored_json_keys=BENCHMARK_CONFIGURATION_VOLATILE_JSON_KEYS.get(relative),
        )

    for relative in BENCHMARK_CONFIGURATION_DIRECTORIES:
        directory = root / relative
        try:
            directory_stat = directory.lstat()
        except FileNotFoundError:
            records.append({"path": relative, "state": "missing-directory"})
            continue
        except OSError as exc:
            raise ef.BenchmarkError(
                f"cannot inspect benchmark configuration directory {relative}: {exc}"
            ) from exc
        if stat.S_ISLNK(directory_stat.st_mode) or not stat.S_ISDIR(directory_stat.st_mode):
            raise ef.BenchmarkError(
                f"benchmark configuration directory must be real and non-symlinked: {relative}"
            )
        records.append({"path": relative, "state": "directory"})

        def walk_error(exc: OSError) -> None:
            raise ef.BenchmarkError(
                f"cannot walk benchmark configuration directory {relative}: {exc}"
            ) from exc

        for current, directory_names, file_names in os.walk(
            directory, topdown=True, followlinks=False, onerror=walk_error
        ):
            directory_names.sort()
            file_names.sort()
            current_path = Path(current)
            for name in directory_names:
                child = current_path / name
                child_relative = child.relative_to(root).as_posix()
                try:
                    child_stat = child.lstat()
                except OSError as exc:
                    raise ef.BenchmarkError(
                        f"cannot inspect benchmark configuration directory {child_relative}: {exc}"
                    ) from exc
                if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISDIR(child_stat.st_mode):
                    raise ef.BenchmarkError(
                        "benchmark configuration directories must not contain links or special files: "
                        f"{child_relative}"
                    )
            for name in file_names:
                child = current_path / name
                add_file(child, child.relative_to(root).as_posix())

    runtime_policy = package_root() / "tools.lock.json"
    add_file(runtime_policy, "@runtime/tools.lock.json")
    machine = os.uname().machine if hasattr(os, "uname") else "unknown"
    payload = {
        "schema_version": 1,
        "files": sorted(records, key=lambda item: item["path"]),
        "facts": {
            "agent_workspace_version": VERSION,
            "ccusage_version": ccusage_version,
            "client_version": client_version,
            "configuration": configuration,
            "environment_id": environment_id,
            "machine": machine,
            "model": model,
            "python": (
                f"{sys.implementation.name}-"
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            ),
            "sys_platform": sys.platform,
            "task_set": task_set,
        },
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def benchmark_capture(
    *,
    path: Path,
    name: str,
    source: str | None,
    since: str | None,
    until: str | None,
    project: str | None,
    session_id: str | None,
    task_set: str,
    model: str,
    client_version: str,
    environment_id: str,
    configuration: str,
    attempted_tasks: int,
    successful_tasks: int,
    replace: bool,
) -> int:
    if not exists("ccusage"):
        print("benchmark: ccusage is not installed", file=sys.stderr)
        return 1
    try:
        if session_id:
            if not source:
                raise ef.BenchmarkError("--session-id requires --source")
            if since or until or project:
                raise ef.BenchmarkError(
                    "--session-id cannot be combined with --since, --until, or --project"
                )
            period = "session"
        else:
            if not since or not until:
                raise ef.BenchmarkError(
                    "capture requires both --since and --until, or one --session-id"
                )
            period = "daily"
        command = ccusage_command(
            period=period,
            source=source,
            since=since,
            until=until,
            project=project,
            session_id=session_id,
            json_output=True,
            offline=True,
        )
        root = git_root(path.resolve())
        git_commit = clean_git_commit(root)
        destination = benchmark_snapshot_path(root, name, create_dir=False)
        if destination.exists() and not replace:
            raise ef.BenchmarkError(
                f"benchmark '{name}' already exists; pass --replace to overwrite it"
            )
        task_set_identity = benchmark_task_set_identity(task_set)
        ccusage_version = command_version("ccusage") or "unknown"
        configuration_digest = benchmark_configuration_digest(
            root,
            task_set=task_set_identity,
            model=model,
            client_version=client_version,
            environment_id=environment_id,
            configuration=configuration,
            ccusage_version=ccusage_version,
        )
        result = run(command, cwd=Path.home(), timeout=120)
        if result.returncode != 0:
            print(
                f"benchmark: ccusage failed with exit {result.returncode}; "
                "run the same ccusage command directly to inspect its diagnostic",
                file=sys.stderr,
            )
            return result.returncode or 1
        metrics = ef.parse_ccusage_json(result.stdout)
        snapshot = ef.make_snapshot(
            name=name,
            metrics=metrics,
            filters={
                "source": source or "all",
                "project": ef.project_fingerprint(project),
                "period": period,
                "selection": "session" if session_id else "date-window",
                "since": since,
                "until": until,
                "offline": True,
            },
            provenance={
                "git_commit": git_commit,
                "task_set": task_set_identity,
                "model": model,
                "client_version": client_version,
                "environment_id": environment_id,
                "configuration": configuration,
                "configuration_digest": configuration_digest,
            },
            attempted_tasks=attempted_tasks,
            successful_tasks=successful_tasks,
            captured_at=now(),
            ccusage_version=ccusage_version,
        )
        # Revalidate the parent immediately before the write. This also avoids
        # leaving an empty benchmark directory when ccusage or parsing fails.
        destination = benchmark_snapshot_path(root, name, create_dir=True)
        if destination.exists() and not replace:
            raise ef.BenchmarkError(
                f"benchmark '{name}' already exists; pass --replace to overwrite it"
            )
        write_benchmark_snapshot(destination, snapshot, replace=replace)
    except subprocess.TimeoutExpired:
        print("benchmark: ccusage timed out after 120 seconds", file=sys.stderr)
        return 1
    except (ef.BenchmarkError, OSError, UnicodeError) as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2
    print(f"Captured aggregate benchmark '{name}' at {destination}")
    print("Stored: token totals, estimated cost, filters, and task counts; no raw sessions or prompts.")
    return 0


def _load_benchmark(project_root: Path, name: str) -> dict[str, Any]:
    path = benchmark_snapshot_path(project_root, name, create_dir=False)
    if path.is_symlink() or not path.is_file():
        raise ef.BenchmarkError(f"benchmark '{name}' does not exist as a regular file")
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ef.BenchmarkError(f"cannot read benchmark '{name}': {exc}") from exc
    return ef.validate_snapshot(value)


def _format_benchmark_number(field: str, value: int | float | None) -> str:
    if value is None:
        return "n/a"
    if field == "estimated_cost_usd" or field == "cost_per_successful_task":
        return f"${value:.6f}"
    if field == "success_rate":
        return f"{value * 100:.2f}%"
    return f"{int(value):,}"


def benchmark_compare(*, path: Path, baseline_name: str, candidate_name: str, json_output: bool) -> int:
    try:
        root = git_root(path.resolve())
        baseline = _load_benchmark(root, baseline_name)
        candidate = _load_benchmark(root, candidate_name)
        comparison = ef.compare_snapshots(baseline, candidate)
    except (ef.BenchmarkError, OSError) as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2
    if json_output:
        print(json.dumps(comparison, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0

    print(f"Benchmark: {comparison['baseline']} -> {comparison['candidate']}")
    provenance = comparison["provenance"]
    print(
        "Evidence: "
        f"commit={provenance['git_commit'][:12]}, task-set={provenance['task_set']}, "
        f"model={provenance['model']}, client={provenance['client_version']}, "
        f"environment={provenance['environment_id']}"
    )
    print(
        "Configuration: "
        f"{provenance['baseline_configuration']} -> "
        f"{provenance['candidate_configuration']}"
    )
    print(
        "Configuration digests: "
        f"{provenance['baseline_configuration_digest'][:12]} -> "
        f"{provenance['candidate_configuration_digest'][:12]}"
    )
    scope = comparison["scope"]
    print(
        "Scope: "
        f"source={scope['source']}, project={scope['project'] or 'all'}, "
        f"period={scope['period']}, offline={str(scope['offline']).lower()}, "
        f"ccusage={scope['ccusage_version'] or 'unknown'}"
    )
    labels = {
        "total_tokens": "Total tokens",
        "estimated_cost_usd": "Estimated cost",
        "success_rate": "Task success rate",
        "cost_per_successful_task": "Cost/successful task",
        "input_tokens": "Input tokens",
        "output_tokens": "Output tokens",
        "cache_creation_tokens": "Cache creation",
        "cache_read_tokens": "Cache read",
    }
    for field in (
        "total_tokens",
        "estimated_cost_usd",
        "success_rate",
        "cost_per_successful_task",
        "input_tokens",
        "output_tokens",
        "cache_creation_tokens",
        "cache_read_tokens",
    ):
        delta = comparison["metrics"][field]
        percent = delta["percent_delta"]
        percent_text = "n/a" if percent is None else f"{percent:+.2f}%"
        print(
            f"- {labels[field]}: "
            f"{_format_benchmark_number(field, delta['baseline'])} -> "
            f"{_format_benchmark_number(field, delta['candidate'])} ({percent_text})"
        )
    print("Interpretation is manual: repeat identical tasks and keep quality constant before adopting a tool.")
    return 0


def benchmark_report(
    *,
    path: Path,
    baseline_names: list[str],
    candidate_names: list[str],
    minimum_trials: int,
    minimum_success_rate: float,
    json_output: bool,
) -> int:
    try:
        root = git_root(path.resolve())
        baseline = [_load_benchmark(root, name) for name in baseline_names]
        candidate = [_load_benchmark(root, name) for name in candidate_names]
        report = ef.report_snapshots(
            baseline,
            candidate,
            minimum_trials=minimum_trials,
            minimum_success_rate=minimum_success_rate,
        )
    except (ef.BenchmarkError, OSError) as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2
    if json_output:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0

    print(
        f"Benchmark report: {report['baseline_configuration']} -> "
        f"{report['candidate_configuration']}"
    )
    print(
        "Configuration digests: "
        f"{report['baseline_configuration_digest'][:12]} -> "
        f"{report['candidate_configuration_digest'][:12]}"
    )
    samples = report["samples"]
    print(
        f"Samples: baseline={samples['baseline']}, candidate={samples['candidate']}, "
        f"minimum={samples['minimum_trials_per_arm']} per arm"
    )
    for field, label in (
        ("cost_per_successful_task", "Median cost/successful task"),
        ("total_tokens", "Median total tokens"),
        ("success_rate", "Median task success rate"),
    ):
        metric = report["metrics"][field]
        delta = metric["median_delta"]
        percent = delta["percent_delta"]
        percent_text = "n/a" if percent is None else f"{percent:+.2f}%"
        print(
            f"- {label}: {_format_benchmark_number(field, delta['baseline'])} -> "
            f"{_format_benchmark_number(field, delta['candidate'])} ({percent_text})"
        )
    print(
        "Quality floor: "
        f"{'met' if report['quality']['candidate_floor_met'] else 'not met'}; "
        "relative quality: "
        f"{'preserved' if report['quality']['relative_quality_preserved'] else 'regressed'}"
    )
    print(f"Result: {report['result']['status']}")
    print("No automated adoption decision is emitted; inspect task quality and repeated evidence manually.")
    return 0


def budget_check(
    *,
    period: str,
    source: str | None,
    since: str | None,
    until: str | None,
    project: str | None,
    session_id: str | None,
    max_cost_usd: float | None,
    max_tokens: int | None,
    spike_baseline_tokens: int | None,
    spike_multiplier: float,
    enforce: bool,
    json_output: bool,
) -> int:
    try:
        if period == "session":
            if not source or not session_id:
                raise ef.BenchmarkError("session budget checks require --source and --session-id")
            if since or until or project:
                raise ef.BenchmarkError(
                    "session budget checks cannot use --since, --until, or --project"
                )
        elif period == "daily":
            if session_id:
                raise ef.BenchmarkError("--session-id requires --period session")
            if bool(since) != bool(until):
                raise ef.BenchmarkError("daily budget checks require both --since and --until")
            if not since:
                since = until = dt.date.today().strftime("%Y%m%d")
        else:
            raise ef.BenchmarkError("budget period must be daily or session")
        # Reject invalid or absent thresholds before invoking the external
        # collector. The dry validation uses zero metrics and has no side effects.
        ef.evaluate_budget(
            {"total_tokens": 0, "estimated_cost_usd": 0.0},
            max_cost_usd=max_cost_usd,
            max_tokens=max_tokens,
            spike_baseline_tokens=spike_baseline_tokens,
            spike_multiplier=spike_multiplier,
        )
        command = ccusage_command(
            period=period,
            source=source,
            since=since,
            until=until,
            project=project,
            session_id=session_id,
            json_output=True,
            offline=True,
        )
        if not exists("ccusage"):
            print("budget: ccusage is not installed", file=sys.stderr)
            return 1
        result = run(command, cwd=Path.home(), timeout=120)
        if result.returncode != 0:
            print(
                f"budget: ccusage failed with exit {result.returncode}; "
                "run the same ccusage command directly to inspect its diagnostic",
                file=sys.stderr,
            )
            return result.returncode or 1
        metrics = ef.parse_ccusage_json(result.stdout)
        evaluation = ef.evaluate_budget(
            metrics,
            max_cost_usd=max_cost_usd,
            max_tokens=max_tokens,
            spike_baseline_tokens=spike_baseline_tokens,
            spike_multiplier=spike_multiplier,
        )
        payload = {
            **evaluation,
            "scope": {
                "period": period,
                "source": source or "all",
                "project": ef.project_fingerprint(project),
                "since": since,
                "until": until,
                "offline": True,
            },
            "enforced": enforce,
        }
    except subprocess.TimeoutExpired:
        print("budget: ccusage timed out after 120 seconds", file=sys.stderr)
        return 1
    except (ef.BenchmarkError, OSError, UnicodeError) as exc:
        print(f"budget: {exc}", file=sys.stderr)
        return 2

    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))
    else:
        print(
            f"Budget: {payload['status']} — {payload['metrics']['total_tokens']:,} tokens, "
            f"estimated ${payload['metrics']['estimated_cost_usd']:.6f}"
        )
        for check in payload["checks"]:
            if check["kind"] == "cost":
                detail = f"${check['actual']:.6f} / ${check['limit']:.6f}"
            else:
                detail = f"{check['actual']:,.0f} / {check['limit']:,.0f} tokens"
            print(f"- {check['kind']}: {check['status']} ({detail})")
        print("Estimates come from offline ccusage data; this is not an invoice or a pre-spend hard cap.")
    if enforce and payload["status"] != "ok":
        return 3
    return 0


def native_doctor(command: str, args: list[str], timeout: float = 20) -> tuple[bool, str]:
    if not exists(command):
        return False, "not installed"
    try:
        result = run([command, *args], cwd=Path.home(), timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout:.0f}s"
    except Exception as exc:
        return False, str(exc)
    text = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode == 0:
        return True, (text.splitlines()[-1][:240] if text else "OK")
    # Older CLIs may not provide a doctor command. Treat unsupported commands as
    # an informational warning, not an Ratchetry failure.
    low = text.lower()
    if "unknown" in low and "doctor" in low or "unrecognized" in low and "doctor" in low:
        return False, "native doctor unavailable in this CLI version"
    return False, f"exit={result.returncode}: {text[-400:]}"


def stale_tools_lock_entries(lock_path: Path | None = None) -> list[str]:
    """Surface catalog entries whose review deadline has passed."""
    lock = load_json(lock_path or package_root() / "tools.lock.json", {})
    if not isinstance(lock, dict):
        return []
    today = dt.date.today()
    overdue: list[str] = []
    for name, entry in lock.items():
        recheck_by = entry.get("recheck_by") if isinstance(entry, dict) else None
        if not recheck_by:
            continue
        try:
            due = dt.date.fromisoformat(recheck_by)
        except ValueError:
            overdue.append(f"tools.lock.json: {name}'s recheck_by ({recheck_by!r}) is not a valid date")
            continue
        if today >= due:
            overdue.append(
                f"tools.lock.json: {name}'s policy metadata hasn't been rechecked "
                f"since its {recheck_by} deadline"
            )
    return overdue


def global_doctor(deep: bool = False) -> int:
    conf = cfg(); errors: list[str] = []; warnings: list[str] = []
    vault_path = conf.get("vault_path")
    if vault_path is not None and not isinstance(vault_path, str):
        errors.append("Configured Vault path must be a string or null")
        vault_path = None
    elif vault_path and not Path(vault_path).exists():
        errors.append("Configured Vault path is unavailable")
    elif not vault_path:
        print("Vault memory: not configured (optional)")
    if not conf.get("projects_root") or not Path(conf["projects_root"]).exists(): errors.append("Projects root missing")
    for path in [Path.home() / ".claude/CLAUDE.md", Path.home() / ".codex/AGENTS.md", Path.home() / ".agents/skills"]:
        if not path.exists(): errors.append(f"Missing {path}")
    try:
        global_skills = registered_global_skills()
    except ValueError as exc:
        errors.append(str(exc))
        global_skills = []
    for name in global_skills:
        source = package_root() / "assets/global/skills" / name / "SKILL.md"
        canonical = Path.home() / ".agents/skills" / name
        if canonical.is_symlink() or managed_directory_marker(canonical) is None:
            errors.append(f"Missing or user-owned global Skill {canonical}")
            continue
        if not (canonical / "SKILL.md").is_file() or (canonical / "SKILL.md").read_bytes() != source.read_bytes():
            errors.append(f"Global Skill content drifted from the installed release: {canonical}")
        claude = Path.home() / ".claude/skills" / name
        if claude.is_symlink():
            if claude.resolve(strict=False) != canonical.resolve(strict=False):
                errors.append(f"Claude global Skill symlink points outside the canonical catalog: {claude}")
        else:
            if managed_directory_marker(claude) is None:
                errors.append(f"Missing or user-owned Claude global Skill {claude}")
            elif not (claude / "SKILL.md").is_file() or (claude / "SKILL.md").read_bytes() != source.read_bytes():
                errors.append(f"Claude global Skill content drifted from the installed release: {claude}")
    if not exists("claude"): warnings.append("Claude Code CLI not found")
    if not exists("codex"): warnings.append("Codex CLI not found")
    for issue in [
        cli_security_version_issue("claude", "Claude Code", CLAUDE_MIN_SECURITY),
        cli_security_version_issue("codex", "Codex CLI", CODEX_MIN_SECURITY),
    ]:
        if issue:
            severity, message = issue
            (errors if severity == "error" else warnings).append(message)
    if sys.version_info < (3, 11): errors.append("Python 3.11+ required")
    qmd_state, qmd_message = qmd_security_state()
    if qmd_state in {"blocked", "unknown"}: warnings.append(qmd_message + "; QMD integration disabled")
    elif deep and vault_path and qmd_state == "safe" and not qmd_configured(): warnings.append("Safe QMD installed but Vault collection is not configured")
    warnings.extend(tool_catalog_issues())
    warnings.extend(stale_tools_lock_entries())

    if deep and exists("codex"):
        ok, detail = native_doctor("codex", ["doctor"], 25)
        print("Codex native doctor:", "OK" if ok else "WARN", "-", detail)
        if not ok and "unavailable" not in detail: warnings.append("Codex native doctor did not complete cleanly")
    if deep and vault_path and qmd_state == "safe" and qmd_configured():
        try:
            result = qmd_run(["doctor"], timeout=30)
            print("QMD doctor:", "OK" if result.returncode == 0 else f"WARN exit={result.returncode}")
            if result.returncode != 0: warnings.append("QMD doctor reported an issue")
        except Exception as exc:
            warnings.append(f"QMD doctor failed: {exc}")

    for item in errors: print("ERROR:", item)
    for item in warnings: print("WARN:", item)
    vault_rc = 0
    if not errors and vault_path:
        print("Running Vault doctor..."); vault_rc = vault_audit(Path(vault_path))
    print(f"Global doctor: {len(errors)} error(s), {len(warnings)} warning(s).")
    return 1 if errors or vault_rc else 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="ratchery")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="cmd", required=True)

    gc = sub.add_parser("global-config", help="Write the global ~/.ratchery config (optional Vault, projects root, layout)."); gc_vault = gc.add_mutually_exclusive_group(); gc_vault.add_argument("--vault", help="Existing Obsidian Vault path (optional)."); gc_vault.add_argument("--no-vault", action="store_true", help="Explicitly disable Vault memory."); gc.add_argument("--projects-root", required=True); gc.add_argument("--project-layout", choices=["flat", "categorized"], default="flat"); gc.add_argument("--external-tools", choices=["none", "recommended"], default="none")
    setup = sub.add_parser("setup", help="Configure this user account after a package manager installs Ratchetry.")
    setup_vault = setup.add_mutually_exclusive_group()
    setup_vault.add_argument("--vault", help="Existing Obsidian Vault path (optional durable memory).")
    setup_vault.add_argument("--no-vault", action="store_true", help="Explicitly disable Vault memory.")
    setup.add_argument("--projects-root", default=str(Path.home() / "Projects"), help="Default parent for projects (default: ~/Projects).")
    setup.add_argument("--project-layout", choices=["flat", "categorized"], default="flat")
    setup.add_argument("--vault-migration", choices=["safe", "preserve"], default="safe")
    setup.add_argument("--external-tools", choices=["none", "recommended"], default="none")
    setup.add_argument("--dry-run", action="store_true", help="Show the plan without writing files.")
    setup.add_argument("--yes", action="store_true", help="Apply without interactive confirmation.")
    sub.add_parser("install-global", help="Install/refresh the global CLAUDE.md and AGENTS.md managed blocks.")
    pf = sub.add_parser("preflight", help="Check environment prerequisites (Python, git, etc.) before install."); pf.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    vi = sub.add_parser("vault-install", help="Install or update the Vault kit at the configured vault path."); vi.add_argument("--migration", choices=["safe", "preserve"], default="safe")
    vp = sub.add_parser("vault-plan", help="Preview what vault-install would change, without writing anything."); vp.add_argument("--vault"); vp.add_argument("--migration", choices=["safe", "preserve"], default="safe")
    va = sub.add_parser("vault-doctor", help="Check the Vault kit for missing/broken required files."); va.add_argument("--vault")
    vrf = sub.add_parser("vault-refresh", help="Re-apply managed Vault blocks (README, AGENTS.md, CLAUDE.md, templates)."); vrf.add_argument("--vault")
    fy = sub.add_parser("vault-fix-yaml", help="Find and fix malformed frontmatter YAML across Vault notes."); fy.add_argument("--vault"); fy.add_argument("--apply", action="store_true", help="Write the fixes; without this flag, only report what would change.")
    sm = sub.add_parser("vault-migrate-session-logs", help="Move logs out of the old global session-logs/ bucket into each project's own folder. Dry-run unless --apply."); sm.add_argument("--vault"); sm.add_argument("--apply", action="store_true")
    rb = sub.add_parser("vault-rollback", help="Restore the Vault from a backup directory created by a previous vault-install/vault-fix-yaml run."); rb.add_argument("backup_dir")
    qs = sub.add_parser("vault-qmd-setup", help="Set up the optional QMD semantic index for the Vault (isolated, opt-in)."); qs.add_argument("--apply", action="store_true", help="Write the setup; without this flag, only report what would change.")
    sub.add_parser("vault-qmd-status", help="Show whether the QMD semantic index is configured and its security state.")
    qr = sub.add_parser("vault-qmd-reindex", help="Rebuild the QMD semantic index for the Vault."); qr.add_argument("--apply", action="store_true", help="Run the reindex; without this flag, only report what would happen.")
    vs = sub.add_parser("vault-search", help="Search the Vault (via QMD if configured, otherwise a plain-text fallback)."); vs.add_argument("query"); vs.add_argument("-n", "--limit", type=int, default=8)
    memory_parser = sub.add_parser(
        "memory", help="Inspect curated memory and exchange bounded provider-neutral handoffs."
    )
    memory_sub = memory_parser.add_subparsers(dest="memory_cmd", required=True)
    memory_backends_parser = memory_sub.add_parser(
        "backends", help="List stable and experimental memory backends without probing them."
    )
    memory_backends_parser.add_argument("--json", action="store_true")
    for command in ("status", "doctor"):
        memory_status_parser = memory_sub.add_parser(
            command, help="Validate this project's curated memory identity and pending handoff."
        )
        memory_status_parser.add_argument("--path", default=".")
        memory_status_parser.add_argument("--json", action="store_true")
    memory_plan_parser = memory_sub.add_parser(
        "plan", help="Print a non-mutating activation/evaluation plan for one backend."
    )
    memory_plan_parser.add_argument("backend", choices=["curated-vault", "ai-memory"])
    memory_plan_parser.add_argument("--json", action="store_true")
    handoff_parser = memory_sub.add_parser(
        "handoff", help="Write, show, or explicitly clear the single pending handoff."
    )
    handoff_sub = handoff_parser.add_subparsers(dest="handoff_cmd", required=True)
    handoff_write_parser = handoff_sub.add_parser(
        "write", help="Validate JSON from stdin and store one provider-neutral handoff."
    )
    handoff_write_parser.add_argument("--path", default=".")
    handoff_write_parser.add_argument(
        "--stdin", action="store_true", help="Confirm that the handoff JSON is supplied on stdin."
    )
    handoff_write_parser.add_argument(
        "--replace", action="store_true", help="Back up and replace an existing pending handoff."
    )
    handoff_write_parser.add_argument("--json", action="store_true")
    handoff_show_parser = handoff_sub.add_parser(
        "show", help="Show the pending handoff without consuming or modifying it."
    )
    handoff_show_parser.add_argument("--path", default=".")
    handoff_show_parser.add_argument("--json", action="store_true")
    handoff_clear_parser = handoff_sub.add_parser(
        "clear", help="Preview or clear the pending handoff after a private backup."
    )
    handoff_clear_parser.add_argument("--path", default=".")
    handoff_clear_parser.add_argument(
        "--apply", action="store_true", help="Actually clear the handoff; default is dry-run."
    )
    dg = sub.add_parser("doctor-global", help="Check the global install (config, Vault, tool policy) for problems."); dg.add_argument("--deep", action="store_true", help="Run additional, slower checks.")
    sub.add_parser("tools-install-recommended", help="Print guidance for installing the recommended optional tool set.")
    tin = sub.add_parser("tools-install", help="Print (never run) the install command for one optional tool."); tin.add_argument("name", choices=["rtk"])
    tr = sub.add_parser("tools-recommend", help="Suggest optional tools worth enabling for a given project."); tr.add_argument("--path"); tr.add_argument("--probe", action="store_true", help="Explicitly execute version/security probes for detected tools.")
    tools_status_parser = sub.add_parser("tools-status", help="Show which optional external tools are discoverable without executing them.")
    tools_status_parser.add_argument("--probe", action="store_true", help="Explicitly execute version/security probes for detected tools.")
    usage_parser = sub.add_parser(
        "usage",
        help="Show local coding-agent token/cost usage via ccusage, if installed.",
    )
    usage_parser.add_argument(
        "--period", choices=["daily", "weekly", "monthly", "session"], default="daily"
    )
    usage_parser.add_argument(
        "--source",
        help="Optional ccusage source namespace (for example: claude or codex).",
    )
    usage_parser.add_argument("--since", help="Start date in YYYYMMDD format.")
    usage_parser.add_argument("--until", help="End date in YYYYMMDD format.")
    usage_parser.add_argument(
        "--project", help="Project name filter; supported with --period daily."
    )
    usage_parser.add_argument(
        "--session-id", help="Exact session ID; supported with --period session."
    )
    usage_parser.add_argument("--json", action="store_true", help="Emit ccusage JSON only.")
    usage_parser.add_argument(
        "--offline",
        action="store_true",
        help="Use cached pricing and avoid ccusage pricing-network access.",
    )

    benchmark = sub.add_parser(
        "benchmark", help="Capture and compare local aggregate token/cost evidence."
    )
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_cmd", required=True)
    benchmark_capture_parser = benchmark_sub.add_parser(
        "capture", help="Capture one offline ccusage aggregate benchmark window."
    )
    benchmark_capture_parser.add_argument("name")
    benchmark_capture_parser.add_argument("--path", default=".")
    benchmark_capture_parser.add_argument("--source")
    benchmark_capture_parser.add_argument("--project")
    benchmark_capture_parser.add_argument("--since", help="YYYYMMDD")
    benchmark_capture_parser.add_argument("--until", help="YYYYMMDD")
    benchmark_capture_parser.add_argument(
        "--session-id",
        help="Exact session to aggregate; requires --source and is never persisted.",
    )
    benchmark_capture_parser.add_argument(
        "--task-set", required=True, help="Stable ID for the repeated task protocol."
    )
    benchmark_capture_parser.add_argument(
        "--model", required=True, help="Exact model ID used for this arm."
    )
    benchmark_capture_parser.add_argument(
        "--client-version", required=True, help="Coding-agent client version ID."
    )
    benchmark_capture_parser.add_argument(
        "--environment-id", required=True, help="Stable environment/permissions ID."
    )
    benchmark_capture_parser.add_argument(
        "--configuration", required=True, help="Arm configuration ID, e.g. native or rtk."
    )
    benchmark_capture_parser.add_argument("--attempted-tasks", type=int, required=True)
    benchmark_capture_parser.add_argument("--successful-tasks", type=int, required=True)
    benchmark_capture_parser.add_argument(
        "--replace", action="store_true", help="Explicitly overwrite an existing snapshot."
    )
    benchmark_compare_parser = benchmark_sub.add_parser(
        "compare", help="Compare two compatible aggregate benchmark snapshots."
    )
    benchmark_compare_parser.add_argument("baseline")
    benchmark_compare_parser.add_argument("candidate")
    benchmark_compare_parser.add_argument("--path", default=".")
    benchmark_compare_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable comparison JSON."
    )
    benchmark_suites_parser = benchmark_sub.add_parser(
        "suites", help="List bundled benchmark task protocols without running an agent."
    )
    benchmark_suites_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable suite metadata."
    )
    benchmark_show_parser = benchmark_sub.add_parser(
        "show", help="Show one bundled benchmark task protocol."
    )
    benchmark_show_parser.add_argument("task_set")
    benchmark_show_parser.add_argument(
        "--json", action="store_true", help="Emit the validated protocol as JSON."
    )
    benchmark_validate_parser = benchmark_sub.add_parser(
        "validate", help="Validate a bundled task-set ID or a local task-set JSON file."
    )
    benchmark_validate_parser.add_argument("task_set")
    benchmark_validate_parser.add_argument(
        "--json", action="store_true", help="Emit the validation result as JSON."
    )
    benchmark_report_parser = benchmark_sub.add_parser(
        "report", help="Summarize repeated compatible benchmark snapshots."
    )
    benchmark_report_parser.add_argument(
        "--baseline", action="append", required=True, help="Baseline snapshot name; repeat for each trial."
    )
    benchmark_report_parser.add_argument(
        "--candidate", action="append", required=True, help="Candidate snapshot name; repeat for each trial."
    )
    benchmark_report_parser.add_argument("--path", default=".")
    benchmark_report_parser.add_argument("--minimum-trials", type=int, default=3)
    benchmark_report_parser.add_argument("--minimum-success-rate", type=float, default=1.0)
    benchmark_report_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable aggregate statistics."
    )

    budget_parser = sub.add_parser(
        "budget", help="Check offline aggregate usage against explicit local thresholds."
    )
    budget_sub = budget_parser.add_subparsers(dest="budget_cmd", required=True)
    budget_check_parser = budget_sub.add_parser(
        "check", help="Evaluate daily or session ccusage totals without persisting them."
    )
    budget_check_parser.add_argument("--period", choices=["daily", "session"], default="daily")
    budget_check_parser.add_argument("--source")
    budget_check_parser.add_argument("--since", help="Start date in YYYYMMDD; defaults to today for daily checks.")
    budget_check_parser.add_argument("--until", help="End date in YYYYMMDD; defaults to today for daily checks.")
    budget_check_parser.add_argument("--project")
    budget_check_parser.add_argument("--session-id")
    budget_check_parser.add_argument("--max-cost-usd", type=float)
    budget_check_parser.add_argument("--max-tokens", type=int)
    budget_check_parser.add_argument(
        "--spike-baseline-tokens", type=int, help="Typical comparable-period token total."
    )
    budget_check_parser.add_argument("--spike-multiplier", type=float, default=10.0)
    budget_check_parser.add_argument(
        "--enforce", action="store_true", help="Return exit 3 when a limit or spike warning fires."
    )
    budget_check_parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable evaluation JSON."
    )
    new = sub.add_parser("new", help="Create a new project directory and initialize it with ratchery."); new.add_argument("name"); new.add_argument("--parent"); new.add_argument("--category", choices=CATEGORIES)
    init = sub.add_parser("init", help="Initialize ratchery files (AGENTS.md, CLAUDE.md, .claude/, .codex/) in an existing project."); init.add_argument("--path", default=".")
    refresh = sub.add_parser("refresh", help="Re-apply managed files in an already-initialized project."); refresh.add_argument("--path", default=".")
    doctor = sub.add_parser("doctor", help="Check a project's ratchery setup for missing/broken required files."); doctor.add_argument("--path", default="."); doctor.add_argument("--deep", action="store_true", help="Run additional, slower checks."); doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of human text (for CI). Exit code is unchanged.")

    tier = sub.add_parser("tier", help="Show/recompute this project's adaptive tier (T0-T3)."); tier.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of human text. Still writes/updates tier state as usual.")
    tier.add_argument("--path", default=".")
    tier.add_argument("--acknowledge-downgrade", metavar="REASON", help="Accept a lower tier than previously recorded; logged with this rationale.")

    ts = sub.add_parser("tier-set", help="Edit the risk-answers facts that drive tier classification, then recompute.")
    ts.add_argument("--path", default=".")
    ts.add_argument("--users", choices=["internal", "external", "public"])
    ts.add_argument("--pii", action=argparse.BooleanOptionalAction)
    ts.add_argument("--payments", action=argparse.BooleanOptionalAction)
    ts.add_argument("--life-safety", action=argparse.BooleanOptionalAction)
    ts.add_argument("--regulated", action=argparse.BooleanOptionalAction)
    ts.add_argument("--data-sensitivity", choices=["none", "internal", "confidential", "restricted"])
    ts.add_argument("--external-exposure", action=argparse.BooleanOptionalAction)
    ts.add_argument("--maturity", choices=["prototype", "active", "stable", "legacy"])

    astat = sub.add_parser("agents-status", help="Show which agents are active in this project and why.")
    astat.add_argument("--path", default=".")

    aen = sub.add_parser("agents", help="Explicitly enable/disable an on-demand agent for this project.")
    aen_sub = aen.add_subparsers(dest="agents_cmd", required=True)
    aen_enable = aen_sub.add_parser("enable", help="Enable an on-demand agent for this project."); aen_enable.add_argument("name"); aen_enable.add_argument("--path", default=".")
    aen_disable = aen_sub.add_parser("disable", help="Disable an agent that was previously enabled for this project."); aen_disable.add_argument("name"); aen_disable.add_argument("--path", default=".")

    mcp_parser = sub.add_parser("mcp", help="Opt in/out of an optional MCP integration (never auto-injected).")
    mcp_sub = mcp_parser.add_subparsers(dest="mcp_cmd", required=True)
    mcp_p_enable = mcp_sub.add_parser("enable", help="Configure an optional MCP server for Claude Code and Codex."); mcp_p_enable.add_argument("name", choices=["serena", "context7"]); mcp_p_enable.add_argument("--path", default=".")
    mcp_p_disable = mcp_sub.add_parser("disable", help="Remove a Ratchetry-managed MCP server from both clients."); mcp_p_disable.add_argument("name", choices=["serena", "context7"]); mcp_p_disable.add_argument("--path", default=".")
    mcp_p_status = mcp_sub.add_parser("status", help="Show which MCP servers are enabled for this project."); mcp_p_status.add_argument("--path", default=".")

    args = parser.parse_args()
    try:
        _dispatch(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


def _dispatch(args: argparse.Namespace) -> None:
    if args.cmd == "global-config":
        vault = setup_vault_path(args.vault, args.no_vault)
        if vault is not None:
            vault = validate_vault_install_targets(vault)
        projects_root = validate_projects_workspace_targets(
            Path(args.projects_root), args.project_layout
        )
        data = {
            "version": VERSION,
            "vault_path": str(vault) if vault is not None else None,
            "projects_root": str(projects_root),
            "project_layout": args.project_layout,
            "external_tools": args.external_tools,
            "thresholds": {"medium_files": 150, "medium_lines": 25000, "large_files": 800, "large_lines": 120000, "large_packages": 5},
        }
        save_cfg(data); setup_projects_workspace(Path(data["projects_root"]), data["project_layout"])
    elif args.cmd == "setup":
        raise SystemExit(
            setup_workspace(
                vault=setup_vault_path(args.vault, args.no_vault),
                projects_root=Path(args.projects_root),
                project_layout=args.project_layout,
                vault_migration=args.vault_migration,
                external_tools=args.external_tools,
                dry_run=args.dry_run,
                assume_yes=args.yes,
            )
        )
    elif args.cmd == "install-global": global_guidance()
    elif args.cmd == "preflight": raise SystemExit(preflight(args.strict))
    elif args.cmd == "vault-install": vault_install(args.migration)
    elif args.cmd == "vault-plan":
        vault = configured_vault_path(args.vault); print_vault_plan(vault_plan(vault, args.migration))
    elif args.cmd == "vault-doctor": raise SystemExit(vault_audit(Path(args.vault) if args.vault else None))
    elif args.cmd == "vault-refresh": vault_refresh(Path(args.vault) if args.vault else None)
    elif args.cmd == "vault-fix-yaml": raise SystemExit(fix_frontmatter_yaml(Path(args.vault) if args.vault else None, args.apply))
    elif args.cmd == "vault-migrate-session-logs":
        vault = configured_vault_path(args.vault)
        plan = migrate_session_logs(vault, args.apply)
        for move in plan["moves"]:
            verb = "Moved" if args.apply else "Would move"
            print(f"{verb}: {move['from']} -> {move['to']}")
        for skip in plan["skipped"]:
            print(f"Skipped: {skip['path']} ({skip['reason']})")
        if not plan["moves"] and not plan["skipped"]:
            print("Nothing to migrate.")
        if args.apply and plan["moves"]:
            print(f"Backup: {plan['backup']}")
        elif plan["moves"]:
            print(f"Dry run only. Re-run with --apply to move {len(plan['moves'])} file(s).")
    elif args.cmd == "vault-rollback": raise SystemExit(rollback_vault(Path(args.backup_dir)))
    elif args.cmd == "vault-qmd-setup": raise SystemExit(vault_qmd_setup(args.apply))
    elif args.cmd == "vault-qmd-status": raise SystemExit(vault_qmd_status())
    elif args.cmd == "vault-qmd-reindex": raise SystemExit(vault_qmd_reindex(args.apply))
    elif args.cmd == "vault-search": raise SystemExit(vault_search(args.query, args.limit))
    elif args.cmd == "memory":
        raise SystemExit(dispatch_memory(args))
    elif args.cmd == "doctor-global": raise SystemExit(global_doctor(args.deep))
    elif args.cmd == "tools-install-recommended": tools_install()
    elif args.cmd == "tools-install": raise SystemExit(tools_install_named(args.name))
    elif args.cmd == "tools-recommend": tools_recommend(Path(args.path) if args.path else None, probe=args.probe)
    elif args.cmd == "tools-status": tools_status(probe=args.probe)
    elif args.cmd == "usage":
        raise SystemExit(
            usage(
                period=args.period,
                source=args.source,
                since=args.since,
                until=args.until,
                project=args.project,
                session_id=args.session_id,
                json_output=args.json,
                offline=args.offline,
            )
        )
    elif args.cmd == "benchmark":
        if args.benchmark_cmd == "capture":
            raise SystemExit(
                benchmark_capture(
                    path=Path(args.path),
                    name=args.name,
                    source=args.source,
                    since=args.since,
                    until=args.until,
                    project=args.project,
                    session_id=args.session_id,
                    task_set=args.task_set,
                    model=args.model,
                    client_version=args.client_version,
                    environment_id=args.environment_id,
                    configuration=args.configuration,
                    attempted_tasks=args.attempted_tasks,
                    successful_tasks=args.successful_tasks,
                    replace=args.replace,
                )
            )
        if args.benchmark_cmd == "compare":
            raise SystemExit(
                benchmark_compare(
                    path=Path(args.path),
                    baseline_name=args.baseline,
                    candidate_name=args.candidate,
                    json_output=args.json,
                )
            )
        if args.benchmark_cmd == "suites":
            raise SystemExit(benchmark_suites(json_output=args.json))
        if args.benchmark_cmd == "show":
            raise SystemExit(benchmark_show(target=args.task_set, json_output=args.json))
        if args.benchmark_cmd == "validate":
            raise SystemExit(benchmark_validate(target=args.task_set, json_output=args.json))
        raise SystemExit(
            benchmark_report(
                path=Path(args.path),
                baseline_names=args.baseline,
                candidate_names=args.candidate,
                minimum_trials=args.minimum_trials,
                minimum_success_rate=args.minimum_success_rate,
                json_output=args.json,
            )
        )
    elif args.cmd == "budget":
        raise SystemExit(
            budget_check(
                period=args.period,
                source=args.source,
                since=args.since,
                until=args.until,
                project=args.project,
                session_id=args.session_id,
                max_cost_usd=args.max_cost_usd,
                max_tokens=args.max_tokens,
                spike_baseline_tokens=args.spike_baseline_tokens,
                spike_multiplier=args.spike_multiplier,
                enforce=args.enforce,
                json_output=args.json,
            )
        )
    elif args.cmd == "new":
        conf = cfg(); parent = Path(args.parent).expanduser() if args.parent else Path(conf["projects_root"])
        if args.category: parent = parent / args.category
        path = parent / args.name; path.parent.mkdir(parents=True, exist_ok=True); path.mkdir(parents=True, exist_ok=False)
        if exists("git"): run(["git", "init"], path)
        init_project(path)
    elif args.cmd in ("init", "refresh"): init_project(Path(args.path))
    elif args.cmd == "doctor": raise SystemExit(doctor_project(Path(args.path), args.deep, args.json))
    elif args.cmd == "tier":
        path = git_root(Path(args.path).resolve())
        require_safe_project_layout(path)
        # Tier is a writing refresh command: always rescan so a stale cached
        # profile cannot keep complexity (and therefore rigor) artificially low.
        p = profile(path)
        out = ae.classify(path, p, acknowledge_downgrade=args.acknowledge_downgrade)
        newly_active = install_agents(path, p, out)
        risk_answers_recorded = ae.default_answers_path(path).is_file()
        if args.json:
            print(json.dumps({
                **out,
                "active_agents": sorted(newly_active),
                "risk_answers_recorded": risk_answers_recorded,
            }, ensure_ascii=False))
        else:
            print(f"Effective tier: {out['effective_tier']} ({out['tier_name']})")
            print(f"Computed this run: {out['computed_tier']}  |  criticality {out['criticality_score']}/15  complexity {out['complexity_score']}/8")
            if out.get("ratcheted"):
                print("NOTE: risk ratchet held the tier at its previously recorded level.")
                print('Run with --acknowledge-downgrade "<reason>" to accept the lower tier.')
            if out.get("downgrade_acknowledged"):
                print(f"Downgrade acknowledged and logged: {out['downgrade_reason']}")
            if not risk_answers_recorded:
                print(
                    "ACTION REQUIRED: this tier uses unreviewed low-risk defaults. Run "
                    "`ratchery tier-set --path .` with the project's real risk facts."
                )
            print(f"Active agents for this tier: {', '.join(sorted(newly_active))}")
            print("Details: .agents/state/tier.md")
    elif args.cmd == "tier-set":
        path = git_root(Path(args.path).resolve())
        require_safe_project_layout(path)
        answers = ae.load_risk_answers(path)
        field_map = {
            "users": args.users, "handles_pii": args.pii, "handles_payments": args.payments,
            "life_safety": args.life_safety, "regulated": args.regulated,
            "data_sensitivity": args.data_sensitivity, "external_exposure": args.external_exposure,
            "maturity": args.maturity,
        }
        for key, value in field_map.items():
            if value is not None: answers[key] = value
        ae.save_risk_answers(path, answers)
        p = profile(path)
        out = ae.classify(path, p)
        install_agents(path, p, out)
        print("Risk answers reviewed and saved to .agents/state/risk-answers.json")
        print(f"Effective tier: {out['effective_tier']} ({out['tier_name']})")
    elif args.cmd == "agents-status":
        path = git_root(Path(args.path).resolve())
        require_safe_project_layout(path)
        # Status is observational; do not create IDs or refresh cached state.
        p = inspect_project(path)
        tier_state = load_json(path / ".agents/state/tier.json", {})
        active = active_agent_names(p, tier_state)
        registry = agent_registry().get("agents", {})
        installed = {f.stem for f in (path / ".claude/agents").glob("*.md")} if (path / ".claude/agents").exists() else set()
        print(f"Tier: {tier_state.get('effective_tier', '?')}")
        print("Active (installed and expected):")
        for name in sorted(ALWAYS_ON_AGENTS | set(active)):
            reason = active.get(name, "baseline agent, always installed")
            mark = "OK" if name in installed else "MISSING"
            print(f"  [{mark}] {name} -- {reason}")
        on_demand = [n for n, meta in registry.items() if meta.get("activation") == "on-demand"]
        print("On-demand (never auto-installed; `ratchery agents enable <name>`):")
        for name in sorted(on_demand):
            mark = "enabled" if name in installed else "available"
            print(f"  [{mark}] {name}")
        orphaned = installed - ALWAYS_ON_AGENTS - set(active) - set(on_demand)
        if orphaned:
            print("Installed but no longer implied by current tier/capabilities (not auto-removed):")
            for name in sorted(orphaned):
                print(f"  {name}")
    elif args.cmd == "agents":
        path = git_root(Path(args.path).resolve())
        require_safe_project_layout(path)
        assets = package_root() / "assets/project"
        registry = agent_registry().get("agents", {})
        name = args.name
        if name not in registry:
            print(f"Unknown agent: {name}. Run 'ratchery agents-status' to see valid names."); raise SystemExit(1)
        if args.agents_cmd == "enable":
            md = assets / ".claude/agents" / f"{name}.md"
            toml = assets / ".codex/agents" / f"{name.replace('-', '_')}.toml"
            if not md.exists():
                print(f"No agent definition found for '{name}'. Run 'ratchery agents-status' to see available on-demand agents."); raise SystemExit(1)
            copy_if_missing(md, path / ".claude/agents" / md.name)
            if toml.exists(): copy_if_missing(toml, path / ".codex/agents" / toml.name)
            print(f"Enabled '{name}' for this project.")
        elif args.agents_cmd == "disable":
            p = inspect_project(path)
            tier_state = load_json(path / ".agents/state/tier.json", {})
            active = active_agent_names(p, tier_state)
            if name in active:
                print(
                    f"Refusing to disable active agent '{name}': {active[name]}. "
                    "Change the tier/capability facts first, then inspect agents-status."
                )
                raise SystemExit(1)
            removed = False
            for target in [path / ".claude/agents" / f"{name}.md", path / ".codex/agents" / f"{name.replace('-', '_')}.toml"]:
                if target.exists(): target.unlink(); removed = True
            print(f"Disabled '{name}'." if removed else f"'{name}' was not installed.")
    elif args.cmd == "mcp":
        path = git_root(Path(args.path).resolve())
        if args.mcp_cmd == "enable":
            mcp_enable(path, args.name)
            print(
                f"Enabled MCP server '{args.name}' for Claude Code and Codex. "
                "Review .mcp.json and .codex/config.toml before the next session."
            )
        elif args.mcp_cmd == "disable":
            removed = mcp_disable(path, args.name)
            print(f"Removed MCP server '{args.name}'." if removed else f"'{args.name}' was not enabled.")
        elif args.mcp_cmd == "status":
            for server, clients in mcp_status(path).items():
                claude = "enabled" if clients["claude"] else "not enabled"
                codex = "enabled" if clients["codex"] else "not enabled"
                print(f"{server}: Claude {claude}; Codex {codex}")


if __name__ == "__main__":
    main()
