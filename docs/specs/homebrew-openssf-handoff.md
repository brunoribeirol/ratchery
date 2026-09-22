# Delta Spec: Verified Homebrew documentation and OpenSSF handoff

Mode: **openspec-light** (T1/T2 default).

## Why

Ratchetry 1.1.0 is now installable from its public Homebrew tap, but current
documentation intentionally says the tap is not yet advertised. The OpenSSF
evidence map must also distinguish completed public release/distribution
evidence from questions only the maintainer can attest.

## What changes

- Make the verified Homebrew Formula the shortest installation path while
  keeping `ratchery setup` explicit and showing source installation as an
  alternative.
- Document Homebrew upgrade/uninstall behavior and persistent user state.
- Record the public tap PR, protected merge, cross-platform checks, and public
  installation test.
- Mark machine-verifiable OpenSSF prerequisites complete and keep the live
  application, human answers, and badge outstanding.
- Refresh project state, changelog, and release inventory.

## Affected contracts

- Public install command: `brew install brunoribeirol/tap/ratchery`.
- Post-install contract: `ratchery setup` remains explicit and idempotent.
- OpenSSF badge policy: no Best Practices badge before an earned live result.

## Out of scope

- Runtime, Formula, stable release, GitHub settings, and release artifact
  changes.
- Automated OpenSSF self-certification or guessed application identifiers.

## Tasks

- [x] Add verified Homebrew onboarding and lifecycle documentation.
- [x] Record public tap validation and current project state.
- [x] Update the OpenSSF evidence/submission boundary.
- [x] Regenerate and verify the manifest.
- [ ] Merge through the protected documentation PR.
- [ ] Complete the human OpenSSF application.

## Validation

Run `git diff --check`, manifest verification, Action-pin verification,
Markdown-link verification, the normal test suite, and release smoke. Require
all protected hosted checks before merge.

## Status

- [x] Proposed
- [x] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
