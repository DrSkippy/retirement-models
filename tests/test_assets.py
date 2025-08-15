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

if __name__ == '__main__':
    unittest.main()
