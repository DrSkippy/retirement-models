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
        a.growth_rate = 0 # No growth for this test
        date_range = create_datetime_sequence(model_dates["first_date"], model_dates["end_date"])
        for p, pdate in enumerate(date_range):
            a.period_update(p, pdate)
            x = a.period_snapshot(p, pdate)
            self.assertEqual(x[0], p)
            self.assertEqual(x[1], pdate)
            if p > 3:  # After retirement
                self.assertEqual(x[6], 0.)
            else:
                self.assertEqual(x[6], 25000.)

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
                self.assertAlmostEqual(x[4], 1000000*(1.+a.growth_rate)**157)
            print(p, pdate, a.debt, a.value)

if __name__ == '__main__':
    unittest.main()
