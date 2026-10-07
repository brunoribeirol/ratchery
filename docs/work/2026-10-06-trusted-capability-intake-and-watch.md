# Work Plan: Trusted capability intake and technology watch

## Objective

Convert ongoing ecosystem research into a bounded, inspectable process while
shipping two immediately useful engineering Skills: test-driven development and
systematic debugging.

## Non-goals

- Do not bulk-copy third-party repositories or install their dependencies.
- Do not activate hosted models, MCP servers, plugins, telemetry, or A2A.
- Do not send repository content, prompts, Vault data, or credentials upstream.
- Do not let scheduled automation write issues, branches, pull requests, or
  repository content.

## Evidence and assumptions

- The current project tier is T1, so a delta spec and smoke tests are required.
- The capability registry and radar introduced by the preceding candidate are
  the compatibility boundary for this stacked change.
- MIT-licensed upstream Skills demonstrate useful workflow patterns, but the
  Ratchetry versions are newly written to match its policy and terminology.
- GitHub repository metadata is useful change-detection evidence, not proof that
  a candidate is safe or valuable.

## Affected contracts and files

- Global Skill registry, Skill assets, routing evals, and goal workflows.
- Technology radar entries and capability documentation.
- New `lib/technology_watch.py`, script adapter, tests, and scheduled workflow.
- Current-state documentation, changelog, and release manifest.

## Risks

- A Skill trigger may be too broad and add unnecessary context.
- A scheduled watcher may leak its token or query arbitrary URLs.
- Upstream metadata may be unavailable or misleading.
- A daily workflow may become noisy without actionable summaries.

Mitigations: negative routing signals, token restricted to `api.github.com`,
strict GitHub URL parsing, bounded response/timeout, read-only permissions,
advisory output, and no automatic promotion.

## Workstreams and ownership

One integration owner handles the work sequentially:

1. Write the two Skills and their deterministic routing fixtures.
2. Integrate them into existing feature/debug workflows.
3. Add reviewed radar entries and the read-only watcher.
4. Validate behavior, security boundaries, packaging, and documentation.

## Acceptance criteria

1. The Skill catalog validates with 18 entries, and positive/negative fixtures
   distinguish TDD/debugging from ordinary edits and known-root-cause fixes.
2. Feature and debugging workflows reference the new Skills without changing
   mutation or approval semantics.
3. Offline watch mode performs no HTTP call and reports the exact curated GitHub
   endpoints it would query.
4. Online mode can query only syntactically valid `github.com/owner/repo`
   entries through `api.github.com`; the authorization header is never emitted.
5. Reports distinguish upstream change, archive state, license mismatch, stale
   review, manual-only sources, and query errors without editing any input.
6. The scheduled workflow has only `contents: read`, uses a pinned checkout,
   and cannot create issues, PRs, releases, or repository changes.
7. Targeted tests and proportionate release checks pass, or unavailable checks
   are recorded as residual risk.

## Validation plan

Run targeted unit tests and Ruff first, followed by workflow/pin validation.
Run the full suite and release smoke only after the repository is fully local.
Do not make live Jev/MCP/plugin calls or install external packages. The online
watcher may be smoke-tested only against public metadata and must not receive
repository content.

## Validation outcome

- Focused capability and watcher tests: 17 passed.
- Full Python discovery: 366 passed; Bash integration also passed.
- Ruff, Python/Bash syntax, 21 immutable Action pins, and 195 Markdown links passed.
- Manifest: 310 files and 1,571,411 bytes verified.
- All 22 Skill routing evals, seven workflows, seventeen radar entries, the offline
  no-network watcher contract, and release smoke passed.
- Local ShellCheck was unavailable; the existing Linux CI jobs remain authoritative.

## Handoff

The implementation is locally complete and release-smoke validated in an exact
inventory snapshot. Apply the final manifest/documentation patch, commit the focused
series, and use the protected pull-request path. Hosted CI, CodeQL, and the scheduled
online metadata query remain post-push evidence; no release or upstream capability was
installed or activated by this work.
