# Work Plan: Ratchetry durable-memory reconstruction

## Objective

Reconnect the clean Ratchetry repository to its curated Obsidian project
memory, preserve the five existing project session logs, add concise logs for
the four meaningful phases that were never persisted, and record the durable
architecture decisions and reusable bugs already proven by repository code and
tests.

## Non-goals

- Do not store prompts, transcripts, hidden reasoning, raw tool output,
  credentials, tokens, customer data, or complete source files.
- Do not create one note per conversation or duplicate an existing note.
- Do not delete the legacy project tree until its backup and the Ratchetry
  memory status have both been verified.
- Do not treat Vault notes as more authoritative than repository code, tests,
  ADRs, manifests, or hosted Git state.

## Evidence and assumptions

- The Vault currently contains five project logs dated 2026-08-28 through
  2026-09-07, one product-definition decision, and two reusable bug notes that
  search as relevant to the project.
- Both old and new repository paths fail `memory status` because the legacy
  Vault `Home.md` has a different project UUID from the committed Ratchetry
  project ID.
- The 2026-09-09, 2026-09-11, 2026-09-12, and 2026-09-13 phases are evidenced
  by repository work plans, specs, changelog entries, tests, signed commits,
  and the local ignored `CURRENT_STATE.md`, but have no Vault session log.
- The new repository is clean and private with seven signed thematic commits.

## Affected contracts

- Repository ADRs under `docs/decisions/` are the source of truth for durable
  technical decisions.
- Vault decision notes are short navigation summaries linking to those ADRs.
- Project logs live only under `projects/ratchery/session-logs/` after the
  migration.
- Reusable bugs remain in the Vault-wide `bugs-solved/` catalog because their
  lessons apply across repositories.

## Risks

- Rebinding the wrong Vault Home would attach another project's memory to this
  repository.
- Blind rewrites could destroy human-written historical notes or wikilinks.
- Duplicate logs would increase retrieval noise and token cost.
- A partial migration could leave both slugs active with conflicting UUIDs.

## Implementation

1. Validate the configured Vault, clean Ratchetry Git state, committed project
   UUID, legacy Home, target absence, and exact existing-note inventory.
2. Create a private timestamped backup outside the Vault before any mutation.
3. Move the legacy project directory to `projects/ratchery`, update only its
   identity/frontmatter and managed metadata, and retain historical prose.
4. Rename legacy session-log filenames and their project metadata without
   changing the factual historical narrative.
5. Add four phase logs, five repository ADRs with five concise linked Vault
   decision notes, and four new reusable bug notes; preserve the two existing
   relevant bug notes.
6. Copy the ignored local state into the new repository, refresh the Vault
   index, and verify memory status, links, uniqueness, file modes, Git diff,
   and note counts.

## Acceptance criteria

- `ratchery memory status --path . --json` reports no error and resolves one
  unique `projects/ratchery/Home.md` with the committed project UUID.
- All five historical logs and four new phase logs are discoverable under the
  Ratchetry project without duplicated content.
- Five accepted ADRs exist in the repository and each has one concise Vault
  navigation note rather than a copied ADR body.
- Six reusable project bugs are present in total: the two existing notes plus
  four new non-obvious, recurrence-worthy lessons.
- No raw conversation, secret-shaped value, absolute personal path, or local
  state file enters the Git inventory.
- The legacy tree is backed up before mutation and no unrelated Vault content
  changes.

## Validation

- `ratchery memory status --path . --json`
- `ratchery vault-search ratchery -n 20`
- `ratchery vault-doctor`
- `ratchery vault-refresh`
- `python3 scripts/verify-doc-links.py`
- `python3 scripts/verify-manifest.py` after regenerating the manifest
- `git diff --check`
- Focused inventory/hash comparison between backup and migrated legacy notes.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
