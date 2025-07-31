import unittest

from models.assets import *
from models.utils import *


class MyTestCase(unittest.TestCase):
    FMT = "%Y-%m-%d"

    def test_F5(self):
        a = SalaryIncome("./configuration/assets/F5.json")
        self.assertEqual(a.name, "F5 Employment Income")
        self.assertEqual(a.start_date, "first_date")
        self.assertEqual(a.end_date, "retirement")

        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2020-06-01"}

        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2020-04-01", self.FMT).date())

    def test_F5_retirement(self):
        a = SalaryIncome("./configuration/assets/F5.json")

        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2020-06-01"}

        a.set_scenario_dates(model_dates)
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            a.growth_rate = 0.0
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            if p > 3:  # After retirement
                self.assertEqual(x[6], 0.)
            else:
                self.assertEqual(x[6], 25031.25) # 1 month of COLA

    def test_socsec_income(self):
        a = SalaryIncome("./configuration/assets/SocSec.json")
        self.assertEqual(a.name, "Social Security Income")
        self.assertEqual(a.start_date, "retirement")
        self.assertEqual(a.end_date, "end_date")
        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2030-01-01"}
        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2030-01-01", self.FMT).date())
        a.period_update(0, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.age_based_benefit[a.benefit_age], a.salary / 12.)
        self.assertEqual(a.age_based_benefit[a.benefit_age], a.income/(1. + a.growth_rate)) # 1 month of COLA

    def test_mortgage_calculation(self):
        a = REAsset("./configuration/assets/primary_residence.json")
        self.assertEqual(a.name, "Primary Residence")
        self.assertEqual(a.start_date, "first_date")

        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2034-01-01"}

        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())

        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        a.debt = 300000.0
        a.value = 1000000.0
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            if p == 156:
                self.assertEqual(x[5], 0.)
                self.assertAlmostEqual(x[4], 1000000 * (1. + a.growth_rate) ** 157)
            print(p, pdate, a.debt, a.value)

    def test_stock_equity(self):
        a = Equity("./configuration/assets/401k_stock.json")
        self.assertEqual(a.name, "401k Stocks")
        self.assertEqual(a.start_date, "first_date")
        self.assertEqual(a.end_date, "end_date")

        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2030-01-01"}

        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2030-01-01", self.FMT).date())

        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        a.value = 100000.0
        a.growth_rate = 0.07 / 12.
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            if p == 100:  # After 10 years
                self.assertAlmostEqual(x[4], 100000 * (1. + a.growth_rate) ** 101)
                a.investment(10000)
            elif p == 120:
                self.assertAlmostEqual(x[4], 100000 * (1. + a.growth_rate) ** 121 + 10000 * (1. + a.growth_rate) ** 20)


if __name__ == '__main__':
    unittest.main()
