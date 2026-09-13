# Delta Spec: Setup-First Foundation

Mode: **openspec-light** (T1/T2 default).

## Why

The project evolved from a complete low-overhead Claude Code + Codex + Obsidian
workspace, but its public positioning now makes the adaptive tier classifier
look like the product itself. At the same time, `doctor --deep` can approve a
project after its actual hook binding or important deny rules are removed, and
it trusts editable derived tier fields. The product promise and the gate that
protects it must be corrected before adding integrations or rebranding.

## What changes

- Define the canonical product as a batteries-included, setup-first operating
  layer whose capabilities are loaded progressively and whose adaptive engine
  selects proportional rigor.
- Define cost, security, continuity/memory, interoperability, preservation of
  user configuration, and evidence-based curation as product principles.
- Reframe README and architecture language around that product contract.
- Make project profiling available through a non-writing path so `doctor`
  remains read-only on a fresh clone.
- Have `doctor` derive the expected tier name and requirements from trusted
  code, recompute the ratcheted effective tier without writing history, and
  reject forged/stale derived fields.
- Reject malformed/non-object ratchet history and invalid risk-answer keys,
  types, or enum values instead of silently falling back to a lower-risk state.
- Have `doctor` validate required Claude permission denies, sandbox filesystem
  and credential denies, protected environment variables, and the real
  PreToolUse hook binding.
- Have `doctor` validate Codex filesystem denies, environment filters,
  `features.hooks`, and the real PreToolUse hook binding.
- Have `preflight`, project `doctor`, and `doctor-global` reject installed
  Claude/Codex versions below Ratchetry's supported security-policy floor,
  while continuing to allow either CLI to be absent for single-client setups.
- Require Python 3.11+ so Codex TOML security validation uses stdlib `tomllib`
  on every supported runtime rather than becoming a warning-only check.
- Keep validation monotonic: stricter user configuration and unrelated custom
  hooks/settings remain valid.
- Validate the exact managed hook type/command/timeout contract rather than a
  marker substring, and keep deep diagnostics free of hook-runtime writes.
- Ignore symlinked and non-regular source files during project inspection so a
  checked-out repository cannot redirect diagnostics outside its tree.
- Ensure `tier`, `tier-set`, and related recomputation paths rescan current
  project facts instead of reusing a stale generated profile.
- Treat the initial default-risk classification as provisional: `init`/`tier`
  surface an action and `doctor` blocks until `tier-set` records reviewed facts.

## Affected contracts

- `doctor [--deep] [--json]` gains stricter errors but no new CLI flags.
- `.agents/state/tier.json` derived fields must match classifier output and the
  ratchet history.
- `.claude/settings.json`, `.codex/config.toml`, and `.codex/hooks.json` must
  retain the shipped security invariants, though safe additions remain allowed.
- Installed Claude Code must be at least 2.1.187 and installed Codex CLI must
  be at least 0.138.0 for the generated security profiles to be considered
  enforceable.
- Risk-answer and tier-history files become fail-closed inputs: malformed or
  schema-invalid content is an error, not an instruction to use benign defaults.
- Python 3.11+ is now the runtime floor; no production dependency or persistent
  file-format version is added.

## Out of scope

- Final Ratchetry naming and installed-path migration.
- New third-party integrations, including Sentrux.
- Release SBOM/provenance and deterministic packaging.
- MCP opt-in persistence and generated-state timestamp cleanup.
- Removing existing agents/Skills before the catalog review phase.

## Tasks

- [x] Write the canonical product context and setup-first README/architecture.
- [x] Add a pure project-profile computation path.
- [x] Add pure expected-tier/ratchet validation for doctor.
- [x] Make risk answers and tier history fail closed on invalid data.
- [x] Validate Claude security invariants and hook binding.
- [x] Validate Codex security invariants and hook binding.
- [x] Enforce minimum security-capable CLI versions when the CLIs are present.
- [x] Reject no-op marker-substring hooks and eliminate deep-probe writes.
- [x] Ignore symlinked/non-regular project files and remove stale-profile CLI paths.
- [x] Add negative regression fixtures for every reproduced bypass.
- [x] Run targeted, full, manifest, and fresh-clone validation.
- [x] Obtain independent security and test review.

## Validation

```bash
python3 tests/test_doctor_tier_json.py
python3 tests/test_adaptive_engine.py
make test
python3 scripts/verify-manifest.py
git diff --check
```

Negative fixtures must prove that removed Claude/Codex PreToolUse bindings,
removed required deny/filter entries, and forged `effective_tier`, `tier_name`,
or `requirements` cause a non-zero doctor result. They must also cover an empty
tier object, malformed history, invalid risk values, marker-only no-op hook
commands, old installed clients, and a source symlink outside the repository. A
fresh clone must show that doctor creates no project profile or other state.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
