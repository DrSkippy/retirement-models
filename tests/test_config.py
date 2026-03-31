import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from models.config import AllocationConfig, TaxConfig, WorldConfig

DAYS_IN_YEAR = 365.25


class TestTaxConfig(unittest.TestCase):
    def test_basic(self):
        cfg = TaxConfig(income=0.37, capital_gain=0.2, social_security=0.153)
        self.assertAlmostEqual(cfg.income, 0.37)
        self.assertAlmostEqual(cfg.capital_gain, 0.2)
        self.assertAlmostEqual(cfg.social_security, 0.153)


class TestAllocationConfig(unittest.TestCase):
    def test_valid(self):
        alloc = AllocationConfig(stock_allocation=0.6, bond_allocation=0.4)
        self.assertAlmostEqual(alloc.stock_allocation + alloc.bond_allocation, 1.0)

    def test_invalid_sum(self):
        with self.assertRaises(ValidationError):
            AllocationConfig(stock_allocation=0.6, bond_allocation=0.3)

    def test_all_stock(self):
        alloc = AllocationConfig(stock_allocation=1.0, bond_allocation=0.0)
        self.assertAlmostEqual(alloc.stock_allocation, 1.0)


class TestWorldConfigFromJson(unittest.TestCase):
    def test_production_config(self):
        cfg = WorldConfig.from_json("./configuration/config.json")
        self.assertEqual(cfg.birth_date, date(1966, 5, 25))
        self.assertEqual(cfg.spouse_birth_date, date(1969, 5, 22))
        self.assertEqual(cfg.retirement_age, 67)
        self.assertAlmostEqual(cfg.inflation_rate, 0.025)
        self.assertAlmostEqual(cfg.savings_rate, 0.2)
        self.assertAlmostEqual(cfg.withdrawal_rate, 0.04)

    def test_production_tax_classes(self):
        cfg = WorldConfig.from_json("./configuration/config.json")
        self.assertAlmostEqual(cfg.tax_classes.income, 0.37)
        self.assertAlmostEqual(cfg.tax_classes.capital_gain, 0.2)
        self.assertAlmostEqual(cfg.tax_classes.social_security, 0.153)

    def test_production_allocation(self):
        cfg = WorldConfig.from_json("./configuration/config.json")
        self.assertAlmostEqual(
            cfg.allocation.stock_allocation + cfg.allocation.bond_allocation, 1.0
        )

    def test_retirement_date_computed(self):
        cfg = WorldConfig.from_json("./configuration/config.json")
        expected = date(1966, 5, 25) + timedelta(days=67 * DAYS_IN_YEAR)
        self.assertEqual(cfg.retirement_date, expected)

    def test_test_config(self):
        cfg = WorldConfig.from_json("./tests/test_config/test.json")
        self.assertEqual(cfg.birth_date, date(1970, 1, 1))
        self.assertEqual(cfg.retirement_age, 65)
        self.assertIsNotNone(cfg.retirement_date)
        expected = date(1970, 1, 1) + timedelta(days=65 * DAYS_IN_YEAR)
        self.assertEqual(cfg.retirement_date, expected)

    def test_start_end_dates(self):
        cfg = WorldConfig.from_json("./tests/test_config/test.json")
        self.assertEqual(cfg.start_date, date(2025, 1, 1))
        self.assertEqual(cfg.end_date, date(2055, 1, 1))


if __name__ == "__main__":
    unittest.main()
