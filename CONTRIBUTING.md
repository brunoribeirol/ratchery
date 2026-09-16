# Contributing to Ratchetry

Thanks for taking the time to contribute. This project is a Python-stdlib-only
CLI and installer, so the bar for changes is: correct, dependency-free, and
consistent with the existing architecture.

## Language

Code, docs, commit messages, and PRs are English-only. An earlier version of
this repository shipped a full Portuguese guide
(`GUIA-COMPLETO-PT-BR.md`); it was removed to keep a single source of truth
in English rather than maintain two guides that would drift apart. If you'd
like to translate the docs, open an issue first to discuss where translated
content should live (a separate file/directory, not a fork of the existing
guides) before submitting a PR.

## Workflow

1. Fork the repository and create a branch off `main` (do not commit directly
   to `main`).
   - `feature/<short-description>` for new functionality
   - `fix/<short-description>` for bug fixes
   - `docs/<short-description>` for documentation-only changes
2. Make the smallest defensible change that solves the problem. Preserve
   existing architecture and coding style unless there is a clear reason to
   change it, and explain that reason in the PR description.
3. Run the test suite locally before opening a PR (see below).
4. Open a PR against `main` using the pull request template. Fill in every
   checklist item honestly — do not check a box for something you didn't
   verify.

Feature PRs opened without a corresponding issue labeled `accepted` risk not
being reviewed — open an issue first so the maintainer can confirm the
direction before you invest time in a PR. Bug fixes and docs-only changes
don't need this.

## Running the tests

Run the portable CI gates in one command:

```bash
make test
```

Or the individual pieces it runs, if you're narrowing down a failure:

```bash
bash tests/run-tests.sh                    # integration suite (installer, hooks, Vault, security)
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile lib/*.py             # byte-compile check
ruff check lib/ scripts/ tests/ bin/       # lint (pip install ruff==0.6.2 to match ci.yml)
python3 scripts/verify-manifest.py         # MANIFEST.json matches the tracked tree
python3 scripts/verify-action-pins.py      # every external Action uses a full commit SHA
python3 scripts/verify-doc-links.py        # local Markdown paths and heading fragments
make shellcheck                            # required for shell changes; installed on Linux CI
```

GitHub's Linux matrix legs run ShellCheck as a blocking gate. It is kept out of
`make test` only because it is not preinstalled on every supported contributor
host; install it and run `make shellcheck` whenever a listed shell file changes.
The separate least-privilege CodeQL workflow performs Python source analysis on
pull requests and `main` pushes.

All applicable checks above must pass before a PR is opened. If you add new behavior,
add or extend tests that cover it — untested behavior changes will be asked
to add coverage in review.

## Code style

- **Python stdlib only.** No new third-party dependencies (`pip install`
  targets, `requirements.txt` entries, vendored packages) without discussion
  in an issue first. This project's entire value proposition is that it runs
  on supported Python 3.11+ runtimes, with nothing else to install.
- Match the existing style in `lib/` (`agent_workspace.py`,
  `adaptive_engine.py`, `context_engine.py`, `efficiency.py`, `tool_router.py`,
  `hook_runtime.py`): type hints, small focused functions, `pathlib.Path`
  over string paths, deterministic behavior over cleverness.
- Do not rewrite whole files for small changes — prefer focused diffs.
- Add docstrings/comments for non-obvious logic, especially anything touching
  the Adaptive Engine's tiering rules or the hook runtime's security guards.
- Shell scripts (`install.sh`, `tests/run-tests.sh`) must remain
  `bash -n`-clean and POSIX-cautious; they run on both Linux and macOS.

## Adding a new Skill or Agent

Skills and Agents ship as templates that the installer copies into a target
project, so a new one needs to exist in the asset tree, not just be described
in docs:

- Global Skills live under `assets/global/skills/`.
- Project-level Agents are mirrored in two places and must stay in sync:
  - `assets/project/.claude/agents/` (Claude Code agent definitions)
  - `assets/project/.codex/agents/` (Codex CLI agent definitions)

When adding a new Skill or Agent:

1. Add the asset file(s) in the correct location(s) above, following the
   format of existing entries.
2. If it's an Agent, add both the `.claude/agents/*.md` and the
   `.codex/agents/*.toml` mirror — the two CLIs must offer equivalent
   capability, not just one of them.
3. Update `README.md`'s roster listing if the change is user-facing.
4. Add or update the relevant test coverage (`tests/test_*.py`) if the change
   affects installer or engine behavior, not just static asset content.

## Proposing a new Tool Router integration

`lib/tool_router.py` routes tasks to external tools (Serena, Context7,
ast-grep, Graphify, RTK, etc.) deliberately and conservatively — nothing is
wired in as a default just because it exists. A new integration proposal
should go through a decision-matrix pattern before code is written, covering
at minimum:

- **What it solves** — the concrete capability gap, not "it's popular."
- **Maturity** — release history, maintenance activity, known CVEs/issues.
- **License** — must be compatible with distributing this project under MIT.
- **Footprint** — what it adds to install size, startup cost, and whether it
  requires network access or a mandatory background process.
- **Dual-CLI compatibility** — the integration (or an equivalent) must be
  usable from both Claude Code and Codex CLI, or explicitly scoped to one
  with a documented reason.
- **Data and command boundary** — what repository/session metadata leaves the
  machine, which credentials it needs, and whether it can execute or rewrite
  commands.
- **Overlap and evidence** — which existing family it duplicates and an A/B
  protocol measuring cost per successful task, not the vendor's percentage.

If accepted for the catalog, add a `tools.lock.json` entry with `family`,
`activation`, `commands`, `network`, `benchmark`, HTTPS `source`, and `policy`.
External tools cannot be `always`; output/retrieval optimizers start as
`experimental` until local repeated evidence justifies promotion. See
`docs/BENCHMARKING.md`.

This project maintains `docs/decision-matrix.md`, which records this
evaluation for every integration decided so far (backed by
`docs/research-external.md`'s per-tool diligence). Add your integration's
evaluation there. If you're working from a tree where it's missing for some
reason, that's fine — follow the pattern above in
your PR description, and consider adding the file as part of your
contribution.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Context7 profile wiring to tool router
fix: resolve macOS mktemp symlink mismatch in run-tests.sh
docs: clarify T2 tier security bar in README
test: cover T3 spec-mode requirement in adaptive engine tests
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Keep the
subject line under ~72 characters; add a body when the "why" isn't obvious
from the diff.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). A **breaking
change** (major version bump) is, specifically for this project: a schema
change to any file under `.agents/state/*.json` that isn't backward-compatible,
removal or renaming of a CLI subcommand, or a change to the file layout
`init`/`refresh` generates in a target project. Concretely:

- Adding a new optional field to a `.agents/state/*.json` schema, or a new
  subcommand/flag, is not breaking.
- Renaming/removing a field an existing consumer reads, renaming/removing a
  subcommand, or moving/renaming files that `init`/`refresh` write into a
  project (`AGENTS.md`, `.claude/`, `.codex/`, `.agents/steering/`, etc.) is
  breaking.

## Release cadence

Releases are ad-hoc — there is no fixed schedule or cadence. See
`docs/ROADMAP.md` for what's shipped versus under consideration.

## Cutting a release

1. Add a dated `## vX.Y.Z` entry to the top of `CHANGELOG.md` listing what changed.
2. Bump `VERSION` in `lib/agent_workspace.py`; `scripts/gen-manifest.py` and
   the installer derive their version from that runtime source of truth.
   `scripts/gen-manifest.py` derives its version from the runtime. Run it and
   commit the regenerated `MANIFEST.json` in the same PR.
3. Merge that PR to `main`.
4. Sign the merged commit's tag and push it: `git tag -s vX.Y.Z -m "vX.Y.Z" <commit> && git
   push origin vX.Y.Z`. Never move or re-push an existing tag — cut a new version instead,
   even for a small fix.
5. Pushing the tag triggers `.github/workflows/release.yml`, which verifies the tag matches
   `VERSION` and that `MANIFEST.json` is accurate; builds a deterministic archive, SPDX SBOM,
   and checksums; creates provenance/SBOM attestations; and publishes all release assets with
   auto-generated notes. Follow the full procedure and repository-settings checklist in
   `docs/PUBLISHING.md`.

The public repository requires verified signed commits on `main`. Configure Git commit
signing before contributing; an unsigned commit may need to be rebased and re-signed before
GitHub can merge it.

## Known limitations

- No co-maintainer yet; see `MAINTAINERS.md`. Final decisions rest with a
  single maintainer.
- `docs/decision-matrix.md` is historical design provenance, while
  `docs/research-external.md` reflects ecosystem research
  from a point in time — re-check tool
  maturity/adoption signals (especially any tool flagged there as
  not-yet-independently-verified) before relying on them further out.
- MCP profile wiring (`ratchery mcp enable/disable/status`), RTK
  opt-in, and the `spec-driven-change` Skill remain tested in this
  project's own development, not yet battle-tested across many independent
  real projects over time.
- No demo GIF/asciinema in the README yet — the single highest-leverage
  discoverability gap, and not something reliably automatable; needs a
  human with a real terminal-recording tool.

## Security-relevant changes

If your change touches `lib/hook_runtime.py`, sandbox/permission
configuration in `assets/project/.claude/settings.json` or the Codex
equivalent, or anything that affects what an agent can read/execute, flag it
explicitly in the PR (the PR template has a checkbox for this) and see
`SECURITY.md` for the threat model this project assumes. Do not change
either of those two files, or the security-invariant checks in
`doctor_project()` (`lib/agent_workspace.py`), without that explicit scope.

## This repo runs its own tooling on itself

This project has been initialized with `ratchery init` on itself, so
`AGENTS.md`, `CLAUDE.md`, `.claude/`, `.codex/`, `.agents/steering/`, and
`.claudeignore` at the repo root are the framework's own output, not hand-written.
Treat `ratchery refresh` as the way to update them, not manual edits inside
the managed blocks.

Two deliberate exceptions to the framework's own defaults, both in `.gitignore`
(see its own comments for exactly how each negation is wired):

- `.agents/state/tier.json`, `tier.md`, `tier-history.jsonl`, `risk-answers.json`,
  `active-agents.json`, `ownership.json`, `project-id`, and `mcp-enabled.json`
  are committed, even
  though `.agents/state/` is normally local-only, gitignored state. This repo
  *is* the Adaptive Engine's showcase, so its own tier classification and the
  ratchet's audit trail are meant to be visible as a live example, not just
  described in docs -- and `ownership.json`/`project-id` specifically are also
  required by `doctor`'s own checks, so excluding them breaks a fresh clone.
  Only `project-profile.json` stays ignored; it's regenerated
  bookkeeping with no demonstration value.
- `docs/CURRENT_STATE.md`, the opposite direction: normally committed
  (`ratchery init` installs it expecting a project to track it), it is
  deliberately *not* committed in this repo. It holds session-to-session
  development notes for whoever is actively working on this codebase, not
  something a downstream user or contributor needs to see -- contributor-
  relevant limitations live in "Known limitations" above instead. The file
  still exists locally and `doctor` still requires it to be present on disk;
  only its git-tracking status changed.

If you change `.agents/state/risk-answers.json` and it moves the tier, re-run
`ratchery tier --path .` and commit the resulting `tier.json`/`tier.md`/
`tier-history.jsonl` together with the reason in your commit message — the same
way the ratchet expects any downgrade to be justified.
