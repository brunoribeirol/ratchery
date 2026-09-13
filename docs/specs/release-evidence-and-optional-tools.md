# Delta Spec: Release Evidence and Optional Tool Evaluation

Mode: **openspec-light** (T1/T2 default).

## Why

The release pipeline verifies archive bytes and provenance but does not install and
exercise the archive it is about to publish. Benchmark snapshots record human labels
but cannot detect configuration drift between repeated trials. Two newly researched
tools may be useful in narrow profiles, but making either a default would violate the
project's cost, privacy, and least-infrastructure principles.

## What changes

- A stdlib-only release smoke command safely extracts the built source archive into an
  isolated temporary environment, installs that exact artifact with external tools
  disabled, initializes a Git fixture, and requires `doctor --json` to report no
  errors. The release build job must pass this gate before uploading artifacts.
- Benchmark snapshot schema v2 records an automatic SHA-256 configuration digest over
  the effective project instructions, client policy, active agents/skills/rules,
  selected state, Ratchetry/runtime facts, task-set identity, and captured tool/client
  labels. Repeated trials within each arm must have the same digest; the two arms may
  differ because the candidate configuration is the variable under test.
- `work-plan` requires an evidence path and a proportional verification budget.
  `security-scan` requires a scoped threat model, trust-boundary tracing, adversarial
  cases, and explicit residual scope.
- `ai-jail` and `ai-memory` enter the advisory catalog as experimental, manual-only
  candidates. They are not routed, installed, started, or enabled automatically.
- A Homebrew tap is documented as a post-rebrand/post-publication distribution step;
  no formula is created against the temporary name or repository.

## Affected contracts

- Release workflow and maintainer procedure; new `scripts/smoke-test-release.py` CLI.
- Benchmark snapshot schema (`schema_version: 2`) and comparison/report provenance.
- Global `work-plan` and `security-scan` Skill instructions installed for both clients.
- `tools.lock.json`, canonical/generated tool policy, roadmap, publishing guide, and
  changelog.

## Out of scope

- No Rust rewrite, daemon, Homebrew repository/formula, rebrand, remote mutation,
  network access, paid benchmark run, or automatic third-party installation.
- No adoption of `ai-jail` as a replacement for native client sandboxing.
- No adoption of `ai-memory` alongside the default curated Vault memory path.
- No claim that the configuration digest attests to OS state, environment variables,
  globally installed client configuration, or arbitrary external binary contents.

## Tasks

- [x] Implement and test the release artifact smoke gate.
- [x] Implement and test benchmark configuration digests and schema v2.
- [x] Update and validate the two global Skills.
- [x] Add the optional-tool evaluations and deferred Homebrew procedure.
- [x] Reconcile docs/manifest and run focused plus full validation.

## Validation

```bash
python3 -m unittest tests.test_release_artifacts tests.test_release_workflow_contract tests.test_efficiency tests.test_tool_policy
python3 scripts/smoke-test-release.py --help
python3 scripts/quick_validate.py assets/global/skills/work-plan  # when available
python3 scripts/quick_validate.py assets/global/skills/security-scan  # when available
python3 scripts/gen-manifest.py
make test
make release-smoke
git diff --check
```

The skill validator lives in the Codex skill-creator installation rather than this
repository; use that canonical script if no project-local validator exists.

## Status

- [ ] Proposed
- [ ] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
