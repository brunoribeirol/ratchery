# Delta Spec: Capability quality, workflows, and technology radar

Mode: **openspec-light** (T1/T2 default). This document describes only the change.

## Why

Ratchetry already ships a curated agent/Skill/tool foundation, but its registry describes
mostly installation and activation. Users must understand internal components to choose a
workflow, while tests prove file presence more strongly than routing behavior. The project
also needs a durable, offline record of external technologies being assessed so adoption is
driven by evidence instead of capability count or popularity.

## What changes

- Enrich the existing registry with versioned capability metadata while preserving current
  `agents` and `skills.available` consumers.
- Add read-only CLI discovery and validation for Skills and agents, including computed
  content digests and Claude/Codex parity.
- Add deterministic, zero-LLM positive/negative routing evals.
- Add goal-oriented workflow discovery and recommendation.
- Add an approval-gated security-hardening Skill/workflow with structured findings and an
  explicit review-fix-retest-review sequence.
- Add an offline technology radar with provenance, adoption state, review date, and
  recheck date.

## Affected contracts

- `assets/global/skills/registry.json` advances to schema 2 while retaining legacy keys.
- New versioned JSON contracts: capability evals, workflows, and technology radar.
- New CLI families: `skills`, extended `agents`, `workflows`, and `radar`.
- CLI validation commands return zero only when structural and behavioral contracts pass.
- Recommendation commands are advisory and never install, enable, invoke, or mutate.

## Out of scope

- Online radar refresh, GitHub scheduled workflows, third-party Skill import, MCP Registry
  integration, plugin export, multi-machine memory, and worktree/tmux orchestration.
- LLM-as-judge evals or paid client calls in default tests.
- Automatic fixes, commits, dependency installation, or changes before human approval.

## Tasks

- [x] Define compatible capability metadata and validation.
- [x] Add deterministic behavior fixtures and runner.
- [x] Add workflow registry/recommendation and security-hardening contract.
- [x] Add offline technology radar.
- [x] Add CLI adapters, focused tests, documentation, and packaging inventory.
- [x] Run proportional validation and record results.

## Validation

`python3 -m unittest tests.test_capability_system`, targeted Ruff/compile checks,
`make test`, manifest and documentation verification, and `make release-smoke`.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
