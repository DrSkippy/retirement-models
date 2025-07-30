import unittest
from models.assets import *


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, True)  # add assertion here

    def test_F5(self):
        a = SalaryIncome("./configuration/assets/F5.json")
        self.assertEqual(a.name, "F5 Employment Income")

        model_dates = { "first_date": "2020-01-01",
                        "retirement": "2020-04-01",
                        "end_date": "2020-06-01" }

        a.set_scenario_dates(model_dates)
        data = []
        for p in range(6):
            a.period_update(p)
            data.append(a.period_snapshot(p))
        print(data)

if __name__ == '__main__':
    unittest.main()
