---
paths:
  - "tests/**"
  - "**/*test*.*"
  - "**/*spec*.*"
---
# Test rules
- Test observable behavior and failure modes, not incidental implementation details.
- Reuse existing fixtures and factories.
- Run targeted tests before broad suites.
- Do not weaken assertions merely to make a failure disappear.
