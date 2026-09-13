# Workflow

## Trivial task
Inspect the target and nearest test, make a focused change, run targeted validation, and report.

## Standard task
Trace contracts and callers, modify the smallest coherent set, run targeted checks and the affected suite.

## Complex or high-risk task
Use the `work-plan` Skill, create a record under `docs/work/`, use read-only subagents for noisy investigation, validate in layers, and request focused review.

## Session boundaries
Continue a session for the same objective. When another client or later session
will continue unfinished work, use `workspace-save` to create one reviewed
provider-neutral handoff and have `workspace-resume` verify its target and Git
provenance before use. The handoff is a bounded baton, never a transcript or
automatic capture feed. Start a fresh session for an unrelated objective. Use
compaction only after durable state is updated.
