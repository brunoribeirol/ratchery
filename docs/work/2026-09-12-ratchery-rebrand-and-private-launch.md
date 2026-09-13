# Work Plan: Ratchetry rebrand and private launch

## Objective

Transform the validated pre-public worktree into Ratchetry, preserve a narrow
upgrade path for the maintainer's existing installation, import only the
release inventory into a new private GitHub repository with clean history, and
exercise hosted publication controls before making anything public.

## Non-goals

- Do not make the repository public without a separate explicit instruction.
- Do not publish a stable release or Homebrew formula before the private
  prerelease and attestations verify.
- Do not add optional infrastructure during a naming/history migration.
- Do not rewrite the frozen `agent-workspace:v8` managed-block format.
- Do not copy `.git`, ignored state, local Vault content, credentials, caches,
  or build output into the new repository.

## Evidence and assumptions

- The user approved Ratchetry as the final identity and asked for a private
  repository until launch readiness.
- The authenticated GitHub profile is configured for `brunoribeirol`, but its
  saved token is invalid and the GitHub API is currently unreachable. Remote
  creation/configuration therefore waits on re-authentication/connectivity;
  local migration work can continue independently.
- The renamed local candidate has passed the isolated integration suite, 311
  unit tests, Ruff, syntax, manifest/pin/link checks, and release smoke. Its
  final inventory is regenerated only after the last reviewed edit.
- The current worktree intentionally contains the previous transformation as
  uncommitted changes. Clean history must be built from a validated inventory,
  not by rewriting or pushing the existing `.git` directory.
- `ratchery` becomes the primary command. The old command is a small migration
  alias, not a second product identity.

## Affected contracts and files

- `bin/`, `install.sh`, runtime/config/state path helpers, release scripts, and
  artifact tests.
- README, contributor/security/publishing docs, templates, examples, Skills,
  workflows, reusable Action metadata, changelog, and license attribution.
- `MANIFEST.json`, `VERSION`, clean repository history, GitHub settings, and
  the future prerelease tag.

## Risks

- A broad text replacement could alter the frozen marker, historical evidence,
  Python import names, or compatibility behavior that must remain stable.
- Migrating local paths could overwrite user state or split one project across
  old/new Vault identities.
- A clean-history copy could silently omit an untracked intended file or include
  ignored/private development state.
- Repository settings may overclaim protection if workflows exist but Rulesets
  or security features are not actually enabled.
- Publishing a tag before the renamed artifact/install paths are exercised
  would create an unrecoverable first-release compatibility mistake.

## Workstreams and ownership

- Primary agent: identity/compatibility design, implementation, integration,
  validation, clean-history construction, GitHub configuration, and reporting.
- Independent reviewers/test agents may be used only when a later sensitive
  review benefits from isolated context and capacity is available.
- Maintainer: complete GitHub device authentication/signing actions and any
  Vault filesystem operation the managed environment cannot perform.

## Acceptance criteria

- A fresh user sees Ratchetry consistently and invokes `ratchery` everywhere.
- Existing managed blocks remain discoverable and `agent-workspace` provides a
  tested compatibility path without creating a permanent duplicate runtime.
- Fresh install, legacy upgrade, rollback, uninstall guidance, memory, doctor,
  benchmarks, release archive, SBOM, and Action all use coherent namespaces.
- Repository-wide stale-name checks leave only reviewed compatibility,
  historical/audit, or source-module occurrences with documented reasons.
- The final manifest-backed source snapshot passes every local gate.
- The new GitHub repository is private, contains no old history/local state,
  and has reviewable thematic commits rather than one bulk import.
- Hosted checks and repository settings are inspected as real remote state.

## Validation plan

Run targeted identity/migration tests first, then compilation, shell syntax,
Ruff, full integration/unit suites, manifest, action pins, Markdown links,
release reproducibility/install smoke, a focused security scan, and clean-tree
inspection. After push, inspect Actions, Rulesets, security features, release
assets, checksums, SBOM, provenance, and tag signature from GitHub itself.

## Handoff

Current state: the local migration and review are complete. Remote creation is
blocked by invalid GitHub authentication/unavailable API, and the current Git
identity has no signing method configured. Do not infer remote success or expose
the repository publicly. Resume clean signed-history creation and the hosted
phase after `gh auth login` and commit/tag signing are configured.
