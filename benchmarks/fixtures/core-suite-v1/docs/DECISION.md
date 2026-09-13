# Decision: monetary rounding

Status: accepted

All public monetary totals are represented with `Decimal` and rounded to two
decimal places using `ROUND_HALF_UP`. This makes displayed totals deterministic
and matches the fixture's business contract. Changes to calculation order must
preserve this final rounding behavior.
