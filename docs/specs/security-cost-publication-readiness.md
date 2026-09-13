# Delta Spec: Security, Cost, and Publication Readiness

Mode: **openspec-light** (T1/T2 default).

## Why

Ratchetry now has a strong adaptive/security baseline and aggregate cost capture,
but four boundaries remain incomplete before its security-first and cost-aware
claims are publishable: Claude permission bypass is not disabled, optional MCP
profiles are broader and less immutable than the clients allow, the documented
benchmark task set is only a label, and no read-only budget or upstream-client
compatibility gate exists.

## What changes

- Claude project policy disables bypass-permissions mode and `doctor` enforces it.
- Ratchetry-managed Serena uses the verified full commit behind release v1.7.0.
  Managed Codex MCP profiles declare bounded startup/tool timeouts, prompt-oriented
  approvals, a tool allowlist, and per-tool output budgets. Claude keeps MCP calls
  permission-gated and adds explicit ask rules for the managed servers.
- A versioned `core-suite-v1` benchmark manifest defines six public, non-secret task
  protocols and success criteria. CLI commands list, show, and validate shipped
  suites without starting an agent or incurring inference cost.
- Benchmark comparison gains a multi-snapshot report that requires compatible
  provenance, reports medians/ranges, preserves the quality floor, and never emits a
  promotion decision from one sample.
- `budget check` uses offline ccusage aggregates for daily/session thresholds and
  spike warnings, emits human or JSON output, stores nothing, and only returns a
  failing policy exit when explicitly requested.
- A scheduled/manual, credential-free workflow validates generated configuration
  against supported Claude/Codex clients separately from normal pull-request CI.
- Canonical docs and generated templates describe these exact boundaries.

## Affected contracts

- `.claude/settings.json`: `permissions.disableBypassPermissionsMode` and managed MCP
  permission rules.
- `.codex/config.toml` managed MCP blocks: immutable source, `enabled_tools`, approval,
  timeout, and output-budget keys.
- CLI: `benchmark suites`, `benchmark show`, `benchmark validate`, `benchmark report`,
  and `budget check`.
- Benchmark task-set JSON schema and aggregate report JSON schema.
- `doctor`/`doctor --json` error contract for removed security controls or MCP drift.
- GitHub workflow surface: scheduled/manual client compatibility canary.

## Out of scope

- No automatic installation or activation of optional tools.
- No automatic or paid execution of Claude/Codex benchmark tasks.
- No daemon, transcript persistence, raw prompt/session storage, or default blocking
  prompt hook.
- No new default agents, Skills, MCPs, scanners, model routing, monorepo tier floors,
  rebrand, remote repository creation, push, tag, or release.

## Tasks

- [x] Implement and test Claude bypass protection and bounded MCP profiles.
- [x] Define and validate `core-suite-v1`; add list/show/validate CLI commands.
- [x] Implement compatible multi-run benchmark reporting.
- [x] Implement offline read-only budget checks with opt-in enforcement.
- [x] Add the credential-free scheduled/manual client compatibility workflow.
- [x] Reconcile user, security, architecture, benchmark, roadmap, changelog, and
      publication documentation.
- [x] Run focused and full validation, independent review, release reproducibility,
      and secret/configuration checks.

## Validation

```bash
python3 -m unittest tests.test_doctor_tier_json tests.test_efficiency
bash tests/run-tests.sh
ruff check lib/ scripts/ tests/ bin/
make test
python3 scripts/verify-manifest.py
python3 scripts/verify-action-pins.py
python3 scripts/verify-doc-links.py
git diff --check
```

Additionally validate generated MCP TOML with `tomllib`, run task-set and budget JSON
black-box tests with fake binaries/data only, and exercise the native-client canary in
an ephemeral credential-free environment without inference.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)

Implementation validation completed on 2026-09-11 from a clean temporary
checkout of the intended index: `doctor --deep` returned zero errors/warnings;
`make test` passed with 260 unit tests plus integration/lint/manifest/pin/link
checks; Python 3.11, 3.12, and 3.14 unit runs passed; two release builds were
byte-identical; and the extracted release passed its own suite with the seven
expected workflow-only skips. The initial independent code/security reviews
produced concrete findings that were fixed and regression-tested. A requested
second independent pass could not run because both agents exhausted their
service quota, so no claim is made that it completed.
