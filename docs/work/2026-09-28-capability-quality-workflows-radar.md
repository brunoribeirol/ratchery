# Work Plan: Capability quality, workflows, and technology radar

## Objective

Make Ratchetry's existing agents and Skills discoverable, verifiable, and useful through
goal-oriented workflows. Add a versioned capability contract, deterministic offline
behavior evals, an approval-gated security-hardening workflow, and an offline technology
radar without adding required dependencies or silently activating tools.

## Non-goals

- Do not resume or modify the OpenSSF Best Practices submission.
- Do not import third-party Skills, enable MCP servers, access the network, or install tools.
- Do not capture raw chats, add a daemon, orchestrate tmux sessions, or auto-commit fixes.
- Do not change tier classification, existing agent activation, or public setup defaults.

## Evidence and assumptions

- T1 requires an `openspec-light` delta spec and smoke tests for changed behavior.
- `assets/global/skills/registry.json` is the existing activation/install source of truth and
  must remain backward compatible with `adaptive_engine` and global installation.
- Claude and Codex definitions under `assets/project` are the shipped client contracts.
- All new selection and eval behavior must be deterministic, local, and zero-LLM.

## Affected contracts and files

- CLI: `skills`, expanded `agents`, `workflows`, and `radar` command families.
- Capability registry: `assets/global/skills/registry.json` schema v2 metadata.
- New declarative workflow, eval, and radar registries under `assets/global/`.
- New `security-hardening` global Skill.
- Isolated implementation module plus a thin CLI adapter in `lib/agent_workspace.py`.
- Focused unit and CLI contract tests, manifest, README, and current-state documentation.

## Risks

- Registry enrichment could break legacy activation/install consumers.
- Heuristic routing could overclaim semantic understanding; output must be described as
  deterministic recommendations, not model behavior.
- Security-hardening automation could accidentally imply permission to edit; the workflow
  must stop at an explicit human approval gate.
- Radar dates can become stale; validation must detect overdue entries offline.
- Packaging omissions could make source-tree tests pass while release artifacts fail.

## Workstreams and ownership

One integration owner handles all workstreams sequentially:

1. Define registries and validation contracts.
2. Implement deterministic recommendations and behavior evals.
3. Add workflow/security-hardening and radar CLI surfaces.
4. Add focused tests, documentation, manifest, and release smoke validation.

## Acceptance criteria

1. Existing activation consumers still read `agents` and `skills.available`; existing
   adaptive-engine tests pass unchanged.
2. `ratchery skills list/show/validate/eval` reports resolved metadata, content digests,
   client coverage, routing signals, and deterministic fixture results.
3. `ratchery agents list/show/validate` verifies both Claude and Codex definitions and
   reports their permission ceilings without changing project state.
4. Positive/negative fixtures exercise actual deterministic routing and fail when an
   expected capability is absent or a forbidden one is selected.
5. `ratchery workflows list/show/recommend --goal ...` maps user outcomes to existing
   capabilities without enabling or invoking them.
6. The security-hardening workflow emits structured finding requirements and contains an
   explicit approval gate before fixes, dependency changes, writes, or commits.
7. `ratchery radar status/show/stale` is offline, validates provenance/review dates, and
   returns a non-zero result for malformed data while treating overdue entries as reportable
   state rather than an execution failure.
8. Targeted tests, the full unit/integration suite, manifest verification, link verification,
   and release smoke pass; any unavailable optional check is recorded.

## Validation plan

Run cheapest checks first:

1. `python3 -m unittest tests.test_capability_system`
2. `ruff check --no-cache lib/capability_system.py tests/test_capability_system.py`
3. `python3 -m py_compile lib/*.py`
4. `python3 scripts/gen-manifest.py` then `python3 scripts/verify-manifest.py`
5. `make test`
6. `python3 scripts/verify-doc-links.py`
7. `make release-smoke`

Stop external work entirely: no hosted canary, MCP call, third-party install, network query,
push, release, or OpenSSF mutation is part of this plan.

## Handoff

Implemented in the local candidate. A temporary Git snapshot containing the exact candidate
passed 359 Python tests, Bash integration, Ruff, Python/Bash syntax, the 301-file manifest,
20 pinned-Action checks, 189 Markdown-link checks, and installed-archive release smoke.
The managed sandbox cannot write the real repository's `.git/index`, so the real worktree
still requires the maintainer's normal staging/PR transaction before source-tree manifest
verification can see the nine new files as tracked. No commit, push, release, network query,
third-party installation, MCP activation, or OpenSSF mutation was performed.
