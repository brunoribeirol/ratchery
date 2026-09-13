---
name: spec-driven-change
description: Write a tier-appropriate spec before implementing a non-trivial change -- a lightweight delta spec at T1/T2, a full phase-gated spec at T3. Use when `.agents/state/tier.json` requirements.spec_mode is not "none" and the change is more than a trivial edit. Do not use for T0 projects or trivial fixes -- use work-plan instead.
---

1. Read `.agents/state/tier.json`. Its `requirements.spec_mode` says which mode applies:
   - `none` (T0): do not use this skill. Use `work-plan` if the task is complex enough to warrant a plan at all.
   - `openspec-light` (T1/T2): copy `docs/specs/DELTA_SPEC_TEMPLATE.md` to `docs/specs/<slug>.md` and fill only the delta -- what changes, not the whole system. This mirrors OpenSpec's diff-based context strategy: keep it short, do not restate unaffected behavior.
   - `speckit-full` (T3): copy `docs/specs/FULL_SPEC_TEMPLATE.md` to `docs/specs/<slug>.md` and complete every phase gate in order (principles -> specify -> design -> tasks -> implement -> validate). Do not skip a phase.
2. For `speckit-full`, do not move to the next phase until the current one is reviewed -- by a human, or by the `architect`/`security-reviewer`/`qa` agents this tier already requires per `tier_requirements()`.
3. Keep the spec file as the source of truth for scope; if implementation reveals the spec was wrong, update the spec first, then continue.
4. Never duplicate this content into an ADR -- use `record-decision` only for a specific non-obvious choice made while executing the spec, and link back to the spec file.
5. Archive (mark Status: Archived) once merged; do not delete completed specs -- they are durable evidence of what was decided and why.
