# Spec: {{title}}

Mode: **speckit-full** (T3 required). Full phase-gated flow, reimplementing the pattern
researched from GitHub Spec Kit's six-step workflow (see `docs/research-external.md`
section 3) -- this is a native template, not a dependency on that project or its CLI.

Do not skip a phase for a T3 change. Each phase gate must be reviewed (by a human, or by
the `architect`/`security-reviewer`/`qa` agents this tier requires) before moving to the next.

## 1. Principles

<what invariants must hold no matter how this is implemented -- security, data integrity,
backward compatibility, regulatory constraints from `.agents/state/risk-answers.json`>

## 2. Specify

<the requirement in full: user-facing behavior, edge cases, error states, non-functional
requirements (performance, availability, auditability)>

## 3. Design / Plan

<architecture: components touched, data flow, interfaces, chosen approach and rejected
alternatives with rationale (link an ADR via `record-decision` for any non-obvious choice)>

## 4. Tasks

- [ ] <task, smallest independently-reviewable unit>
- [ ] <task>

## 5. Implement

<link commits/PRs as they land; do not mark a task done without a passing validation step>

## 6. Validate / Converge

<the exact tests/checks that prove every principle in section 1 held; explicit sign-off
line for each required agent: architect / security-reviewer / qa>

## Status

- [ ] Principles agreed
- [ ] Specified
- [ ] Designed
- [ ] Tasks broken down
- [ ] Implemented
- [ ] Validated and converged
