# Project Context

## Purpose

Ratchetry is an opinionated, batteries-included operating layer for AI-assisted
software development. It turns a normal repository into a well-configured
Claude Code and OpenAI Codex workspace with safe permissions, curated agents
and Skills, reusable project templates, diagnostics, and cost-aware tool
routing. Durable memory is a first-class optional workflow rather than an
installation prerequisite.

The product deliberately ships more capability than it activates. A small
project receives a small working set; specialized agents, process, external
tools, and broad context are introduced only when project facts or the current
task justify their token, security, dependency, and maintenance cost.

The product name is Ratchetry and the primary CLI command is `ratchery`. The
first public release is staged in a separate clean-history repository; the
pre-rebrand `agent-workspace` command and internal ownership markers remain
only where required for a bounded 1.x upgrade path.

## Problem

Building a good coding-agent environment currently requires users to research
and reconcile many independent concerns:

- how Claude Code and Codex should share repository instructions;
- which permissions and sandbox settings actually protect local credentials;
- which agents, Skills, hooks, and templates are worth maintaining;
- how to preserve decisions and project state across sessions;
- when code graphs, MCP servers, semantic search, or output compression save
  more context than they consume;
- how to refresh generated configuration without destroying human edits; and
- how much process is appropriate for a script versus a public or regulated
  product.

Ratchetry packages those decisions into one inspectable, reversible setup.

## Product promise

> Maximum useful capability, minimum justified cost.

The setup should feel complete on day one without making every capability an
always-on tax. "Available" never means "loaded in every session."

### Principles

1. **Safe by default.** Network, credentials, destructive operations, and
   untrusted content receive explicit boundaries. The OS/CLI sandbox is the
   primary boundary; deterministic hooks are defense in depth.
2. **Cheapest sufficient tool first.** Native search and code intelligence
   precede semantic indexes, graphs, MCP calls, subagents, and external tools.
3. **Progressive disclosure.** Instructions, Skills, agents, and repository
   context are loaded only when their trigger or scope is relevant.
4. **Proportional rigor.** The Adaptive Engine selects a T0-T3 policy from the
   codebase profile and explicit human-owned risk facts. The risk ratchet
   prevents an unreviewed silent downgrade.
5. **Durable, provider-neutral memory.** Repository evidence remains
   authoritative. Obsidian stores concise decisions, reusable fixes, project
   state, session summaries, and one bounded cross-agent handoff—not raw
   prompts, transcripts, source dumps, or secrets.
6. **Human ownership survives automation.** Managed blocks, owned hook groups,
   atomic writes, backups, dry runs, and rollback preserve user configuration.
7. **Evidence over fashion.** An integration must solve a measured problem and
   justify its token, permission, supply-chain, and maintenance footprint.
8. **Transparent core.** The CLI remains Python-stdlib-only and its policy is
   represented in reviewable files and deterministic code.

## Product model

### Core operating layer

- global and per-repository Claude Code/Codex contracts;
- fail-closed sandbox and credential/environment protections;
- four baseline read/review/test/security agents;
- progressive-disclosure Skills and context rules;
- managed configuration, backups, refresh, diagnostics, and rollback;
- optional project-to-Vault identity, explicit `workspace-resume`/`workspace-save`,
  and a machine-readable provider-neutral handoff when memory is configured.

### Adaptive control plane

- project size and capability profiling;
- explicit risk facts plus deterministic T0-T3 classification;
- one-way risk ratchet with logged downgrade acknowledgement;
- tier/capability-based agent, Skill, documentation, test, and review policy;
- task-to-tool routing that prefers the lowest-cost sufficient mechanism.

The control plane serves the setup. It is a differentiating mechanism, not the
whole product identity.

### Optional capabilities

Obsidian is the flagship durable-memory experience. The core project workflow
should remain understandable when Vault features are not in use. QMD, Serena,
Context7, Graphify, RTK, Gitleaks, ccusage, Sentrux, and similar tools are
optional integrations, never mandatory startup dependencies. Some are only
researched or routed to; inclusion in documentation is not an endorsement or
an instruction to install them.

### Evidence loop

- cost changes are evaluated with aggregate ccusage snapshots, task-success
  counts, a digest-bound public task suite, repeated-sample reports, and cost
  per successful task;
- daily/session budget checks are local post-usage estimates that persist
  nothing and block only when a caller explicitly requests enforcement;
- external optimizers start as profile/on-demand/experimental, never universal
  always-on dependencies;
- scanner profiles optimize risk at explicit boundaries instead of flooding
  every agent call with duplicate work/output;
- prompts, raw sessions, source code, and session identifiers are outside the
  benchmark persistence boundary.

## Primary users

- Individual developers who use Claude Code, Codex, or both across multiple
  repositories and want continuity without repeatedly rebuilding context.
- Small teams that want a shared, reviewable agent contract without adopting a
  heavyweight orchestration platform.
- Maintainers of sensitive or public projects who need safer defaults and a
  visible explanation of why additional rigor was activated.
- Advanced users who want an excellent default setup but retain ownership of
  their existing files, hooks, tools, and workflow.

## Core user journeys

1. Install the core with an explicit projects path and preview changes; add a Vault only
   when durable memory is wanted.
2. Run `ratchery init` in a new or existing repository.
3. Record real project risk facts and review the resulting tier policy.
4. Work with a minimal context contract and invoke specialized capabilities
   only when their trigger applies.
5. When optional memory is enabled, resume from curated project memory, exchange a bounded
   handoff when another agent client continues the work, and explicitly save outcomes.
6. Run `doctor`, `refresh`, and rollback without losing human configuration.
7. Inspect local cost, receive optional budget/spike warnings, and benchmark an
   optimizer before deciding whether it earns activation.

## Non-goals

- Hosting models or replacing Claude Code, Codex, Git, CI, or the editor.
- Maximizing the number of agents, Skills, MCP servers, or generated files.
- Acting as a general multi-agent orchestration runtime.
- Reimplementing Spec Kit, OpenSpec, BMAD, or an architecture-analysis engine.
- Claiming that configuration files alone prove compliance or that every code
  change satisfied a tier's human review/testing requirements.
- Automatically installing third-party tools or sending repository/Vault
  content to external services.
- Persisting raw conversations as project memory.

## Architecture

`lib/agent_workspace.py` owns the CLI, installation, managed configuration,
project/Vault lifecycle, and diagnostics. `lib/adaptive_engine.py` owns tiering
and the ratchet. `lib/context_engine.py` owns bounded context and steering
generation. `lib/tool_router.py` owns deterministic tool recommendations.
`lib/efficiency.py` owns aggregate usage validation, benchmark evidence, and
budget evaluation.
`lib/memory_engine.py` owns the bounded provider-neutral handoff schema and
rendering; the CLI owns Vault identity, safe storage, and backup operations.
`lib/hook_runtime.py` is deployed into projects as the secondary local guard.
Assets under `assets/` are the shipped global, project, and Vault templates.

See `docs/ARCHITECTURE.md` for implementation details and trust boundaries.

## Constraints

- Compatibility: Python 3.11+; current security policy requires Claude Code
  2.1.187+ and Codex CLI 0.138.0+ when those clients are installed.
- Security: least privilege, fail closed where enforcement is promised, never
  expose credentials, and treat repository/fetched instructions as untrusted.
- Cost: no external runtime dependency in the core CLI; optional tools must
  remain lazy and have a native/raw fallback.
- Data: repository code/config is authoritative; durable memory is concise,
  curated, and secret-free.
- Operations: changes must be reversible, diagnostics must be read-only, and
  refresh must preserve user-owned content.

## Success criteria

- A first-time user can install and initialize a real repository without
  manually assembling agent instructions, security config, or memory folders.
- The default session context stays small and optional tool definitions do not
  load without an applicable trigger or explicit opt-in.
- Security diagnostics fail on removed enforcement bindings, not only malformed
  files, and never claim guarantees unsupported by the installed CLI version.
- Re-running setup produces no unexplained semantic churn and preserves human
  edits.
- Each shipped component has a documented trigger, test or validation path,
  and a reason its benefit exceeds its ongoing cost.

## Sources of truth

- Current behavior: `lib/`, `assets/`, `tests/`, `install.sh`, and `action.yml`.
- Product scope and principles: this document.
- Public onboarding and promises: `README.md` and `docs/USER-GUIDE.md`.
- Architecture and threat boundaries: `docs/ARCHITECTURE.md` and
  `docs/10-SECURITY.md`.
- Tier policy: `lib/adaptive_engine.py` and `.agents/state/risk-answers.json`.
- Meaningful changes: `CHANGELOG.md`; active implementation work:
  `docs/work/` and `docs/specs/`.
