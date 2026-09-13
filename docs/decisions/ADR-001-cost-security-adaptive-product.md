# ADR-001: Make cost and security the product pillars

- Status: accepted
- Date: 2026-09-07

## Context

The project began as a broad collection of agent instructions, Skills, hooks,
templates, and memory conventions. A collection alone does not explain why a
component should be active, how much context it costs, or which security
boundary it strengthens. The product needed a stable definition that remains
useful across Claude Code, Codex, and different technology stacks.

## Options considered

- Market the project primarily as a T0-T3 risk classifier.
- Ship the largest possible catalog of agent tooling.
- Define cost efficiency and security as the product pillars, with adaptive
  tiering as the control mechanism.

## Decision

Ratchetry is a security-first, cost-aware operating layer for AI-assisted
development. The T0-T3 classifier, risk ratchet, project profile, and task
policy adapt the amount of process and capability to the real project. They
serve the two product pillars; they are not the entire product identity.

## Rationale

This framing matches the concrete implementation: sandbox and permissions are
the primary security boundary; deterministic hooks add defense in depth;
progressive disclosure, bounded retrieval, optional tools, budgets, and
benchmarks constrain cost. It also prevents a small repository from paying the
same process and context tax as a regulated or high-impact system.

## Trade-offs

- The product must measure efficiency rather than promise universal savings.
- Tiering needs explicit human risk facts and cannot infer business impact
  perfectly from files.
- Some useful capabilities remain available but inactive by default.

## Consequences

- Documentation and defaults must justify both security surface and ongoing
  token/maintenance cost.
- The risk ratchet never silently lowers an already recorded tier.
- New tools require evidence that their marginal value exceeds overlap and
  supply-chain cost.

## Reversal conditions

Reconsider only if measured use shows that one pillar consistently conflicts
with task success or that adaptive activation cannot remain deterministic and
understandable.
