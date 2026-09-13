# Workflow

## Trivial task
Inspect the target and nearest test, make a focused change, run targeted validation, and report.

## Standard task
Trace contracts and callers, modify the smallest coherent set, run targeted checks and the affected suite.

## Complex or high-risk task
Use the `work-plan` Skill, create a record under `docs/work/`, use read-only subagents for noisy investigation, validate in layers, and request focused review.

## Session boundaries
Continue a session for the same objective. Start a fresh session for an unrelated objective. Use compaction only after durable state is updated.
