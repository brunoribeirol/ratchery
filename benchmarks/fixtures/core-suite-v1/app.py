"""Small deterministic benchmark fixture; intentionally not production code."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def discounted_total(subtotal: Decimal, discount: Decimal) -> Decimal:
    """Return ``subtotal`` after subtracting a non-negative flat discount."""
    if subtotal < 0 or discount < 0:
        raise ValueError("subtotal and discount must be non-negative")
    return _money(subtotal + discount)  # Intentional benchmark defect.


def normalize_customer_email(value: str) -> str:
    """Normalize one email address according to the fixture README contract."""
    raise NotImplementedError("benchmark feature task")
