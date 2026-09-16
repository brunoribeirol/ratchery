# Delta Spec: Stable, Homebrew, and OpenSSF preparation

Mode: **openspec-light** (T1/T2 default).

## Why

The public `v1.0.0-rc.1` release proved the runtime, protected-release, SBOM,
provenance, and Scorecard paths, but the stable release still lacks a single
supported post-package-manager setup command, a blocking reviewed ShellCheck
contract, accurate immutable Action documentation, and a public evidence map
for an honest OpenSSF Best Practices application.

## What changes

- Add an idempotent `ratchery setup` command that configures an existing Vault,
  projects root, global guidance, and optional-tool policy after a package
  manager has installed the runtime. The command supports a no-write dry run
  and explicit non-interactive confirmation.
- Make ShellCheck blocking on the Linux CI legs while retaining the existing
  six required matrix contexts.
- Add a least-privilege Python CodeQL workflow so a real source static-analysis
  result exists before stable publication rather than treating lint or
  Scorecard repository-health checks as SAST.
- Display the already-published OpenSSF Scorecard badge, document the exact
  immutable `@v1.0.0` reusable-Action reference, and add an evidence inventory
  for a future Best Practices application without claiming that badge early.
- Promote the runtime metadata and release documentation from the RC to
  `1.0.0`; regenerate the release manifest after every intended file is staged.

## Affected contracts

- CLI: new `ratchery setup --vault PATH [--projects-root PATH]
  [--project-layout flat|categorized] [--vault-migration safe|preserve]
  [--external-tools none|recommended] [--dry-run] [--yes]` command.
- User state: the existing Ratchetry config, managed global guidance/Skills,
  projects workspace, and Vault kit; no new config keys or formats.
- CI: ShellCheck failures on Linux become merge-blocking inside the existing
  required `test (ubuntu-latest, pyX)` checks.
- Security analysis: CodeQL runs on pull requests, `main` pushes, and explicit
  dispatch with source-read/SARIF-write permissions only.
- Release: runtime/version metadata becomes `1.0.0`; the RC tag remains
  immutable and unchanged.
- Public docs: Scorecard and Best Practices are explicitly treated as distinct
  programs; only verified status is displayed.

## Out of scope

- Creating or pushing the `v1.0.0` tag or GitHub Release.
- Creating the Homebrew tap repository or publishing a Formula.
- Submitting answers to the OpenSSF Best Practices questionnaire or displaying
  its badge before the project reaches Passing.
- Installing optional external tools automatically, changing managed-block
  marker `v8`, or adding runtime dependencies.

## Tasks

- [x] Implement and test `ratchery setup`, including dry-run, validation,
  confirmation, idempotency, and isolated HOME/XDG behavior.
- [x] Make Linux ShellCheck blocking and add a workflow contract test.
- [x] Add and locally validate least-privilege Python CodeQL analysis. Hosted
  analysis remains a protected-PR gate.
- [x] Correct Scorecard, reusable-Action, installation, publishing, security,
  and OpenSSF evidence documentation.
- [x] Bump stable version/changelog metadata. Regenerate `MANIFEST.json` only
  after the complete reviewed file set is staged for its signed commit.
- [ ] Merge the signed protected PR after its six CI jobs and CodeQL pass on
  the exact commit. Local targeted/full gates, release reproducibility, and
  clean consumer setup/doctor smoke are complete.

## Validation

```text
python3 tests/test_setup_command.py
python3 tests/test_ci_workflow_contract.py
python3 tests/test_scorecard_workflow_contract.py
python3 tests/test_release_workflow_contract.py
python3 scripts/smoke-test-release.py <built-release-archive>
ruff check lib/ scripts/ tests/ bin/
make test
make release-smoke
python3 scripts/verify-manifest.py
python3 scripts/verify-action-pins.py
python3 scripts/verify-doc-links.py
```

The protected PR must also show all six required CI matrix jobs passing; those
hosted Ubuntu jobs are the authoritative ShellCheck execution environment.

## Status

- [ ] Proposed
- [x] In progress
- [ ] Implemented
- [ ] Archived (link the merged PR/commit)
