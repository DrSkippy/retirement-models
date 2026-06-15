import unittest
from datetime import datetime, date

import pandas as pd

from models.scenarios import *

FMT = "%Y-%m-%d"

class MyTestCase(unittest.TestCase):
    def test_model_setup(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        self.assertEqual(m.birth_date, datetime.strptime("1970-01-01",FMT).date())  # add assertion here
        self.assertEqual(m.spouse_birth_date,  datetime.strptime("1980-01-01",FMT).date() )  # add assertion here
        self.assertEqual(m.start_date, datetime.strptime("2025-01-01",FMT).date() )  # add assertion here
        self.assertEqual(m.end_date,  datetime.strptime("2055-01-01",FMT).date())  # add assertion here
        self.assertEqual(m.retirement_date,  datetime.strptime("2035-01-01",FMT).date())  # add assertion here

    def test_model_setup_assets(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        self.assertEqual(len(m.assets), 4)
        for i in range(4):
            self.assertIsInstance(m.assets[i], Asset)
        self.assertTrue(str(m.assets[0]).endswith("$0.00, $0.00, $0.00, $0.00 ,0.00, 0.00"))
        self.assertTrue(str(m.assets[1]).endswith("$0.00, $0.00, $0.00, $0.00 ,0.00, 0.00"))
        self.assertTrue(str(m.assets[2]).endswith("$0.00, $0.00, $0.00, $0.00 ,0.00, 0.00"))
        self.assertTrue(str(m.assets[3]).endswith("$0.00, $0.00, $0.00, $0.00 ,0.00, 0.00"))
        self.assertEqual(len(m.timeline), 12*30 + 1)  # 12 months * 30 years, inclusive of start and end dates

    def test_operating_expenses(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        self.assertEqual(m.calculate_operating_expenses(), 0.0)

    def test_portfolio_value(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        self.assertEqual(m.retirement_portfolio_value(), 0.0)

    def test_from_json_factory(self):
        """RetirementFinancialModel.from_json() should return a properly initialised model."""
        m = RetirementFinancialModel.from_json("./tests/test_config/test.json")
        self.assertEqual(m.birth_date, datetime.strptime("1970-01-01", FMT).date())
        self.assertEqual(m.retirement_date, datetime.strptime("2035-01-01", FMT).date())

    def test_get_scenario_dataframe(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        rm, rh, am, ah = m.run_model()
        df = m.get_scenario_dataframe(rm, rh)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(list(df.columns), rh)
        self.assertGreater(len(df), 0)

    def test_get_asset_dataframe_found(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        rm, rh, am, ah = m.run_model()
        first_asset = m.assets[0].name
        df = m.get_asset_dataframe(first_asset, am, ah)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)

    def test_get_asset_dataframe_not_found(self):
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        rm, rh, am, ah = m.run_model()
        result = m.get_asset_dataframe("NonExistentAsset", am, ah)
        self.assertIsNone(result)

    def test_allocate_investment_evenly_no_match(self):
        """Distributing to a name that matches no assets should return 0."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        result = m.allocate_investment_evenly(1000.0, "xyzzy_no_match")
        self.assertAlmostEqual(result, 0.0)

    def test_allocate_investment_evenly_distributes(self):
        """Investment is distributed to matching assets."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        # Run one period so equity has a value
        for asset in m.assets:
            asset.set_scenario_dates({
                "first_date": m.start_date,
                "retirement": m.retirement_date,
                "end_date": m.end_date,
                "retirement_date": m.retirement_date,
                "retirement_age": int(m.retirement_age),
            })
        pdate = m.timeline[1]
        for asset in m.assets:
            asset.period_update(0, pdate)
        equity_asset = next(a for a in m.assets if isinstance(a, Equity))
        before = equity_asset.value
        m.allocate_investment_evenly(5000.0, "equity")
        self.assertGreater(equity_asset.value, before)

    def test_calculate_monthly_taxes_with_withdrawal(self):
        """Withdrawal amount should add to ordinary income taxes."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        taxes_no_withdrawal = m.calculate_monthly_taxes(0.0)
        taxes_with_withdrawal = m.calculate_monthly_taxes(10000.0)
        self.assertGreater(taxes_with_withdrawal, taxes_no_withdrawal)

    def test_rmd_withdrawal_age_73(self):
        """At age 73, RMD = portfolio / (24.6 * 12)."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        portfolio = 1_000_000.0
        rmd = m.calculate_rmd_withdrawal(73.5, portfolio)
        expected = portfolio / (24.6 * 12)
        self.assertAlmostEqual(rmd, expected, places=4)

    def test_rmd_withdrawal_age_80(self):
        """At age 80, RMD = portfolio / (18.5 * 12)."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        portfolio = 500_000.0
        rmd = m.calculate_rmd_withdrawal(80.9, portfolio)
        expected = portfolio / (18.5 * 12)
        self.assertAlmostEqual(rmd, expected, places=4)

    def test_rmd_withdrawal_zero_portfolio(self):
        """Zero portfolio should return 0.0."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        self.assertAlmostEqual(m.calculate_rmd_withdrawal(75.0, 0.0), 0.0)

    def test_rmd_withdrawal_pre_table_age(self):
        """Age below the IRS table (< 70) should return 0.0."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        self.assertAlmostEqual(m.calculate_rmd_withdrawal(65.0, 1_000_000.0), 0.0)

    def test_rmd_increases_withdrawal_at_old_age(self):
        """At high age the RMD should exceed a flat 4% withdrawal rate."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        portfolio = 1_000_000.0
        flat = 0.04 * portfolio / 12
        rmd_90 = m.calculate_rmd_withdrawal(90.0, portfolio)
        # At 90: factor=10.8, so RMD = 1_000_000 / (10.8*12) ≈ $7,716/mo vs $3,333/mo flat
        self.assertGreater(rmd_90, flat)

    def test_rmd_default_age_is_73(self):
        """WorldConfig and model should default rmd_age to 73."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        self.assertEqual(m.rmd_age, 73)

    def test_mheader_contains_rmd_required(self):
        """run_model output header should include rmd_required column."""
        m = RetirementFinancialModel("./tests/test_config/test.json")
        m.setup("./tests/test_config/assets")
        _, mheader, _, _ = m.run_model()
        self.assertIn("rmd_required", mheader)

if __name__ == '__main__':
    unittest.main()
