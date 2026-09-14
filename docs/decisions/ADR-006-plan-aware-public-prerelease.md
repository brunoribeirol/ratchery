# ADR-006: Gate the first prerelease on hosted feature availability

- Status: accepted
- Date: 2026-09-13
- Refines: [ADR-005](ADR-005-private-staging-and-release-provenance.md)
- Spec: [Plan-aware private staging](../specs/plan-aware-private-staging.md)

## Context

ADR-005 chose a clean private staging repository and a provenance-backed
release. Its original ordering expected a fully attested private prerelease
before changing visibility. GitHub Free, Pro, and Team expose artifact
attestations only for public repositories; private attestations require
Enterprise Cloud. Private Rulesets and SARIF upload have separate plan and
repository-owner constraints. Treating those capabilities as universal would
make the mandatory release job fail or encourage disabling provenance.

## Options considered

- Buy Enterprise Cloud solely to attest the private release candidate.
- Publish a private release candidate without attestations.
- Keep private staging tag-free when attestations are unavailable, then perform
  a separately approved public-launch transaction before creating the signed
  release-candidate tag.

## Decision

Private staging ends at a clean, signed, pushed commit with local validation,
hosted CI, the no-inference client canary, and all plan-supported repository
controls verified. Before any tag, the maintainer records actual visibility
and feature availability.

If private attestations are unavailable, Ratchetry does not create an
unattested or predictably failing private tag. A separate explicit approval is
required to make the repository public. Publicly available Rulesets and
security controls are then enabled and verified immediately, public Scorecard
is run, and only then is the signed `v1.0.0-rc.1` tag pushed. The release
workflow remains fail-closed: publication depends on successful provenance and
SBOM attestations.

Scorecard has one public visibility-gated job. Private staging deliberately
skips the Action: upstream supports private Action runs only with GitHub
Advanced Security and recommends additional read access to issues, pull
requests, and checks. The project does not buy that capability or broaden the
private workflow token merely to move a gate earlier. The public job receives
only the repository read, OIDC, and code-scanning write scopes needed for its
published result.

## Rationale

This preserves the security property that every published release is attested
without buying infrastructure that the project does not otherwise need. It
also prevents unsupported hosted features from being presented as completed
gates and keeps unnecessary workflow permissions and plan costs out of private
staging.

## Trade-offs

- On non-Enterprise plans, the full release path cannot be proven before the
  repository is public.
- Public launch becomes a short ordered transaction rather than one visibility
  toggle, and its public controls need immediate verification.
- Scorecard evidence is unavailable until the ordered public-launch
  transaction. CI, client compatibility, and local security gates remain the
  private checkpoint evidence.

## Consequences

- Repository visibility must remain a separate explicit user decision.
- A failed public attestation blocks the Release job and must be fixed rather
  than bypassed.
- Private-only feature gaps are recorded as deferred with their reason; they do
  not block the private ready-for-public checkpoint.
- The project does not need Enterprise Cloud merely to satisfy its own release
  process.

Revisit the Scorecard boundary separately if upstream adds private Action
support without GitHub Advanced Security and without materially broader token
permissions.

## Reversal conditions

Revisit the sequence if GitHub makes private attestations available on the
maintainer's plan, the repository moves to Enterprise Cloud, or another
maintained provenance system provides equivalent verification without adding
greater operational or supply-chain cost.
