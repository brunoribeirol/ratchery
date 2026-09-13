# Delta Spec: Provider-neutral memory handoff

Mode: **openspec-light** (T1/T2 default). This document describes only the
memory delta; existing Vault search, session logs, project lifecycle, and agent
configuration remain unchanged unless stated below.

## Why

The curated Vault preserves decisions across sessions, but it has no canonical
machine-readable baton for one agent client to hand unfinished work to another.
Copying a transcript wastes context and can persist sensitive material. The
setup needs a small explicit handoff that is independent of model/provider and
retains enough provenance to detect stale context.

## What changes

- Add a versioned, bounded JSON handoff schema containing objective, completed
  work, changed paths, checks, open risks, and the next action.
- Derive project UUID, creation time, Git commit, and dirty state at write time.
- Store at most one pending handoff in the matching project directory of the
  configured Vault, outside the repository and outside QMD's Markdown index.
- Resolve identity only from one unique frontmatter field, reject blocking
  special files, and serialize the complete mutation with a per-project lock.
- Add read-only backend/status commands and explicit handoff write/show/clear
  commands. Clear previews by default; replacement and deletion are backed up.
- Teach `workspace-save` and `workspace-resume` to use the protocol only when a
  real cross-session/client continuation exists.
- Expose `ai-memory` as an experimental backend candidate with a plan-only
  security baseline; do not configure or invoke it.

## Affected contracts

- CLI: `ratchery memory backends|status|plan` and
  `ratchery memory handoff write|show|clear` (renamed to `ratchery`
  during the separate rebrand).
- Handoff storage: `projects/<vault-slug>/Handoff.json` in the configured Vault.
- Handoff schema: `schema_version = 1`; caller-owned fields are strictly
  enumerated and bounded; provenance fields are CLI-owned.
- Exit status: `0` success, `1` invalid/missing state or invalid input, `2`
  refused replacement or `argparse` usage error.

## Out of scope

- Automatic lifecycle capture or context injection.
- Raw transcript, prompt, response, hidden reasoning, or tool-output storage.
- Remote memory servers, authentication, embeddings, or LLM consolidation.
- Direct Kiro/Gemini/OpenCode configuration.
- Greenlight task queues, GitHub automation, or agent orchestration.

## Tasks

- [x] Implement schema validation, secret screening, and compact rendering.
- [x] Implement identity-bound, symlink-safe Vault storage and CLI dispatch.
- [x] Update Skills, templates, docs, changelog, and roadmap.
- [x] Add positive and adversarial unit/integration coverage.
- [x] Regenerate the manifest and run the full validation/release smoke gates.

## Validation

Validation completed against a clean temporary checkout of the exact intended
release inventory: 35 focused memory tests and 306 total unit tests passed,
along with Python compilation, shell syntax, Ruff, links across 164 Markdown
files, the 267-file manifest, all 15 GitHub Action pins, the integration suite,
and `make release-smoke` against the built archive. Independent correctness and
security reviews found filesystem, concurrency, provenance, and display-spoofing
defects; each accepted finding was fixed and given regression coverage. The
final security re-review reported no blocking finding.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
