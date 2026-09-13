# Architecture

This document describes how the current Ratchetry runtime is actually built: the module
boundaries, how the managed-content model avoids destroying human edits, the two-layer
security model, and why the system has this shape instead of a simpler one.

Ratchetry is a setup-first operating layer for Claude Code, Codex, and durable
project memory. The Adaptive Engine is its control plane: it selects how much
of the shipped capability and process a project should activate. It is not a
standalone risk product with a workspace attached. Product scope, principles,
users, and non-goals are canonical in `docs/PROJECT_CONTEXT.md`.

For day-to-day usage see `USER-GUIDE.md`. For extending the framework see
`DEVELOPER-GUIDE.md`. The numbered `docs/00-START-HERE.md` … `docs/18-QMD-SECURITY.md` set
remains the detailed reference for individual subsystems (Vault migration, hooks, QMD
security, etc.) and is cross-referenced below rather than duplicated.

## Module boundaries

The runtime is seven Python modules under `lib/`, all stdlib-only:

| Module | Responsibility |
|---|---|
| `lib/agent_workspace.py` | Core engine, CLI (`argparse`), installer glue, project/Vault file generation, managed-block merge engine, doctors, QMD integration |
| `lib/adaptive_engine.py` | T0–T3 tier classification, the risk ratchet, `tier_requirements()` |
| `lib/context_engine.py` | `.claudeignore` generation, steering-file generation (`product.md`/`structure.md`/`tech.md`) |
| `lib/tool_router.py` | Pure task-kind → tool routing table (no I/O) |
| `lib/efficiency.py` | Pure ccusage aggregate validation, benchmark task-set/snapshot/report schemas, and budget evaluation |
| `lib/memory_engine.py` | Pure validation and rendering for the bounded provider-neutral handoff schema |
| `lib/hook_runtime.py` | The secondary `PreToolUse` regex guard installed into `.agents/runtime/agent_workspace.py` in every project (see "Two-layer security model" below) |

`agent_workspace.py` is the entry point and orchestrator; the other six are sibling
modules it imports/deploys and calls into — it does not duplicate their logic. Unlike the
other five imported siblings, `hook_runtime.py` is never imported directly: `agent_workspace.py`
copies it verbatim into each project (`.agents/runtime/agent_workspace.py`) as the file
Claude Code's `PreToolUse` hook actually invokes at runtime, and `doctor --deep` later
hash-verifies that deployed copy against this same source file before ever executing
anything from a target project (see the RCE fix referenced in `CHANGELOG.md`'s
`v1.0.0-rc.1` section — this hash-then-execute-only-the-trusted-copy pattern is exactly
why the module boundary matters here).

```python
import adaptive_engine as ae
import context_engine as ce
import efficiency as ef
import memory_engine as me
import tool_router as tr
```

This works regardless of how `ratchery` is invoked (the `bin/ratchery` shim,
a direct `python3 lib/agent_workspace.py` call, or the installed copy under
`~/.local/share/ratchery/lib/`) because Python always puts the running script's own
directory at `sys.path[0]`. Since `adaptive_engine.py`, `context_engine.py`,
`efficiency.py`, `memory_engine.py`, and `tool_router.py` live next to
`agent_workspace.py` in the same `lib/` directory, the plain
`import adaptive_engine` resolves without any path manipulation, `PYTHONPATH` setup, or
package `__init__.py` — as long as the seven files are copied together, which the
validated `MANIFEST.json` staging step in `install.sh` guarantees.

`agent_workspace.py` still owns `inspect_project()`/`profile()`
(file/line/dependency/capability scanning — the "how big and what kind of project is this"
signal). `inspect_project()` is pure; `profile()` adds stable identity/timestamps and writes
the generated profile state. `adaptive_engine.py` is deliberately separate from this scan
so the "how big is this repo" question and
the "how much rigor does this repo need" decision stay independently testable and
readable — `adaptive_engine.classify()` consumes a `profile()` dict as input, it never
re-walks the filesystem itself. See `lib/adaptive_engine.py`'s own module docstring for the
full rationale.

## How the modules compose

```text
                     ┌─────────────────────┐
   CLI (argparse) →  │ agent_workspace.py   │
                     │  - profile()          │
                     │  - project_files()    │───calls───▶ context_engine.py
                     │  - doctor_project()    │            (.claudeignore, steering/*.md)
                     │  - init_project()      │
                     │  - vault_* / qmd_*      │───calls───▶ adaptive_engine.py
                     └─────────────────────┘            (classify, tier_requirements)
                                │
                                ├──calls (tools-recommend)──▶ tool_router.py
                                ├──calls (usage/benchmark/budget)──▶ efficiency.py
                                ├──calls (memory handoff schema)──▶ memory_engine.py
                                └──deploys a verbatim copy──▶ hook_runtime.py
                                   (.agents/runtime/agent_workspace.py)
```

`init_project()` is the representative call chain, in its actual order:
`profile(path)` → `ae.classify(path, p)` (tier is computed *before* project files are
generated, because steering-file content and agent activation both depend on knowing the
tier, not just the raw profile) → `project_files(path, p, tier)` (which calls
`ce.generate_claudeignore()` and `ce.generate_steering_files()`) → `vault_project(path, p)`.
Each stage writes its own state file under `.agents/state/` (`project-profile.json`,
`tier.json`, `tier-history.jsonl`). Risk answers are created or changed explicitly through
`tier-set` (or by reviewing the JSON directly). `refresh` and `tier` rescan current project
facts before writing; `doctor` independently rescans and evaluates the tier in memory so a
stale generated profile cannot produce a false green result.

The memory call chain is intentionally separate from initialization:
`memory handoff write` resolves the configured Vault project by exact durable
UUID, derives Git provenance, validates the caller's bounded JSON through
`memory_engine.py`, and atomically writes one `Handoff.json` through anchored
directory descriptors. `show` is read-only; replacement and clear require
explicit flags, take a per-project POSIX advisory lock across the complete
mutation, and create no-follow private XDG-state backups. Git provenance turns
off repository-configured fsmonitor execution. No lifecycle hook invokes this
path and no optional backend is contacted.

## The managed-block content model

Every generated file that a human is also expected to edit (`AGENTS.md`, `CLAUDE.md`,
`.gitignore`, `docs/COMMANDS.md`, `VAULT-INDEX.md`, Vault `Home.md` notes) uses the same
pattern: a pair of marker comments delimits the region Ratchetry owns. Everything
outside the markers is the human's, and `refresh` never touches it.

The marker constants, defined once in `lib/agent_workspace.py`:

> The `"v8"` in every marker is the managed-block **merge-format** version, tracked
> separately from the software's own `VERSION` and frozen on purpose: bumping it would
> break `refresh`'s ability to find the managed block in any already-installed project
> unless paired with an explicit migration path. Ratchetry instead recognizes
> the internal pre-rebrand marker and keeps it frozen through 1.x. See the
> comment above these constants in `lib/agent_workspace.py`.

```python
MSTART = "<!-- agent-workspace:v8:start -->"
MEND   = "<!-- agent-workspace:v8:end -->"
TSTART = "# agent-workspace:v8:start"
TEND   = "# agent-workspace:v8:end"
INDEX_START    = "<!-- agent-workspace:v8:index:start -->"
INDEX_END      = "<!-- agent-workspace:v8:index:end -->"
COMMANDS_START = "<!-- agent-workspace:v8:commands:start -->"
COMMANDS_END   = "<!-- agent-workspace:v8:commands:end -->"
```

- `MSTART`/`MEND` — HTML-comment markers used in Markdown files that support HTML comments
  (`AGENTS.md`, `CLAUDE.md`, Vault `Home.md` metadata blocks).
- `TSTART`/`TEND` — plain `#`-comment markers used where an HTML comment is inappropriate
  for the file's own syntax (`.gitignore`, `.codex/config.toml`).
- `INDEX_START`/`INDEX_END` — the Vault dashboard's own managed activity block inside
  `VAULT-INDEX.md`.
- `COMMANDS_START`/`COMMANDS_END` — the auto-detected command block inside
  `docs/COMMANDS.md`.

The rewrite logic is one shared function, `replace_managed_block(old, body, start, end)`: if
both markers are already present, only the text between them is replaced; otherwise the new
block is appended once. `managed()` wraps this with a read-modify-write-if-changed cycle
in `lib/agent_workspace.py`.

For structured files (`.claude/settings.json`, `.codex/hooks.json`) a plain text-block
marker doesn't work, so `merge_project_json()` / `merge_codex_hooks()` do a recursive
key-aware merge instead: dicts merge recursively, most user-set scalars are preserved
as-is, and `hooks` arrays are special-cased. A hook group is only ever replaced or removed
if `is_owned_hook_group()` recognizes it as framework-owned:

```python
RUNTIME_MARKER = ".agents/runtime/agent_workspace.py"

def is_owned_hook_group(group: Any) -> bool:
    ...
    return any(
        isinstance(h, dict) and RUNTIME_MARKER in hook_runtime_reference(h)
        for h in hooks
    )
```

`hook_runtime_reference()` checks both a shell-form `command` and exec-form
`args`. Any hook group that does *not* reference the runtime marker is left untouched on
refresh, no matter what event or matcher it's registered under — that's how a user-added
Claude/Codex hook survives an upgrade. Directories of copied assets (global Skills,
conditional project Skills) use a third mechanism: a `MANAGED_BY_RATCHERY` sentinel
file written into the directory root by `copy_managed_dir()`. A directory without that
sentinel is treated as user-owned and is never overwritten or deleted by a refresh; a
directory that does carry it is safely replaced wholesale on the next run. The former
`MANAGED_BY_AGENT_WORKSPACE` sentinel is accepted only as an upgrade input; the next
managed replacement writes the Ratchetry name.

See `docs/12-FILE-REFERENCE.md` for the full list of managed vs. human-owned files, and
`docs/04-VAULT-MIGRATION.md` for how the same discipline applies to Vault content
specifically (including the legacy-kit detection in `legacy_kit_detected()`/`legacy_owned()`
that lets a pre-release internal Vault migrate safely).

## Two-layer security model

Layer 1 — the OS-level sandbox and CLI permission config, generated into each project's
`.claude/settings.json` (`sandbox.enabled`, `sandbox.failIfUnavailable: true`,
`sandbox.allowUnsandboxedCommands: false`, bypass-permissions mode disabled,
subprocess credential-env scrub) and
`.codex/config.toml` (restricted workspace, network off by default). This is the real
security boundary — the OS/runtime enforces it, not a string match.

Layer 2 — a deterministic `PreToolUse` hook (`lib/hook_runtime.py`, copied per-project to
`.agents/runtime/agent_workspace.py`) that pattern-matches obviously dangerous commands
(reading `.env`/credential files, destructive shell operations) before they run. This layer
is explicitly documented as secondary defense-in-depth, not the primary boundary — a
determined obfuscated command can defeat a literal string match, which is why Layer 1 exists
underneath it. `doctor_project()` validates the required permission, sandbox,
credential, environment-filter, and real `PreToolUse` bindings for both clients.
Under `--deep` it also hash-compares the deployed runtime with the trusted bundled
copy before exercising that bundled copy with a synthetic denied operation. The probe
proves the guard behavior; the separate binding checks prove the clients will invoke it.

Before any project mutation, the lifecycle commands validate the complete
managed directory/file layout with `lstat` and stop at the first unsafe parent,
so a symlink cannot redirect a settings, state, agent, or documentation write
outside the selected checkout. MCP changes additionally use a prepared
multi-file transaction with rollback. The deployed hook's task-policy write is
anchored to a verified `.agents/state` directory descriptor and uses a private,
unpredictable temporary file.

Full threat model and the documented limits of Layer 2: `docs/10-SECURITY.md`.

## Why this shape, not something simpler

**"MAXIMUM USEFUL CAPABILITY, MINIMUM JUSTIFIED COST."** The global install provides the
small core contract and Skills; project initialization provides four baseline agents plus
the minimal tier floor. Specialized capabilities are tier-gated, capability-conditional,
or on-demand. No third-party tool is installed by `install.sh`. `tools.lock.json`
classifies optional integrations by family, activation mode, command probe,
network posture, and benchmark requirement. `tools-status` reports that policy;
`tools-recommend`/`tool_router.route()` rank advisory candidates with the
smallest native capability first. They do not enable or authorize a tool.
No MCP
server is auto-injected into a project's `.mcp.json`; migration code removes the
exact legacy auto-injected Context7 entry without touching user-owned definitions. No SessionEnd hook exists
by default — durable memory only happens through the explicit `workspace-save` Skill, never
as a side effect of the client closing.

The Adaptive Engine and Tool Router exist specifically to make the alternative — "just tell
the agent to be selective in a big prose doc" — insufficient. A tier (T0–T3, computed
deterministically from a scanned codebase size/structure profile plus explicit human-owned
facts in `risk-answers.json`) turns "how careful should this project be" into an auditable
policy recorded in `.agents/state/tier.json` and
`.agents/state/tier-history.jsonl` — including a one-way ratchet so rigor can't silently
regress. The Tool Router turns "which tool for this job" into a reviewable, unit-tested
table (`lib/tool_router.py`) instead of guidance an agent can silently ignore. Both are
consumed by the same generated `AGENTS.md` block (`assets/project/AGENTS.block.md`'s
"Context efficiency and tool routing" section) so the policy an agent actually reads and the
code that computes it never drift apart.

This is why the repo has seven modules instead of one script: workspace lifecycle and
profiling, risk/tier classification, context policy, tool selection, aggregate
cost measurement, bounded handoff validation, and the deployed runtime guard are
separate concerns with different inputs and failure modes. Splitting
them keeps the policy testable without making every optional capability a runtime
dependency or an always-loaded context cost.

## Cost-measurement boundary

`ratchery usage` builds a validated argv list and invokes an independently
installed ccusage from the user's home directory, not from an untrusted repository
that could supply local ccusage config. `benchmark capture` and `budget check` force
JSON and offline mode, pass either an exact session selector or a date/project window,
and send
the result to `efficiency.parse_ccusage_json()`. That pure boundary immediately
reduces the report to token/cost totals; session IDs, per-day/session rows, models,
paths, prompts, and responses are never written.

The resulting schema-versioned snapshot lives under the user's XDG state
directory, outside the repository; relative XDG state and resolved in-repository
destinations are rejected. Its namespace binds the committed project UUID
to a canonical-path fingerprint. Names and selectors are validated, shell
execution is never used, symlinked storage is rejected, writes are atomic, and
replacement requires `--replace`. Capture requires a clean Git worktree and
records the capture-time commit plus user-supplied model/client/task/environment
labels. A bundled task-set ID is bound to its validated SHA-256 digest. Pairwise
compare rejects incompatible provenance and scopes; repeated `benchmark report`
also rejects mixed arm configurations, exposes ranges/medians and quality floors,
and never emits an automatic adoption decision. `budget check` writes no snapshot
and only maps a threshold to a nonzero policy exit when `--enforce` is explicit.
These controls detect unlike captures but do not attest which commit produced
historical usage or prevent future spend. See
`BENCHMARKING.md` for the user protocol and limits.

## Upstream-client compatibility boundary

The normal CI tests Ratchetry's own parsers and generated contracts without
downloading changing clients. A separate scheduled/manual
`.github/workflows/client-canary.yml` installs minimum-supported and current
Claude Code/Codex packages in an ephemeral credential-free runner, generates a
project, and asks each client to parse the configuration without model inference
or MCP connection. Codex receives an ephemeral user-level trust entry because it
correctly ignores repository configuration until the user trusts that checkout;
Ratchetry never writes this decision during normal installation. The canary detects
upstream compatibility drift, not sandbox containment or upstream MCP safety.
