# Delta Spec: Fix all blocking + should-fix findings from the Codex pre-publish review

> Follow-up (2026-09-07): the later setup-first/pruning phase also removed the dormant
> `qmd_version_tuple()` helper and runtime `SessionEnd` writer that this historical spec
> explicitly left out of scope. Scoped monorepo tier floors remain a roadmap item.

Mode: **openspec-light** (T1). Describe only what changes.

## Why

An independent seven-persona Codex review found 6 blocking issues and 10
should-fix-before-publish issues, none of which were caught by this session's
own two prior review agents.
Every blocking finding was independently reproduced before starting this
spec (see the conversation record / commit messages) -- this is not a
blind pass-through of the report.

## What changes (grouped by finding)

**Blocking:**

1. **RCE in `doctor --deep`** (`action.yml`/`lib/agent_workspace.py:1284-1289`):
   the deep probe executed `<target>/.agents/runtime/agent_workspace.py`
   directly -- a file inside the (possibly untrusted) checked-out target.
   Fixed by hash-comparing the target's copy against the framework's own
   bundled `lib/hook_runtime.py`; only the bundled copy is ever executed,
   and only after the hashes match. A mismatch is reported as an error
   without executing anything from the target.
2. **`doctor` approves an empty `.claude/settings.json`** (`:1201-1238`):
   `parse_json_file()` silently mapped non-dict JSON to `{}`, and
   `doctor_project()` gated the whole Claude-sandbox check block on
   `if claude:` (falsy for `{}`). Fixed: `parse_json_file()` now reports an
   error for non-object JSON; the gate is now `.claude/settings.json`
   existing on disk, not the parsed dict being truthy.
3. **Shipped `.gitignore` conflicts with `doctor`'s required files**
   (`assets/project/gitignore.block`, `.gitignore`): `ownership.json` was
   excluded from the tier-state negation exception in both this repo's own
   `.gitignore` and the template shipped to every new project, while
   `doctor_project()` unconditionally requires it. Reproduced on a genuine
   fresh clone of this repo's own `main`. Fixed by adding
   `!.agents/state/ownership.json` to both files and committing the
   previously-ignored file in this repo.
4. **`doctor` never checks recorded tier against current risk facts**
   (`:1211-1229`): added a pure (non-writing) recomputation using
   `adaptive_engine.compute_tier()` against the currently-recorded
   `.agents/state/tier.json`'s `computed_tier`; a mismatch is an error
   telling the user to re-run `tier`/`tier-set`.
5. **README's literal install command fails** (`README.md`, `docs/*.md`):
   `~` doesn't expand inside double quotes in bash. Every occurrence
   changed to `"$HOME/..."`.
6. **Acknowledged tier downgrade doesn't persist**
   (`lib/adaptive_engine.py:207-252`): `highest_recorded_tier()` looked at
   the entire append-only history, including entries from before an
   acknowledged downgrade, so the very next ordinary run ratcheted back up.
   Fixed: `highest_recorded_tier()` now finds the most recent history entry
   with `downgrade_acknowledged: true` (already an existing field written by
   `classify()` -- no new field needed) and only considers entries from that
   point onward, so the acknowledged tier becomes the new floor going
   forward instead of being overridden by older, higher entries still
   sitting in the log.

**Should-fix-before-publish:**

7. Portuguese-language response rule in `assets/global/AGENTS.block.md` /
   `CLAUDE.block.md` removed from the shipped global template (was a
   personal preference, not something to install for every user).
8. MCP `enable`/`disable`/`status` documented explicitly as Claude-only
   (writes `.mcp.json`; Codex's `[mcp_servers.*]` TOML format is a
   different, not-yet-implemented surface) instead of implying dual-CLI
   support. `tools.lock.json`'s Serena version and the generated
   `--context` value reconciled to the same version.
9. `examples/t1-backend-api/requirements.txt`: FastAPI/Starlette bumped
   past the DoS advisory range; `.github/dependabot.yml` extended with a
   `pip` ecosystem entry scoped to the examples directory.
10. `README.md`'s enforcement language softened to describe deterministic
    classification/scaffolding/routing, not change-level enforcement it
    doesn't perform; the "nothing auto-installs" claim qualified (baseline
    agents/global skills do install automatically).
11. README's "Why not just `<X>`?" table updated for Spec Kit's/OpenSpec's
    current (2026-09) feature sets per the Codex review's external
    references, narrowed to the still-defensible differentiator.
12. Steering files (`.agents/steering/*.md`) and `docs/CURRENT_STATE.md`'s
    tier-related claims refreshed to match the currently recorded tier and
    file counts; `docs/PROJECT_CONTEXT.md` left as a template (expected --
    see Out of scope) but the module docstring in `context_engine.py`
    corrected to state steering files are seeded once, not kept updated.
13. `Makefile`'s `test`/`unit` targets include `ruff`/manifest verification
    (matching what CI actually runs and what `CONTRIBUTING.md` claims);
    `docs/specs/ci-json-doctor-gate.md`'s coverage claim narrowed to match
    what the tests actually assert (already partially true from the prior
    session's fix; confirming/tightening wording here).
14. `.github/workflows/release.yml`: `persist-credentials: false` on
    checkout.
15. `docs/ARCHITECTURE.md`'s module table/count fixed (5 modules, not 4;
    `lib/hook_runtime.py` added to the table); dangling references in
    `SECURITY.md`/`docs/ROADMAP.md`/`docs/MIGRATION.md`/
    `assets/global/skills/registry.json` fixed.
16. Private-baseline-only docs (`docs/01-INSTALLATION.md`,
    `docs/MIGRATION.md`, `docs/TEST-REPORT.md`, `docs/SPEC.md`) removed
    from the live doc tree (history stays in git log/`CHANGELOG.md`);
    the then-current audit snapshot kept temporarily as historical evidence)
    are not linked from live navigation as if they were current guidance.

**Found during this spec's own fresh-clone validation, not in the original
report**: `.agents/state/project-id` -- a bare-text sibling file to
`ownership.json`, whose content `doctor` compares against
`ownership.json`'s `project_id` field -- was excluded by the exact same
`.gitignore` bug as finding 3. Fixed identically (both `.gitignore` files,
committed this repo's own copy). This is exactly why the spec's own
Validation section requires a genuine fresh clone, not a re-read of the
dirty working tree: the fix for finding 3 alone still failed this check
until the sibling file was found.

## Out of scope (explicitly, from the review's own scoping or the user's prior decisions)

- Finding 17 (GitHub Ruleset) -- a repository *setting*, not a code change;
  applies to the new repo at creation time, tracked in the migration plan.
- Findings 18-20 (nice-to-have / worth-considering-later): social-preview
  image, OpenSSF Best Practices Badge, SBOM/SLSA attestation, dormant
  `qmd_version_tuple()`/`session_log()` removal, per-path tiering for
  mixed-risk monorepos. Not requested as "should be resolved" -- tracked in
  `docs/ROADMAP.md` instead.
- `docs/PROJECT_CONTEXT.md` staying a template is intentional (same
  "written once, human-owned" contract as the steering files) -- not a bug
  to fix, per the existing `context_engine.py` design already reviewed in
  the etapa-4 pass.

## Tasks

- [x] Fix 1: hash-compare + framework-owned execution for the deep probe.
- [x] Fix 2: `parse_json_file()` rejects non-dict JSON; gate on file
      existence, not dict truthiness.
- [x] Fix 3: `!.agents/state/ownership.json` in both `.gitignore` files;
      commit this repo's own `ownership.json`.
- [x] Fix 4: pure tier-vs-risk-facts divergence check in `doctor_project()`.
- [x] Fix 5: `"$HOME/..."` everywhere the README/docs used `"~/..."`.
- [x] Fix 6: ratchet-floor-reset marker + `highest_recorded_tier()` fix.
- [x] Fix 7: remove the Portuguese rule from the shipped global template.
- [x] Fix 8: document MCP as Claude-only; reconcile Serena version.
- [x] Fix 9: bump the example's FastAPI/Starlette; add a scoped pip
      Dependabot entry.
- [x] Fix 10: soften README's enforcement claims.
- [x] Fix 11: refresh the competitor-comparison table.
- [x] Fix 12: refresh steering-file/CURRENT_STATE tier claims; fix the
      `context_engine.py` docstring.
- [x] Fix 13: `Makefile` runs ruff + manifest verification.
- [x] Fix 14: `persist-credentials: false` in `release.yml`.
- [x] Fix 15: `ARCHITECTURE.md` module table + dangling references.
- [x] Fix 16: remove private-baseline-only docs from the live tree.
- [x] Add regression tests for fixes 1, 2, 4, 6 (the four with real
      exploit/logic-bug reproductions).
- [x] `CHANGELOG.md` + `docs/CURRENT_STATE.md` updated.

## Validation

- New regression tests for the RCE fix, the empty-settings-bypass fix, the
  tier-divergence check, and the ratchet-floor-reset fix -- each written to
  fail against the pre-fix code path (verified by checking out the fix
  commit's parent and confirming red, where practical) and pass after.
- Full unit suite + `bash tests/run-tests.sh` (now confirmed runnable per
  the Codex review's environment) + `ruff check` + `scripts/verify-manifest.py`.
- Manual re-reproduction of all 6 blocking scenarios from the review,
  confirming each now behaves correctly.
- Fresh `git clone` of the branch (not the dirty working tree) re-run
  through `doctor --deep`, to specifically close the gap that let finding 3
  go undetected for two prior review passes.

## Status

- [x] Proposed
- [x] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
