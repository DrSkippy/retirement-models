import unittest
from datetime import date

from models.expenses import ExpenseCategory, ExpenseLedger, LivingExpenseConfig


class TestExpenseCategory(unittest.TestCase):
    def test_values_are_strings(self):
        self.assertEqual(ExpenseCategory.HOUSING, "housing")
        self.assertEqual(ExpenseCategory.ASSET_OPERATING, "asset_operating")
        self.assertEqual(ExpenseCategory.DEBT_SERVICE, "debt_service")

    def test_all_categories_enumerable(self):
        cats = list(ExpenseCategory)
        self.assertGreaterEqual(len(cats), 8)


class TestExpenseLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = ExpenseLedger()

    def test_initial_total_is_zero(self):
        self.assertAlmostEqual(self.ledger.total(), 0.0)

    def test_add_single_category(self):
        self.ledger.add(ExpenseCategory.HOUSING, 1500.0)
        self.assertAlmostEqual(self.ledger.total(), 1500.0)

    def test_add_accumulates_within_category(self):
        self.ledger.add(ExpenseCategory.FOOD, 300.0)
        self.ledger.add(ExpenseCategory.FOOD, 200.0)
        self.assertAlmostEqual(self.ledger.by_category()[ExpenseCategory.FOOD], 500.0)

    def test_add_multiple_categories(self):
        self.ledger.add(ExpenseCategory.HOUSING, 1000.0)
        self.ledger.add(ExpenseCategory.FOOD, 400.0)
        self.ledger.add(ExpenseCategory.HEALTHCARE, 200.0)
        self.assertAlmostEqual(self.ledger.total(), 1600.0)

    def test_by_category_returns_all_entries(self):
        self.ledger.add(ExpenseCategory.TRANSPORTATION, 250.0)
        by_cat = self.ledger.by_category()
        self.assertIn(ExpenseCategory.TRANSPORTATION, by_cat)
        self.assertAlmostEqual(by_cat[ExpenseCategory.TRANSPORTATION], 250.0)
        # Non-added categories should be zero
        self.assertAlmostEqual(by_cat[ExpenseCategory.ENTERTAINMENT], 0.0)

    def test_by_category_is_copy(self):
        """Mutating the returned dict should not affect the ledger."""
        by_cat = self.ledger.by_category()
        by_cat[ExpenseCategory.HOUSING] = 99999.0
        self.assertAlmostEqual(self.ledger.total(), 0.0)

    def test_living_expenses_excludes_asset_operating_and_debt_service(self):
        self.ledger.add(ExpenseCategory.HOUSING, 1000.0)
        self.ledger.add(ExpenseCategory.FOOD, 400.0)
        self.ledger.add(ExpenseCategory.ASSET_OPERATING, 300.0)
        self.ledger.add(ExpenseCategory.DEBT_SERVICE, 800.0)
        living = self.ledger.living_expenses_total()
        self.assertAlmostEqual(living, 1400.0)

    def test_living_expenses_includes_other_categories(self):
        self.ledger.add(ExpenseCategory.HEALTHCARE, 200.0)
        self.ledger.add(ExpenseCategory.ENTERTAINMENT, 100.0)
        self.ledger.add(ExpenseCategory.TRANSPORTATION, 150.0)
        self.assertAlmostEqual(self.ledger.living_expenses_total(), 450.0)

    def test_asset_operating_total(self):
        self.ledger.add(ExpenseCategory.ASSET_OPERATING, 500.0)
        self.ledger.add(ExpenseCategory.HOUSING, 1000.0)
        self.assertAlmostEqual(self.ledger.asset_operating_total(), 500.0)

    def test_asset_operating_total_zero_when_empty(self):
        self.assertAlmostEqual(self.ledger.asset_operating_total(), 0.0)

    def test_total_equals_sum_of_all_categories(self):
        amounts = {
            ExpenseCategory.HOUSING: 1000.0,
            ExpenseCategory.FOOD: 400.0,
            ExpenseCategory.HEALTHCARE: 200.0,
            ExpenseCategory.ASSET_OPERATING: 300.0,
            ExpenseCategory.DEBT_SERVICE: 500.0,
        }
        for cat, amt in amounts.items():
            self.ledger.add(cat, amt)
        expected = sum(amounts.values())
        self.assertAlmostEqual(self.ledger.total(), expected)


class TestLivingExpenseConfig(unittest.TestCase):
    def test_basic(self):
        cfg = LivingExpenseConfig(monthly_amount=3000.0)
        self.assertAlmostEqual(cfg.monthly_amount, 3000.0)
        self.assertAlmostEqual(cfg.inflation_rate, 0.025)
        self.assertIsNone(cfg.start_date)
        self.assertIsNone(cfg.end_date)

    def test_custom_inflation(self):
        cfg = LivingExpenseConfig(monthly_amount=2000.0, inflation_rate=0.03)
        self.assertAlmostEqual(cfg.inflation_rate, 0.03)

    def test_with_dates(self):
        cfg = LivingExpenseConfig(
            monthly_amount=1500.0,
            start_date=date(2030, 1, 1),
            end_date=date(2055, 1, 1),
        )
        self.assertEqual(cfg.start_date, date(2030, 1, 1))
        self.assertEqual(cfg.end_date, date(2055, 1, 1))


if __name__ == "__main__":
    unittest.main()
