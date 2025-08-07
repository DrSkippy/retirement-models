import unittest

from models.assets import *
from models.utils import *


class MyTestCase(unittest.TestCase):
    FMT = "%Y-%m-%d"

    def test_F5_salary_0(self):
        a = SalaryIncome("./configuration/assets/F5.json")
        self.assertEqual(a.name, "F5 Employment Income")
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

        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p, pdate in enumerate(date_range):
            print(pdate, a.start_date, a.end_date)
            a.period_update(p, pdate)
            a.growth_rate = 0.0
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            if p > 2:  # After retirement
                self.assertEqual(x[6], 0.)
            if p == 1:  # Before retirement
                self.assertEqual(x[6], 25031.25) # 1 month of COLA

    def test_socsec_income(self):
        a = SalaryIncome("./configuration/assets/SocSec.json")
        self.assertEqual(a.name, "Social Security Income")
        self.assertEqual(a.start_date, "retirement")
        self.assertEqual(a.end_date, "end_date")
        model_dates = {"first_date": "2020-01-01",
                       "retirement": "2020-04-01",
                       "end_date": "2030-01-01",
                       "retirement_age": 65}
        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2030-01-01", self.FMT).date())
        a.period_update(0, datetime.strptime("2020-04-01", self.FMT).date())
        self.assertEqual(a.retirement_age_based_benefit[str(a.retirement_age)], a.salary)
        self.assertEqual(a.retirement_age_based_benefit[str(a.retirement_age)], a.income/(1. + a.growth_rate)) # 1 month of COLA

    def test_mortgage_calculation(self):
        a = REAsset("./configuration/assets/primary_residence.json")
        self.assertEqual(a.name, "Primary Residence")
        self.assertEqual(a.start_date, "first_date")

        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2034-01-01"}

        a.set_scenario_dates(model_dates)
        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            if p == 0:
                tmp = a.value
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            self.assertAlmostEqual(x[4], tmp * (1. + a.growth_rate) ** p, 2)
            print(x)
            if p == 156:
                self.assertAlmostEqual(x[5], 175372.5628, 2)
                self.assertAlmostEqual(x[6], 0)
                self.assertAlmostEqual(x[7], 522.518, 2)
                break

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
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            if p == 0:
                tmp = a.value
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            print (x)
            if p == 10:  # After 10 years
                self.assertAlmostEqual(x[4], tmp * (1. + a.growth_rate) ** 10, 2)
                self.assertEqual(x[5], 0.)
                self.assertAlmostEqual(x[6],   262.78503, 2)
                self.assertEqual(x[7], 0)
                a.update_value_with_investment(10000)
            elif p == 12:
                self.assertAlmostEqual(x[4], tmp * (1. + a.growth_rate) ** 12 + 10000 * (1. + a.growth_rate) ** 2, 2)

    def test_REAsset_xtras(self):
        a = REAsset("./configuration/assets/rental_114.json")
        self.assertEqual(a.start_date, "first_date")
        self.assertEqual(a.end_date, "end_date")

        model_dates = {"first_date": "2020-01-01",
                       "end_date": "2030-01-01"}
        a.set_scenario_dates(model_dates)

        self.assertEqual(a.start_date, datetime.strptime("2020-01-01", self.FMT).date())
        self.assertEqual(a.end_date, datetime.strptime("2030-01-01", self.FMT).date())

        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])

        for p, pdate in enumerate(date_range):
            _p, _pdata, xtras = a.period_update(p, pdate)
            self.assertEqual(_p, p)
            self.assertEqual(_pdata, pdate)
            self.assertEqual(len(xtras), 4)
            x = a.period_snapshot(p, pdate, xtras)
            self.assertEqual(len(x), 12)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            print (x)
            if p == 10:  # After 10 mmonths
                self.assertAlmostEqual(x[4], a.initial_value * (1. + a.growth_rate) ** 11, 2)
                self.assertAlmostEqual(x[5], 16048.60746, 2)
                self.assertAlmostEqual(x[7],   155.9716844085628, 2) # interest
                self.assertAlmostEqual(x[8],  664.3042529126141 , 2) # principle

if __name__ == '__main__':
    unittest.main()
