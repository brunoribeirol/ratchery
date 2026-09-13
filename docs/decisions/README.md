# Architecture decisions

These records explain the durable decisions that shape Ratchetry. Code, tests,
manifests, and current repository documentation remain authoritative for
behavior; an ADR records why an accepted constraint exists and when to revisit
it.

- [ADR-001: Make cost and security the product pillars](ADR-001-cost-security-adaptive-product.md)
- [ADR-002: Gate optional tools on local evidence](ADR-002-evidence-gated-optional-tools.md)
- [ADR-003: Keep durable memory explicit and provider-neutral](ADR-003-explicit-provider-neutral-memory.md)
- [ADR-004: Rebrand without breaking persisted ownership markers](ADR-004-compatibility-safe-ratchery-rebrand.md)
- [ADR-005: Stage privately and publish provenance-backed releases](ADR-005-private-staging-and-release-provenance.md)

Use [ADR_TEMPLATE.md](ADR_TEMPLATE.md) for a new durable decision. Superseded
records stay in this directory with their status and replacement link updated;
do not silently rewrite their original rationale.
