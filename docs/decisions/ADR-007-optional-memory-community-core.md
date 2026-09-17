# ADR-007: Keep memory first-class but optional to the community core

- Status: accepted
- Date: 2026-09-16
- Related spec: [Community-first core mode](../specs/community-first-core-mode.md)

## Context

Ratchetry's source installer and package-manager setup required an existing Obsidian
Vault even though the security policy, adaptive tiering, context controls, agents, Skills,
project lifecycle, and diagnostics can operate without one. `cfg()` already allowed a
null `vault_path`, and project initialization already skipped Vault materialization when
no path was configured. The mandatory flag therefore coupled onboarding to an optional
backend and delayed the first useful result.

## Options considered

- Keep Obsidian mandatory and explain it more prominently.
- Remove durable memory from the product.
- Make the core independently installable while retaining Obsidian as the recommended,
  explicit durable-memory enhancement.
- Adopt an automatic third-party memory daemon as the default instead.

## Decision

The community default is a local, dependency-free core that can be installed without a
Vault. Obsidian memory remains first-class and supported, but opt-in. A fresh omission
selects core-only mode; later omission preserves the existing selection, while
`--no-vault` explicitly disables memory without deleting notes. Absence is a healthy
configuration; an explicitly configured but unavailable Vault remains an error. Memory-
only commands must explain how to configure the feature and fail without a traceback.

## Rationale

The decision shortens time to value without weakening the security or cost pillars. It
also makes the trust boundary honest: users who want durable memory explicitly select a
storage location and accept its lifecycle. Automatic-capture systems introduce daemons,
hooks, retention questions, and additional data surfaces that are not justified for every
user.

## Trade-offs

- Users in core mode do not receive cross-session curated memory or handoff features.
- Documentation and tests must cover both core-only and core-plus-memory paths.
- Some existing commands need explicit unconfigured-state handling.

## Consequences

- `--vault` is optional during installation and setup; `--no-vault` is the explicit
  disable operation and flag omission is upgrade-safe.
- `vault_path: null` is a supported persistent configuration.
- Product messaging leads with safe/cost-aware repository setup; memory is presented as
  an optional workflow rather than an installation prerequisite.
- New memory backends remain mutually exclusive experiments subject to ADR-002's evidence
  gate; they are not stacked into the default.

## Reversal conditions

Reconsider if measured support burden shows that core-only operation cannot remain safe
and coherent, or if a memory backend can provide equivalent explicit consent, local
control, bounded context, interoperability, and negligible default operational surface.
