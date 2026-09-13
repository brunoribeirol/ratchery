---
name: work-plan
description: Plan a complex, risky, cross-module, migration, security, architecture, or multi-agent task before implementation.
---

1. Establish objective, non-goals, assumptions, affected contracts, risks, and
   observable acceptance criteria.
2. Give each acceptance criterion an evidence path: the implementation boundary to
   inspect, the behavior or invariant to exercise, and the result that would prove it.
   A command name alone is not evidence when its assertions do not cover the risk.
3. Set a proportional verification budget before implementation: cheapest targeted
   checks first, broader suites for cross-cutting or high-impact changes, explicit stop
   conditions for costly/external work, and skipped checks recorded as residual risk.
4. Identify the smallest initial file set; expand it only when callers, contracts, or
   failing evidence require more context.
5. Split only genuinely independent workstreams and keep one integration owner. Use
   read-only explorer/reviewer agents only when noisy investigation benefits from
   isolated context enough to justify their token cost.
6. Write the plan to `docs/work/YYYY-MM-DD-<slug>.md` using the template.
7. Update assumptions, scope, and evidence paths when findings change. Do not create a
   plan for trivial edits, and do not mark acceptance complete without the named proof.
