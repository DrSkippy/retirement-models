import unittest

from models.config import TaxConfig
from models.taxes import TaxCalculator, TaxableIncomeBreakdown


class MockAsset:
    """Minimal asset stub for testing TaxCalculator."""

    def __init__(self, tax_class: str, income: float) -> None:
        self.tax_class = tax_class
        self.income = income


class TestTaxableIncomeBreakdown(unittest.TestCase):
    def test_defaults_zero(self):
        b = TaxableIncomeBreakdown()
        self.assertEqual(b.ordinary_income, 0.0)
        self.assertEqual(b.capital_gains, 0.0)
        self.assertEqual(b.social_security, 0.0)


class TestTaxCalculator(unittest.TestCase):
    def setUp(self) -> None:
        self.config = TaxConfig(income=0.37, capital_gain=0.2, social_security=0.153)
        self.calc = TaxCalculator(self.config)

    def test_zero_income(self):
        breakdown = TaxableIncomeBreakdown()
        self.assertAlmostEqual(self.calc.calculate_monthly(breakdown), 0.0)

    def test_ordinary_income_only(self):
        breakdown = TaxableIncomeBreakdown(ordinary_income=1000.0)
        self.assertAlmostEqual(self.calc.calculate_monthly(breakdown), 370.0)

    def test_capital_gains_only(self):
        breakdown = TaxableIncomeBreakdown(capital_gains=500.0)
        self.assertAlmostEqual(self.calc.calculate_monthly(breakdown), 100.0)

    def test_social_security_only(self):
        breakdown = TaxableIncomeBreakdown(social_security=200.0)
        self.assertAlmostEqual(self.calc.calculate_monthly(breakdown), 30.6)

    def test_multi_class_accumulation(self):
        """Regression: taxes must accumulate across classes (+=), not overwrite (=)."""
        breakdown = TaxableIncomeBreakdown(
            ordinary_income=1000.0,
            capital_gains=500.0,
            social_security=200.0,
        )
        taxes = self.calc.calculate_monthly(breakdown)
        expected = 1000.0 * 0.37 + 500.0 * 0.2 + 200.0 * 0.153
        self.assertAlmostEqual(taxes, expected, places=4)
        # Confirm the result is NOT just the last class (the original bug)
        self.assertNotAlmostEqual(taxes, 200.0 * 0.153, places=2)

    def test_build_breakdown_from_assets(self):
        assets = [
            MockAsset("income", 5000.0),
            MockAsset("social_security", 2000.0),
            MockAsset("capital_gain", 1000.0),
        ]
        breakdown = self.calc.build_breakdown_from_assets(assets)
        self.assertAlmostEqual(breakdown.ordinary_income, 5000.0)
        self.assertAlmostEqual(breakdown.capital_gains, 1000.0)
        self.assertAlmostEqual(breakdown.social_security, 2000.0)

    def test_build_breakdown_with_withdrawal(self):
        assets = [MockAsset("income", 1000.0)]
        breakdown = self.calc.build_breakdown_from_assets(assets, withdrawal=500.0)
        self.assertAlmostEqual(breakdown.ordinary_income, 1500.0)

    def test_unknown_tax_class_ignored(self):
        """Assets with unknown tax_class should not raise; they're silently ignored."""
        assets = [MockAsset("unknown_class", 9999.0)]
        breakdown = self.calc.build_breakdown_from_assets(assets)
        self.assertAlmostEqual(breakdown.ordinary_income, 0.0)
        self.assertAlmostEqual(breakdown.capital_gains, 0.0)
        self.assertAlmostEqual(breakdown.social_security, 0.0)

    def test_multiple_assets_same_class(self):
        """Multiple assets in the same class should sum their income."""
        assets = [
            MockAsset("income", 1000.0),
            MockAsset("income", 2000.0),
        ]
        breakdown = self.calc.build_breakdown_from_assets(assets)
        self.assertAlmostEqual(breakdown.ordinary_income, 3000.0)
        taxes = self.calc.calculate_monthly(breakdown)
        self.assertAlmostEqual(taxes, 3000.0 * 0.37, places=4)


if __name__ == "__main__":
    unittest.main()
