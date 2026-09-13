# T3 example: AI application handling PII

`main.py` (FastAPI app, one endpoint) + `models/user.py` (a Pydantic `UserProfile` model
holding name, email, and date of birth) — a small AI-assisted profile-completion feature
open to the general public. It directly touches personal data and operates under explicit
regulatory scope, which is enough on its own to make this a Critical/regulated-system
(T3) project regardless of how small the codebase is.

## Why this lands at T3

`.agents/state/risk-answers.json` in this directory:

```json
{
  "users": "public",
  "handles_pii": true,
  "handles_payments": false,
  "life_safety": false,
  "regulated": true,
  "data_sensitivity": "internal",
  "external_exposure": true,
  "maturity": "active"
}
```

**Criticality score** (`criticality_score()`):

- `_RISK_WEIGHTS["handles_pii"]` → `3`.
- `_RISK_WEIGHTS["regulated"]` → `4`.
- `_RISK_WEIGHTS["external_exposure"]` → `2`.
- (`handles_payments` and `life_safety` are `False` → `0` each.)
- `_SENSITIVITY_WEIGHTS["internal"]` → `1` (the request/response payload itself isn't marked
  confidential/restricted at the field level here, even though PII is present — sensitivity
  and the `handles_pii` flag are independent inputs).
- `_USERS_WEIGHTS["public"]` → `4`.
- Total: `3 + 4 + 2 + 1 + 4` = **14** (out of 15, the cap in `criticality_score()`).

**Complexity score** (`complexity_score()`): two small Python files, `profile()` reports
`size: "small"` → `_SIZE_COMPLEXITY["small"] = 0`. Not a monorepo, no package roots →
**0** (out of 8).

**Tier lookup** (`_base_tier(criticality=14, complexity=0)`): criticality `14` clears the
`>= 10` threshold, so the table returns **T3** directly — `if criticality >= 10: return "T3"`
is the very first check in `_base_tier()`, before complexity is even consulted.

Because the base score already reaches T3 on its own, `_HARD_FLOORS["regulated"] = "T2"` plays
no additional role here — the floor loop only raises the tier when the current tier's index
is below the floor's index (`TIERS.index("T2") > TIERS.index("T3")` is `False`). `regulated:
true` is doing double duty in this example: it contributes `4` points to the weighted score
*and* would independently guarantee a minimum of T2 even if every other answer were at its
lowest-risk default — see `examples/critical-system` for a case where a hard floor is the
thing that actually changes the outcome.

Verified directly against the scorer:

```text
python3 -c "... ae.compute_tier(stub, answers)"
-> {'computed_tier': 'T3', 'criticality_score': 14, 'complexity_score': 0, 'floor_reasons': []}
```

## What T3's `tier_requirements()` demands beyond T2

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

The jump from T2 is significant: full phase-gated spec mode (`speckit-full`, not
`openspec-light`), a mandatory `docs/SECURITY_REVIEW.md`, a `qa` agent added to the required
roster, regression tests and **human review before merge** required (not just CI), and the
`security-reviewer` sign-off becomes mandatory rather than "on risk-relevant changes." This
is the rigor level appropriate for a service that stores real people's names, emails, and
dates of birth and is reachable by the public.
