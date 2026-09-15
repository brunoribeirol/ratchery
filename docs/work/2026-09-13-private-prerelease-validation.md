# Work Plan: Private prerelease validation

## Objective

Complete every safe and plan-supported gate while `brunoribeirol/ratchery`
remains private, leave evidence for deferred hosted controls, and reach a
well-defined ready-for-public state without publishing or tagging prematurely.

## Non-goals

- Do not change repository visibility.
- Do not create or push `v1.0.0-rc.1` when private attestations are unavailable.
- Do not publish stable `v1.0.0`, create a Homebrew tap, or install speculative
  optional tools.
- Do not claim unavailable GitHub features are enabled.

## Evidence and assumptions

- The clean repository exists privately at `brunoribeirol/ratchery`, with signed
  clean-history commits on `main` and provider-neutral durable memory restored.
- GitHub documents private artifact attestations as Enterprise Cloud-only;
  private Rulesets require Pro/Team/Enterprise Cloud; private SARIF upload needs
  GitHub Code Security on an eligible organization repository.
- The current execution sandbox cannot use the maintainer's Keychain/GPG state
  or reach GitHub, so authenticated hosted mutations and signed commits must run
  in the maintainer's normal Terminal through a fail-closed, inspectable driver.

## Affected contracts and files

- `.github/workflows/scorecard.yml`
- `tests/test_scorecard_workflow_contract.py`
- `docs/PUBLISHING.md`
- `docs/decisions/ADR-005-private-staging-and-release-provenance.md`
- `docs/decisions/ADR-006-plan-aware-public-prerelease.md`
- `docs/decisions/README.md`
- `docs/specs/plan-aware-private-staging.md`
- `CHANGELOG.md`, `MANIFEST.json`, and ignored `docs/CURRENT_STATE.md`
- Local installed runtime and configured Vault state
- GitHub repository metadata, Actions defaults, supported security features,
  hosted CI, client canary, public-only Scorecard deferral, and Rulesets where
  available

## Risks

- A premature tag can start a release workflow whose mandatory attestation job
  is unsupported and leave a misleading failed release event.
- Running the Scorecard Action privately would require GitHub Advanced Security
  plus broader repository reads; granting those solely for staging would add
  cost and permission surface without improving the published artifact.
- Enabling a Ruleset before the final preparation commit lands can lock the sole
  maintainer out of the intended direct push.
- Automated GitHub settings must fail closed on unexpected owner, repository,
  visibility, branch, origin, dirty worktree, signature, or account capability.
- Installing the candidate may touch managed home/Vault files; dry-run evidence
  and framework backups must precede mutation.
- A compatibility canary can itself create false failures by disabling a
  client's required installer step or by attempting to nest an OS sandbox in a
  hosted environment that forbids its namespace primitives.
- Interactive/connectivity diagnostics such as older `claude doctor` releases
  are not valid CI parsers; each real-client command must have closed stdin, a
  short timeout, and its own named step.

## Workstreams and ownership

1. Correct the workflow privilege boundary and add regression coverage.
2. Reconcile the spec, ADRs, publishing guide, changelog, and manifest.
3. Run local tests, release smoke, manifest/link/action-pin checks, and bounded
   security/dependency checks.
4. Through the maintainer-terminal boundary, create focused thematic commits,
   each signed and without co-author trailers, push them over HTTPS, validate
   hosted checks and supported controls, update the local installation, and
   preserve a private evidence record.
5. Stop at ready-for-public and require a separate explicit instruction before
   visibility change or tag creation.

## Acceptance criteria

- Scorecard has no runnable private job and is explicitly deferred until public
  launch.
- Public Scorecard publication exists in a visibility-gated job with only its
  documented scopes.
- Documentation never promises a private prerelease on a plan that cannot
  attest it.
- The final private `main` commit is GPG-signed, pushed over HTTPS, clean,
  manifest-valid, and green in CI plus the no-inference client canary.
- Repository metadata and Actions token defaults are verified; unsupported
  private settings are explicitly deferred.
- The installed `ratchery` command and Vault memory pass their diagnostics.
- No visibility change, tag, Release, or Homebrew publication occurs.
- The client canary generates its fixture in a read-only job, installs public
  clients in separate zero-permission/source-free jobs, and passes its
  preparation job plus all four minimum/current legs.

## Validation plan

Run the commands named in the linked delta spec, plus targeted secret/path
scans, dependency-example installation in a temporary environment when network
is available, GitHub workflow inspection, signed-commit verification, and
read-only postcondition checks.

The real-client remediation is specified in
[`client-canary-runtime-contract.md`](../specs/client-canary-runtime-contract.md).
Local evidence must include the generated fixture parsing under current
Claude/Codex and under an available Codex version older than the declared
floor. Hosted evidence remains mandatory for the exact minimum packages and
the Claude npm native installer.

## Handoff

When all private gates pass, record the exact commit and the plan-dependent
deferred controls. The next action is a separately approved public-launch
transaction: make public, immediately apply/verify public controls, run public
Scorecard, create the signed RC tag, and verify release assets and attestations.
