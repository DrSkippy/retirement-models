import unittest
from datetime import datetime, date

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

if __name__ == '__main__':
    unittest.main()
