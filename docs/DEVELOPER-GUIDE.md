# Developer Guide

For someone extending Ratchetry itself (not a project it manages). Read
`ARCHITECTURE.md` first for the module boundaries and managed-block model this guide
assumes.

## Adding a new global Skill

Global Skills live under `assets/global/skills/<name>/SKILL.md` and are installed to
`~/.agents/skills/<name>/` (canonical) with a symlink at `~/.claude/skills/<name>/`
(`global_guidance()` in `lib/agent_workspace.py`, via `copy_managed_dir()`).

Format — read two existing ones before writing a new one, e.g.
`assets/global/skills/work-plan/SKILL.md`:

```markdown
---
name: work-plan
description: Plan a complex, risky, cross-module, migration, security, architecture, or multi-agent task before implementation.
---

1. Establish objective, non-goals, assumptions, affected contracts, risks, and acceptance criteria.
2. Identify the smallest initial file set and the validation commands.
...
```

and the shorter `assets/global/skills/record-bug/SKILL.md`:

```markdown
---
name: record-bug
description: Create or update a reusable bug-solution note after a non-obvious investigation.
---

Create a permanent bug note only when the root cause was non-obvious, the issue may recur, or the lesson is reusable. ...
```

Conventions to match: YAML frontmatter with exactly `name` and a one-sentence `description`
(the description is what an agent uses to decide *when* to reach for the skill — write it as
a trigger condition, not a summary); body is imperative numbered steps or a short paragraph,
no filler. To add one:

1. Create `assets/global/skills/<name>/SKILL.md` following the format above.
2. Add its name to `assets/global/skills/registry.json`'s `skills.available` list.
   `global_guidance()` refuses registry/disk drift, so an unregistered directory or a
   registered missing Skill fails installation instead of silently changing the catalog.
   A user-owned same-name destination is also preserved with an explicit collision error;
   `doctor-global` verifies managed markers, canonical symlinks/copies, and Skill content.
3. Regenerate `MANIFEST.json` (see below) since it's a new shipped file.

**Conditional** (stack-triggered) project Skills are a different, narrower mechanism:
`assets/project/conditional-skills/<skill-name>/SKILL.md`, wired into the capability →
skill mapping inside `install_conditional_skills()`:

```python
mapping = {
    "data": "data-pipeline-review",
    "frontend": "frontend-a11y-review",
    "database": "database-migration-review",
    "api": "api-contract-review",
}
```

Adding a new conditional skill means adding both the `SKILL.md` under
`conditional-skills/` **and** a new `capability: skill-name` entry here — the capability
key must already exist in `profile()`'s `capabilities` dict (`lib/agent_workspace.py`'s
`profile()` function), or you'd need to add a new capability signal there too.

## Adding a new Agent

Agents are mirrored in two formats for the two CLIs — write both, they are not
auto-generated from each other:

- `assets/project/.claude/agents/<name>.md` — Claude Code format:

  ```markdown
  ---
  name: explorer
  description: Read-only explorer for locating code paths and returning concise evidence.
  tools: Read, Grep, Glob, Bash
  permissionMode: plan
  ---

  Stay read-only. Locate definitions, callers, contracts, tests, and configuration. Return a concise evidence map. Do not propose broad rewrites.
  ```

- `assets/project/.codex/agents/<name>.toml` — Codex format (note the filename uses
  underscores where the agent name has a hyphen, e.g. `security-reviewer.md` pairs with
  `security_reviewer.toml`):

  ```toml
  name = "explorer"
  description = "Read-only codebase explorer for gathering evidence before changes."
  default_permissions = ":read-only"
  developer_instructions = """
  Stay read-only. Trace definitions, callers, contracts, tests, and configuration. Prefer targeted search and return a concise evidence map.
  """
  ```

Both files should express the *same* behavior contract (scope, read-only vs. write,
`permissionMode`/`default_permissions`) in each CLI's own idiom — keep the prose instructions
close in wording, not copy-pasted, since Claude's `tools:`/`permissionMode` and Codex's
`default_permissions` are different permission models. `project_files()` copies every `*.md`
under `.claude/agents/` and every `*.toml` under `.codex/agents/` with `copy_if_missing()` —
so, like the top-level docs, an existing project's hand-edited agent file is never
overwritten by `refresh`; only genuinely new agent files reach existing projects.

If the new agent should be tier-gated (only expected at T2/T3, say), add it to the relevant
tier's `required_agents` list in `adaptive_engine.tier_requirements()` — that's what
`doctor_project()` checks against, not the mere presence of the file.

## Test suite layout

```text
tests/run-tests.sh             bash integration suite (see below)
tests/test_*.py                all stdlib unit/regression modules, auto-discovered
```

`tests/run-tests.sh` is the end-to-end integration suite: it builds an isolated `$HOME`
under a resolved (non-symlinked) temp directory — note the comment explaining *why*
(`mktemp -d` on macOS returns a path under `/var`, itself a symlink to `/private/var`;
subprocess `cwd` values report the resolved path, so `pwd -P` is used to avoid a spurious
mismatch) — seeds a fixture Vault including a legacy Vault Agent Memory Kit v1.0 layout, then
runs the real `install.sh` and CLI commands against it and asserts on output/generated
files.

The `test_*.py` files use plain `unittest.TestCase` classes with no pytest/other
dependency. Run one directly (for example, `python3 tests/test_adaptive_engine.py`) or all
of them with `python3 -m unittest discover -s tests -p 'test_*.py'`.
Each inserts `lib/` onto `sys.path` directly (`sys.path.insert(0, str(Path(__file__)...
/ "lib"))`) rather than relying on an installed package — match that pattern for a new test
module rather than introducing a test framework dependency.

Run everything with `make test`. To isolate only the shell integration path, run
`bash tests/run-tests.sh`; unit tests are a separate auto-discovered target so failures are
easy to localize and CI exercises both paths explicitly.

## Regenerating MANIFEST.json

```bash
python3 scripts/gen-manifest.py
```

`scripts/gen-manifest.py` enumerates tracked files with `git ls-files` (excluding
`.github` and `MANIFEST.json` itself), computes a SHA-256 + byte size per file, and writes the full list plus
`upgrade_from`/`security_baseline` metadata into `MANIFEST.json`. Run this any time files are
added, removed, or modified, and always as the last step before packaging a release — it's
the integrity source of truth the test suite checks against. There is no partial/incremental
mode; it always regenerates the full manifest from what's actually on disk.

## Coding conventions

- **Stdlib only, no new pip dependencies.** Every module in `lib/` imports only from the
  Python standard library (`argparse`, `json`, `pathlib`, `subprocess`, `hashlib`, etc. —
  check the `import` block at the top of any `lib/*.py` file). This is a deliberate
  constraint (see `ARCHITECTURE.md`'s "why this shape" section and the Decision Matrix's
  repeated "avoid adding an external dependency" rationale for Spec Kit/OpenSpec/etc.) — a
  new feature that needs a third-party package should be reconsidered or implemented as an
  optional, explicitly-installed external tool routed through `tool_router.py` instead.
- **Every optional tool needs policy metadata.** Add its `family`, `activation`,
  safe `commands` probe, `network` posture, `benchmark` rule, HTTPS `source`, and
  concrete `policy` to `tools.lock.json`; `tool_catalog_issues()` and tests
  validate the schema. No external tool may use an `always` activation mode.
  Output/retrieval optimizers begin as `experimental` and must be tested through
  the bundled suite plus repeated `benchmark capture/report` trials before
  promotion. The report is evidence for human review, never an automatic gate
  that enables the tool.
- **Match existing function/naming style.** Short, verb-first function names
  (`profile()`, `classify()`, `render_claudeignore()`), `snake_case` throughout, module-level
  constants in `SCREAMING_CASE` near the top of the file, type hints on function signatures
  using `from __future__ import annotations` (already present at the top of every module —
  keep it), docstrings on modules and non-obvious functions explaining *why*, not just *what*
  (see `adaptive_engine.py`'s and `context_engine.py`'s module docstrings as the model to
  follow).
- Prefer extending an existing module's pattern over introducing a new one — e.g. a new
  generated artifact that needs "create once, never clobber" semantics should reuse
  `copy_if_missing()`; a new merged-JSON config should reuse `merge_project_json()`, not a
  bespoke merge function.

## How refresh avoids clobbering user edits

This is the same managed-block/ownership-marker system `ARCHITECTURE.md` describes,
summarized here from the extension author's point of view — what you must do to keep a new
generated file safe to `refresh`:

- **Free-text files a human edits directly** (`AGENTS.md`, `CLAUDE.md`, `.gitignore`,
  `docs/COMMANDS.md`): wrap only the generated part in a marker pair and call `managed()`.
  Never call `atomic_write_text()` directly on a file a human might have added content to.
- **Files created once and then hand-populated** (`docs/PROJECT_CONTEXT.md`, steering files,
  ADR/task templates): use `copy_if_missing()` — write only if the destination doesn't
  already exist, full stop.
- **Structured JSON config another tool also writes to**
  (`.claude/settings.json`, `.codex/hooks.json`): use `merge_project_json()` /
  `merge_codex_hooks()`, and if you're adding hook groups, make sure every hook command you
  generate contains the `RUNTIME_MARKER` sentinel string
  (`".agents/runtime/agent_workspace.py"`) so `is_owned_hook_group()` correctly identifies it
  as framework-owned on the *next* refresh — a hook group without that marker in its command
  is permanently treated as user-owned from the moment it's written, even if you wrote it.
- **Whole directories** (Skills, agent definition sets): use `copy_managed_dir()`, which
  writes a `MANAGED_BY_RATCHERY` sentinel file into the directory root. A directory
  without that sentinel — including one a user created by hand with the same name — is never
  touched. `managed_directory_marker()` also recognizes the old
  `MANAGED_BY_AGENT_WORKSPACE` sentinel strictly as a migration input, so an existing
  managed directory is upgraded once without weakening the user-owned collision guard.

`write_ownership_manifest()` records the marker constants and the `RUNTIME_MARKER` string
into each project's `.agents/state/ownership.json`, and `doctor_project()` cross-checks that
manifest's `project_id` against `.agents/state/project-id` on every run — so a new generated
file that's supposed to be marker-protected but isn't will not, by itself, be caught by
`doctor`; testing an actual `init` → hand-edit → `refresh` round trip is the real
verification step for any new generated artifact.
