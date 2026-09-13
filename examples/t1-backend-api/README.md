# T1 example: standard backend API

A small FastAPI service (`main.py` + `routes/health.py` + `routes/inventory.py`) exposing
inventory lookup/adjust endpoints to a couple of external partner integrations, alongside
internal staff use. It's the "standard project" tier: real usage and real (if modest)
complexity, but no PII, no payments, no regulated data.

Unlike `examples/t0-python-script`, this example ships a
`.agents/state/risk-answers.json` because the *default* risk answers
(`users: "internal"`) would score this as T0 — the point of this example is to show the
smallest set of real-world facts that pushes a project from T0 to T1.

## Why this lands at T1

`.agents/state/risk-answers.json` in this directory:

```json
{
  "users": "external",
  "handles_pii": false,
  "handles_payments": false,
  "life_safety": false,
  "regulated": false,
  "data_sensitivity": "internal",
  "external_exposure": false,
  "maturity": "active"
}
```

**Criticality score** (`criticality_score()`):

- All five `_RISK_WEIGHTS` flags are `False` → `0`.
- `_SENSITIVITY_WEIGHTS["internal"]` → `1`.
- `_USERS_WEIGHTS["external"]` → `2` (partner integrations are outside the org, but not the
  general public — `external`, not `public`).
- Total: **3** (out of 15).

**Complexity score** (`complexity_score()`): three small Python files, `profile()` reports
`size: "small"` → `_SIZE_COMPLEXITY["small"] = 0`. Not a monorepo, no package roots →
**0** (out of 8).

**Tier lookup** (`_base_tier(criticality=3, complexity=0)`): criticality `3` clears the
`>= 3` threshold, and complexity `0` is `< 6`, so the table returns **T1**
(`"T1" if complexity < 6 else "T2"` branch for the `criticality >= 3` band).

Verified directly against the scorer:

```text
python3 -c "... ae.compute_tier(stub, answers)"
-> {'computed_tier': 'T1', 'criticality_score': 3, 'complexity_score': 0, 'floor_reasons': []}
```

## What T1's `tier_requirements()` demands beyond T0

```python
{
    "spec_mode": "openspec-light",
    "required_docs": ["docs/PROJECT_CONTEXT.md"],
    "required_agents": [],
    "required_skills": [],
    "testing_bar": "smoke tests for changed behavior",
    "security_bar": "sandbox + secondary hook (framework default)",
}
```

Compared with T0: a lightweight spec mode is now expected (`openspec-light`, not `none`),
`docs/PROJECT_CONTEXT.md` becomes a required doc rather than merely a nice-to-have, and
there's now an explicit testing bar — smoke tests for changed behavior — where T0 required
none. The security bar is unchanged from T0 (still just the framework's own sandbox +
secondary hook); no extra required agents or skills yet, unlike T2 which adds
`security-reviewer` and `security-scan`.
