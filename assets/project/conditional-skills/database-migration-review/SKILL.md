---
name: database-migration-review
description: Review database schema and migration changes for safety, compatibility, locking, data backfill, rollback, and application sequencing. Use when migrations, ORM schemas, or SQL DDL are involved.
---

# Database Migration Review

- Identify the database engine, migration tool, deployment model, and application compatibility window.
- Check destructive DDL, table rewrites, long locks, default-value backfills, index creation, nullable-to-required transitions, and data conversions.
- Prefer expand/migrate/contract sequencing when zero-downtime compatibility matters.
- Confirm downgrade/rollback expectations rather than assuming every migration is reversible.
- Check transactional behavior and engine-specific limitations.
- Verify corresponding model, query, test, and deployment changes.
- Return risks, sequencing, validation queries, and rollback or forward-fix strategy.
