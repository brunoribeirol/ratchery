from __future__ import annotations

import unittest
from decimal import Decimal

from app import discounted_total, normalize_customer_email


class DiscountedTotalTests(unittest.TestCase):
    def test_subtracts_flat_discount(self):
        self.assertEqual(
            discounted_total(Decimal("100.00"), Decimal("15.00")),
            Decimal("85.00"),
        )

    def test_rejects_negative_inputs(self):
        with self.assertRaises(ValueError):
            discounted_total(Decimal("-1"), Decimal("0"))


class NormalizeEmailTests(unittest.TestCase):
    def test_strips_and_lowercases(self):
        self.assertEqual(
            normalize_customer_email("  Owner@Example.COM "),
            "owner@example.com",
        )

    def test_requires_exactly_one_at_sign(self):
        for value in ("missing.example.com", "two@@example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_customer_email(value)


if __name__ == "__main__":
    unittest.main()
