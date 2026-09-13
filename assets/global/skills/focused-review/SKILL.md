---
name: focused-review
description: Review a change for correctness, security, behavior regressions, and missing tests. Use after risky changes or before merge.
---

1. Review the diff and affected call paths, not the whole repository.
2. Prioritize concrete defects over style opinions.
3. Check authorization, validation, error handling, data integrity, concurrency, migrations, and backward compatibility when applicable.
4. Cite files and line ranges.
5. Separate findings from questions and residual risks.
6. State which checks were not performed.
