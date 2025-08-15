import unittest
import pandas as pd
from models.utils import *


class MyTestCase(unittest.TestCase):

    def test_utils_datetime_sequence(self):
        x = create_datetime_sequence("2020-01-01", "2020-06-01")
        self.assertEqual(len(x), 6)
        self.assertEqual(x[0].strftime("%Y-%m-%d"), "2020-01-01")
        self.assertEqual(x[-1].strftime("%Y-%m-%d"), "2020-06-01")

    def test_utils_create_assets_0(self):
        assets = create_assets("./tests/test_config/assets", asset_name_filter=["Income"])
        self.assertEqual(len(assets), 2)
        self.assertEqual(assets[0].name, "Income")
        self.assertEqual(assets[1].name, "Social Security Income")
        self.assertIsInstance(assets[0], SalaryIncome)

    def test_utils_create_assets_1(self):
        assets = create_assets("./tests/test_config/assets", asset_name_filter=["Equity"])
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "Test Equity")
        self.assertIsInstance(assets[0], Equity)

    def test_utils_create_assets_2(self):
        assets = create_assets("./tests/test_config/assets", asset_name_filter=["Estate"])
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "Real Estate")
        self.assertIsInstance(assets[0], REAsset)

    def test_utils_create_assets_3(self):
        # Test with an empty filter
        assets = create_assets("./tests/test_config/assets", asset_name_filter=[])
        self.assertEqual(len(assets), 4)

if __name__ == '__main__':
    unittest.main()
