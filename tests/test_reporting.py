import tempfile
import unittest
from datetime import date

import pandas as pd

from models.monte_carlo import MonteCarloResults, SimulationResult
from models.reporting import ReportBuilder


def _make_scenario_df(n: int = 12) -> pd.DataFrame:
    """Create a minimal scenario DataFrame for report tests."""
    rows = []
    for i in range(n):
        rows.append(
            {
                "Period": i,
                "Date": date(2025 + i // 12, (i % 12) + 1, 1),
                "age": 55.0 + i / 12,
                "retirement_withdrawal": 0.0,
                "net_worth": 500_000.0 + i * 1000,
                "debt": 100_000.0,
                "monthly_taxable_income": 8000.0,
                "monthly_operational_expenses": 3000.0,
                "taxes_paid": 2000.0,
                "free_cash_flows": 5000.0,
                "investment": 1000.0,
            }
        )
    return pd.DataFrame(rows)


def _make_rmd_scenario_df() -> pd.DataFrame:
    """Scenario DataFrame that includes ages above 73 for RMD testing."""
    rows = []
    for i in range(24):
        rows.append(
            {
                "Period": i,
                "Date": date(2038 + i // 12, (i % 12) + 1, 1),
                "age": 72.0 + i / 12,
                "taxes_paid": 1500.0 + i * 10,
                "monthly_taxable_income": 5000.0,
            }
        )
    return pd.DataFrame(rows)


def _make_mc_results(n: int = 20) -> MonteCarloResults:
    results = [
        SimulationResult(
            run_id=i,
            terminal_net_worth=200_000.0 + i * 5000.0,
            ruin_period=None if i % 5 != 0 else 100,
        )
        for i in range(n)
    ]
    return MonteCarloResults(n_runs=n, results=results)


class TestReportBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.builder = ReportBuilder(output_dir=self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # single_run_report
    # ------------------------------------------------------------------

    def test_single_run_report_creates_pdf(self):
        scenario_df = _make_scenario_df()
        asset_dfs = {
            "Equity": pd.DataFrame(
                [{"Date": date(2025, 1, 1), "Value": 10000.0, "Income": 100.0}]
            )
        }
        path = self.builder.single_run_report(scenario_df, asset_dfs)
        self.assertTrue(path.exists())
        self.assertTrue(str(path).endswith(".pdf"))

    def test_single_run_report_creates_csv(self):
        scenario_df = _make_scenario_df()
        self.builder.single_run_report(scenario_df, {})
        csv_path = self.builder.output_dir / "single_run_summary.csv"
        self.assertTrue(csv_path.exists())

    def test_single_run_report_empty_asset_dfs(self):
        scenario_df = _make_scenario_df()
        path = self.builder.single_run_report(scenario_df, {})
        self.assertTrue(path.exists())

    def test_single_run_report_skips_none_asset_df(self):
        scenario_df = _make_scenario_df()
        asset_dfs = {"Missing": None}
        path = self.builder.single_run_report(scenario_df, asset_dfs)
        self.assertTrue(path.exists())

    def test_single_run_report_skips_empty_asset_df(self):
        scenario_df = _make_scenario_df()
        asset_dfs = {"Empty": pd.DataFrame()}
        path = self.builder.single_run_report(scenario_df, asset_dfs)
        self.assertTrue(path.exists())

    def test_single_run_report_asset_without_value_column(self):
        scenario_df = _make_scenario_df()
        asset_dfs = {
            "NoValueCol": pd.DataFrame([{"Date": date(2025, 1, 1), "Debt": 0.0}])
        }
        path = self.builder.single_run_report(scenario_df, asset_dfs)
        self.assertTrue(path.exists())

    # ------------------------------------------------------------------
    # monte_carlo_report
    # ------------------------------------------------------------------

    def test_monte_carlo_report_creates_pdf(self):
        mc = _make_mc_results()
        path = self.builder.monte_carlo_report(mc)
        self.assertTrue(path.exists())
        self.assertTrue(str(path).endswith(".pdf"))

    def test_monte_carlo_report_custom_percentiles(self):
        mc = _make_mc_results()
        path = self.builder.monte_carlo_report(mc, percentiles=[10, 90])
        self.assertTrue(path.exists())

    def test_monte_carlo_report_all_ruin(self):
        results = [
            SimulationResult(run_id=i, terminal_net_worth=-1000.0, ruin_period=50)
            for i in range(5)
        ]
        mc = MonteCarloResults(n_runs=5, results=results)
        path = self.builder.monte_carlo_report(mc)
        self.assertTrue(path.exists())

    # ------------------------------------------------------------------
    # tax_optimization_report
    # ------------------------------------------------------------------

    def test_tax_report_creates_pdf(self):
        scenario_df = _make_scenario_df()
        path = self.builder.tax_optimization_report(scenario_df)
        self.assertTrue(path.exists())

    def test_tax_report_with_rmd_ages(self):
        """Scenario spanning age 73+ should produce the RMD page."""
        scenario_df = _make_rmd_scenario_df()
        path = self.builder.tax_optimization_report(scenario_df)
        self.assertTrue(path.exists())

    def test_tax_report_no_rmd_ages(self):
        """Scenario entirely below age 73 should still produce a valid PDF."""
        scenario_df = _make_scenario_df()  # ages 55-56, no RMD
        path = self.builder.tax_optimization_report(scenario_df)
        self.assertTrue(path.exists())

    def test_tax_report_missing_columns(self):
        """DataFrame missing tax columns should not raise."""
        df = pd.DataFrame([{"Date": date(2025, 1, 1), "age": 60.0}])
        path = self.builder.tax_optimization_report(df)
        self.assertTrue(path.exists())

    # ------------------------------------------------------------------
    # ReportBuilder construction
    # ------------------------------------------------------------------

    def test_output_dir_created_automatically(self):
        import os
        new_dir = self._tmpdir.name + "/nested/reports"
        builder = ReportBuilder(output_dir=new_dir)
        self.assertTrue(os.path.isdir(new_dir))


if __name__ == "__main__":
    unittest.main()
