# Delta Spec: Trusted capability intake and technology watch

Mode: **openspec-light** (T1/T2 default). This document describes only the
change.

## Why

Ratchetry has a curated capability catalog and an offline technology radar, but
it does not yet turn recurring upstream research into a safe, repeatable intake
process. The project also lacks two high-value engineering disciplines that are
repeatedly useful across stacks: behavior-first TDD and evidence-first debugging.

## What changes

- Add native `test-driven-development` and `systematic-debugging` Skills. Their
  instructions adapt broadly established MIT-licensed workflow patterns to
  Ratchetry's existing safety and proportional-rigor contracts; third-party
  files are not vendored.
- Route feature implementation through vertical red/green/refactor slices and
  route difficult failures through reproduce/minimize/hypothesize/prove/fix.
- Expand the curated radar with reviewed engineering-Skill sources, Jev, A2A,
  OpenTelemetry GenAI conventions, and skills.sh as discovery-only evidence.
- Add a stdlib-only, read-only GitHub metadata watcher. Offline mode plans the
  exact endpoints without network access; online mode is explicit, allow-listed
  to `api.github.com`, bounded, and never modifies the radar or installs code.
- Add a daily least-privilege GitHub workflow that publishes the advisory watch
  report to the run summary without creating issues or pull requests.

## Affected contracts

- The global Skill catalog grows from 16 to 18 Skills.
- The `implement-feature` and `debug-failure` advisory workflows reference the
  new Skills.
- The technology radar remains backward compatible and gains reviewed entries.
- `scripts/technology-watch.py` emits schema-versioned JSON or Markdown and
  returns non-zero on malformed input or upstream query failure.

## Out of scope

- No automatic Skill, plugin, MCP, dependency, or code import.
- No arbitrary web crawling, trend-based installation, issue creation, or
  unattended repository mutation.
- No Jev API integration, credential collection, source-code upload, A2A
  runtime, or telemetry exporter.
- No claim that popularity, a security badge, or a passing upstream audit is
  sufficient evidence for adoption.

## Tasks

- [x] Add and register the two native engineering Skills and routing evals.
- [x] Update the affected workflow contracts.
- [x] Expand radar evidence and document explicit adoption/hold decisions.
- [x] Implement and test the bounded watcher and least-privilege workflow.
- [x] Update documentation, manifest, and release validation evidence.

## Validation

`python3 -m unittest tests.test_capability_system tests.test_technology_watch`,
targeted Ruff and `py_compile`, action-pin and workflow contract checks,
`make test`, manifest/link verification, and `make release-smoke`.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
