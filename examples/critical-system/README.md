# critical-system example: life-safety hard floor

`main.py` + `shutoff.py` — a tiny controller that arms and triggers a physical
emergency-shutoff relay for an industrial line. It's used only by plant staff on an internal
network: not public, no PII, no payments, no explicit regulatory scope. By every *weighted*
risk signal this would otherwise be a low-to-mid tier project. This is deliberately the
example where a single fact — `life_safety: true` — overrides the weighted score entirely,
via the hard-floor mechanism, to demonstrate that mechanism concretely rather than just
reaching T3 by accumulating enough weighted points (contrast with `examples/t3-ai-application`,
where T3 is reached by score alone and the floor never actually has to fire).

## Why this lands at T3 — and why via the floor, not the score

`.agents/state/risk-answers.json` in this directory:

```json
{
  "users": "internal",
  "handles_pii": false,
  "handles_payments": false,
  "life_safety": true,
  "regulated": false,
  "data_sensitivity": "internal",
  "external_exposure": false,
  "maturity": "stable"
}
```

**Criticality score** (`criticality_score()`):

- `_RISK_WEIGHTS["life_safety"]` → `6` (the only `True` risk flag here).
- `_SENSITIVITY_WEIGHTS["internal"]` → `1`.
- `_USERS_WEIGHTS["internal"]` → `0`.
- Total: `6 + 1 + 0` = **7** (out of 15).

**Complexity score** (`complexity_score()`): two small Python files, `profile()` reports
`size: "small"` → `_SIZE_COMPLEXITY["small"] = 0`. Not a monorepo, no package roots →
**0** (out of 8).

**Tier lookup, before the floor** (`_base_tier(criticality=7, complexity=0)`): criticality
`7` is in the `>= 6` band and complexity `0` is `< 6`, so the *base* table alone would
return **T2** — same band `examples/t2-data-pipeline` lands in.

**The hard floor is what changes the outcome.** `_HARD_FLOORS = {"life_safety": "T3",
"regulated": "T2"}`. `compute_tier()` runs the floor loop after `_base_tier()`:

```python
for key, floor in _HARD_FLOORS.items():
    if answers.get(key) and TIERS.index(floor) > TIERS.index(tier):
        tier = floor
        floor_reasons.append(f"{key}=true forces minimum {floor}")
```

`life_safety` is `True` and `TIERS.index("T3") > TIERS.index("T2")`, so `tier` is raised from
T2 to **T3** and `floor_reasons` records exactly why:
`["life_safety=true forces minimum T3"]`. This is the framework's explicit design intent —
a single unmitigated life-safety fact is disqualifying at low rigor *by itself*, regardless
of how modest every other risk/complexity signal looks.

Verified directly against the scorer:

```text
python3 -c "... ae.compute_tier(stub, answers)"
-> {'computed_tier': 'T3', 'criticality_score': 7, 'complexity_score': 0,
    'floor_reasons': ['life_safety=true forces minimum T3']}
```

(Compare: `examples/t3-ai-application` reaches T3 with `floor_reasons: []` — its criticality
score of 14 already clears the `>= 10` threshold on its own, so the `regulated` hard floor
there never has to do any work. This example is the one where the floor mechanism is
observably load-bearing.)

## What T3's `tier_requirements()` demands

Same as `examples/t3-ai-application` — T3 requirements are tier-wide, not scenario-specific:

```python
{
    "spec_mode": "speckit-full",
    "required_docs": ["docs/PROJECT_CONTEXT.md", "docs/decisions/", "docs/SECURITY_REVIEW.md"],
    "required_agents": ["architect", "security-reviewer", "qa"],
    "required_skills": ["security-scan", "dependency-audit", "architecture-map"],
    "testing_bar": "unit + integration + regression tests required, CI required, human review before merge",
    "security_bar": "sandbox + secondary hook + mandatory security-reviewer sign-off + CodeGuard rules (if installed)",
}
```

This is exactly the point of the ratchet-adjacent hard-floor design: a project that "looks"
like a T2 by weighted score but touches physical safety does not get T2's lighter bar
(`security-reviewer` only "on risk-relevant changes", no mandatory `docs/SECURITY_REVIEW.md`,
no required `qa` agent) — it gets T3's full bar, including mandatory human review before
merge, unconditionally.
