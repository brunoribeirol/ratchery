# Roadmap

This roadmap reflects what's actually shipped, what's actively under
consideration, and what's still speculative. Nothing in "Next" or
"Later / exploratory" is a commitment or a timeline — treat those sections as
"under consideration," not "coming soon."

## Current stable line (v1.1.0)

The capabilities below are implemented. Stable publication still requires the
exact release commit's protected CI, CodeQL, client canary, signed tag,
artifacts, checksums, SBOM, and attestations to pass; this heading does not
replace those gates.

- **Adaptive Engine (T0-T3)** — deterministic risk tiering
  (`lib/adaptive_engine.py`) with per-tier requirements (spec mode, required
  docs, required agents/skills, testing bar, security bar) and a risk
  ratchet that does not silently downgrade a project's recorded tier.
- **Context Engine** — `.claudeignore`-based context pruning plus steering
  files, so large repositories don't get pushed wholesale into the model
  context.
- **Tool Router** — deliberate, conservative routing to optional external
  tools (Serena, Context7, ast-grep, Graphify, RTK, ccusage) based on task
  shape, not automatic adoption.
- **Cost/quality evidence loop** — `usage` exposes validated ccusage source,
  period, date/project/session, JSON, and offline selection; `benchmark
  capture/compare/report` stores aggregate-only snapshots, binds the bundled
  six-task protocol to its digest, requires repeated samples for a report, and
  reports tokens, estimated cost, success rate, and cost per successful task
  without making an adoption decision. Snapshot schema v2 automatically binds
  repeated samples to a bounded configuration digest and rejects drift inside
  either arm without confusing intended baseline/candidate differences.
- **Read-only budget warnings** — `budget check` evaluates offline ccusage
  aggregates against daily/session cost, token, and spike thresholds, stores
  nothing, and returns a policy failure only with explicit `--enforce`.
- **Provider-neutral memory handoff** — `memory handoff write/show/clear`
  exchanges one bounded, revision-aware baton through the exact UUID-matched
  Vault project. It is explicit, outside the repository/QMD index, rejects
  secret-like or unsafe input, and never launches or captures an agent session.
  `memory backends/status/doctor/plan` keeps the built-in Vault path distinct
  from experimental automatic services.
- **Versioned optional-tool policy** — `tools.lock.json` classifies tools by
  family, `profile`/`on-demand`/`experimental` activation, command probe,
  network posture, and benchmark requirement. No external tool is `always`.
- **Expanded agent/skill roster** — four compatibility-baseline agents (`explorer`,
  `reviewer`, `security-reviewer`, `test-runner`), `developer` from the T0 floor, and
  additional tier/capability/on-demand agents, plus 15 globally available,
  progressive-disclosure Skills, including
  (`workspace-save`, `workspace-resume`, `work-plan`, `focused-review`,
  `record-decision`, `record-bug`, `search-vault`, `repo-investigate`,
  `architecture-map`, `structural-search`, `security-scan`,
  `dependency-audit`) mirrored for both Claude Code and Codex CLI.
- **Two-layer security model** — native sandbox/permission deny-lists as the
  primary boundary, plus a deterministic `PreToolUse` regex hook
  (`lib/hook_runtime.py`) as a secondary guard. See `SECURITY.md`.
- **QMD hardening** — QMD is optional, version-gated (`<=2.6.3` blocked),
  isolated to a dedicated Vault index, and never auto-installed.
- **Registry-driven agent activation** — `assets/global/skills/registry.json`
  is now actually consumed (`adaptive_engine.resolve_active_agents`,
  `agent_workspace.install_agents`): only the 4 baseline agents plus
  tier-gated/capability-matched agents are installed per project; the
  remaining specialized/optimization/operations agents are on-demand only
  (`ratchery agents enable/disable <name>`,
  `ratchery agents-status`). This closes the gap where all 24 agents
  used to ship to every project regardless of tier.
- **Real Serena / Context7 optional MCP profile wiring** — `ratchery
  mcp enable/disable/status <serena|context7>` writes/removes reviewable,
  repository-shared Claude and Codex definitions, one integration at a time,
  never automatically. Managed profiles use immutable source pinning where
  executable code is fetched, narrow tool allowlists, prompt approval, and
  bounded output/timeouts where the client supports them.
- **Credential-free client canary** — a weekly/manual workflow verifies the
  generated policy against minimum-supported and current Claude/Codex clients
  without credentials, inference, or normal pull-request cost.
- **RTK experimental install step** — `ratchery tools-install rtk`
  prints (never runs) a pinned install command and separate Claude/Codex
  dry-run/apply instructions. Promotion requires a local benchmark and raw
  failure-output fallback.
- **OpenSpec-light / Spec-Kit-full spec-driven modes** — the
  `spec-driven-change` Skill reads `.agents/state/tier.json`'s
  `requirements.spec_mode` and walks the matching template
  (`docs/specs/DELTA_SPEC_TEMPLATE.md` for T1/T2,
  `docs/specs/FULL_SPEC_TEMPLATE.md` for T3's full phase-gated flow).
- **Portable local gates** — `make test` runs compile, Ruff, integration,
  unit, manifest, Action-pin, and documentation-link checks; Linux CI adds
  blocking ShellCheck and the separate CodeQL workflow provides Python SAST.
- **Exact release-artifact smoke gate** — the tag workflow and
  `make release-smoke` safely extract, install, initialize, and diagnose the
  actual manifest-backed tarball in an isolated environment before publication.

## Next (candidates, not scheduled)

These are directions the project is actively considering, not things you
should expect in the next release without further evaluation:

- **CoSAI CodeGuard rule sync** — `tier_requirements()` for T3 mentions
  CodeGuard rules "if installed" as part of the T3 security bar; there is no
  sync/installation mechanism for those rules yet (the `security-rules-check`
  Skill is a native reimplementation of the Core Rules concept, not a sync
  against the upstream ruleset).
- **`doctor` auto-removal of orphaned agents** — `agents-status` already
  detects agent files that are installed but no longer implied by the
  current tier/capabilities; it only reports them today, on purpose (the
  framework never deletes without an explicit action). A guided
  `ratchery agents prune` could offer to remove them one at a time.
- **Scoped tier overrides for monorepos** — the current tier is intentionally
  repository-wide. A repo containing both a low-risk site and a regulated
  service must choose between over-applying T3 and under-protecting a package.
  Explore audited package floors that can only raise (never lower) the root
  tier, without weakening the global ratchet.
- **Provider-side/pre-spend budget controls** — the shipped local check observes
  estimates after usage. Consider stronger provider-side integration only if it
  can be accurate across clients without exposing prompts, adding a daemon, or
  pretending a local hook is an authoritative billing boundary.

## After stable release

- **Homebrew tap** — `ratchery setup` now separates package-manager runtime
  installation from user-specific Vault onboarding. Create the tap only after
  stable `v1.1.0` exists, then require its exact release URL/checksum plus
  macOS/Linux Formula audit and isolated setup/doctor tests. See
  `docs/PUBLISHING.md`.

## Later / exploratory

Flagged in project research as immature for default-on inclusion — not
because the tools are judged bad, but because their adoption/popularity
signals are not independently verifiable yet, and this project deliberately
does not treat popularity as a trust signal (see the Untrusted content /
tool-routing policy in `assets/project/AGENTS.block.md`):

- **Graphify** — already usable as an opt-in, already-installed capability
  for broad architecture/impact questions in large repositories (see
  `docs/09-TOOLS.md`'s "Graphify" section). Before any move toward
  default-on or bundled installation, it needs independent trust
  verification beyond release notes and reported adoption numbers.
- **Caveman** — noted in research as a candidate in the same category as
  Graphify. No integration exists in this codebase today. Any future
  integration would need the same independent trust verification before
  being considered for default-on inclusion, and would go through the
  Tool Router decision-matrix pattern described in `CONTRIBUTING.md`.
- **Context Mode** — tool-output interception may help log/API-heavy work, but
  its MCP schemas, hooks, process/storage, overlap with RTK, and broader trust
  surface keep it experimental until local A/B evidence exists.
- **Agent Scan / MCP gateway** — consider only for MCP-heavy profiles after a
  current data-flow, credential, network, command-execution, and false-positive
  review. Neither fits the universal local-first core.
- **Sentrux** — complementary architecture regression sensor (`check`, saved
  baseline, post-session `gate`), not a substitute for project risk tiering.
  Consider only an optional Tool Router/CI adapter after a stable pinned
  release and a local false-positive/latency benchmark; never auto-install it.
- **ai-jail** — experimental outer sandbox for a specifically tested platform,
  not a replacement for native client isolation or a disposable hostile-code
  VM. Network, agent-state, environment, Docker, IPC, and platform limitations
  must remain explicit in any trial.
- **ai-memory automatic backend** — the provider-neutral handoff removes client
  lock-in without automatic capture. Consider ai-memory only for a demonstrated
  team/multi-machine need, comparing it against curated Vault memory with
  zero-LLM/loopback defaults and explicit capture, retention, authentication,
  context, recovery, and operations evidence before activation.
- **specs.md and similar adaptive SDD entrants** — track as competitive/design
  evidence. They make “adaptive rigor” a category rather than an exclusive
  claim, but do not currently replace Ratchetry's persistent risk ratchet,
  dual-client configuration lifecycle, and memory layer.

No timeline is implied for anything in this section. If you want to help
move an item from "Later" to "Next," the first useful contribution is
usually the trust/maturity evaluation itself, not code.
