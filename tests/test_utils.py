import unittest

from models.utils import *


class MyTestCase(unittest.TestCase):

    def test_utils_datetime_sequence(self):
        x = create_datetime_sequence("2020-01-01", "2020-06-01")
        self.assertEqual(len(x), 6)
        self.assertEqual(x[0].strftime("%Y-%m-%d"), "2020-01-01")
        self.assertEqual(x[-1].strftime("%Y-%m-%d"), "2020-06-01")

    def test_utils_create_assets_0(self):
        assets = create_assets("./configuration/assets", asset_name_filter=["F5 Employment Income"])
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "F5 Employment Income")
        self.assertIsInstance(assets[0], SalaryIncome)

    def test_utils_create_assets_1(self):
        assets = create_assets("./configuration/assets", asset_name_filter=["401k Stocks"])
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "401k Stocks")
        self.assertIsInstance(assets[0], Equity)

    def test_utils_create_assets_2(self):
        assets = create_assets("./configuration/assets", asset_name_filter=["Brighton Rental Property"])
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "Brighton Rental Property")
        self.assertIsInstance(assets[0], REAsset)

    def test_utils_create_assets_3(self):
        # Test with an empty filter
        assets = create_assets("./configuration/assets", asset_name_filter=[])
        self.assertGreater(len(assets), 6)


if __name__ == '__main__':
    unittest.main()
