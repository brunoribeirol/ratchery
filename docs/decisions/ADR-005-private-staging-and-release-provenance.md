# ADR-005: Stage privately and publish provenance-backed releases

- Status: accepted
- Date: 2026-09-12

## Context

The original development repository contained private working history and
local state that should not become the public project's trust foundation. A
release archive built from a dirty checkout can also include untracked or
ignored data, while one privileged workflow job can execute tag-controlled
code with release credentials.

## Options considered

- Rename and expose the existing repository and history.
- Publish an archive built directly from the working directory.
- Import a reviewed inventory into a private clean-history repository, verify a
  prerelease there, and isolate build, attestation, and publication privileges.

## Decision

Ratchetry begins in a private clean-history repository with signed thematic
commits. The installer and release builder consume only a hash/size-verified
Git inventory. Releases contain a deterministic source archive, SPDX 2.3 SBOM,
manifest, and SHA-256 checksums. A read-only build job executes the tag; a
no-checkout OIDC job attests fixed outputs; a separate contents-write job
publishes them. Stable public release follows a verified private prerelease and
an explicit visibility decision.

## Rationale

This makes the shipped bytes auditable, excludes local state by construction,
and keeps privileged tokens away from untrusted tag code. Signed commits/tags,
Rulesets, immutable Action pins, artifact smoke tests, SBOM, and attestations
provide complementary evidence rather than one overclaimed badge.

## Trade-offs

- Clean import loses the old Git history from the public repository; meaningful
  changes remain summarized in the changelog and curated memory.
- Hosted settings and attestations require real GitHub validation and may vary
  by account plan.
- Release preparation has more gates than a simple archive upload.

## Consequences

- `docs/CURRENT_STATE.md` stays ignored/local and never enters the manifest.
- Public visibility, stable release, and Homebrew distribution are separate
  gates.
- A green workflow is not evidence that Rulesets or repository security
  settings are enabled; those settings require inspection.

## Reversal conditions

Simplify only if an alternative preserves exact inventory, least-privilege
execution, reproducibility, and verifiable provenance with less operational
cost.
