# Store Total Fixture

This dependency-free Python fixture exposes two public helpers in `app.py`.

- `discounted_total(subtotal, discount)` subtracts a flat discount, rejects
  negative inputs, and returns a monetary value rounded to two decimal places.
- `normalize_customer_email(value)` strips surrounding whitespace, lowercases
  the address, and rejects values that do not contain exactly one `@`.

The committed fixture intentionally contains one arithmetic defect and one
unimplemented helper. Each benchmark task must start from a fresh checkout or
worktree at the recorded commit so relative commands and Git cleanliness checks
remain meaningful.

The rounding decision and its rationale live in `docs/DECISION.md`.
