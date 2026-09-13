# Delta Spec: Cost and Security Measurement

Mode: **openspec-light** (T1/T2 default).

## Why

Ratchetry says optional capabilities must justify their token, monetary,
permission, and maintenance cost, but the repository has no reproducible local
comparison format and exposes only a hard-coded `ccusage daily` shortcut.
Meanwhile, its optional-tool inventory cannot express activation or security
cost, and its RTK setup text currently conflates different Claude and Codex
integration mechanisms. The product principle is therefore stronger than the
implemented evidence loop.

## What changes

- Expand `usage` with a validated report period, optional source, date window,
  project filter, JSON mode, and offline mode. Build a subprocess argv list and
  run ccusage from the user's home directory so repository-local ccusage config
  is not implicitly trusted.
- Add `benchmark capture`: run an offline daily ccusage aggregate for an
  explicit date window, attach user-supplied attempted/successful task counts,
  and persist only aggregates plus reproducibility identifiers in local XDG
  state outside the repository.
- Add `benchmark compare`: validate two snapshots, reject incompatible
  source/project scopes, and report absolute/percentage deltas plus success rate
  and cost per successful task. Zero baselines produce `null`/`n/a`, not an
  invented percentage.
- Add a pure stdlib `lib/efficiency.py` module for report/snapshot validation and
  comparison.
- Enrich `tools.lock.json` with an explicit schema version and, for each tool,
  command probe, family, activation mode, network posture, benchmark policy,
  and coexistence guidance. Existing tool names stay at the top level.
- Correct RTK guidance to preview and configure Claude and Codex separately.
- Replace frozen steering counts with pointers to the refreshed project profile.
- Document the measurement protocol, privacy boundary, limitations, security
  profiles, and why heavier tools are experimental/on-demand rather than core.

## Affected contracts

- CLI:
  - `ratchery usage [--period ...] [--source ...] [--since ...]
    [--until ...] [--project ...] [--json] [--offline]`
  - `ratchery benchmark capture NAME --since YYYYMMDD --until YYYYMMDD
    --task-set ID --model ID --client-version ID --environment-id ID
    --configuration ID --attempted-tasks N --successful-tasks N
    [--source ...] [--project ...] [--path ...]`
  - `ratchery benchmark compare BASELINE CANDIDATE [--path ...]
    [--json]`
- Snapshot schema version 1 stores aggregate token/cost/task metrics only.
- Capture requires a valid clean Git `HEAD`; compare requires identical commit,
  task set, model, client, and environment identifiers while allowing the arm
  configuration identifier to differ.
- The Git value is capture-time provenance, not an attestation over historical
  usage; documentation requires keeping the measured checkout unchanged through
  capture and labels date-window protocol data as self-attested.
- Benchmark snapshots are local XDG state, namespaced by project UUID and
  canonical-path fingerprint; they are never stored in generated projects.
- `tools.lock.json` keeps its flat tool-key layout; `_schema_version` is the only
  reserved non-tool key.

## Out of scope

- Automatic execution of benchmark prompts or paid model calls.
- An automatic daily/monthly spending blocker.
- Installing ccusage, RTK, Context Mode, Serena, QMD, scanners, or MCP security
  services.
- Persisting ccusage session/project rows, prompts, model transcripts, or raw
  tool output.
- Declaring a universal winner before local repeated measurements exist.

## Tasks

- [x] Implement and test aggregate parsing/snapshot comparison.
- [x] Implement and test safe `usage` and `benchmark` dispatch.
- [x] Version and validate the tool-policy catalog.
- [x] Correct RTK/ccusage status and recommendations.
- [x] Remove volatile steering duplication.
- [x] Document benchmark and security/cost profiles end to end.
- [x] Classify and clean live v8.2/v9 remnants.
- [x] Run targeted/full validation and independent review.

## Validation

```bash
python3 tests/test_efficiency.py
python3 tests/test_tool_policy.py
python3 tests/test_context_engine.py
python3 tests/test_merge_and_slug.py
make test
python3 scripts/verify-manifest.py
git diff --check
```

Fixtures must cover empty/malformed ccusage JSON, negative/non-finite metrics,
unsafe benchmark/source names, invalid date windows, zero successful tasks,
incompatible comparison scopes, stdout purity in JSON mode, and a fake ccusage
failure. Tests must not inspect real local usage data.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
