# Work Plan: Close Homebrew distribution and hand off OpenSSF submission

## Objective

Publish accurate Homebrew installation guidance backed by the verified public
tap, update durable project state, and leave the OpenSSF Best Practices
application at the explicit maintainer-attestation boundary.

## Non-goals

- Do not change runtime behavior, the `v1.1.0` tag, or release assets.
- Do not claim a Best Practices level or add its badge before the live service
  reports that level.
- Do not automate answers that depend on maintainer knowledge or response
  history.
- Do not add bottles, another package manager, or a new dependency.

## Evidence and assumptions

- `brunoribeirol/homebrew-tap` PR #2 merged the reviewed Formula as commit
  `837424e7ed9133ce854a83e998b4c07b51180216`.
- The Formula passed `brew audit --strict --online --new`, `brew style`, source
  install, setup, doctor, and version checks locally.
- The exact PR and protected merge passed the tap's macOS 26 and Ubuntu jobs.
- A fresh public `brew install brunoribeirol/tap/ratchery` was followed by
  `brew test` and an explicit installed-command version check.
- The stable `v1.1.0` release, checksums, SPDX SBOM, and attestations remain the
  immutable Formula input.

## Affected contracts

- README's shortest supported installation path.
- `docs/INSTALLATION.md` package-manager install, setup, upgrade, and uninstall
  boundary.
- `docs/PUBLISHING.md` status of the v1.1.0 Homebrew gate.
- `docs/OPENSSF.md` public evidence and remaining human-attestation boundary.
- `CHANGELOG.md` and `MANIFEST.json`; the ignored local
  `docs/CURRENT_STATE.md` is refreshed only after the protected merge.

## Risks

- Advertising a command before it is publicly installable.
- Making Homebrew setup look automatic and thereby hiding the explicit user
  configuration boundary.
- Treating an automated Scorecard or repository evidence as a human Best
  Practices attestation.
- Leaking a maintainer-local evidence path into public documentation.

## Acceptance criteria and evidence paths

1. README and Installation show the exact public Formula and require explicit
   `ratchery setup`; inspect both files and run Markdown-link verification.
2. Publishing records the public tap repository, PR, merge commit, and the
   macOS/Linux validation boundary without local paths; inspect the section and
   search for private filesystem prefixes.
3. OpenSSF remains unclaimed while its completed machine-verifiable steps and
   outstanding maintainer steps are distinguishable; inspect `docs/OPENSSF.md`.
4. The release inventory matches every tracked file; regenerate and verify
   `MANIFEST.json`.
5. The protected PR passes the six CI jobs and CodeQL on the exact candidate
   and merge commits.

## Verification budget and stop conditions

- First: diff check, targeted text assertions, manifest, Action pins, and doc
  links.
- Then: the normal local suite and release smoke because the manifest and
  public installation contract change.
- Finally: protected PR checks. Stop on any failed required check; do not merge
  or submit OpenSSF claims.

## Handoff

After merge, the maintainer signs in to `bestpractices.dev`, creates the
Ratchetry entry, and answers the live metal Passing and OSPS Baseline Level 1
questions literally. Add an application badge only in a later PR after the
service reports an earned level.
