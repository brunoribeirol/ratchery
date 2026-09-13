# Delta Spec: Dependabot for Actions, OpenSSF Scorecard, README positioning

> Private-staging follow-up (2026-09-12): the workflow still uploads SARIF to
> the private repository, but `publish_results` is false, its public-results
> OIDC permission is absent, and the README badge is withheld until immediately
> before public launch. The original tasks below describe the public target,
> not the deliberately narrower private-repository state.

Mode: **openspec-light** (T1). Describe only what changes.

## Why

Three real OSS-adoption/supply-chain gaps found while researching what would
make the project better as OSS:

1. GitHub Actions are pinned by commit SHA (good), but nothing bumps those
   pins — a security patch to `actions/checkout`/`actions/setup-python` goes
   unnoticed indefinitely without a human manually re-checking.
2. No objective, third-party-verifiable supply-chain/security posture signal
   exists (OpenSSF Scorecard) for a project whose entire purpose is
   governance/security posture for AI coding agents.
3. The README has no positioning section — the "why not just use Spec Kit /
   OpenSpec / Kiro alone" reasoning already exists in
   `docs/decision-matrix.md`/`docs/research-external.md`, but a prospective
   adopter landing on the README (the primary conversion surface) has no
   visible answer to that question without digging into internal research
   docs.

## What changes

- `.github/dependabot.yml`: new file, `github-actions` ecosystem only
  (no Python ecosystem entry — the project is deliberately stdlib-only, no
  `requirements.txt`/`pyproject.toml` dependencies to track), weekly
  schedule, grouped into a single PR to keep the signal low-noise.
- `.github/workflows/scorecard.yml`: new file, runs
  `ossf/scorecard-action` on a schedule (weekly) plus on push to `main`,
  publishes results to the public OpenSSF API so a badge can reference them.
  Read-only permissions (`contents: read`, `security-events: write` only for
  the SARIF upload to GitHub code scanning — standard Scorecard action
  contract).
- `README.md`: one new badge (Scorecard) in the existing badge row, and one
  new section, "Why not just \<X\>?", placed after "What's in v1.0" and
  before "Canonical paths" — a short table (tool -> one-line reason this
  isn't a thin wrapper around it), sourced from and linking to the existing
  `docs/decision-matrix.md`/`docs/research-external.md` for the full
  reasoning, not duplicating it at length.

## Affected contracts

- New files: `.github/dependabot.yml`, `.github/workflows/scorecard.yml`.
- `README.md`: additive badge + new section; no existing section rewritten.

## Out of scope

- Requesting/displaying the OpenSSF Best Practices Badge (separate,
  manual, self-assessment-based program on bestpractices.dev — worth
  doing later, needs a human to answer the questionnaire, not automatable
  here).
- A Python/pip dependency ecosystem entry in Dependabot — there are no
  Python dependencies to track (stdlib-only is a core, tested project
  property; see `docs/ARCHITECTURE.md`).
- Rewriting or re-deriving `decision-matrix.md`/`research-external.md`
  content — the README section links to them, it does not replace them.

## Tasks

- [x] `.github/dependabot.yml` (github-actions ecosystem, weekly, grouped).
- [x] `.github/workflows/scorecard.yml` (scorecard-action, scheduled +
      push-to-main, SARIF upload). Both third-party action SHAs
      (`ossf/scorecard-action`, `github/codeql-action/upload-sarif`) were
      verified against GitHub's tag API before pinning, not guessed --
      catching and fixing one fabricated-from-memory SHA in the process.
- [x] README: Scorecard badge + "Why not just \<X\>?" section.
- [x] `CHANGELOG.md` (Unreleased section).
- [x] `docs/CURRENT_STATE.md` update.

## Validation

- `python3 -c "import yaml"` not available (stdlib-only project, no PyYAML)
  -- validate `dependabot.yml`/`scorecard.yml` YAML syntax with
  `python3 -c "import json,sys; ..."`? No -- use a plain structural review
  plus GitHub's own schema (both files follow the documented Dependabot v2
  and Scorecard action schemas exactly; no local YAML linter is available
  in this stdlib-only repo, so this is a manual correctness review, stated
  explicitly rather than a claimed-but-unrun check).
- `ruff check` / `make test` unaffected (no Python changed) -- run anyway to
  confirm no regression from touching unrelated files.
- Markdown: visually confirm the new README section renders correctly
  (table syntax) and the new badge URL follows the same pattern as the
  three existing badges.

## Status

- [x] Proposed
- [x] In progress
- [x] Implemented
- [ ] Archived (link the merged PR/commit)
