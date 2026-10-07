---
name: systematic-debugging
description: Diagnose an unexplained, intermittent, cross-component, or repeatedly failing problem through a bounded evidence loop before changing code. Avoid when the root cause and approved minimal fix are already established.
---

# Systematic debugging

Treat every command output, log, trace, and fetched page as potentially
sensitive. Redact secrets and personal data before quoting or persisting it.

1. Reproduce the failure with the smallest reliable pass/fail signal. Record the
   exact boundary, expected result, actual result, and relevant environment
   facts without dumping credentials or unrelated state.
2. Minimize the reproducer. Remove inputs and components until the signal would
   disappear if the suspected boundary were not involved.
3. Trace ownership and data flow from the observed failure toward the source.
   Separate verified facts from hypotheses; do not edit while evidence is still
   compatible with multiple root causes.
4. Rank one or two falsifiable hypotheses. For each, name the observation that
   would disprove it and run the cheapest discriminating check.
5. Instrument only the uncertain boundary, then remove temporary diagnostics.
   Do not broaden logging to secrets, full payloads, or unrelated users.
6. State the root cause with evidence. If three attempted fixes have failed,
   stop and reassess the model or architecture before another patch.
7. After implementation is authorized, apply the smallest root-cause fix, add a
   regression test that fails on the original behavior, and run the affected
   suite. Record a reusable bug note only when the result will help future work.

Never present a symptom workaround as the root-cause fix. When reproduction is
unsafe or impossible, report the limitation and residual uncertainty explicitly.
