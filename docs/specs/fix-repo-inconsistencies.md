# Delta Spec: Fix three verified repo inconsistencies

> Superseded detail (2026-09-07): the second finding below correctly rejected the old
> "15 always-on" wording but replaced it with a `12 + 3 on-demand` split that the installer
> never enforced. The live registry now records all 15 global Skills as installed and
> discoverable with progressively loaded bodies. This spec remains as historical evidence
> of the change that was reviewed at the time.

Mode: **openspec-light** (T1). Describe only what changes.

## Why

Full-repo review (step 4 of the OSS-readiness pass) found three verified
inconsistencies not covered by the existing regression suite:

1. The `"v8"` string baked into `MSTART`/`MEND`/`TSTART`/`TEND`/
   `INDEX_START`/`INDEX_END`/`COMMANDS_START`/`COMMANDS_END` in
   `lib/agent_workspace.py` has no comment distinguishing "this is a
   managed-block *format* version, deliberately independent of `VERSION`"
   from "this is a leftover from the internal v8.2.1 baseline." It propagates
   into every generated `AGENTS.md`/`CLAUDE.md`/`docs/COMMANDS.md`/
   `VAULT-INDEX.md` and is asserted by literal string in 7 places in
   `tests/run-tests.sh`.
2. `README.md`'s "What's in v1.0" section claims "19 skills (15 global
   always-on + 4 project-level capability-conditional)". The actual split
   (verified against `assets/global/skills/registry.json`) is 12 always-on +
   3 on-demand = 15 global, not 15 all-always-on.
3. The numbered docs sequence (`docs/00-START-HERE.md` ... `19-QMD-SECURITY.md`)
   has a gap: `17-` does not exist and nothing references or explains it,
   likely a leftover from the "16 files -> 8 anchor files" doc reorg in the
   v1.0.1 changelog entry.

## What changes

- `lib/agent_workspace.py`: add a comment block directly above the marker
  constants stating explicitly that the embedded `"v8"` is the
  **managed-block format version**, frozen independently of the software's
  `VERSION`, and must not be bumped without a corresponding migration path
  for already-installed projects (same reasoning `docs/MIGRATION.md`
  documents for the v8.2.1 -> 1.0.0 transition). No behavior change --
  purely a documentation fix resolving the ambiguity, per the decision made
  when this was flagged: freeze-and-document, not rename-and-migrate.
- `docs/ARCHITECTURE.md`: one short note in the module table's surrounding
  text pointing at the same explanation, so a reader doesn't have to find
  the code comment first.
- `README.md`: correct the skills line to "19 skills (12 global always-on +
  3 global on-demand + 4 project-level capability-conditional)".
- Numbered docs: renumber `18-CONTEXT-TOKENS.md` -> `17-CONTEXT-TOKENS.md`
  and `19-QMD-SECURITY.md` -> `18-QMD-SECURITY.md` (closes the gap by
  shifting down rather than inventing a placeholder `17-`), via `git mv` so
  history is preserved; fix every cross-reference to the old filenames
  (`docs/00-START-HERE.md`, and any other doc/README pointing at
  `18-CONTEXT-TOKENS.md`/`19-QMD-SECURITY.md`).

## Affected contracts

- No CLI/API/schema change. `lib/agent_workspace.py`'s marker constants
  keep their exact current string values (`"v8"` unchanged) -- comment-only.
- File renames: `docs/18-CONTEXT-TOKENS.md` -> `docs/17-CONTEXT-TOKENS.md`,
  `docs/19-QMD-SECURITY.md` -> `docs/18-QMD-SECURITY.md`. Any external link
  to the old paths breaks -- acceptable for a pre-1.0-OSS-migration internal
  doc, not a released API.

## Out of scope

- Actually renaming/versioning the `"v8"` marker string itself, or building
  a migration path for it -- explicitly the user's call to defer, tracked as
  a decision item for the etapa-5 migration plan, not resolved by this delta.
- Any other doc/count claim not verified in the etapa-4 review (e.g. the
  `~1775` vs actual 1817 line-count approximation in `ARCHITECTURE.md` --
  reviewed and judged within acceptable "~" tolerance, not touched here).

## Tasks

- [x] Add the format-version comment above the marker constants in
      `lib/agent_workspace.py`.
- [x] Add the pointer note in `docs/ARCHITECTURE.md`.
- [x] Fix `README.md`'s skills breakdown line.
- [x] `git mv docs/18-CONTEXT-TOKENS.md docs/17-CONTEXT-TOKENS.md`;
      `git mv docs/19-QMD-SECURITY.md docs/18-QMD-SECURITY.md`.
- [x] Fix every live reference to the two renamed files (`CHANGELOG.md`'s
      then-historical entries deliberately left as-is -- see Out of scope).
- [x] `CHANGELOG.md` (Unreleased section).
- [x] `docs/CURRENT_STATE.md` update.

## Validation

- `grep -rn "18-CONTEXT-TOKENS\|19-QMD-SECURITY" .` (excluding `.git/`)
  returns zero hits outside this spec file, which names the old filenames as
  evidence.
- Repo-wide broken-markdown-link scan (same script used in the etapa-4
  review) returns zero hits.
- `make test` (no Python behavior changed, but confirms nothing broke).
- Manual: `python3 lib/agent_workspace.py doctor --deep` on this repo itself
  still passes (managed-block detection unaffected by a comment-only change).

## Status

- [x] Proposed
- [x] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
