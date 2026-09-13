#!/usr/bin/env python3
"""Context Intelligence Engine: decide what an agent should load, not "read everything".

Two concrete artifacts, both generated deterministically from profile()
output, but with different refresh contracts -- see each one's own docstring
below for exactly which:

  1. `.claudeignore` -- keeps build output, dependency trees, and vendored
     code out of Claude Code's own context by default. Regenerated on every
     init/refresh (preserving any human-added tail, see
     `generate_claudeignore()`). This closes the real regression the audit
     found versus the internal baseline (which had a directory-walk IGNORE
     set for the *profiler*, but never generated a `.claudeignore` a coding
     agent itself would read).

  2. Steering files (`.agents/steering/product.md`, `structure.md`,
     `tech.md`) -- topic-scoped, individually small context files an agent
     loads selectively instead of one growing monolithic doc. Written once,
     on first `init`, and never touched again by `refresh` (see
     `generate_steering_files()`) because they become human-owned. Volatile
     counts are deliberately not copied into these files; current generated
     facts live in `.agents/state/project-profile.md`. The pattern is
     reimplemented natively from Kiro's public "steering files" UX
     (https://kiro.dev -- proprietary product, pattern only, no code
     borrowed) because it demonstrably beats a single large context dump at
     zero dependency cost. AGENTS.md/CLAUDE.md `@import` these by reference
     rather than inlining their content, so an agent that doesn't need
     `tech.md` this turn never pays to load it.

This module does not itself intercept or filter what Claude Code/Codex read
at runtime -- neither CLI exposes a hook for that. It produces the artifacts
those tools already know how to consume (`.claudeignore`, imported markdown
files) so the "read only what's necessary" decision is made once, on disk,
rather than re-derived by the agent every session.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Baseline ignore patterns. Kept separate from agent_workspace.py's IGNORE
# set (which drives the profiler's directory walk and must stay a plain
# `set[str]` of directory names) because `.claudeignore` is gitignore-style
# glob syntax read by a different consumer (the coding agent itself).
_BASE_PATTERNS = [
    "# Managed by Ratchetry (ratchery CLI) -- edit CUSTOM section below, not above it.",
    "node_modules/", "vendor/", ".venv/", "venv/", "env/",
    "dist/", "build/", "target/", "coverage/", ".next/", ".nuxt/",
    ".cache/", ".turbo/", "__pycache__/", "*.pyc", "graphify-out/",
    ".git/", ".hg/", ".svn/",
    "*.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock",
    "# Secrets and credentials: never let these enter agent context, even by accident.",
    ".env", ".env.*", "!.env.example", "!.env.sample", "!.env.template",
    "*.pem", "*.key", ".aws/credentials", ".ssh/",
]

_MARKER_START = "# --- ratchery: managed baseline (do not edit above) ---"
_MARKER_END = "# --- end managed baseline; add project-specific entries below ---"


def claudeignore_path(project_root: Path) -> Path:
    return project_root / ".claudeignore"


def render_claudeignore(existing_custom_tail: str = "") -> str:
    body = "\n".join([_MARKER_START, *_BASE_PATTERNS, _MARKER_END])
    tail = existing_custom_tail.strip("\n")
    return body + ("\n\n" + tail + "\n" if tail else "\n")


def _split_custom_tail(text: str) -> str:
    if _MARKER_END not in text:
        return ""
    return text.split(_MARKER_END, 1)[1]


def generate_claudeignore(project_root: Path) -> Path:
    """Create or refresh `.claudeignore`, preserving any human-added lines
    after the managed baseline marker (same managed-block discipline as the
    rest of the package -- never destroy content this framework didn't add)."""
    path = claudeignore_path(project_root)
    existing = path.read_text() if path.exists() else ""
    tail = _split_custom_tail(existing)
    path.write_text(render_claudeignore(tail))
    return path


def steering_dir(project_root: Path) -> Path:
    return project_root / ".agents/steering"


def render_product_md(profile_data: dict[str, Any], tier_state: dict[str, Any] | None) -> str:
    tier_line = ""
    if tier_state:
        tier_line = f"\n- Tier: **{tier_state.get('effective_tier', '?')}** ({tier_state.get('tier_name', '')})\n"
    return (
        "# Product\n\n"
        "What this project is for and who it serves. Fill in once; agents load this "
        "when reasoning about scope, priorities, or user impact -- not on every turn.\n"
        f"{tier_line}\n"
        "## Goal\n\n<one paragraph: what problem this solves and for whom>\n\n"
        "## Non-goals\n\n<what this project explicitly does not try to do>\n\n"
        "## Primary users\n\n<internal team / external customers / public -- see .agents/state/risk-answers.json>\n"
    )


def render_structure_md(profile_data: dict[str, Any]) -> str:
    packages = profile_data.get("package_roots") or []
    lines = ["# Structure", "", "Architecture and directory layout an agent should know before navigating.", ""]
    if profile_data.get("monorepo"):
        lines += ["## Monorepo packages", ""] + [f"- `{p}`" for p in packages] + [""]
    lines += [
        "## Layout notes",
        "",
        "<fill in: where does business logic live, where are tests, what's generated vs. hand-written>",
        "",
        "Current generated size/package facts: `.agents/state/project-profile.md`.",
    ]
    return "\n".join(lines) + "\n"


def render_tech_md(profile_data: dict[str, Any]) -> str:
    lines = ["# Tech", "", "Stack and tooling an agent should assume without re-deriving it every session.", ""]
    lines += [
        "## Project-specific stack",
        "",
        "<fill in only stable choices and constraints; do not copy volatile file counts here>",
        "",
        "Current generated language/capability facts: `.agents/state/project-profile.md`.",
        "",
        "## Commands",
        "",
        "See `docs/COMMANDS.md` (kept in sync automatically).",
    ]
    return "\n".join(lines) + "\n"


def generate_steering_files(project_root: Path, profile_data: dict[str, Any], tier_state: dict[str, Any] | None = None) -> list[Path]:
    """Create steering files only if absent -- these are meant to be hand-edited
    by a human once populated, so refresh must never clobber real content
    (same policy as docs/PROJECT_CONTEXT.md and friends)."""
    directory = steering_dir(project_root)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, renderer in [
        ("product.md", lambda: render_product_md(profile_data, tier_state)),
        ("structure.md", lambda: render_structure_md(profile_data)),
        ("tech.md", lambda: render_tech_md(profile_data)),
    ]:
        path = directory / name
        if not path.exists():
            path.write_text(renderer())
        written.append(path)
    return written


def steering_import_block() -> str:
    """The line set AGENTS.md/CLAUDE.md should carry to pull steering files in
    by reference. Import syntax, not inline content -- so an agent only pays
    the token cost for a steering file when it actually follows the import."""
    return (
        "## Steering (topic-scoped project context)\n\n"
        "@.agents/steering/product.md\n"
        "@.agents/steering/structure.md\n"
        "@.agents/steering/tech.md\n"
    )
