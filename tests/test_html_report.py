import tempfile
import unittest
from datetime import date

import pandas as pd

from models.html_report import HtmlReportBuilder, _compute_summary_metrics, _fmt_dollar
from models.monte_carlo import MonteCarloResults, SimulationResult


def _make_scenario_df(n: int = 36) -> pd.DataFrame:
    rows = []
    for i in range(n):
        age = 55.0 + i / 12
        rows.append({
            "Period": i,
            "Date": date(2025 + i // 12, (i % 12) + 1, 1),
            "age": age,
            "retirement_withdrawal": 5000.0 if age >= 67 else 0.0,
            "net_worth": 1_000_000.0 + i * 5000,
            "debt": 200_000.0 - i * 500,
            "monthly_taxable_income": 8000.0,
            "monthly_operational_expenses": 3000.0,
            "taxes_paid": 2000.0,
            "free_cash_flows": 5000.0,
            "investment": 1000.0,
            "tax_ordinary_income": 1200.0,
            "tax_capital_gains": 600.0,
            "tax_social_security": 200.0,
        })
    return pd.DataFrame(rows)


def _make_mc_results(n: int = 50) -> MonteCarloResults:
    results = [
        SimulationResult(
            run_id=i,
            terminal_net_worth=300_000.0 + i * 10_000.0,
            ruin_period=None if i % 10 != 0 else 120,
        )
        for i in range(n)
    ]
    return MonteCarloResults(n_runs=n, results=results)


class TestFmtDollar(unittest.TestCase):
    def test_millions(self):
        self.assertEqual(_fmt_dollar(1_500_000), "$1.50m")

    def test_thousands(self):
        self.assertEqual(_fmt_dollar(500_000), "$500k")

    def test_negative(self):
        result = _fmt_dollar(-250_000)
        self.assertIn("-", result)

    def test_none(self):
        self.assertEqual(_fmt_dollar(None), "N/A")


class TestComputeSummaryMetrics(unittest.TestCase):
    def test_peak_net_worth(self):
        df = _make_scenario_df(12)
        m = _compute_summary_metrics(df)
        self.assertAlmostEqual(m["peak_net_worth"], df["net_worth"].max())

    def test_net_worth_at_ages(self):
        df = _make_scenario_df(36)
        m = _compute_summary_metrics(df)
        # Ages only reach ~57.9 in 36 months; higher ages should be None
        self.assertIsNone(m["net_worth_at_70"])

    def test_terminal_net_worth(self):
        df = _make_scenario_df(12)
        m = _compute_summary_metrics(df)
        self.assertAlmostEqual(m["terminal_net_worth"], df["net_worth"].iloc[-1])


class TestSingleRunReport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.builder = HtmlReportBuilder(output_dir=self.tmpdir, label="test")

    def test_creates_all_pages(self):
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        for page in ["index.html", "timeseries.html", "portfolio.html", "tax.html"]:
            self.assertTrue((run_dir / page).exists(), f"{page} missing")

    def test_index_contains_metric_cards(self):
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        html = (run_dir / "index.html").read_text()
        self.assertIn("metric-card", html)
        self.assertIn("Peak Net Worth", html)

    def test_index_contains_formatted_dollar(self):
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        html = (run_dir / "index.html").read_text()
        self.assertIn("$", html)

    def test_run_dir_contains_label(self):
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        self.assertIn("test", run_dir.name)

    def test_run_dir_name_format(self):
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        self.assertTrue(run_dir.name.startswith("run_"))
        self.assertNotIn("run_mc_", run_dir.name)

    def test_timeseries_has_plotly_divs(self):
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        html = (run_dir / "timeseries.html").read_text()
        self.assertIn("plotly", html.lower())

    def test_tax_page_rmd_section_hidden_when_no_rmd(self):
        df = _make_scenario_df(12)  # ages 55-56, no RMD
        run_dir = self.builder.single_run_report(df, {})
        html = (run_dir / "tax.html").read_text()
        self.assertNotIn("Required Minimum Distributions", html)

    def test_no_pdf_files_created(self):
        import os
        df = _make_scenario_df()
        run_dir = self.builder.single_run_report(df, {})
        pdf_files = [f for f in os.listdir(run_dir) if f.endswith(".pdf")]
        self.assertEqual(pdf_files, [])


class TestMonteCarloReport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.builder = HtmlReportBuilder(output_dir=self.tmpdir)

    def test_creates_both_pages(self):
        mc = _make_mc_results()
        run_dir = self.builder.monte_carlo_report(mc)
        self.assertTrue((run_dir / "index.html").exists())
        self.assertTrue((run_dir / "distribution.html").exists())

    def test_run_dir_prefixed_mc(self):
        mc = _make_mc_results()
        run_dir = self.builder.monte_carlo_report(mc)
        self.assertIn("run_mc_", run_dir.name)

    def test_mc_index_contains_ruin_probability(self):
        mc = _make_mc_results()
        run_dir = self.builder.monte_carlo_report(mc)
        html = (run_dir / "index.html").read_text()
        self.assertIn("Ruin Probability", html)

    def test_mc_index_contains_percentile_table(self):
        mc = _make_mc_results()
        run_dir = self.builder.monte_carlo_report(mc)
        html = (run_dir / "index.html").read_text()
        self.assertIn("P50", html)

    def test_labelled_mc_run(self):
        builder = HtmlReportBuilder(output_dir=self.tmpdir, label="scenario_a")
        mc = _make_mc_results()
        run_dir = builder.monte_carlo_report(mc)
        self.assertIn("scenario_a", run_dir.name)


if __name__ == "__main__":
    unittest.main()
