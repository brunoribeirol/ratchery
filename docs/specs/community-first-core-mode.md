# Delta Spec: Community-first core mode

Mode: **openspec-light** (T1/T2 default). This file describes only the behavior changing
from the v1.0.0 contract.

## Why

Ratchetry's security, tiering, context, agent, Skill, lifecycle, and diagnostic core does
not require Obsidian, but both supported onboarding paths currently require an existing
Vault. That makes a useful optional memory backend a prerequisite and hides the product's
immediate value behind setup knowledge a first-time community user may not have.

## What changes

- A fresh source install and `ratchery setup` may omit `--vault`. They install/configure
  the core and persist `vault_path: null`.
- On later runs, omitting both memory flags preserves the existing selection. `--no-vault`
  is the explicit, non-destructive way to switch configuration to core-only mode.
- When `--vault` is supplied, all existing validation, migration, backup, merge,
  installation, and doctor behavior remains unchanged.
- `doctor-global` treats an absent Vault as a healthy optional state, but a configured
  missing/invalid path remains an error.
- Vault-only commands fail with a concise configuration instruction when memory is not
  configured.
- Public onboarding leads with the core outcome and a short no-Vault path; Obsidian
  memory is documented as an explicit enhancement.
- The requested named README comparison is removed. Historical research remains in the
  dated research record.

## Affected contracts

- `install.sh --vault PATH`: optional instead of required; `--no-vault` explicitly disables
  memory, and omission preserves an existing selection.
- `ratchery setup --vault PATH`: same tri-state contract.
- `ratchery global-config --vault PATH`: same lower-level tri-state contract so the source
  installer and CLI share the nullable configuration schema.
- `~/.config/ratchery/config.json`: `vault_path` remains present and may be JSON `null`.
- `doctor-global`: no error for an unconfigured Vault; error for an explicitly configured
  path that is unavailable.
- Vault-only CLI commands: actionable non-zero result when `vault_path` is null.

## Out of scope

- Replacing Obsidian, automatic memory capture, team memory servers, new client providers,
  external tool installation, orchestration, or a new benchmark claim.
- Changing tier classification, sandbox policy, the risk ratchet, managed-block format,
  or published release history.

## Tasks

- [x] Re-derive the product and onboarding boundary from code and current research.
- [x] Implement nullable Vault setup/install/doctor behavior.
- [x] Add no-Vault, invalid-configured-Vault, and Vault-command contract tests.
- [x] Rewrite public first-use/product documentation and remove the named README link.
- [x] Record the architectural decision and dated external research.
- [x] Regenerate the manifest and run the complete affected validation suite.

## Validation

```text
python3 tests/test_setup_command.py
bash tests/run-tests.sh
python3 -m unittest discover -s tests -p 'test_*.py'
ruff check lib/ scripts/ tests/ bin/
python3 scripts/verify-manifest.py
python3 scripts/verify-action-pins.py
python3 scripts/verify-doc-links.py
make release-smoke
```

The release/tag boundary is not part of this delta.

Validated on 2026-09-17: the Bash install integration passed in configured-Vault and
core-only modes; 348 Python tests passed; Ruff, Python/Bash syntax, the 288-file release
manifest, 20 Action pins, 181 Markdown-link checks, and installed-archive release smoke all
passed. ShellCheck was not installed locally and remains a required hosted Linux PR check.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
