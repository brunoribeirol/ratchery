# Optional Tools

## Routing order

Use the smallest capability that can answer reliably:

1. Native file search.
2. Native code intelligence/LSP.
3. `structural-search` / ast-grep when syntax awareness helps.
4. Context7 when current third-party docs are required.
5. Serena when symbolic navigation materially improves over native capabilities.
6. Graphify for broad architecture/impact questions in genuinely large repositories.
7. QMD for curated external Vault knowledge.
8. One measured output optimizer for known verbose workloads, with a raw fallback.

Gitleaks is for explicit security/release scans. ccusage is optional observability. No optional tool is required for core operation.

`ratchery tools-status` discovers command paths and prints each catalog
entry's activation family and network posture without executing optional
binaries. Add `--probe` only when you explicitly want version and QMD security
probes to run. `ratchery tools-recommend --path .` prints read-only,
advisory routing candidates; it neither changes project state nor authorizes an
installation. Add its `--probe` only when QMD's installed/configured state must
participate in the recommendation.

## Activation matrix

| Family | Default candidate | Mode | Rule |
|---|---|---|---|
| Cost observability | ccusage | profile | Local measurement; not a runtime dependency |
| Shell/tool output | RTK / Context Mode | experimental | Benchmark separately before broad activation |
| Code retrieval | native search, then Serena | profile | One primary retrieval engine; symbol search only when it wins |
| Document retrieval | lexical fallback, then QMD | profile | Snippets before full files; isolated local index |
| Architecture discovery | Graphify | on-demand | Broad/large repository questions only |
| External library docs | Context7 | on-demand | Network only when current upstream docs are needed |
| Secret/security scan | Gitleaks / Trivy / Semgrep / Checkov | profile / on-demand | Choose by risk/capability; Checkov follows a demonstrated IaC coverage gap, never every tool call |
| Supply chain | existing SPDX builder, OSV/Syft/Grype | on-demand | Add only for incremental findings or required artifact formats |
| MCP security | native sandbox first, Agent Scan/gateway later | on-demand | Review external data flow, credentials, and command execution |
| Outer agent isolation | native client sandbox, then ai-jail | experimental | Platform-specific defense in depth; never a hostile-code VM substitute |
| Team/multi-machine memory | curated Vault, or ai-memory | experimental | One memory backend at a time; review capture/privacy/context cost first |

The exact catalog is `tools.lock.json`. It has no external `always` entry.

## Graphify

Known current release when this baseline was cut: **0.9.47**. Keep it global/on-demand. Do not build a graph for every repository and do not install watch/commit hooks automatically. For large repositories and broad architecture questions, prefer a fresh existing graph when it reduces file reads.

## QMD isolation and version gate

Ratchetry uses the dedicated named QMD index `ratchery-vault` and collection `vault`. Setup/reindex are explicit and commands run from `$HOME`, never from an arbitrary repository.

QMD **2.6.3 and older are blocked** by the integration because project-local `.qmd/index.yml` trust issues were reported. Ratchetry does not auto-install QMD. Install a verified stable release newer than 2.6.3 only after reviewing its release notes, then use `vault-qmd-setup`. See `18-QMD-SECURITY.md`.

## RTK

RTK is experimental until your own workload shows lower cost per successful
task. `ratchery tools-install rtk` prints a pinned, reviewable install
template and separate dry-run/apply commands. The template deliberately requires
the full release commit SHA: `--locked` fixes Cargo dependencies but a Git tag
alone is mutable. Verify the signed release and replace the placeholder before
running it.

- Claude Code: `rtk init -g --dry-run -v`, then `rtk init -g`;
- Codex: `rtk init -g --codex --dry-run -v`, then `rtk init -g --codex`.

They are different integrations: Claude receives a `PreToolUse` rewrite hook;
Codex receives `AGENTS.md`/`RTK.md` instructions. Keep telemetry disabled for
Ratchetry's baseline. Verify raw failure-output recovery before relying on
compressed output.

## ccusage and local evidence

Current ccusage can aggregate multiple coding-agent sources locally; older
installed releases may still be Claude-only. Ratchetry never hides a source
failure. Use `ratchery usage --offline` to inspect reports and
`ratchery budget check` for no-state threshold warnings, and
`ratchery benchmark suites/capture/compare/report` for versioned,
repeated aggregate-only evidence. A report never makes an automatic adoption
decision.
The full protocol and privacy boundary are in `BENCHMARKING.md`.

## Security scanners

Gitleaks is the small explicit secret-scan starting point. For container, IaC,
or broader release scanning, prefer evaluating Trivy before stacking separate
scanners. Add Semgrep for code-bearing T2/T3 projects and Checkov only for an
IaC profile. OSV-Scanner, Syft, and Grype are on-demand when they add evidence
or formats that the existing scanner/release SBOM does not provide.

These tools optimize security risk, not token counts. Compare false positives,
incremental findings, database/network cost, and latency. Never place suspected
secret values from scanner output into an agent response or Vault note.

## Why Context Mode and Agent Scan are not core

Context Mode adds an MCP process, tool schemas, hooks, storage, and broader
tool-output interception. It may help tool-heavy workloads, but that overhead
and overlap with RTK require an A/B trial. Agent Scan may help an MCP-heavy
profile, but its current service/token/data-flow and command-execution boundary
conflicts with a universal local-first default. Both stay optional and are never
auto-installed.

## ai-jail: optional outer isolation

`ai-jail` can add a private home and OS-level filesystem/process restrictions
around an agent. Keep it experimental and manual: Linux has the strongest
backend; macOS relies on Apple's deprecated `sandbox-exec`, and native Windows
is not supported. Enabling network grants unrestricted network to everything in
the jail; mounting agent state exposes those credentials to every sandboxed
process; Docker access is effectively host-root. It therefore complements but
never replaces the clients' native sandbox/permission policy. Use a disposable
VM for genuinely hostile code. Ratchetry does not install, configure, or launch
it, and any evaluation must cover failed startup, escape-sensitive paths, and
normal workflow overhead on the target platform.

## ai-memory: optional team memory backend

`ai-memory` is a credible experiment when a real team needs automatic
cross-agent, cross-machine handoffs and an auditable shared Markdown-backed
memory service. It is not additive to the built-in provider-neutral Vault
handoff: choose one primary memory backend for a trial. Its daemon, SQLite
index, hooks, MCP surface, authentication, and capture of sanitized prompts/tool
calls plus raw managed-workstream segments add privacy, context, operations,
and supply-chain cost. Start loopback-only with LLM/embedding providers
disabled; use repository allowlist mode, disable Claude prompt/assistant capture
for the baseline, and define retention/exclusion rules before capture. Then
compare retrieval quality, injected tokens, latency, and cost against the
curated `workspace-save`/`workspace-resume` path. `ratchery memory plan
ai-memory` reports this baseline without executing the binary; Ratchetry does not
install, start, route, or configure it.
