# Delta Spec: Ratchetry rebrand and private launch

Mode: **openspec-light** (T1/T2 default). This document describes only the
identity, compatibility, and publication delta. The risk classifier, security
boundaries, tool policy, memory model, and release evidence remain unchanged
unless explicitly stated below.

## Why

The implementation is locally release-candidate quality, but its temporary
pre-public identity, generic `agent-workspace` command, old repository URLs, and
uncommitted development history are not the intended public product. Ratchetry
needs one coherent identity and a private clean-history repository where hosted
security and release gates can be exercised before public launch.

## What changes

- Rename the user-facing product, repository, release artifact, documentation,
  GitHub metadata, and primary executable to **Ratchetry** / `ratchery`.
- Install new runtime, config, state, and template namespaces under `ratchery`.
- Preserve `agent-workspace` as a documented compatibility command during the
  first major release and migrate recognized legacy local state without
  overwriting unrelated/user-owned data.
- Keep the complete `agent-workspace:v8` managed-block marker frozen. It is a
  persisted merge-format identifier, not product branding; changing it would
  make existing managed blocks undiscoverable.
- Create `brunoribeirol/ratchery` as a private GitHub repository, import only
  the validated release inventory with clean history, and organize it into
  reviewable thematic commits.
- Configure repository metadata, Actions/security settings, branch/tag
  Rulesets, and hosted validation before any visibility change or release.
- Use `1.0.0-rc.1` for the first hosted prerelease candidate; publish stable
  `1.0.0` only after private-repository gates and artifact attestations pass.

## Affected contracts

- Primary CLI: `ratchery`; compatibility alias: `agent-workspace`.
- Runtime/config/state namespaces: `ratchery`, with bounded legacy migration
  from recognized `agent-workspace` locations.
- Source archives and SBOM package: `ratchery-X.Y.Z`.
- Repository identity and links: `github.com/brunoribeirol/ratchery`.
- Version transition: internal `1.0.1` development line to public
  `1.0.0-rc.1`, then `1.0.0` after release verification.
- Persisted managed-block markers remain exactly `agent-workspace:v8:*`.

## Out of scope

- Making the repository public in this phase.
- Creating or publishing a Homebrew tap before the first verified release.
- Adding dependencies, MCPs, automatic memory, telemetry, or hosted services.
- Rewriting existing user repositories solely to replace the frozen marker.
- Claiming hosted gates passed before they run in the destination repository.

## Tasks

- [x] Rebrand runtime, installer, release artifacts, docs, templates, and CI.
- [x] Implement and test the compatibility command and safe local migration.
- [x] Regenerate the manifest and pass local unit/integration/release gates.
- [x] Perform focused correctness and security review of the migration delta.
- [ ] Create the private GitHub repository and clean thematic commit history.
- [ ] Configure hosted repository settings, Rulesets, CI, and security features.
- [ ] Cut and verify `v1.0.0-rc.1` without changing repository visibility.

## Validation

- `python3 -m unittest discover -s tests -p 'test_*.py'`
- `python3 -m py_compile lib/*.py scripts/*.py tests/*.py`
- `bash -n bin/ratchery bin/agent-workspace install.sh tests/run-tests.sh`
- `ruff check lib/ scripts/ tests/ bin/`
- `python3 scripts/verify-manifest.py`
- `python3 scripts/verify-action-pins.py`
- `python3 scripts/verify-doc-links.py`
- `make test`
- `make release-smoke`
- Clean install, legacy upgrade, rollback, command-alias, archive/SBOM identity,
  and forbidden-stale-brand tests.
- Hosted matrix, Scorecard, attestation, and signed-tag verification in the
  private destination repository.

Local evidence on 2026-09-12: 311 unit tests, the isolated installer/integration
suite (including a rejected symlinked legacy runtime), Ruff, Python and shell
syntax, manifest integrity, 15 immutable GitHub Action pins, 163 Markdown files,
and release archive/install smoke all passed from a clean candidate checkout.
The hosted items remain deliberately unclaimed until the destination repository
exists and its checks have run.

## Status

- [ ] Proposed
- [x] In progress
- [ ] Implemented
- [ ] Archived (link the merged PR/commit)
