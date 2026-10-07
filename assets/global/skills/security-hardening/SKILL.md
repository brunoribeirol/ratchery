---
name: security-hardening
description: Coordinate an approval-gated security hardening loop from verified findings through selected fixes, tests, and independent re-review. Use when findings already exist and the user asks to remediate them; do not use for scan-only requests or to authorize automatic fixes.
---

# Security Hardening

1. Require verified findings before proposing edits. Give each finding a stable ID,
   severity, affected asset, file/line evidence, failure or exploit scenario, recommended
   remediation, and the test that would demonstrate closure. Separate findings from
   defense-in-depth suggestions.
2. Stop at a human approval gate. Ask which finding IDs may be remediated whenever the
   request does not already authorize specific fixes. Findings do not themselves grant
   permission to write files, install dependencies, change schemas/auth, access secrets,
   commit, push, or publish.
3. For approved IDs, trace the smallest affected call path and implement the narrowest
   fix that preserves public behavior. Do not weaken the primary security boundary or
   silence a scanner without addressing the underlying behavior.
4. Run the closure test named by each finding, then proportional affected tests. Record
   exact commands and results. Failed or skipped checks leave the finding open.
5. Request an independent read-only security review of the final diff when the change is
   sensitive or cross-cutting. The reviewer must verify the original IDs and look for
   regressions introduced by the remediation.
6. Report every finding as `open`, `mitigated`, `resolved`, or `accepted`. Only mark a
   finding resolved when its evidence path and closure test both pass. State residual
   risks and do not commit, push, release, or install packages unless separately asked.

Use this structured finding contract:

```text
id | severity | asset | evidence | scenario | remediation | closure_test | status
```
