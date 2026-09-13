# Delta Spec: JSON output for `doctor`/`tier` + a reusable CI gate Action

Mode: **openspec-light** (T1). Describe only what changes.

## Why

`tier`/`doctor` state (`.agents/state/tier.json`, `tier-history.jsonl`, etc.) is
already git-committed, so the risk ratchet is shared across a team via the
repo — but nothing enforces it. Compliance today depends entirely on an agent
voluntarily running `ratchery doctor`/`tier` inside a live session; a
PR can merge without that ever happening. `doctor_project()` already returns
the right exit code (1 on error) but only prints human text, so there is no
machine-readable contract a CI system could consume even if someone wired a
workflow today.

## What changes

- `ratchery doctor [--path .] [--deep] [--json]`: new `--json` flag.
  When set, suppress the existing human-readable `print()` lines and instead
  emit one JSON object to stdout: `{"errors": [...], "warnings": [...],
  "tier": <effective_tier or null>, "tier_name": <str or null>}`. Exit code
  behavior is unchanged (`1` if any error, else `0`).
- `ratchery tier [--path .] [--acknowledge-downgrade REASON] [--json]`:
  new `--json` flag. When set, suppress the human `print()` lines and emit
  the same structure `classify()` already returns
  (`effective_tier`/`computed_tier`/`criticality_score`/`complexity_score`/
  `ratcheted`/`downgrade_acknowledged`/`downgrade_reason`/`tier_name`) plus
  `active_agents` (the result of `install_agents()`, already computed today).
  This command still writes/updates tier state and installs newly-active
  agent files exactly as it does today — `--json` only changes what is
  printed, not what the command does.
- New composite GitHub Action, `action.yml` at the repo root, wrapping
  `bin/ratchery doctor --path <inputs.path> --deep --json` as a CI
  merge gate. Inputs: `path` (default `.`), `deep` (default `true`). The
  action fails the step when `doctor` exits non-zero, and sets a
  `doctor-result` output containing the raw JSON for downstream steps
  (e.g. posting a PR comment) to consume. `tier` is intentionally **not**
  invoked by the Action — it mutates repo state (writes tier files, installs
  agent files) and isn't the right primitive for a read-mostly CI gate;
  `--json` is still added to it for other consumers (dashboards, scripts).
- One new doc, `docs/CI_GATE.md`: how to consume the Action from a
  downstream project's own workflow (`uses:` example, inputs/outputs table,
  what a failing gate means and how to fix it via `ratchery doctor`
  locally).

## Affected contracts

- CLI: `doctor` and `tier` subcommands gain an additive `--json` flag (no
  existing flag/behavior removed; default behavior — no flag — is byte-for-
  byte unchanged).
- New file: `action.yml` (GitHub composite action contract: `inputs.path`,
  `inputs.deep`, `outputs.doctor-result`).
- New doc: `docs/CI_GATE.md`.

## Out of scope

- Publishing the Action to the GitHub Actions Marketplace (needs the repo to
  exist under its final name first — tracked as a discoverability follow-up
  in `docs/CURRENT_STATE.md`, not part of this delta).
- Any change to `doctor_project()`'s or `classify()`'s actual check logic —
  this only changes how results are reported.
- Wiring `tier` into the Action (see rationale above).
- Retrofitting this repo's own `.github/workflows/ci.yml` to use the new
  Action on itself — worth doing later, not required to ship the feature.

## Tasks

- [x] Add `--json` to `doctor` subcommand parser; refactor `doctor_project()`
      to collect `errors`/`warnings`/tier info into a dict first, then either
      print human lines or `json.dumps()` it, gated on the flag.
- [x] Add `--json` to `tier` subcommand parser; same print-vs-json split for
      the `tier` dispatch branch in `main()`.
- [x] Add `tests/test_doctor_tier_json.py`: `--json` on both commands emits
      valid JSON with the expected keys, exit code unchanged. Non-`--json`
      output is cross-checked against the same invocation's `--json` facts
      (`test_json_and_text_report_the_same_facts`), not diffed against a
      byte-for-byte golden baseline -- an independent review correctly
      flagged the original wording here as overclaiming coverage the test
      didn't have.
- [x] Write `action.yml` (composite action, `runs.using: composite`, no
      Docker — matches the project's stdlib-only/no-new-deps posture).
- [x] Write `docs/CI_GATE.md`.
- [x] Update `CHANGELOG.md` (Unreleased section).

## Validation

- `python3 lib/agent_workspace.py doctor --path . --json | python3 -m json.tool`
  parses cleanly.
- `python3 lib/agent_workspace.py tier --path . --json | python3 -m json.tool`
  parses cleanly.
- `make test` (full suite, includes the new test file) green.
- Manual: run `doctor`/`tier` without `--json` before and after, diff output
  — must be identical.

## Status

- [x] Proposed
- [x] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
