# Changelog

## Unreleased

- No changes yet.

## v1.0.0-rc.1 - 2026-09-12

First private release candidate under the Ratchetry identity. It is intended
for hosted CI, repository-policy, installation, migration, and attestation
verification before the repository becomes public or `v1.0.0` is tagged.

### Changed (Ratchetry identity)

- Renamed the product, repository links, release artifacts, documentation, and
  primary executable to Ratchetry / `ratchery`.
- Fresh installs use `~/.local/share/ratchery`, `~/.config/ratchery`, and
  `~/.local/state/ratchery`. A regular legacy config may be read once and the
  confirmed installer writes the new namespace; legacy runtime/config bytes
  are preserved and the previous runtime is backed up.
- `agent-workspace` remains a compatibility command during the 1.x migration
  window and executes the same installed runtime. Persisted
  `agent-workspace:v8`/`agent-workspace:mcp` markers and the internal
  `agent_workspace.py` hook path remain readable so existing projects refresh
  instead of silently duplicating managed content.
- Managed Skill directories now write `MANAGED_BY_RATCHERY`; the former
  `MANAGED_BY_AGENT_WORKSPACE` sentinel is accepted only as a safe ownership
  proof during upgrade and is replaced on the next managed refresh.
- Removed private pre-publication audit snapshots from the release inventory.
  Their actionable findings remain represented by regression tests, security
  documentation, and these release notes.

### Added (provider-neutral memory handoff)

- `ratchery memory backends/status/doctor/plan` now exposes the built-in
  explicit Vault backend and the separate experimental `ai-memory` evaluation
  path without executing optional binaries or treating their presence as
  activation.
- `ratchery memory handoff write/show/clear` exchanges one bounded,
  revision-aware baton between agent clients through the exact UUID-matched
  Vault project. The schema excludes raw conversations, derives Git/project
  provenance, rejects unsafe paths, duplicate keys, multiline/control data and
  common credential forms, and refuses silent replacement.
- Handoff writes use anchored directory descriptors and private atomic files;
  replacement and explicit clear create no-follow private XDG-state backups. A
  per-project POSIX lock serializes mutations, special files fail without
  blocking, Vault identity is read only from unique real frontmatter, and Git
  provenance disables repository-configured fsmonitor execution. There is no
  lifecycle capture, daemon, MCP, network, model, or QMD-index cost in the
  default path.
- `workspace-save`/`workspace-resume` and the Vault session template now carry
  a concise revision-bound handoff contract. The design was considered during
  the Greenlight review but implemented independently; task queues, PR runners,
  remote approvals, and orchestration remain outside the product.

### Added (release and experiment evidence)

- The release workflow now installs and exercises the exact manifest-backed
  archive before it can reach attestation/publication. The stdlib-only smoke
  command rejects traversal, links, special files, duplicate paths, unsafe
  modes/roots, and oversized archives, then uses an isolated HOME/config/state
  to run the installer, initialize a Git fixture, and parse installed
  `doctor --json` output.
- Benchmark snapshot schema v2 adds an automatic bounded configuration digest
  over effective repository agent policy and runtime facts. Repeated reports
  reject drift within either arm while allowing the baseline and candidate
  configurations to differ intentionally.
- The advisory tool catalog now records `ai-jail` and `ai-memory` as manual,
  experimental candidates with explicit sandbox/network/credential and
  capture/privacy/context limitations. Neither is routed or installed.
- The publication guide defines Homebrew as a post-first-release
  distribution phase and records the required separation between immutable
  formula installation and user-specific Vault onboarding.

### Changed (planning and security skills)

- `work-plan` now requires evidence paths and proportional verification budgets;
  `security-scan` now requires a scoped threat model, trust-boundary tracing,
  bounded adversarial cases, and explicit unreviewed/residual scope.

### Changed (governance visibility)

- CLI security-floor checks no longer fail on a measurement that never happened.
  `command_version()` swallowed every exception, so a version probe that timed out
  (a loaded CI runner, a slow cold start) was indistinguishable from a genuinely
  unusable CLI, and `doctor` reported both as the same hard error -- a security gate
  failing for reasons unrelated to security. `command_version_probe()` now classifies
  the outcome (`absent` / `transient` / `unreadable`), and `cli_security_version_issue()`
  (replacing `cli_security_version_error()`) returns a severity with its message: a
  version read and found below the floor stays an **error**, an incomplete probe becomes
  a **warning** that says the floor is unverified rather than violated. `command_version()`
  keeps its original signature and contract for its other callers.

- **Breaking for T2/T3 projects:** a missing `required_docs` entry is now a `doctor`
  **error** instead of a warning, matching how `required_agents` and `required_skills`
  are already reported. A T2 project without `docs/decisions/`, or a T3 project without
  `docs/SECURITY_REVIEW.md`, previously passed CI with a warning nobody had to act on --
  a requirement that never blocks is governance theatre, and it is the same "requirement
  satisfied by absence" failure the tier derivation already guards against. Create the
  missing document, or lower the tier deliberately with
  `ratchery tier --acknowledge-downgrade "<reason>"`. Documents that are also
  managed files (`docs/PROJECT_CONTEXT.md`) are reported once, not twice.
- An acknowledged tier downgrade now keeps announcing itself. `highest_recorded_tier()`
  deliberately resets the ratchet floor at the last acknowledgement, which also made the
  acknowledgement invisible to every later run: a project downgraded from T3 reported as an
  ordinary T1 forever. `adaptive_engine.acknowledged_downgrade()` and `downgrade_notice()`
  surface the origin tier, date, and recorded rationale in both `tier.md` and `doctor`'s
  warnings, for as long as the project sits below the tier it was downgraded from. The
  notice clears itself once the project is reclassified back up; the ratchet's arithmetic
  is unchanged.
- `doctor --json` gained `commit` and `dirty`, so a stored diagnostic result says which tree
  it describes and can be re-checked against that exact revision. Both degrade to `null`
  outside Git; unlike `benchmark capture`, `doctor` never refuses to run on an unclean or
  shallow checkout. The human-readable output prints the same commit line.
- README now states the project's non-goals with their reasoning, instead of leaving them
  only in `docs/PROJECT_CONTEXT.md` and product steering where contributors do not see them.

### Changed (setup-first foundation)

- Established the product contract around Ratchetry's goal: a
  batteries-included Claude Code + Codex + Obsidian operating layer with broad capability
  available but minimal justified token, permission, dependency, and maintenance cost.
  `docs/PROJECT_CONTEXT.md` is now the canonical scope/non-goal document; README,
  architecture, start-here, and product steering lead with the complete setup while treating
  T0-T3 tiering as its adaptive control plane.
- Split pure project inspection (`inspect_project()`) from stateful profile generation so
  diagnostics can re-evaluate current project facts without creating files.
- `adaptive_engine.evaluate_tier()` now provides a read-only ratchet evaluation shared with
  `classify()`, keeping the write and diagnostic paths on the same tier logic.
- Replaced the unenforced "12 global always-on + 3 global on-demand" Skill split with an
  honest inventory of 15 installed/discoverable global Skills. Their instruction bodies
  still load progressively only when client-side description matching selects them.
- Updated `actions/checkout` and `actions/setup-python` to their Node 24 generations before
  GitHub's Node 20 action-runtime removal.
- Consolidated Python unit-test discovery so newly added `test_*.py` modules run locally and
  in CI without another hand-maintained command entry.
- Removed the uncalled `qmd_version_tuple()` helper and the dormant runtime `SessionEnd`
  Vault writer. The shipped setup has no `SessionEnd` hook; explicit `workspace-save`
  remains the only durable-memory boundary, while legacy log migration remains supported.
- Replaced the 1,291-line baseline `~/Projects/README.md` template with a concise workspace
  index. Installation, architecture, security, and tool guidance now stay in the canonical
  repository docs instead of being duplicated into every user's projects directory.
- Refreshed the two direct dependencies in the runnable FastAPI example to the current
  stable upstream releases; the framework runtime remains Python-stdlib-only and Dependabot
  continues to monitor that example separately.

### Fixed (setup trust boundaries)

- Project lifecycle, tier, agent, MCP, and diagnostic paths now reject
  symlinked/non-regular managed parents and files before reading or writing
  configuration. `doctor` returns the same human/JSON contract on this early
  failure instead of continuing through the unsafe parent.
- A project that explicitly ignores `docs/CURRENT_STATE.md` no longer receives
  the same missing-local-memory warning on every clean clone; absence still
  warns when it was not a deliberate repository policy.
- Claude hooks now use the client's project-directory variable in exec form.
  Codex hook discovery and the runtime's own Git probe scrub caller-controlled
  Git routing; task-policy persistence is anchored to a verified state-directory
  descriptor with private unpredictable temporary files.
- Primary Claude/Codex deny layers now include nested project-local package and
  cloud credential files, not only home-directory and generic secret patterns.
- MCP enable/disable is a prepared multi-file transaction with rollback. Its
  pre-change backups use private modes and project-relative source labels rather
  than disclosing absolute checkout paths.

- `doctor` now derives and validates every stable tier field (`computed_tier`, effective
  ratcheted tier, scores, floor reasons, name, and requirements) instead of trusting editable
  derived values from `.agents/state/tier.json`.
- `doctor` now verifies the shipped Claude permission/sandbox/credential deny layers and the
  actual managed `PreToolUse` binding, plus Codex workspace/global denies, environment
  filters, hooks feature, restricted profile inheritance, and managed `PreToolUse` binding.
  Safe unrelated user additions remain permitted.
- `doctor` no longer writes project-profile state when run against a fresh checkout.
- `preflight`, project `doctor`, and `doctor-global` reject an installed Claude Code older
  than 2.1.187 or Codex CLI older than 0.138.0, the supported floor for Ratchetry's generated
  security-policy contract. Either client may still be absent for a single-client setup.
- Raised the runtime floor to Python 3.11 so Codex TOML security validation is available in
  the standard library on every supported runtime instead of degrading to a warning.
- Risk answers and tier history now fail closed on malformed JSON, unknown fields, invalid
  types/enums, or impossible downgrade records. `doctor --json` preserves valid JSON output
  when reporting those failures.
- `tier`/`tier-set` now rescan current project facts instead of trusting a stale cached
  profile; the read-only scanner ignores symlinked/non-regular files.
- Initial classifications based on absent risk answers are now visibly provisional;
  `doctor`/CI block until a human runs `tier-set` to record reviewed project facts.
- MCP opt-ins are now team-durable through committed `.agents/state/mcp-enabled.json`.
  `mcp enable` configures static, reviewable Claude and Codex definitions, refuses to
  overwrite same-name user config, and project `doctor` detects drift on either client.
- Claude project policy now disables bypass-permissions mode. Ratchetry-managed
  MCP profiles use explicit Claude ask rules and narrow Codex tool allowlists,
  prompt approval, output limits, and timeouts; Serena's executable source is
  pinned to the full commit behind v1.7.0 and its dashboard is disabled.
- Added negative regression tests for removed or no-op security hooks, missing deny layers,
  forged/empty tier state, malformed risk/history state, read-only deep diagnostics, stale
  profiles, external symlinks, required client parity/Skills, and minimum CLI versions.

### Fixed (final pre-publish audit)
- `tests/test_doctor_tier_json.py`: the "non-`--json` output unchanged" tests were smoke
  tests only (checked for the string `"Doctor:"`, never diffed against the actual `--json`
  facts) despite the delta spec claiming byte-level regression coverage. Added
  `test_json_and_text_report_the_same_facts` to both `TestDoctorJson`/`TestTierJson`,
  cross-checking that the JSON payload and the human-text output report identical
  counts/tier/active-agents from the same invocation.
- `assets/global/skills/registry.json` no longer claims three global Skills are operationally
  "on-demand". A later first-principles review found no enable command or installation gate:
  all 15 were copied by `global_guidance()` and eligible for client trigger matching. The
  installer now consumes and validates one exact registry/disk inventory.
- `action.yml`: inputs are now passed via `env:` instead of interpolated directly into the
  inline bash script (closes a script-injection class of bug for third-party consumers of
  this reusable Action, even though nothing in this repo's own usage triggers it today);
  the `GITHUB_OUTPUT` heredoc delimiter is now randomized per run instead of a fixed string,
  and the project path must resolve inside `GITHUB_WORKSPACE`.
- `.github/workflows/ci.yml`: added an explicit `permissions: contents: read` at the
  workflow level instead of relying on the inherited repo/org default token scope; checkout
  no longer persists credentials. The Scorecard job now explicitly retains only the
  `contents: read` scope its checkout needs alongside its two write scopes.
- `docs/specs/fix-repo-inconsistencies.md`'s Validation section claimed a grep for the old
  doc filenames returns "zero hits", which was literally false (contradicted its own Tasks
  section's correctly-scoped historical-file exception two paragraphs above) -- reworded.

### Added
- `ratchery usage` now supports validated ccusage source, period,
  date/project/session, JSON, and offline selection. New `benchmark
  capture/compare` commands persist aggregate-only token/cost/task snapshots
  outside the repository in local XDG state and report cost per successful task
  without storing prompts, responses, session IDs, paths, project labels, or raw
  usage rows. Non-sensitive commit/model/client/task/environment identifiers make
  incompatible A/B arms fail closed. Capture requires a clean `HEAD`; the Git
  value is explicitly documented as capture-time provenance rather than an
  attestation over historical usage.
- Added a bundled, digest-bound `core-suite-v1` with six public task protocols
  and fixtures plus `benchmark suites/show/validate/report`. Repeated reports
  require compatible arms, expose medians/ranges and quality floors, and never
  emit an automatic adoption decision.
- Added `budget check` for offline, aggregate-only daily/session cost, token,
  and spike warnings. It stores nothing and remains advisory unless
  `--enforce` explicitly requests exit 3.
- Added a weekly/manual, credential-free client compatibility canary for the
  minimum-supported and current Claude/Codex packages. It parses generated
  policy without model inference or MCP connection and is intentionally kept
  out of normal pull-request CI.
- `tools.lock.json` is now a schema-validated optional-tool policy catalog with
  family, activation mode, command probe, network posture, and benchmark
  requirement. Added profile/on-demand/experimental decisions for the security
  scanner and output-optimization candidates evaluated in current research; no
  external tool became an automatic dependency.
- `ratchery doctor --json` and `ratchery tier --json`: machine-readable
  output for CI consumption. Human and JSON branches share the same derived
  facts; the human doctor now also prints the commit/dirty provenance described
  above. See
  `docs/specs/ci-json-doctor-gate.md`.
- `action.yml`: a reusable composite GitHub Action that runs `doctor --deep --json` as a
  CI merge gate for downstream projects, closing the gap where tier/doctor compliance
  depended entirely on an agent voluntarily running the CLI in a live session even
  though `.agents/state/tier.json` and friends are already git-committed. See
  `docs/CI_GATE.md`.
- `.github/dependabot.yml`: weekly, grouped bump PRs for the `github-actions` ecosystem --
  Actions were already pinned by commit SHA, but nothing previously bumped those pins.
- `.github/workflows/scorecard.yml`: OpenSSF Scorecard analysis (scheduled weekly + on push
  to `main`), with a badge in `README.md` -- an objective, third-party-verifiable
  supply-chain/security posture signal.
- `README.md`: "Why not just \<X\>?" section -- a short table answering, on the README itself,
  the positioning question previously only answered inside `docs/decision-matrix.md`/
  `docs/research-external.md`.
- `scripts/build-release.py`: deterministic manifest-backed source archive, SPDX 2.3 SBOM,
  release manifest, and checksums, with traversal/symlink/drift rejection and reproducibility
  tests.
- `install.sh` now derives its version from the validated manifest and stages only verified
  manifest entries. Installing from a dirty clone no longer copies `.git`, ignored state,
  or unrelated untracked files into the global runtime.
- `.github/workflows/release.yml`: SHA-pinned SLSA provenance and SBOM attestations, with
  build execution isolated from the release job's `contents: write` token.
- `scripts/verify-action-pins.py` and `docs/PUBLISHING.md`: automated pin enforcement plus
  maintainer/consumer release verification and post-rebrand repository-settings guidance.
- `scripts/verify-doc-links.py`: stdlib-only local Markdown target/fragment checking, now
  enforced by `make verify` and CI instead of relying on one-off audit scripts.

### Fixed

- Benchmark evidence rejects zero-token snapshots and duplicate snapshot names
  within an arm, preventing empty or repeatedly supplied evidence from satisfying
  a multi-trial quality gate. Budget arguments are validated before optional
  ccusage discovery, so invalid input has one deterministic exit contract.
- Manifest/release Git commands scrub repository-routing environment variables;
  `gen-manifest.py --help` is now read-only. The release builder uses the exact
  manifest bytes already validated, refuses nonempty or symlink-selected output
  directories, and publishes an explicit four-file inventory.
- Release privileges are split across a read-only build, a no-checkout/no-shell
  OIDC attestation job, and a contents-write-only publication job. The action-pin
  verifier also requires container actions to use immutable SHA-256 digests.
- RTK guidance now requires replacing an install placeholder with the
  independently verified full commit SHA for reviewed v0.48.0, previews changes first, and
  distinguishes Claude's `PreToolUse` hook from Codex's instruction-file
  integration. Serena is no longer reported installed merely because the `uvx`
  runner exists.
- Benchmark state now rejects relative XDG configuration, a destination that
  resolves inside the project (including through a symlink), path-like evidence
  labels, Git environment redirection, non-finite metrics, incompatible
  provenance, and implicit snapshot replacement. Namespaces bind the durable
  project UUID to the checkout path without persisting that path in a snapshot.
- `tools-status`, `tools-recommend`, and install-guidance commands no longer
  execute optional binaries unless an explicit `--probe` is supported and
  supplied. Recommendations are read-only/advisory; blocked QMD never enters a
  route, and Checkov remains on-demand behind the consolidated Trivy profile.
- Manifest verification and release building now require an exact match with
  the tracked release inventory, preventing a newly tracked file from being
  silently omitted from installation or the source archive.
- Project inspection recognizes notebooks as Data/AI profile evidence and
  nested container/Kubernetes/Terraform/Helm paths as Cloud/IaC evidence without
  reading notebook JSON as source. One-time steering templates no longer freeze
  volatile file/language counts that duplicate the refreshable project profile.
- `lib/agent_workspace.py`: documented, with an explicit comment, that the `"v8"` embedded
  in the managed-block marker constants is a merge-format version frozen independently of
  `VERSION` -- not a stale leftover -- and must not be bumped without a migration path for
  already-installed projects. Mirrored in `docs/ARCHITECTURE.md`. No behavior change.
- `README.md`: removed the misleading global Skill activation counts. All 15 global Skills
  are installed/discoverable with progressively loaded bodies; the 4 project-level Skills
  remain capability-conditional.
- Numbered docs sequence had a gap (`16-REFERENCES.md` jumped straight to
  `18-CONTEXT-TOKENS.md`, no `17-`): renamed `18-CONTEXT-TOKENS.md` -> `17-CONTEXT-TOKENS.md`
  and `19-QMD-SECURITY.md` -> `18-QMD-SECURITY.md` (`git mv`, history preserved), fixed every
  live cross-reference.
