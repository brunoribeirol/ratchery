# T0 example: personal script

`main.py` is a two-file, no-dependency word-frequency counter. It's a prototype tool for
personal use: no users but the author, no network exposure, no sensitive data of any kind.
There is no `.agents/state/risk-answers.json` checked in here on purpose — this example
demonstrates what `ratchery tier` computes with the **default** risk answers, which
is exactly the point: a project like this should need zero setup to land at the lowest tier.

## Why this lands at T0

`ae.load_risk_answers()` falls back to `DEFAULT_RISK_ANSWERS` when no
`.agents/state/risk-answers.json` exists:

```python
DEFAULT_RISK_ANSWERS = {
    "users": "internal", "handles_pii": False, "handles_payments": False,
    "life_safety": False, "regulated": False, "data_sensitivity": "internal",
    "external_exposure": False, "maturity": "prototype",
}
```

**Criticality score** (`criticality_score()`, weights from `lib/adaptive_engine.py`):

- All five `_RISK_WEIGHTS` flags (`handles_pii` 3, `handles_payments` 4, `life_safety` 6,
  `regulated` 4, `external_exposure` 2) are `False` → contributes `0`.
- `_SENSITIVITY_WEIGHTS["internal"]` → `1`.
- `_USERS_WEIGHTS["internal"]` → `0`.
- Total: **1** (out of a max of 15).

**Complexity score** (`complexity_score()`): this project is two files, well under every
threshold in `_SIZE_COMPLEXITY`, so `profile()` reports `size: "small"` → `_SIZE_COMPLEXITY["small"]
= 0`. Not a monorepo, no package roots → **0** (out of a max of 8).

**Tier lookup** (`_base_tier(criticality=1, complexity=0)`): criticality `1` is below the
`>= 3` threshold for T1, and complexity `0` is below the `>= 3` threshold for a
complexity-driven T1/T2, so the table falls through to the default: **T0**.

Verified directly against the scorer:

```text
python3 -c "... ae.compute_tier(stub, DEFAULT_RISK_ANSWERS)"
-> {'computed_tier': 'T0', 'criticality_score': 1, 'complexity_score': 0, 'floor_reasons': []}
```

## What T0's `tier_requirements()` demands

```python
{
    "spec_mode": "none",
    "required_docs": [],
    "required_agents": [],
    "required_skills": [],
    "testing_bar": "none required",
    "security_bar": "sandbox + secondary hook (framework default)",
}
```

Nothing beyond the framework's own always-on defaults (the OS sandbox + the secondary
`PreToolUse` hook, present for every tier). No extra required docs, no extra required
agents/skills, no CI/testing bar. Compare with T1, which already requires
`docs/PROJECT_CONTEXT.md` and a "smoke tests for changed behavior" bar — a script this small
genuinely doesn't need either.
