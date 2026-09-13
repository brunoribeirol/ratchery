# T2 example: data pipeline

`pipeline/pipeline.py` (extract/transform/load) + `pipeline/schema.py` (event schema
validation) — a small ETL job that reads customer usage events from an
internet-reachable upload endpoint and loads them into an analytics warehouse. No PII, no
payments, no regulatory scope — but the ingestion surface is reachable from the public
internet, which is exactly the `external_exposure` risk fact the Adaptive Engine treats as
Product-tier (T2), not merely a "standard project."

## Why this lands at T2

`.agents/state/risk-answers.json` in this directory:

```json
{
  "users": "external",
  "handles_pii": false,
  "handles_payments": false,
  "life_safety": false,
  "regulated": false,
  "data_sensitivity": "confidential",
  "external_exposure": true,
  "maturity": "active"
}
```

**Criticality score** (`criticality_score()`):

- `_RISK_WEIGHTS["external_exposure"]` → `2` (the only `True` risk flag here — `handles_pii`,
  `handles_payments`, `life_safety`, `regulated` are all `False`).
- `_SENSITIVITY_WEIGHTS["confidential"]` → `3` (partner usage data, not public but not
  restricted/regulated either).
- `_USERS_WEIGHTS["external"]` → `2`.
- Total: **7** (out of 15).

**Complexity score** (`complexity_score()`): two small Python files, `profile()` reports
`size: "small"` → `_SIZE_COMPLEXITY["small"] = 0`. Not a monorepo, no package roots →
**0** (out of 8).

**Tier lookup** (`_base_tier(criticality=7, complexity=0)`): criticality `7` is in the
`>= 6` band, and complexity `0` is `< 6`, so the table returns **T2**
(`"T2" if complexity < 6 else "T3"` branch for the `criticality >= 6` band). No hard floor
applies here — `regulated` and `life_safety` are both `False`, and the explicit
`handles_payments + external_exposure` combo rule doesn't trigger either since
`handles_payments` is `False`. This project reaches T2 purely on the weighted score, not a
floor.

Verified directly against the scorer:

```text
python3 -c "... ae.compute_tier(stub, answers)"
-> {'computed_tier': 'T2', 'criticality_score': 7, 'complexity_score': 0, 'floor_reasons': []}
```

## What T2's `tier_requirements()` demands beyond T1

```python
{
    "spec_mode": "openspec-light",
    "required_docs": ["docs/PROJECT_CONTEXT.md", "docs/decisions/"],
    "required_agents": ["architect", "security-reviewer"],
    "required_skills": ["security-scan", "dependency-audit"],
    "testing_bar": "unit + integration tests for changed behavior, CI required",
    "security_bar": "sandbox + secondary hook + security-reviewer agent on risk-relevant changes",
}
```

This is the first tier where the security posture actually changes: T0/T1 both stop at
"sandbox + secondary hook (framework default)"; T2 adds a mandatory `security-reviewer`
agent pass on risk-relevant changes, plus the `security-scan` and `dependency-audit` skills
as required rather than optional. `docs/decisions/` (ADRs) become required alongside
`docs/PROJECT_CONTEXT.md`, and the testing bar jumps from "smoke tests" to "unit + integration
tests ... CI required" — appropriate for a pipeline whose ingestion endpoint faces the
public internet, even though it never touches PII or payment data.
