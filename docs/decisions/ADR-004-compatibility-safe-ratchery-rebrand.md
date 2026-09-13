# ADR-004: Rebrand without breaking persisted ownership markers

- Status: accepted
- Date: 2026-09-12

## Context

The public product needed one distinctive identity and a clean repository,
while private-development installations already contained runtime/config paths,
an executable name, managed blocks, MCP ownership markers, and Skill sentinels.
A global search-and-replace would make existing managed content undiscoverable
or could overwrite user-owned files.

## Options considered

- Break all compatibility and require a fresh install.
- Rename every internal string, including persisted merge-format markers.
- Make `ratchery` canonical while preserving a bounded 1.x compatibility and
  migration path for recognized legacy state.

## Decision

The product, repository, release artifacts, runtime/config/state namespaces,
templates, and primary command use Ratchetry / `ratchery`. The former command
is a temporary 1.x alias backed by the same runtime. Recognized regular legacy
state is backed up and migrated; symlinked inputs are rejected. Persisted
`agent-workspace:v8` and `agent-workspace:mcp` markers remain frozen because
they identify merge ownership and format, not the software version.

## Rationale

Changing the marker without dual-format migration would cause `refresh` to
leave stale blocks behind or create duplicates. One runtime plus a narrow alias
avoids a permanent second product identity while preserving a safe upgrade.

## Trade-offs

- Some internal compatibility strings intentionally do not match the public
  brand.
- The alias and migration tests must be maintained throughout 1.x.
- Removing the alias later requires an announced major-version decision.

## Consequences

- Public documentation explains the frozen marker once instead of treating it
  as stale branding.
- New managed Skill sentinels use Ratchetry, while the old sentinel is accepted
  only as an upgrade input.
- User-owned collisions are rejected rather than overwritten.

## Reversal conditions

Introduce a new marker only with an explicit transition that recognizes both
formats, proves idempotent upgrades, and documents eventual retirement.
