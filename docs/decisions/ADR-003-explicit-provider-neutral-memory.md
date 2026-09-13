# ADR-003: Keep durable memory explicit and provider-neutral

- Status: accepted
- Date: 2026-09-12

## Context

Automatic conversation capture can improve continuity but also persists raw
prompts, secrets, irrelevant output, and provider-specific state. Injecting all
memories into later sessions simply replaces repository-reading cost with
memory-context cost. Claude Code and Codex also need to continue the same work
without one provider owning the project history.

## Options considered

- Automatically save every session or transcript.
- Adopt a third-party automatic memory daemon as a core dependency.
- Use curated Markdown memory plus one bounded, machine-readable handoff at
  explicit continuation boundaries.

## Decision

Repository code and committed documentation remain authoritative. Obsidian is
the default curated backend for project Homes, session summaries, decisions,
bugs, commands, and references. `workspace-save` is the explicit persistence
boundary. A single provider-neutral `Handoff.json` may carry bounded unfinished
state between clients; automatic lifecycle capture remains disabled.

## Rationale

The design preserves continuity without storing raw conversations or loading a
memory service and its schemas in every session. UUID-bound project identity,
progressive disclosure, strict input limits, private permissions, locks,
no-follow filesystem operations, and backups provide an inspectable local
boundary.

## Trade-offs

- Meaningful sessions can be missed if an explicit save is not performed.
- Curated summaries require judgment and discipline.
- A handoff source label is self-declared, not an identity attestation.

## Consequences

- Session logs contain outcomes, evidence, risks, and next steps, never raw
  prompts or transcripts.
- Only one handoff is pending; replacement and clearing are explicit and
  backed up.
- Optional automatic-memory products remain experiments until their measured
  value and threat model justify the extra surface.

## Reversal conditions

Reconsider automatic capture only if it can enforce equivalent minimization,
local control, interoperability, and measurable context savings without
turning session end into an unreliable persistence boundary.
