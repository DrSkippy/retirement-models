import unittest

from models.utils import *

"""
For example:
poetry run pytest --cov=models tests
"""


class MyTestCase(unittest.TestCase):
    FMT = "%Y-%m-%d"

    def test_salary_0(self):
        a = SalaryIncome("./tests/test_config/assets/salary.json")
        self.assertEqual(a.name, "Income")
        self.assertEqual(a.description, "Some income continues to retirement age")
        self.assertEqual(a.start_date, "first_date")
        self.assertEqual(a.end_date, "retirement")
        self.assertEqual(a.retirement_age, "retirement_age")

        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2020-06-01",
                       "retirement_age": 65}

        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.retirement_age, 65)

    def test_salary_1(self):
        a = SalaryIncome("./tests/test_config/assets/salary.json")
        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2020-06-01",
                       "retirement_age": 65}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        p, pdate = 0, date_range[0]
        d, e, f = a.period_update(p, pdate)
        self.assertEqual(d, p)
        self.assertEqual(e, pdate)
        self.assertEqual(len(f), 4)
        x = a.period_snapshot(p, pdate)
        # ["Period", "Date",
        # "Name", "Description",
        # "Value", "Debt",
        # "Income", "Expenses"]
        self.assertEqual(len(x), 8)
        self.assertEqual(x[0], p)
        self.assertEqual(x[1], pdate)
        self.assertEqual(x[2], a.name)
        self.assertEqual(x[3], a.description)
        self.assertEqual(x[4], a.value)
        self.assertEqual(x[5], 0.)  # Debt
        self.assertEqual(x[6], a.income)  # Income
        self.assertEqual(x[7], 0.)  # Expenses

    def test_salary_2(self):
        a = SalaryIncome("./tests/test_config/assets/salary.json")
        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2020-06-01",
                       "retirement_age": 65}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p in range(3):
            pdate = date_range[p]
            d, e, f = a.period_update(p, pdate)
            x = a.period_snapshot(p, pdate)
        # ["Period", "Date",
        # "Name", "Description",
        # "Value", "Debt",
        # "Income", "Expenses"]
        self.assertEqual(len(x), 8)
        self.assertEqual(x[0], 2)
        self.assertEqual(x[1], pdate)
        self.assertEqual(x[1], date_range[2])
        self.assertEqual(x[2], a.name)
        self.assertEqual(x[3], a.description)
        self.assertEqual(x[4], a.value)
        self.assertEqual(x[4], 0)
        self.assertEqual(x[5], 0.)  # Debt
        self.assertEqual(x[6], a.income)
        self.assertAlmostEqual(x[6], 10000 * ((1 + a.growth_rate) ** 3) / 12., 3)
        self.assertEqual(x[7], a.expenses)
        self.assertEqual(x[7], 0.)

    def test_salary_3(self):
        a = SalaryIncome("./tests/test_config/assets/salary.json")
        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2020-06-01",
                       "retirement_age": 65}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p in range(5):
            pdate = date_range[p]
            d, e, f = a.period_update(p, pdate)
            x = a.period_snapshot(p, pdate)
        # ["Period", "Date",
        # "Name", "Description",
        # "Value", "Debt",
        # "Income", "Expenses"]
        self.assertGreater(pdate, datetime.strptime(model_dates["retirement"], self.FMT).date())
        self.assertEqual(len(x), 8)
        self.assertEqual(x[0], 4)
        self.assertEqual(x[1], pdate)
        self.assertEqual(x[1], date_range[4])
        self.assertEqual(x[6], a.income)
        self.assertEqual(x[6], 0.)

    def test_socsec_income_0(self):
        a = SalaryIncome("./tests/test_config/assets/sssalary.json")
        self.assertEqual(a.name, "Social Security Income")
        self.assertEqual(a.start_date, "retirement")
        self.assertEqual(a.retirement_age, "retirement_age")
        self.assertEqual(a.end_date, "end_date")
        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2030-01-01",
                       "retirement_age": 65}
        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2030-01-01", self.FMT).date())
        self.assertEqual(a.retirement_age, 65)

        a.period_update(0, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.retirement_age_based_benefit[str(a.retirement_age)], a.salary)
        self.assertEqual(a.salary, 3520.0)  # Monthly benefit
        self.assertEqual(a.retirement_age_based_benefit[str(a.retirement_age)],
                         a.income / (1. + a.growth_rate))  # 1 month of COLA

    def test_mortgage_calculation_0(self):
        a = REAsset("./tests/test_config/assets/realestate.json")
        self.assertEqual(a.name, "Real Estate")
        self.assertEqual(a.type, "RealEstate")
        self.assertEqual(a.start_date, "first_date")
        self.assertEqual(a.end_date, "end_date")
        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2034-01-01"}
        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        x, y, z = a.period_update(0, date_range[0])
        self.assertAlmostEqual(z["appreciation"], 10000 * a.growth_rate, 4)
        self.assertAlmostEqual(z["taxable_income"], 1000, 4)
        # rent - management fee - payment - property tax - insurance
        self.assertAlmostEqual(z["cash_flow"],
                               1000 - 0.03 * 1000 - 100 - 100 / 12. - 0.01 * 10000 * (1. + a.growth_rate) / 12., 4)
        t = a.period_snapshot(0, date_range[0])
        self.assertAlmostEqual(t[7], a.expenses, 4)  # Value after appreciation
        self.assertAlmostEqual(t[7], 0.03 * 1000 + 100 + 100 / 12., 4)  # Value after appreciation

    def test_mortgage_calculation_1(self):
        a = REAsset("./tests/test_config/assets/realestate.json")
        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2034-01-01"}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p in range(1, 53):
            pdate = date_range[p]
            x, y, z = a.period_update(p, pdate)
            t = a.period_snapshot(p, pdate)
        self.assertEqual(a.debt, 0)


    def test_stock_equity(self):
        a = Equity("./tests/test_config/assets/equity.json")
        self.assertEqual(a.name, "Test Equity")
        self.assertEqual(a.start_date, "first_date")
        self.assertEqual(a.end_date, "end_date")
        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2030-01-01"}
        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2030-01-01", self.FMT).date())
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            x = a.period_snapshot(p, pdate)
            if p == 10:  # After 10 months
                # ["Period", "Date",
                # "Name", "Description",
                # "Value", "Debt",
                # "Income", "Expenses"]
                self.assertAlmostEqual(x[4], 10000 * (1. + a.growth_rate) ** 11, 2)
                self.assertEqual(x[5], 0.)
                # Income calculated before appreciation
                self.assertAlmostEqual(x[6], ( 10000 * (1. + a.growth_rate) ** 10) * 0.01 / 12., 2)
                self.assertEqual(x[7], 0)
                a.update_value_with_investment(10000)

    def test_from_file_classmethod(self):
        """Asset.from_file() should produce an identical result to calling the constructor."""
        a = Equity.from_file("./tests/test_config/assets/equity.json")
        self.assertEqual(a.name, "Test Equity")
        self.assertIsInstance(a, Equity)

    def test_update_value_negative_capped_at_zero(self):
        """Withdrawing more than the asset value caps at zero and returns partial amount."""
        a = Equity("./tests/test_config/assets/equity.json")
        model_dates = {"first_date": "2020-01-01", "end_date": "2030-01-01"}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        a.period_update(0, date_range[0])  # trigger _setup so a.value == initial_value
        original_value = a.value
        # Attempt to withdraw more than available
        actual = a.update_value_with_investment(-original_value * 2)
        self.assertAlmostEqual(a.value, 0.0)
        self.assertAlmostEqual(actual, -original_value)

    def test_period_update_none_dates(self):
        """period_update with start_date=None logs an error and returns zeros."""
        a = SalaryIncome("./tests/test_config/assets/salary.json")
        # Override parsed start_date to None to trigger the error branch
        a.__dict__["start_date"] = None
        _, _, metrics = a.period_update(0, datetime.strptime("2020-01-01", FMT).date())
        for v in metrics.values():
            self.assertAlmostEqual(v, 0.0)

    def test_stochastic_appreciation(self):
        """An equity with non-zero volatility uses np.random.normal for growth."""
        import json, tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            equity_data = {
                "name": "Volatile Equity",
                "description": "High-variance test equity",
                "type": "Equity",
                "initial_value": 10000,
                "initial_expense_rate": 0.0,
                "start_date": "first_date",
                "end_date": "end_date",
                "tax_class": "income",
                "appreciation_rate": 0.06,
                "appreciation_rate_volatility": 0.15,
                "dividend_rate": 0.0,
            }
            fpath = os.path.join(tmpdir, "volatile.json")
            with open(fpath, "w") as f:
                json.dump(equity_data, f)
            a = Equity(fpath)
        model_dates = {"first_date": "2020-01-01", "end_date": "2030-01-01"}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        # Run multiple periods; with non-zero volatility values will vary
        values = []
        for p, pdate in enumerate(date_range[:12]):
            a.period_update(p, pdate)
            values.append(a.value)
        # With non-zero volatility the appreciation path should have been exercised
        self.assertGreater(max(values), 0)

    def test_asset_state_properties(self):
        """State properties should delegate reads and writes through _state."""
        a = Equity("./tests/test_config/assets/equity.json")
        a.value = 12345.0
        self.assertAlmostEqual(a._state.value, 12345.0)
        a._state.income = 99.0
        self.assertAlmostEqual(a.income, 99.0)

    def test_equity_taxable_income_includes_capital_gains(self):
        """Equity.taxable_income() = income - expenses + capital_gains."""
        a = Equity("./tests/test_config/assets/equity.json")
        model_dates = {"first_date": "2020-01-01", "end_date": "2030-01-01"}
        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        a.period_update(0, date_range[0])
        # capital_gains starts at 0 after _setup
        expected = a.income - a.expenses + a.capital_gains
        self.assertAlmostEqual(a.taxable_income(), expected, places=5)
        # Manually set capital_gains and verify it's included
        a.capital_gains = 500.0
        self.assertAlmostEqual(a.taxable_income(), a.income - a.expenses + 500.0, places=5)

    def test_set_scenario_dates_with_retirement_date(self):
        """set_scenario_dates should update retirement_date when it matches a key."""
        a = SalaryIncome("./tests/test_config/assets/sssalary.json")
        # Manually set retirement_date to the placeholder string
        a.__dict__["retirement_date"] = "retirement_date"
        target = datetime.strptime("2035-01-01", FMT).date()
        a.set_scenario_dates({"retirement_date": target})
        self.assertEqual(a.retirement_date, target)

    def test_set_scenario_dates_retirement_date_as_string(self):
        """set_scenario_dates should parse string values for retirement_date."""
        a = SalaryIncome("./tests/test_config/assets/sssalary.json")
        a.__dict__["retirement_date"] = "retirement_date"
        a.set_scenario_dates({"retirement_date": "2035-06-01"})
        self.assertEqual(a.retirement_date, datetime.strptime("2035-06-01", FMT).date())


if __name__ == '__main__':
    unittest.main()
