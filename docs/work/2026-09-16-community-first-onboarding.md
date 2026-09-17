# Work Plan: Community-first onboarding

## Objective

Make Ratchetry useful before a new user learns its internal architecture: install the
security/cost-aware core without requiring Obsidian, initialize a repository with one
short path, and explain optional memory separately. Re-check adjacent projects for
transferable product ideas without importing their dependency, permission, or context
surface by default.

## Non-goals

- Do not add another provider, daemon, MCP server, automatic memory capture, or agent
  orchestrator in this change.
- Do not promote an external tool because of stars or README benchmark claims.
- Do not remove the existing Obsidian workflow or weaken its path/symlink checks.
- Do not rewrite published tags or releases.
- Do not erase historical research attribution; remove the named comparison only from
  the public README positioning requested by the maintainer.

## Evidence and assumptions

- The installer and `ratchery setup` currently require `--vault`, while project
  initialization already skips Vault writes when `vault_path` is unset.
- `cfg()` already models `vault_path` as nullable, so mandatory Vault setup is an
  onboarding constraint rather than a core runtime dependency.
- Current AkitaOnRails and Lucas Rosati projects succeed at making one problem and one
  first action obvious. Their useful lesson is product clarity; their daemons, automatic
  capture, orchestration, or broad credential access are not free additions.
- Repository code/tests/docs are authoritative. External repositories are untrusted
  research inputs and no source is copied from them.

## Affected contracts and files

- Source install CLI: `install.sh`
- Package-manager onboarding: `setup_workspace()`, `global-config`, `setup`, and
  `doctor-global` in `lib/agent_workspace.py`
- Setup/integration contracts: `tests/test_setup_command.py`, `tests/run-tests.sh`, and
  release smoke where affected
- Public onboarding/product contract: `README.md`, `docs/00-START-HERE.md`,
  `docs/INSTALLATION.md`, `docs/PROJECT_CONTEXT.md`, and `docs/USER-GUIDE.md`
- Durable rationale/research: `docs/decisions/ADR-007-optional-memory-community-core.md`
  and `docs/research-external.md`
- Release inventory and change history: `MANIFEST.json`, `CHANGELOG.md`

## Risks

- A nullable Vault path could cause a traceback in a Vault-only command if dispatch does
  not reject the unconfigured state explicitly.
- Conditional install logic could accidentally skip global safety guidance along with
  Vault content.
- Changing `doctor-global` from an error to an optional state could hide a broken path
  that was explicitly configured; an absent path and an invalid configured path must
  remain distinct.
- Documentation could imply that optional memory is unavailable or unimportant; it must
  stay a first-class opt-in workflow.

## Workstreams and ownership

1. Primary agent: specify the core/memory boundary and record the durable decision.
2. Primary agent: implement optional-Vault source and package-manager onboarding.
3. Primary agent: add black-box coverage for no-Vault and configured-invalid-Vault paths.
4. Primary agent: rewrite the first-use narrative and record current external research.
5. Primary agent: run targeted, full, inventory, link, and release-smoke validation.

## Acceptance criteria

- `bash install.sh --projects-root <tmp> --dry-run` succeeds without `--vault`, prints
  `Vault memory: not configured (optional)`, and performs no writes. Evidence:
  integration assertion plus an isolated manual run.
- `ratchery setup --projects-root <tmp> --yes` writes `vault_path: null`, installs global
  guidance, prepares the project workspace, and passes `doctor-global`. Evidence:
  black-box setup test inspecting files/config and doctor output.
- Passing a nonexistent or unsafe explicit `--vault` still fails before any write.
  Evidence: existing and new setup security tests.
- Vault-only commands without a configured path fail with an actionable message rather
  than a Python traceback. Evidence: targeted CLI tests.
- Existing configured-Vault setup remains idempotent and doctor-clean. Evidence: the
  pre-existing black-box setup test.
- The README contains no `lucasrosati` or `claude-code-memory-setup` reference, states
  the product outcome before implementation details, and shows a no-Vault quickstart plus
  a separate optional-memory path. Evidence: text contract tests/search and link check.
- Current external research yields explicit add/profile/defer decisions. Evidence: dated
  addendum with primary repository links and no new default dependency.

## Validation plan

Run setup-command and integration tests first. Then run Python/Bash syntax, Ruff, the full
unit and integration suite, manifest regeneration/verification, Action-pin verification,
Markdown-link verification, and release smoke. Networked research is read-only and
bounded to public primary repositories. Stop before any tag/release; use a protected PR
for repository mutation.

## Handoff

Deliver the protected PR plus a concise product statement, the exact first-use path, the
external tools deliberately deferred, and any validation unavailable in the environment.

## Outcome

Implemented on `feat/community-first-onboarding`. A focused pre-merge review found and
fixed one backward-compatibility issue: omission originally cleared an existing Vault
selection. Setup now has an upgrade-safe tri-state contract—fresh omission starts core
only, later omission preserves the current selection, `--vault` enables/selects memory,
and `--no-vault` disables it without deleting notes.

No new default third-party dependency was added. Local validation passed the full Bash
integration suite, 348 Python tests, Ruff, Python/Bash syntax, manifest, Action-pin,
Markdown-link, and release-smoke gates. Local ShellCheck was unavailable; the protected
Linux PR check remains required evidence before merge.
