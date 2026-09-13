# Work Plan: Cost and Security Baseline

## Objective

Make Ratchetry's cost-first promise measurable without adding a runtime
dependency, and make optional-tool decisions explicit enough that a user can
tell what is local, what may add context/network/supply-chain surface, and what
must remain experimental. Correct stale RTK/ccusage guidance and remove live
documentation facts inherited from the internal baseline when they no longer
earn their maintenance cost.

## Non-goals

- Do not auto-install, auto-enable, or silently update any external tool.
- Do not add an MCP server, package dependency, background daemon, automatic
  memory system, telemetry collector, or network-enabled scanner.
- Do not claim vendor-reported token savings as Ratchetry results.
- Do not automate paid agent runs; the user owns the prompts and spend.
- Do not rename the product or the `ratchery` command in this change.
- Do not rename the frozen `agent-workspace:v8` merge-format markers.

## Evidence and assumptions

- The current `usage` command is only `ccusage daily`; it cannot select a
  source, time range, JSON output, or offline operation.
- `tools.lock.json` records versions and prose policies, but not activation
  mode, tool family, command probe, network behavior, or benchmark requirement.
- The RTK guidance currently tells users to run the Claude initialization for
  both clients. Current upstream behavior uses a Claude `PreToolUse` hook for
  `rtk init -g`, while Codex uses `rtk init -g --codex` and instruction files.
- Current ccusage supports local aggregate reports across multiple coding
  clients, but an older installed release may still expose Claude-only command
  grammar. Ratchetry must report the upstream error instead of pretending the
  requested source worked.
- `.agents/steering/tech.md` contains a one-time language/file count already
  contradicted by `.agents/state/project-profile.md`; the generated profile is
  the proper current snapshot.

## Affected contracts and files

- New local benchmark commands under `ratchery benchmark`.
- Expanded, safely constructed flags for `ratchery usage`.
- A versioned aggregate benchmark snapshot under local XDG state, outside the
  repository; no session IDs, prompts, raw reports, project labels, or file
  paths are persisted.
- `tools.lock.json` becomes an executable catalog for activation and security
  policy while retaining the existing top-level tool keys for compatibility.
- Tool/status/recommendation output, CLI docs, architecture docs, and security
  docs describe the same policy.
- Steering templates stop freezing volatile counts.

## Risks

- ccusage JSON may vary between legacy Claude-only and current unified
  releases; parsing must accept only the small documented `totals` contract and
  fail clearly on unknown or empty output.
- Benchmark windows can include unrelated work; capture must record its exact
  source/project/date filters and comparison must reject incompatible scopes.
- A comparison can look valid while changing code, model, client, permissions,
  or task set; capture requires a clean commit and records those identifiers,
  while compare rejects mismatches other than the arm configuration. The commit
  is capture-time provenance rather than an attestation over historical rows;
  the user protocol must keep the checkout unchanged through capture.
- Tool metadata can become another stale inventory; schema validation and
  `recheck_by` warnings must cover every entry.
- Optional compression can hide diagnostic evidence; RTK remains experimental
  until a local comparison passes, with raw-output fallback documented.

## Workstreams and ownership

1. **Measurement:** stdlib aggregate parser, capture/compare commands, local
   snapshot format, tests, and benchmark protocol.
2. **Tool policy:** activation/family/security metadata, adaptive recommendation
   output, and corrected RTK/ccusage behavior.
3. **Pruning/documentation:** eliminate stale steering counts, classify
   v8.2/v9 references, update canonical user/security/architecture docs.
4. **Validation:** targeted tests, full suite, manifest, link/action-pin checks,
   dependency/security review, and independent focused review.

The primary agent owns implementation and integration. Independent agents are
read-only reviewers/test runners after the diff stabilizes.

## Acceptance criteria

- A user can produce two privacy-preserving aggregate snapshots and compare
  total tokens, estimated cost, task success rate, and cost per successful task.
- Benchmark capture forces ccusage offline mode, uses an argv list (never a
  shell), validates all user-controlled arguments, and persists no raw usage
  rows or sensitive usage identifiers. It records only explicit reproducibility
  labels and the clean Git commit.
- Comparisons reject different source/project scopes and never divide by zero.
- `usage --json` emits only ccusage JSON on stdout; errors remain non-zero.
- Tool policy identifies activation mode and security/network cost, recommends
  profiles rather than a universal heavy stack, and installs nothing.
- RTK instructions correctly separate Claude and Codex setup and begin with a
  dry-run/review step.
- Live docs contain no unexplained product-version `v8.2`/`v9` residue; frozen
  merge markers and clearly historical migration/audit records remain.
- The standard test, lint, manifest, and documentation checks pass.

## Validation plan

```bash
python3 tests/test_efficiency.py
python3 tests/test_tool_policy.py
python3 tests/test_context_engine.py
python3 tests/test_merge_and_slug.py
make test
python3 scripts/verify-manifest.py
python3 scripts/verify-doc-links.py
python3 scripts/verify-action-pins.py
git diff --check
```

Also exercise capture/compare against a fake ccusage executable so tests never
read a developer's real usage history, and inspect the final diff with the
security-scan, dependency-audit, and focused-review checklists.

## Handoff

Status: complete. The implemented behavior and user protocol are documented in
`docs/BENCHMARKING.md`; validation evidence and remaining environment-dependent
checks are recorded in the local `docs/CURRENT_STATE.md` handoff.
