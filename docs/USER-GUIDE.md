# User Guide

Day-to-day usage of Ratchetry once it's installed (`INSTALLATION.md`). For
the full daily-workflow reference see `07-DAILY-WORKFLOW.md`; this document focuses on
tiering, cost measurement, optional capabilities, and—when configured—the Vault workflow
with concrete commands. Core project initialization and doctors do not require a Vault.

## Creating a new project

```bash
ratchery new my-project --category personal
```

`--category` must be one of `personal | academic | learning | work | experiments | archived`
(`CATEGORIES` in `lib/agent_workspace.py`) and is only meaningful if the global config's
project layout is `categorized` (see `INSTALLATION.md`'s `--project-layout` flag) — under
`flat` layout the category still creates a subdirectory under `--parent`/the configured
projects root. `--parent PATH` overrides the parent directory outright.

`new` creates the directory, runs `git init` if `git` is on `PATH`, then calls the same
`init_project()` an existing repo uses. What gets generated (`project_files()` in
`lib/agent_workspace.py`):

- `AGENTS.md` / `CLAUDE.md` — managed blocks from `assets/project/AGENTS.block.md` /
  `CLAUDE.block.md` (see `ARCHITECTURE.md`'s managed-block model).
- `docs/PROJECT_CONTEXT.md`, `docs/CURRENT_STATE.md`, `docs/WORKFLOW.md`,
  `docs/TOOL_POLICY.md` — copied once, never overwritten if already present.
- `docs/COMMANDS.md` — auto-detected build/test/lint commands in a managed block
  (`detect_commands_body()` — Makefile, Python via `uv`/`poetry`/`pip`, Node via
  `pnpm`/`yarn`/`bun`/`npm`, Rust, Go, Maven/Gradle), human notes below the block survive.
- `.gitignore`, `.claudeignore` — the latter is new in v1.0 (`context_engine.py`); it keeps
  build output, dependency trees, and secrets-adjacent paths out of the coding agent's own
  context by default, not just out of the profiler's directory walk.
- `.agents/steering/{product,structure,tech}.md` — new in v1.0: topic-scoped context files,
  created once with placeholders for you to fill in, imported by reference from `AGENTS.md`
  rather than inlined.
- `.claude/settings.json`, `.claude/rules/`, `.claude/agents/` and `.codex/config.toml`,
  `.codex/hooks.json`, `.codex/agents/` — sandboxed tool config + the four unconditional
  baseline agents (`explorer`, `reviewer`, `security-reviewer`, `test-runner`), mirrored for
  both CLIs. A brand-new project also gets `developer` (tier-gated at T0, so effectively
  always active) — five agents present from the start, not four; see `agents-status --path .`
  for the exact active set and why.
- `.agents/runtime/agent_workspace.py` — the `PreToolUse` hook runtime (`lib/hook_runtime.py`
  copied per-project).
- `.agents/state/project-profile.json`, `.agents/state/tier.json` — the profiler and tier
  outputs, described below.
- A linked Vault `Home.md` under `projects/<slug>/` (if a vault is configured).

## Checking and setting the tier

Every `init`/`refresh` run computes a tier automatically using whatever risk answers already
exist, defaulting to the lowest-risk answers (`adaptive_engine.DEFAULT_RISK_ANSWERS`) if
none do yet. That first result is provisional: `init` and `tier` print an action message,
and `doctor`/CI fail until a human records the project's real facts with `tier-set`. To see
or recompute the provisional/current result explicitly:

```bash
ratchery tier
```

This prints the effective tier, this run's freshly computed tier, and the criticality/
complexity scores, and writes `.agents/state/tier.json` + a human-readable
`.agents/state/tier.md`. The **risk ratchet**: if this run computes a lower tier than the
project's historical high (tracked in `.agents/state/tier-history.jsonl`), the effective
tier stays at the historical high and a note is printed — rigor never silently regresses.
To accept a real downgrade (e.g. after removing a payments integration), you must say why:

```bash
ratchery tier --acknowledge-downgrade "Removed Stripe integration, PII no longer stored"
```

That acknowledgement is itself logged in the same history file, so the downgrade is
auditable, not silent.

To change the facts that actually drive the score, edit them via `tier-set` (this writes
`.agents/state/risk-answers.json` and immediately recomputes):

```bash
ratchery tier-set \
  --users public \
  --pii \
  --payments \
  --regulated \
  --data-sensitivity confidential \
  --external-exposure \
  --maturity active
```

Every `tier-set` flag maps directly to a `lib/adaptive_engine.py` risk-answers field:
`--users {internal,external,public}`, `--pii/--no-pii`, `--payments/--no-payments`,
`--life-safety/--no-life-safety`, `--regulated/--no-regulated`,
`--data-sensitivity {none,internal,confidential,restricted}`,
`--external-exposure/--no-external-exposure`,
`--maturity {prototype,active,stable,legacy}` (the `--no-*` forms exist because these are
`argparse.BooleanOptionalAction` flags). Omitted flags leave the existing answer unchanged.
On a new project, `ratchery tier-set --path .` with no additional flags explicitly
confirms the low-risk defaults; do that only after reviewing every fact.

See the `examples/` directory for five worked examples (T0 through a hard-floored T3) with
the exact score math.

## Everyday checks

```bash
ratchery doctor --deep
```

Validates required files exist (including `.agents/state/tier.json` and whatever docs the
recorded tier's `tier_requirements()` says are required), Claude sandbox/credential-scrub
config, Codex hook timeouts, that no raw prompt text leaked into `task-policy.json`, TOML
validity, ownership-manifest/project-id consistency, and — with `--deep` — actually invokes
the `PreToolUse` hook with a synthetic `cat .env` command and asserts it's denied.

Project `doctor` also rescans the project without writing state, derives the expected
tier/ratchet instead of trusting cached fields, validates required agents and Skills for
both clients, enforces supported client versions, and treats malformed risk/history state
as an error. It stops before reading project configuration if a managed parent/file is a
symlink or has the wrong file type. The deep probe hash-compares the deployed runtime with Ratchetry's bundled
copy and executes only the trusted bundled copy; it never runs code from the inspected
project and does not create diagnostic state.

```bash
ratchery tools-recommend --path .
```

Inspects the given path without updating profile/tier state and prints, for every task kind in `lib/tool_router.py`
(`locate_string`, `navigate_symbols`, `understand_architecture`, `third_party_docs`,
`verbose_output`, `security_scan`, `vault_retrieval`, `orient_large_repo`), the ranked
guidance based on command discovery and committed MCP opt-ins. It is advisory and does not
install, enable, or authorize anything. QMD is kept out of the route until
`tools-recommend --probe --path .` explicitly runs its version/configuration checks.

## Agents: what's active, and enabling more

```bash
ratchery agents-status --path .
```

Shows every agent active for the project's current tier/capabilities and why (`tier-gated at
T2; project is T2`, `capability 'api' detected`, or `baseline agent, always installed` for the
original `explorer`/`reviewer`/`security-reviewer`/`test-runner` four), plus which
specialized/optimization/operations agents are available but not installed. Only the 4
baseline agents plus whatever the current tier/capabilities imply are ever copied
automatically — the rest (`security-engineer`, `context-optimizer`, `cost-optimizer`,
`architecture-auditor`, `release-manager`, `migration-agent`, `embedded-engineer`,
`performance-engineer`) are on-demand:

```bash
ratchery agents enable cost-optimizer --path .
ratchery agents disable cost-optimizer --path .
```

Nothing is ever auto-removed when a tier/capability stops requiring an agent — `agents-status`
lists these as "installed but no longer implied" so a human decides.

## Optional MCP servers (Serena, Context7)

```bash
ratchery mcp enable serena --path .
ratchery mcp status --path .
ratchery mcp disable serena --path .
```

Writes/removes the static definition for one server at a time in both client formats:
Claude Code's `.mcp.json` and a dedicated Ratchetry-owned `[mcp_servers.*]` block in
`.codex/config.toml`. It never starts or downloads the server. Review both files before the
next session. The explicit opt-in is recorded in committed
`.agents/state/mcp-enabled.json`, so a teammate's first `refresh` preserves the decision;
`doctor` reports drift if either client side is later removed or changed.

The three project files are updated as one process-level transaction: both
client representations are validated and backed up first, and a failed replace
rolls all project files back. Backups are private local state outside the
repository and contain a project-relative source label, not the checkout's
absolute path.

If the same server name already has a user-owned definition, enable refuses to overwrite
it. Disable only removes an opt-in recorded by Ratchetry and refuses to delete a modified
Claude definition. This keeps MCP opt-in reversible without claiming arbitrary user config.
The Codex table shape follows [Codex's MCP documentation](https://developers.openai.com/codex/mcp).

Managed MCP profiles are intentionally narrow. Serena is fixed to the full
commit behind v1.7.0 and exposes only symbol overview/find/reference retrieval;
Context7 exposes only library-ID resolution and documentation queries. Codex
uses prompt approval, bounded startup/tool timeouts, and per-tool output limits;
Claude lists the same tools under explicit `permissions.ask`. These controls
reduce exposure and context volume, but do not turn an upstream MCP into trusted
code. Keep network disabled unless the reviewed integration needs it.

Codex loads a repository's `.codex/config.toml` only after the user trusts that
repository. Review the checkout and accept Codex's trust prompt on first use;
Ratchetry deliberately cannot write a user-level trust decision on the
repository's behalf. `doctor` validates the committed policy, while the client
compatibility canary separately proves that supported Codex versions parse it
after an explicit ephemeral trust grant.

## Optional third-party tools (RTK)

```bash
ratchery tools-install rtk
```

Prints the pinned install command plus distinct preview/apply commands for
Claude and Codex; never runs them. Claude's integration is a `PreToolUse` hook,
while Codex's is `AGENTS.md`/`RTK.md` guidance. Review the dry-run, leave
telemetry disabled, verify raw failure-output recovery, and measure the result
before enabling RTK broadly.

`tools-status` shows every catalog entry's `profile`, `on-demand`, or
`experimental` mode and network posture without executing optional binaries;
`tools-status --probe` explicitly adds version and QMD security probes.
`tools-recommend` is adaptive guidance, not authorization to install. The
complete selection policy and security-scanner profiles are in `09-TOOLS.md`
and `TOOL_POLICY.md`.

## Measuring token cost and task success

With ccusage installed explicitly, inspect local usage without creating state:

```bash
ratchery usage --source claude --period daily \
  --since 20260901 --until 20260907 --offline
ratchery usage --source codex --period session \
  --session-id SESSION_ID --json --offline
```

`--offline` prevents pricing refresh access. `--json` emits ccusage's JSON
without a Ratchetry preamble, so it is safe for scripts. Costs are estimates and
an older Claude-only ccusage may reject a source namespace; the command returns
that failure instead of silently broadening the query.

For an A/B experiment, use fresh sessions with the same repository/commit,
model, prompt, permissions, environment, and starting state:

```bash
ratchery benchmark show core-suite-v1
ratchery benchmark capture baseline-1 --source codex \
  --session-id BASELINE_SESSION_ID --task-set core-suite-v1 \
  --model MODEL_ID --client-version codex-VERSION \
  --environment-id ENVIRONMENT_ID --configuration native \
  --attempted-tasks 6 --successful-tasks 6
ratchery benchmark capture rtk-1 --source codex \
  --session-id RTK_SESSION_ID --task-set core-suite-v1 \
  --model MODEL_ID --client-version codex-VERSION \
  --environment-id ENVIRONMENT_ID --configuration rtk-v0.48.0 \
  --attempted-tasks 6 --successful-tasks 6
```

Run every task from the shown suite in a fresh fixture copy and repeat each arm
at least three times. Capture the additional trials as `baseline-2`,
`baseline-3`, `rtk-2`, and `rtk-3`, then summarize them:

```bash
ratchery benchmark report \
  --baseline baseline-1 --baseline baseline-2 --baseline baseline-3 \
  --candidate rtk-1 --candidate rtk-2 --candidate rtk-3 --json
```

The session IDs are sent only to local ccusage and are not persisted. Snapshots
live in local XDG state outside the repository and contain aggregate tokens,
estimated cost, filters, task counts, and reproducibility identifiers — no raw
rows, prompts, responses, paths, project labels, or model breakdowns.
Use `--since/--until` plus optional `--project` instead of `--session-id` for a
fully isolated batch. Capture refuses to overwrite unless `--replace` is
explicit and requires a clean Git worktree. Compare also requires the same
commit, task set, model, client/environment IDs, ccusage version, and
attempted-task count; date-window arms must have equal duration. See
`BENCHMARKING.md` for the full protocol and interpretation.

For a no-state cost warning, use:

```bash
ratchery budget check --source codex \
  --max-cost-usd 5 --max-tokens 200000
```

The command always asks ccusage for offline aggregates and exits 0 for advisory
warnings. Add `--enforce` only when a script should receive exit 3. It does not
prevent future spend or replace provider billing limits.

Keep the measured commit checked out and clean until each capture. The recorded
commit describes capture-time state; it cannot cryptographically prove which
commit generated an older ccusage record.

## Spec-driven changes (tier-appropriate)

For anything beyond a trivial fix, once the project is above T0, invoke the
`spec-driven-change` Skill. It reads `.agents/state/tier.json`'s `requirements.spec_mode` and
picks the template: `docs/specs/DELTA_SPEC_TEMPLATE.md` (lightweight, delta-only) at T1/T2,
`docs/specs/FULL_SPEC_TEMPLATE.md` (full phase-gated: principles -> specify -> design -> tasks
-> implement -> validate) at T3. T0 projects use `work-plan` instead, if the task is complex
enough to warrant a plan at all.

## Vault workflow

```bash
ratchery vault-search "some query"          # QMD if configured+safe, lexical fallback otherwise
ratchery vault-doctor                        # frontmatter/managed-block/legacy-kit checks
ratchery vault-refresh                        # regenerate VAULT-INDEX.md's managed dashboard
```

`vault-search` prefers QMD (`qmd query -c ratchery-vault --json ...`) only when the
installed version passes the security gate (`>= 2.6.4`, never `<= 2.6.3`) *and* the
collection is already configured; otherwise it transparently falls back to a lightweight
lexical scorer over the vault's own Markdown files (`fallback_vault_search()`) and tells you
which path it took, on stderr. See `docs/18-QMD-SECURITY.md` for the full rationale.

`vault-doctor` (`vault_audit()`) checks: `AGENTS.md`/`CLAUDE.md`/`VAULT-INDEX.md` exist, the
index has exactly one managed activity block, no leftover legacy-kit artifacts, frontmatter
YAML issues (a scalar containing a bare `: ` that should be quoted), and flags executable
`.sh`/`.py` files or `.DS_Store` clutter as warnings. `ratchery vault-fix-yaml --apply`
fixes the frontmatter class of issue it reports (dry-run by default).

### Provider-neutral handoff

Use a handoff only when another agent client or later session will continue
unfinished work. It is one bounded JSON baton in the UUID-matched Vault project,
not a transcript or automatic memory feed:

```bash
ratchery memory backends
ratchery memory status --path .
ratchery memory handoff show --path . --json
ratchery memory handoff clear --path .          # dry run
ratchery memory handoff clear --path . --apply
```

`workspace-save` supplies the reviewed write payload and `workspace-resume`
checks for a pending baton. The CLI derives Git/project provenance, accepts no
caller-supplied revision, rejects unsafe paths and common credential forms, and
will not replace an existing handoff without `--replace`. Showing a handoff
never consumes it; verify it against the repository before clearing it.

The built-in backend has no daemon, network, model call, hook capture, or QMD
indexing cost. `memory plan ai-memory` only describes an experimental automatic
team/multi-machine trial and never executes the discovered binary. The complete
write schema and threat boundary are in [Provider-neutral Memory](MEMORY.md).

### Session logs are per-project, not one shared bucket

Every project gets its own `projects/<slug>/session-logs/` folder (created by `ratchery
init`/`new`). The `workspace-save` Skill writes there, and the Vault dashboard's "Recent
sessions" aggregates across every project's folder, newest first.

If you have logs from before this layout existed (a flat `session-logs/` folder at the Vault
root, shared by every project — the old default), migrate them:

```bash
ratchery vault-migrate-session-logs           # dry run: shows every planned move
ratchery vault-migrate-session-logs --apply   # backs up first, then moves matched logs
```

Matching is by each log's `project:` frontmatter field against an existing
`projects/<slug>/Home.md`. A log with no `project:` field, a project with no matching Home, or
a destination that already exists is left alone and reported — nothing is guessed or
overwritten. Re-run after creating a missing project Home to pick up previously-skipped logs.

## What changes across tiers: T0 vs T2 vs T3

Everything below is read literally from `lib/adaptive_engine.py`'s `tier_requirements()` —
this is data the framework enforces via `doctor`, not aspirational documentation.

| | T0 — Experiment/personal | T2 — Product | T3 — Critical/regulated |
|---|---|---|---|
| `spec_mode` | `none` | `openspec-light` | `speckit-full` |
| `required_docs` | *(none beyond baseline)* | `docs/PROJECT_CONTEXT.md`, `docs/decisions/` | `docs/PROJECT_CONTEXT.md`, `docs/decisions/`, `docs/SECURITY_REVIEW.md` |
| `required_agents` | *(none beyond core)* | `architect`, `security-reviewer` | `architect`, `security-reviewer`, `qa` |
| `required_skills` | *(none beyond global)* | `security-scan`, `dependency-audit` | `security-scan`, `dependency-audit`, `architecture-map` |
| `testing_bar` | `none required` | `unit + integration tests for changed behavior, CI required` | `unit + integration + regression tests required, CI required, human review before merge` |
| `security_bar` | `sandbox + secondary hook (framework default)` | `sandbox + secondary hook + security-reviewer agent on risk-relevant changes` | `sandbox + secondary hook + mandatory security-reviewer sign-off + CodeGuard rules (if installed)` |

T1 sits between T0 and T2: `spec_mode: openspec-light`, `required_docs:
["docs/PROJECT_CONTEXT.md"]`, `testing_bar: "smoke tests for changed behavior"`, and the
same baseline `security_bar` as T0 (no extra required agents/skills yet).

`tier_requirements()` output is *data*; `doctor_project()` is the caller that decides how
strictly to enforce it. Today it reports a missing `required_docs`, `required_agents`, or
`required_skills` entry as an **error**, at the same severity, so a tier requirement cannot
be satisfied by nobody looking at the warning. Create the missing document, or lower the
tier deliberately with `ratchery tier --acknowledge-downgrade "<reason>"` — which is
itself logged, and which `doctor` keeps reporting for as long as the project stays below the
tier it was downgraded from.
