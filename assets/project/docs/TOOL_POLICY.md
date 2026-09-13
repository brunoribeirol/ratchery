# Tool Policy

## Routing principle
Use the smallest capability that can answer the question reliably:

1. repository instructions and manifests;
2. native file search;
3. native code intelligence/LSP;
4. structural search (`ast-grep`) when syntax matters;
5. external documentation (Context7) when current library behavior is required;
6. symbolic navigation (Serena) when native intelligence is insufficient;
7. architecture graph (Graphify) only for broad, large-repository questions;
8. Vault retrieval (QMD) only for curated external memory.

Do not activate tools simply because they are installed.

## Activation modes

- `profile` — recommend only when detected project/tier facts justify it;
- `on-demand` — invoke for one bounded task, then leave it out of normal sessions;
- `experimental` — require a local A/B benchmark before broad use;
- `disabled` — known but not eligible for recommendation.

These modes, command probes, network posture, and benchmark requirements are
machine-readable in the Ratchetry distribution's `tools.lock.json`. No optional external tool is `always`:
the always-present security core is the clients' native sandbox/permissions plus
Ratchetry's deterministic secondary hook.

## Context7
Use only to verify current third-party library/framework documentation. Do not use it for local-code discovery.

## Serena
Use for symbol definitions, references, callers, and cross-file refactors only when configured and it materially improves over native code intelligence.

## Graphify
Use only for broad architecture questions in large repositories. Generate lazily, reuse a fresh graph, keep generated caches out of Git, and never enable a global watch/commit hook automatically.

## QMD
Use only for semantic retrieval from the configured Obsidian Vault. QMD indexing is explicit opt-in. Ratchetry blocks QMD <=2.6.3 and unknown versions for mutating/search integration because project-local `.qmd` trust issues were reported in 2.6.3. Use only the dedicated `ratchery-vault` index, run QMD from outside arbitrary repositories, read snippets first, and open full notes only when needed.

## ast-grep
Use for syntax-aware search/refactor discovery when text search is ambiguous. Search first; do not perform repository-wide rewrites without review.

## Gitleaks
Use for explicit security/release scans. Do not run on every edit and never echo discovered secret values into reports or Vault notes.

## Security profiles
Start with one scanner that matches the risk. Trivy is the consolidated candidate
for container/IaC/repository release scans; Semgrep belongs in code-bearing T2/T3
SAST; Checkov is on-demand only in an IaC profile after a demonstrated Trivy
coverage gap. OSV-Scanner, Syft, and Grype are
on-demand when they add findings or formats beyond the primary scanner. None is
installed automatically, and scan output containing a suspected secret must be
redacted before entering an issue, agent response, or Vault note.

## RTK
Experimental until measured locally. Preview Claude and Codex integration
separately: Claude uses a `PreToolUse` hook; Codex uses instruction files. Keep
telemetry disabled for the baseline. If compression hides evidence or a command
behaves unexpectedly, inspect RTK's saved raw failure output or repeat the raw
command.

## Context Mode
Experimental alternative/companion for tool-heavy output, not a universal core.
Its MCP schemas, hooks, process, and broader interception add context and trust
surface, so benchmark it against RTK and raw tools before combining them.

## ai-jail
Experimental outer isolation only. It may wrap an agent on a specifically tested
platform, but it never replaces native Claude/Codex sandboxing and is not a hostile-code
VM boundary. Do not enable network, agent-state mounts, inherited environment, Docker,
host IPC, or broad path maps implicitly; measure failed-start and workflow overhead.

## ai-memory
Experimental one-of automatic alternative to the built-in provider-neutral
Vault handoff, only for a demonstrated team/multi-machine need. Review hook
capture, raw sanitized segments, retention, authentication, recovery, MCP
exposure, and injected context before a loopback/zero-LLM trial. Use
`ratchery memory plan ai-memory` for the non-mutating baseline; presence
on `PATH` does not enable it. Do not run it alongside the default memory path
merely to accumulate capabilities.

## ccusage
Optional local observability only. Use `ratchery usage --offline` and the
aggregate `ratchery benchmark suites/capture/compare/report` workflow;
use `ratchery budget check` only as a read-only estimated threshold, not
a billing boundary. Cost is estimated, and a vendor's claimed savings are never
Ratchetry evidence.

## MCP security
MCP servers inherit the sandbox/least-privilege policy and remain explicit,
static opt-ins. Agent Scan or a container gateway may be useful in an MCP-heavy
profile, but neither is local-first core: review what metadata/content leaves the
machine, credentials required, commands executed, and tool-definition changes
before adoption.

## External tool installation
Hooks never install or update tools. Use `ratchery tools-status` to see
activation/network policy and discover command paths without executing optional
binaries. Use `--probe` only for an explicit version/QMD check. Use
`tools-recommend` to see what may help, then review and install explicitly.
Prefer native/CLI capabilities over a permanent MCP when both solve the same
task.
