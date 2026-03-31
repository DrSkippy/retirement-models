import json
import os
import tempfile
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

    def test_create_assets_unknown_type_is_skipped(self):
        """Assets with unrecognised type should be silently skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "unknown.json")
            data = {
                "name": "Mystery",
                "description": "Unknown type",
                "type": "Blockchain",
                "start_date": "first_date",
                "end_date": "end_date",
                "tax_class": "income",
            }
            with open(fpath, "w") as f:
                json.dump(data, f)
            assets = create_assets(tmpdir)
        self.assertEqual(len(assets), 0)

    def test_persist_metric_creates_csv(self):
        """persist_metric should write a CSV with the requested columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            df = pd.DataFrame(
                [{"Period": 0, "Date": "2025-01-01", "net_worth": 500_000.0}]
            )
            persist_metric("net_worth", ["net_worth"], df, output_path=tmpdir)
            files = [f for f in os.listdir(tmpdir) if f.endswith(".csv")]
            self.assertEqual(len(files), 1)
            result = pd.read_csv(os.path.join(tmpdir, files[0]))
            self.assertIn("net_worth", result.columns)
            self.assertIn("Period", result.columns)
            self.assertIn("Date", result.columns)

    def test_persist_metric_creates_output_dir(self):
        """persist_metric should create the output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "metrics_new")
            df = pd.DataFrame(
                [{"Period": 0, "Date": "2025-01-01", "net_worth": 100.0}]
            )
            persist_metric("test", ["net_worth"], df, output_path=new_dir)
            self.assertTrue(os.path.isdir(new_dir))

    def test_plot_asset_model_data_runs(self):
        """plot_asset_model_data should produce a PDF without raising."""
        date_seq = create_datetime_sequence("2025-01-01", "2025-06-01")
        rows = [{"Date": d, "Value": float(i * 100), "Income": float(i * 10)}
                for i, d in enumerate(date_seq)]
        df = pd.DataFrame(rows)
        os.makedirs("./output", exist_ok=True)
        # Should not raise
        plot_asset_model_data(df, "_test_coverage", offset=0)
        self.assertTrue(os.path.exists("./output/scenario__test_coverage.pdf"))

    def test_plot_asset_model_data_empty_df(self):
        """plot_asset_model_data with an empty DataFrame should return early."""
        df = pd.DataFrame()
        # Should not raise, just logs an error
        plot_asset_model_data(df, "_test_empty")


if __name__ == '__main__':
    unittest.main()
