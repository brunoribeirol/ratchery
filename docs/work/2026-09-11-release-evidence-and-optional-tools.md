# Work Plan: Release Evidence and Optional Tool Evaluation

## Objective

Close the two remaining evidence gaps before rebranding: prove the built release can
actually install and run, and bind repeated cost trials to an automatically derived
configuration identity. Improve the planning/security Skills using independently
useful concepts from the reviewed external repositories, classify `ai-jail` and
`ai-memory` without adopting them, and leave Homebrew ready for the final identity.

## Non-goals

- Do not install, execute, vendor, or copy code from the reviewed external tools.
- Do not weaken native Claude/Codex sandboxing or persist raw prompts/tool transcripts.
- Do not create a tap/formula before the final owner, repository, binary compatibility,
  and release URL exist.
- Do not rewrite the stdlib-only Python control plane in Rust.

## Evidence and assumptions

- `.github/workflows/release.yml` builds then uploads without exercising the exact
  tarball. Existing tests validate construction, not the installed runtime journey.
- The current benchmark requires the same commit and human environment label, but
  repeated snapshots can retain those labels while settings/agents/skills drift.
- Repository-managed configuration can be hashed without storing file contents or
  paths outside a fixed public inventory. External/global runtime state remains an
  explicitly documented limitation rather than an unsafe broad scan.
- `ai-jail` adds outer filesystem isolation on supported platforms but unrestricted
  network/agent-state modes and weak macOS portability prevent default adoption.
- `ai-memory` may help multi-machine/team handoffs, but its daemon/index/hook/MCP and
  capture surface overlap the curated Vault default and add non-zero context/security
  cost.

## Affected contracts and files

- Release: `.github/workflows/release.yml`, `scripts/smoke-test-release.py`, Makefile,
  focused tests, `docs/PUBLISHING.md`.
- Benchmark: `lib/efficiency.py`, `lib/agent_workspace.py`, `tests/test_efficiency.py`,
  `docs/BENCHMARKING.md`.
- Skills/catalog: `assets/global/skills/{work-plan,security-scan}/SKILL.md`,
  `tools.lock.json`, canonical and generated tool-policy docs, focused tests.
- Product state: roadmap, changelog, spec, local current state, and `MANIFEST.json`.

## Risks

- Archive extraction is an attacker-controlled boundary even for a locally built
  artifact; reject traversal, links, devices, duplicate paths, and multiple roots.
- The smoke environment must not touch the maintainer's real home/config/Vault or run
  optional/client binaries found on the host.
- A digest can create false confidence. It must describe its exact inventory and never
  be called a full environment attestation.
- Requiring equal digests across baseline and candidate would make an A/B test
  impossible; equality applies within an arm, while both arm digests remain visible.
- Catalog presence can look like endorsement. Experimental entries must state their
  platform/privacy/overlap limitations and remain outside automatic routing.

## Workstreams and ownership

The primary agent owns all implementation and integration; no parallel writers are
needed for this tightly coupled change.

1. Add fail-closed archive extraction and isolated artifact install/runtime checks.
2. Add privacy-preserving configuration digest collection, schema validation, output,
   and same-arm repeat enforcement.
3. Tighten the two Skills and validate their structure.
4. Record optional-tool and post-rebrand Homebrew decisions consistently.
5. Regenerate the manifest, run focused checks, then the complete suite and real smoke.

## Acceptance criteria

- Publication cannot proceed if the exact archive fails safe extraction, installation,
  project initialization, or machine-readable doctor validation.
- The smoke command uses only a temporary HOME/state/config/cache, external tools are
  disabled, and host Claude/Codex executables are not discoverable.
- Every new benchmark snapshot has a validated 64-hex configuration digest. Reports
  reject drift within either repeated arm and expose both arm digests without requiring
  them to match each other.
- The enhanced Skills remain concise and change decisions: each plan maps acceptance to
  evidence/budget; each security scan scopes actors/assets/boundaries and residual risk.
- `ai-jail` and `ai-memory` appear only as experimental manual candidates. Homebrew is
  an explicit post-identity release task, not current implementation.

## Validation plan

Cheap/targeted evidence first: compile the changed Python, run the four focused test
modules, validate the two Skill directories, and run workflow/catalog contracts. Then
regenerate the manifest once, run `make test`, build and smoke the real archive, verify
documentation links/action pins, and run `git diff --check`. External scanners remain
out of budget unless installed; no network or paid inference is necessary.

## Handoff

Status: implemented and locally validated. The exact 261-file release inventory
passed 269 tests, immutable-Action-pin and Markdown-link checks, two byte-identical
release builds, and the real archive install/init/`doctor --json` smoke. Focused
configuration-digest, archive-adversarial, workflow, and tool-policy tests also
passed. The Skill structures passed a stdlib frontmatter/scaffold check; the
skill-creator's optional Python validator could not run because PyYAML is not
installed. `gitleaks`, `trivy`, `semgrep`, `shellcheck`, and `pip-audit` were not
available, so their external scans remain explicit residual validation.

No push, tag, release, rebrand, Homebrew tap, external install, or paid benchmark
was performed. `ai-jail` and `ai-memory` remain catalog-only experiments and no
optional executable was invoked by the implementation or validation path.
