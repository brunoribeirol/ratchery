#!/usr/bin/env python3
"""Tool Router: pick the cheapest tool that actually answers the question.

This is a pure, testable decision table -- no subprocess calls, no I/O
beyond what the caller passes in. It exists so "which tool for this job" is
an explicit, reviewable, unit-tested rule set instead of prose scattered
across docs, and so `ratchery tools-recommend` and the generated
AGENTS.md guidance stay derived from the same source rather than drifting
apart.

Design rule from the brief: never force a heavyweight tool (a knowledge
graph, a semantic index, a subagent) onto a job a plain search already
solves. `route()` always ranks the cheapest applicable tool first.
"""
from __future__ import annotations

from typing import Any

TASK_KINDS = (
    "locate_string",        # find a known string/filename/symbol name
    "navigate_symbols",     # go-to-definition, find-references, rename
    "understand_architecture",  # broad "how does X relate to Y" over a large repo
    "third_party_docs",     # current API/library documentation
    "verbose_output",       # compress noisy command output (build/test/docker logs)
    "security_scan",        # explicit secret/dependency/config security review
    "vault_retrieval",      # search Obsidian Vault notes/decisions/session logs
    "orient_large_repo",    # first pass in an unfamiliar large codebase
)


def route(task_kind: str, profile_data: dict[str, Any] | None = None, installed: dict[str, bool] | None = None) -> list[dict[str, str]]:
    """Return an ordered list of {tool, rationale} recommendations for one
    task kind, cheapest/most-applicable first. `installed` (tool name ->
    bool) lets the caller down-rank tools that aren't actually available;
    unknown/omitted tools are assumed not installed (never assume presence)."""
    profile_data = profile_data or {}
    installed = installed or {}
    size = profile_data.get("size", "small")

    def available(name: str) -> bool:
        return bool(installed.get(name))

    if task_kind == "locate_string":
        return [
            {"tool": "ripgrep/grep/git grep", "rationale": "A known string or filename is always answerable by plain search. Never escalate to a graph/semantic tool for this."},
        ]

    if task_kind == "navigate_symbols":
        out = [{"tool": "native code intelligence (editor/LSP already in Claude Code/Codex)", "rationale": "Try native go-to-definition/find-references first; no extra tool needed for most repos."}]
        if available("serena"):
            out.append({"tool": "Serena", "rationale": "Symbol-level navigation/rename across a large or unfamiliar codebase, when native capability is insufficient."})
        return out

    if task_kind == "understand_architecture":
        out = [
            {"tool": "architecture-map skill / manual read of docs + entry points", "rationale": "Default local-first path; sufficient for small/medium repos and often for a bounded large-repo question."}
        ]
        if size == "large" and available("graphify"):
            out.append({"tool": "Graphify", "rationale": "On-demand candidate only after the bounded local pass is insufficient; reuse an existing graph and benchmark its output quality."})
        return out

    if task_kind == "third_party_docs":
        out = []
        if available("context7"):
            out.append({"tool": "Context7", "rationale": "Fetches current, version-pinned library/API docs -- avoids hallucinated signatures from stale training data."})
        out.append({"tool": "vendored docs / official website", "rationale": "Fallback when Context7 isn't configured for this project."})
        return out

    if task_kind == "verbose_output":
        out = [
            {"tool": "raw command + targeted flags/manual truncation", "rationale": "Default path: no third-party execution or hidden filtering; often sufficient for short output."}
        ]
        if available("rtk"):
            out.append({"tool": "RTK", "rationale": "Experimental candidate for known-verbose output only after a local A/B; always retain the raw-command fallback."})
        return out

    if task_kind == "security_scan":
        out = [{"tool": "security-scan skill", "rationale": "Framework-native explicit review: secrets, config, deps, auth, dangerous paths."}]
        if available("gitleaks"):
            out.append({"tool": "gitleaks", "rationale": "Dedicated secret-scan pass, e.g. before a release."})
        return out

    if task_kind == "vault_retrieval":
        out = [
            {"tool": "lexical Vault fallback", "rationale": "Default zero-dependency retrieval; consume a bounded snippet before adding an index."}
        ]
        if available("qmd"):
            out.append({"tool": "QMD (via search-vault skill)", "rationale": "Profile candidate only when security-probed/configured and local evidence justifies the index cost."})
        return out

    if task_kind == "orient_large_repo":
        return [
            {"tool": "bounded read-only explore pass (locate by file/line reference, not full-file reads)", "rationale": "Cheapest way to orient in an unfamiliar large repo before deciding whether Graphify/Serena are actually warranted."},
        ]

    return [{"tool": "native search/read", "rationale": f"Unrecognized task kind '{task_kind}'; default to the cheapest native capability."}]


def recommend_for_profile(profile_data: dict[str, Any], installed: dict[str, bool]) -> dict[str, list[dict[str, str]]]:
    """Convenience wrapper used by `ratchery tools-recommend`: route
    every task kind at once for a given project profile."""
    return {kind: route(kind, profile_data, installed) for kind in TASK_KINDS}
