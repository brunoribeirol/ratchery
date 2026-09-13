# Delta Spec: Plan-aware private staging

Mode: **openspec-light** (T1/T2 default).

## Why

The current release plan assumes that a private `v1.0.0-rc.1` can exercise
GitHub artifact attestations, Rulesets, and SARIF upload. GitHub availability is
plan-dependent: private artifact attestations require Enterprise Cloud, private
Rulesets require at least Pro/Team/Enterprise Cloud, and private SARIF upload
requires GitHub Code Security on an eligible organization repository. A tag on
an unsupported private repository would therefore start a release workflow that
cannot satisfy its provenance gate.

## What changes

- Scorecard analysis runs in a read-only private job and retains its SARIF as a
  short-lived private workflow artifact. Public repositories use a separate job
  with only the OIDC and `security-events` scopes required to publish Scorecard
  results and upload SARIF.
- Release instructions must inspect repository visibility and account/feature
  availability before creating a tag.
- If private attestations are unavailable, private staging stops at a validated,
  signed, CI-green commit. The signed prerelease tag is created only after a
  separately approved public visibility change and immediate hosted-control
  verification.
- Unsupported private security features are recorded as deferred gates, not
  falsely reported as configured.

## Affected contracts

- `.github/workflows/scorecard.yml` job permissions and visibility routing.
- `docs/PUBLISHING.md` maintainer sequence and GitHub settings checklist.
- ADR-006 records the durable release-gating decision and supersedes the
  private-prerelease ordering in ADR-005.
- Git-backed unit fixtures explicitly opt out of inherited commit signing; this
  affects tests only, never maintainer or release signatures.
- No CLI, installed runtime, release artifact, or manifest schema changes.

## Out of scope

- This change does not make the repository public, push a tag, publish a
  release, buy or change a GitHub plan, or weaken the attestation requirement.
- It does not silently fall back to an unattested GitHub Release.

## Tasks

- [x] Record the availability constraints and safe sequencing.
- [x] Isolate private and public Scorecard privileges.
- [x] Add workflow contract coverage.
- [x] Reconcile publishing documentation and changelog.
- [x] Run full repository and release validation.

## Validation

```bash
python3 tests/test_scorecard_workflow_contract.py
python3 scripts/verify-action-pins.py
python3 scripts/gen-manifest.py
make test
make release-smoke
git diff --check
```

Hosted validation must additionally inspect actual repository visibility and
available features, then run CI, private Scorecard analysis, and the client
canary before any visibility change or tag.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
