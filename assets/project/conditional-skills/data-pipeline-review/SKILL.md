---
name: data-pipeline-review
description: Review a data engineering pipeline for correctness, idempotency, schemas, lineage, partitioning, data quality, observability, retries, and cost. Use only in repositories with meaningful data-pipeline signals.
---

# Data Pipeline Review

Review the actual architecture rather than imposing a generic medallion pattern.

- Trace sources, transformations, orchestration, destinations, schemas, and ownership.
- Check idempotency, incremental behavior, late or replayed data, partition strategy, deduplication, and backfills.
- Check schema contracts, nullability, keys, quality tests, lineage, freshness, retries, and alerting.
- Check secrets, PII, access boundaries, retention, and destructive data operations.
- Check warehouse/lake query cost and avoid full scans when design evidence suggests a cheaper pattern.
- Verify testability and local/reproducible execution.
- Return prioritized findings with affected files and concrete validation steps.
