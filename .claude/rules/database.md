---
paths:
  - "**/migrations/**"
  - "**/*.sql"
  - "**/models/**"
  - "**/schema/**"
---
# Database rules
- Treat schema and migration changes as high risk.
- Preserve data, compatibility, reversibility, and transactional safety.
- Inspect existing migration conventions and query plans before optimizing.
- Never mutate production data or credentials from an agent session.
