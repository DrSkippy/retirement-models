"""Reporting module: single-run reports, Monte Carlo fan charts, tax analysis."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec

from models.monte_carlo import MonteCarloResults

# ---------------------------------------------------------------------------
# Style foundation
# ---------------------------------------------------------------------------

plt.style.use("bmh")
plt.rcParams.update(
    {
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        "axes.edgecolor": "#BDBDBD",
        "axes.grid": True,
        "grid.color": "#E0E0E0",
        "grid.linewidth": 0.6,
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
    }
)

PALETTE: dict[str, str] = {
    "net_worth": "#1A6FAF",
    "equity_asset": "#4DA6E8",
    "real_estate": "#2B8C8C",
    "income": "#2E7D32",
    "salary": "#43A047",
    "social_security": "#81C784",
    "expenses": "#C62828",
    "debt": "#E57373",
    "taxes": "#EF6C00",
    "investment": "#3949AB",
    "free_cash_flow": "#F9A825",
    "withdrawal": "#7B1FA2",
    "retirement_line": "#455A64",
    "rmd_line": "#B71C1C",
    "percentile_band": "#90CAF9",
    "median_line": "#0D47A1",
}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _fmt_dollar_axis(ax: plt.Axes, axis: str = "y") -> None:
    """Format axis ticks as $Xk / $X.Xm."""

    def _fmt(x: float, _pos: object) -> str:
        if abs(x) >= 1_000_000:
            return f"${x/1_000_000:.1f}m"
        if abs(x) >= 1_000:
            return f"${x/1_000:.0f}k"
        return f"${x:.0f}"

    formatter = mticker.FuncFormatter(_fmt)
    if axis == "y":
        ax.yaxis.set_major_formatter(formatter)
    else:
        ax.xaxis.set_major_formatter(formatter)


def _add_retirement_vline(
    ax: plt.Axes, retirement_date: object, label: str = "Retirement"
) -> None:
    """Draw a solid vertical line at the retirement boundary."""
    ax.axvline(
        retirement_date,
        color=PALETTE["retirement_line"],
        linewidth=1.2,
        linestyle="-",
        label=label,
        zorder=3,
    )


def _add_rmd_vline(ax: plt.Axes, rmd_date: object, label: str = "RMD Age 73") -> None:
    """Draw a dashed dark-red vertical line at first RMD period."""
    ax.axvline(
        rmd_date,
        color=PALETTE["rmd_line"],
        linewidth=1.0,
        linestyle="--",
        label=label,
        zorder=3,
    )


def _shade_post_retirement(
    ax: plt.Axes, retirement_date: object, end_date: object
) -> None:
    """Apply light grey shading over the post-retirement region."""
    ax.axvspan(retirement_date, end_date, alpha=0.06, color="grey", zorder=0)


def _find_retirement_date(scenario_df: pd.DataFrame) -> Optional[object]:
    """Return first Date where retirement_withdrawal > 0, or None."""
    if "retirement_withdrawal" not in scenario_df.columns:
        return None
    mask = scenario_df["retirement_withdrawal"] > 0
    if not mask.any():
        return None
    return scenario_df.loc[mask, "Date"].iloc[0]


def _find_rmd_date(scenario_df: pd.DataFrame) -> Optional[object]:
    """Return first Date where age >= 73, or None."""
    if "age" not in scenario_df.columns:
        return None
    mask = scenario_df["age"] >= 73
    if not mask.any():
        return None
    return scenario_df.loc[mask, "Date"].iloc[0]


def _annotate_axes(
    ax: plt.Axes,
    scenario_df: pd.DataFrame,
    retirement_date: Optional[object],
    rmd_date: Optional[object],
    shade: bool = True,
) -> None:
    """Apply retirement vline, RMD vline and post-retirement shading to an axes."""
    if retirement_date is not None:
        _add_retirement_vline(ax, retirement_date)
        if shade and "Date" in scenario_df.columns and not scenario_df.empty:
            _shade_post_retirement(ax, retirement_date, scenario_df["Date"].iloc[-1])
    if rmd_date is not None:
        _add_rmd_vline(ax, rmd_date)


# ---------------------------------------------------------------------------
# ReportBuilder
# ---------------------------------------------------------------------------


class ReportBuilder:
    """Builds PDF reports from simulation output.

    Existing utils.plot_asset_model_data() remains in place for backwards
    compatibility; ReportBuilder is purely additive.
    """

    def __init__(self, output_dir: str = "./output") -> None:
        """Initialise with an output directory (created if absent).

        Args:
            output_dir: Directory where reports and CSVs are written.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Report 1: single_run_report
    # ------------------------------------------------------------------

    def single_run_report(
        self,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
    ) -> Path:
        """Generate a multi-page single-run PDF report.

        Page 1 — Executive summary (6-panel GridSpec 2×3).
        Page 2 — Portfolio composition (4-panel 2×2).
        Pages 3+ — Per-asset detail (1×3 each).

        Args:
            scenario_df: Scenario-level DataFrame from get_scenario_dataframe().
            asset_dfs: Mapping of asset name → asset DataFrame.

        Returns:
            Path to the generated PDF.
        """
        output_path = self.output_dir / "single_run_report.pdf"
        retirement_date = _find_retirement_date(scenario_df)
        rmd_date = _find_rmd_date(scenario_df)

        with PdfPages(str(output_path)) as pdf:
            self._single_run_page1(
                pdf, scenario_df, asset_dfs, retirement_date, rmd_date
            )
            self._single_run_page2(pdf, scenario_df, asset_dfs, retirement_date, rmd_date)
            self._single_run_asset_pages(pdf, asset_dfs, retirement_date, rmd_date)

        csv_path = self.output_dir / "single_run_summary.csv"
        scenario_df.to_csv(str(csv_path), index=False)
        logging.info(f"Single-run report written to {output_path}")
        return output_path

    def _single_run_page1(
        self,
        pdf: PdfPages,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        """Executive summary page: 2×3 GridSpec."""
        fig = plt.figure(figsize=(18, 10), constrained_layout=True)
        fig.suptitle("Retirement Model — Executive Summary", fontsize=14, fontweight="bold")
        gs = GridSpec(2, 3, figure=fig)

        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None

        # [0, 0:2] Net Worth & Debt
        ax_nw = fig.add_subplot(gs[0, 0:2])
        if dates is not None and "net_worth" in scenario_df.columns:
            ax_nw.fill_between(
                dates,
                scenario_df["net_worth"],
                alpha=0.3,
                color=PALETTE["net_worth"],
                label="Net Worth",
            )
            ax_nw.plot(dates, scenario_df["net_worth"], color=PALETTE["net_worth"], linewidth=1.5)
        if dates is not None and "debt" in scenario_df.columns:
            ax_nw.plot(
                dates,
                scenario_df["debt"],
                color=PALETTE["debt"],
                linewidth=1.5,
                label="Debt",
            )
        ax_nw.set_title("Net Worth & Debt")
        ax_nw.set_xlabel("Date")
        _fmt_dollar_axis(ax_nw)
        _annotate_axes(ax_nw, scenario_df, retirement_date, rmd_date)
        ax_nw.legend()

        # [0, 2] Income Sources — stacked area
        ax_inc = fig.add_subplot(gs[0, 2])
        self._plot_income_stack(ax_inc, scenario_df, asset_dfs)
        ax_inc.set_title("Income Sources")
        ax_inc.set_xlabel("Date")
        _fmt_dollar_axis(ax_inc)
        _annotate_axes(ax_inc, scenario_df, retirement_date, rmd_date, shade=False)

        # [1, 0] Free Cash Flow
        ax_fcf = fig.add_subplot(gs[1, 0])
        if dates is not None and "free_cash_flows" in scenario_df.columns:
            fcf = scenario_df["free_cash_flows"]
            colors = [
                PALETTE["free_cash_flow"] if v >= 0 else PALETTE["expenses"] for v in fcf
            ]
            ax_fcf.bar(dates, fcf, color=colors, width=20, align="center")
        ax_fcf.set_title("Free Cash Flow")
        ax_fcf.set_xlabel("Date")
        _fmt_dollar_axis(ax_fcf)
        _annotate_axes(ax_fcf, scenario_df, retirement_date, rmd_date, shade=False)
        if rmd_date is not None:
            ax_fcf.legend(fontsize=7)

        # [1, 1] Investment Flow
        ax_inv = fig.add_subplot(gs[1, 1])
        if dates is not None and "investment" in scenario_df.columns:
            ax_inv.bar(
                dates,
                scenario_df["investment"],
                color=PALETTE["investment"],
                width=20,
                align="center",
                alpha=0.85,
            )
        ax_inv.set_title("Investment Flow")
        ax_inv.set_xlabel("Date")
        _fmt_dollar_axis(ax_inv)
        _annotate_axes(ax_inv, scenario_df, retirement_date, rmd_date, shade=False)

        # [1, 2] Effective Tax Rate
        ax_tax = fig.add_subplot(gs[1, 2])
        if (
            dates is not None
            and "taxes_paid" in scenario_df.columns
            and "monthly_taxable_income" in scenario_df.columns
        ):
            income = scenario_df["monthly_taxable_income"].replace(0, np.nan)
            eff_rate = (scenario_df["taxes_paid"] / income * 100).fillna(0)
            ax_tax.fill_between(
                dates, eff_rate, alpha=0.4, color=PALETTE["taxes"], label="Eff. Tax Rate"
            )
            ax_tax.plot(dates, eff_rate, color=PALETTE["taxes"], linewidth=1.2)
        ax_tax.set_title("Effective Tax Rate (%)")
        ax_tax.set_xlabel("Date")
        ax_tax.set_ylabel("%")
        _annotate_axes(ax_tax, scenario_df, retirement_date, rmd_date, shade=False)

        pdf.savefig(fig)
        plt.close(fig)

    def _plot_income_stack(
        self,
        ax: plt.Axes,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
    ) -> None:
        """Plot stacked income area from asset_dfs if available, else from scenario_df."""
        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None
        if dates is None:
            return

        # Try to build stacked income from asset_dfs
        income_series: dict[str, pd.Series] = {}
        income_colors: list[str] = []
        color_cycle = [
            PALETTE["salary"],
            PALETTE["real_estate"],
            PALETTE["social_security"],
            PALETTE["equity_asset"],
            PALETTE["withdrawal"],
            PALETTE["income"],
        ]

        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Income" not in df.columns or "Date" not in df.columns:
                continue
            merged = pd.merge(
                pd.DataFrame({"Date": dates}), df[["Date", "Income"]], on="Date", how="left"
            ).fillna(0)
            income_series[name] = merged["Income"]
            income_colors.append(color_cycle[i % len(color_cycle)])

        if income_series:
            labels = list(income_series.keys())
            data = [income_series[k].values for k in labels]
            ax.stackplot(dates, *data, labels=labels, colors=income_colors, alpha=0.75)
            ax.legend(fontsize=7, loc="upper left")
        elif "monthly_taxable_income" in scenario_df.columns:
            ax.fill_between(
                dates,
                scenario_df["monthly_taxable_income"],
                alpha=0.4,
                color=PALETTE["income"],
                label="Taxable Income",
            )
            ax.plot(
                dates,
                scenario_df["monthly_taxable_income"],
                color=PALETTE["income"],
                linewidth=1.2,
            )
            ax.legend(fontsize=7)

        if "retirement_withdrawal" in scenario_df.columns:
            ax.plot(
                dates,
                scenario_df["retirement_withdrawal"],
                color=PALETTE["withdrawal"],
                linewidth=1.2,
                linestyle="--",
                label="Withdrawal",
            )

    def _single_run_page2(
        self,
        pdf: PdfPages,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        """Portfolio composition page: 2×2."""
        fig = plt.figure(figsize=(18, 10), constrained_layout=True)
        fig.suptitle("Portfolio Composition", fontsize=14, fontweight="bold")
        gs = GridSpec(2, 2, figure=fig)

        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None

        # [0, 0] Stacked asset values
        ax_stack = fig.add_subplot(gs[0, 0])
        self._plot_stacked_assets(ax_stack, dates, scenario_df, asset_dfs)
        ax_stack.set_title("Stacked Asset Values")
        ax_stack.set_xlabel("Date")
        _fmt_dollar_axis(ax_stack)
        _annotate_axes(ax_stack, scenario_df, retirement_date, rmd_date, shade=False)

        # [0, 1] Per-equity growth
        ax_eq = fig.add_subplot(gs[0, 1])
        self._plot_equity_growth(ax_eq, asset_dfs)
        ax_eq.set_title("Per-Equity Asset Growth")
        ax_eq.set_xlabel("Date")
        _fmt_dollar_axis(ax_eq)
        if retirement_date is not None:
            _add_retirement_vline(ax_eq, retirement_date)

        # [1, 0] Real estate value / debt / equity
        ax_re = fig.add_subplot(gs[1, 0])
        self._plot_real_estate(ax_re, asset_dfs)
        ax_re.set_title("Real Estate: Value / Debt / Equity")
        ax_re.set_xlabel("Date")
        _fmt_dollar_axis(ax_re)
        if retirement_date is not None:
            _add_retirement_vline(ax_re, retirement_date)

        # [1, 1] Annual income by asset (stacked bar sampled every 12 periods)
        ax_ann = fig.add_subplot(gs[1, 1])
        self._plot_annual_income_bars(ax_ann, scenario_df, asset_dfs)
        ax_ann.set_title("Annual Income by Asset")
        ax_ann.set_xlabel("Year")
        _fmt_dollar_axis(ax_ann)
        if retirement_date is not None:
            _add_retirement_vline(ax_ann, retirement_date)

        pdf.savefig(fig)
        plt.close(fig)

    def _plot_stacked_assets(
        self,
        ax: plt.Axes,
        dates: Optional[pd.Series],
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
    ) -> None:
        """Stackplot of all asset values."""
        if dates is None:
            return
        color_cycle = [
            PALETTE["equity_asset"],
            PALETTE["real_estate"],
            PALETTE["investment"],
            PALETTE["net_worth"],
            PALETTE["salary"],
            PALETTE["social_security"],
        ]
        stacks: list[np.ndarray] = []
        labels: list[str] = []
        colors: list[str] = []

        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Value" not in df.columns or "Date" not in df.columns:
                continue
            merged = pd.merge(
                pd.DataFrame({"Date": dates}), df[["Date", "Value"]], on="Date", how="left"
            ).fillna(0)
            stacks.append(merged["Value"].values)
            labels.append(name)
            colors.append(color_cycle[i % len(color_cycle)])

        if stacks:
            ax.stackplot(dates, *stacks, labels=labels, colors=colors, alpha=0.7)
            # Total dashed line
            total = np.sum(stacks, axis=0)
            ax.plot(dates, total, color="black", linewidth=1.2, linestyle="--", label="Total")
            ax.legend(fontsize=7)
        elif "net_worth" in scenario_df.columns:
            ax.plot(dates, scenario_df["net_worth"], color=PALETTE["net_worth"])

    def _plot_equity_growth(
        self, ax: plt.Axes, asset_dfs: dict[str, Optional[pd.DataFrame]]
    ) -> None:
        """One line per equity-type asset."""
        color_cycle = [PALETTE["equity_asset"], PALETTE["investment"], PALETTE["net_worth"]]
        plotted = False
        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Value" not in df.columns or "Date" not in df.columns:
                continue
            ax.plot(
                df["Date"],
                df["Value"],
                label=name,
                color=color_cycle[i % len(color_cycle)],
                linewidth=1.4,
            )
            plotted = True
        if plotted:
            ax.legend(fontsize=7)

    def _plot_real_estate(
        self, ax: plt.Axes, asset_dfs: dict[str, Optional[pd.DataFrame]]
    ) -> None:
        """Real estate value, debt fill and net equity dashed."""
        for name, df in asset_dfs.items():
            if df is None or df.empty or "Value" not in df.columns or "Date" not in df.columns:
                continue
            ax.plot(
                df["Date"],
                df["Value"],
                color=PALETTE["real_estate"],
                linewidth=1.4,
                label=f"{name} Value",
            )
            if "Debt" in df.columns:
                ax.fill_between(
                    df["Date"],
                    df["Debt"],
                    alpha=0.3,
                    color=PALETTE["debt"],
                    label=f"{name} Debt",
                )
                net_equity = df["Value"] - df["Debt"]
                ax.plot(
                    df["Date"],
                    net_equity,
                    color=PALETTE["net_worth"],
                    linestyle="--",
                    linewidth=1.0,
                    label=f"{name} Equity",
                )
        ax.legend(fontsize=7)

    def _plot_annual_income_bars(
        self,
        ax: plt.Axes,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
    ) -> None:
        """Stacked bar of annual income sampled every 12 periods."""
        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None
        if dates is None:
            return

        color_cycle = [
            PALETTE["salary"],
            PALETTE["real_estate"],
            PALETTE["social_security"],
            PALETTE["equity_asset"],
            PALETTE["withdrawal"],
        ]
        annual_data: dict[str, list[float]] = {}
        annual_dates: list[object] = []
        n = len(scenario_df)

        for period_start in range(0, n, 12):
            period_end = min(period_start + 12, n)
            annual_dates.append(scenario_df["Date"].iloc[period_start])
            for i, (name, df) in enumerate(asset_dfs.items()):
                if df is None or df.empty or "Income" not in df.columns:
                    continue
                total_income = df["Income"].iloc[period_start:period_end].sum() if len(df) >= period_end else df["Income"].sum()
                if name not in annual_data:
                    annual_data[name] = []
                annual_data[name].append(total_income)

        if not annual_data or not annual_dates:
            return

        x = np.arange(len(annual_dates))
        bottom = np.zeros(len(annual_dates))
        for i, (name, values) in enumerate(annual_data.items()):
            # Pad or trim to match annual_dates length
            vals = np.array(values[: len(annual_dates)], dtype=float)
            if len(vals) < len(annual_dates):
                vals = np.pad(vals, (0, len(annual_dates) - len(vals)))
            ax.bar(
                x,
                vals,
                bottom=bottom[: len(vals)],
                label=name,
                color=color_cycle[i % len(color_cycle)],
                alpha=0.8,
            )
            bottom[: len(vals)] += vals

        tick_step = max(1, len(annual_dates) // 10)
        ax.set_xticks(x[::tick_step])
        ax.set_xticklabels(
            [str(d)[:4] if hasattr(d, "__str__") else str(d) for d in annual_dates[::tick_step]],
            rotation=45,
            fontsize=7,
        )
        ax.legend(fontsize=7)

    def _single_run_asset_pages(
        self,
        pdf: PdfPages,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        """One 1×3 page per asset."""
        for asset_name, df in asset_dfs.items():
            if df is None or df.empty:
                continue
            fig, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)
            fig.suptitle(f"Asset Detail: {asset_name}", fontsize=13, fontweight="bold")

            # Value over time
            if "Value" in df.columns and "Date" in df.columns:
                axes[0].fill_between(
                    df["Date"],
                    df["Value"],
                    alpha=0.3,
                    color=PALETTE["equity_asset"],
                )
                axes[0].plot(
                    df["Date"],
                    df["Value"],
                    color=PALETTE["equity_asset"],
                    linewidth=1.5,
                )
                axes[0].set_title("Value")
                axes[0].set_xlabel("Date")
                _fmt_dollar_axis(axes[0])
                if retirement_date is not None:
                    _add_retirement_vline(axes[0], retirement_date)

            # Income vs Expenses
            if "Date" in df.columns:
                if "Income" in df.columns:
                    axes[1].plot(
                        df["Date"],
                        df["Income"],
                        color=PALETTE["income"],
                        linewidth=1.5,
                        label="Income",
                    )
                if "Expenses" in df.columns:
                    axes[1].plot(
                        df["Date"],
                        df["Expenses"],
                        color=PALETTE["expenses"],
                        linewidth=1.5,
                        label="Expenses",
                    )
                axes[1].set_title("Income vs Expenses")
                axes[1].set_xlabel("Date")
                _fmt_dollar_axis(axes[1])
                axes[1].legend()
                if retirement_date is not None:
                    _add_retirement_vline(axes[1], retirement_date)

            # Debt or summary stats
            if "Debt" in df.columns and "Date" in df.columns:
                axes[2].fill_between(
                    df["Date"],
                    df["Debt"],
                    alpha=0.3,
                    color=PALETTE["debt"],
                )
                axes[2].plot(
                    df["Date"],
                    df["Debt"],
                    color=PALETTE["debt"],
                    linewidth=1.5,
                    label="Debt",
                )
                axes[2].set_title("Debt")
                axes[2].set_xlabel("Date")
                _fmt_dollar_axis(axes[2])
                axes[2].legend()
            else:
                # Summary stats text box
                stats_lines = []
                for col in df.columns:
                    if col == "Date":
                        continue
                    try:
                        stats_lines.append(
                            f"{col}: min={df[col].min():,.0f}  max={df[col].max():,.0f}"
                        )
                    except (TypeError, ValueError):
                        pass
                stats_text = "\n".join(stats_lines) if stats_lines else "No numeric data"
                axes[2].text(
                    0.05,
                    0.95,
                    stats_text,
                    transform=axes[2].transAxes,
                    fontsize=8,
                    verticalalignment="top",
                    fontfamily="monospace",
                )
                axes[2].set_title("Summary Stats")
                axes[2].axis("off")

            pdf.savefig(fig)
            plt.close(fig)

    # ------------------------------------------------------------------
    # Report 2: monte_carlo_report
    # ------------------------------------------------------------------

    def monte_carlo_report(
        self,
        mc_results: MonteCarloResults,
        percentiles: list[float] = [10, 25, 50, 75, 90],
        reference_df: Optional[pd.DataFrame] = None,
    ) -> Path:
        """Generate a two-page Monte Carlo summary PDF.

        Page 1 — Trajectory fan chart (or histogram fallback) + KPI strip.
        Page 2 — Terminal wealth analysis (2×2).

        Args:
            mc_results: Results from MonteCarloRunner.run().
            percentiles: Percentile values to highlight.
            reference_df: Optional scenario DataFrame for date axis on fan chart.

        Returns:
            Path to the generated PDF.
        """
        output_path = self.output_dir / "monte_carlo_report.pdf"
        terminal_worths = [r.terminal_net_worth for r in mc_results.results]
        ruin_prob = mc_results.ruin_probability()
        pct_values = mc_results.terminal_wealth_percentiles(percentiles)

        with PdfPages(str(output_path)) as pdf:
            self._mc_page1_fan(
                pdf, mc_results, percentiles, pct_values, ruin_prob, terminal_worths, reference_df
            )
            self._mc_page2_terminal(
                pdf, mc_results, percentiles, pct_values, ruin_prob, terminal_worths
            )

        logging.info(f"Monte Carlo report written to {output_path}")
        return output_path

    def _mc_page1_fan(
        self,
        pdf: PdfPages,
        mc_results: MonteCarloResults,
        percentiles: list[float],
        pct_values: dict[float, float],
        ruin_prob: float,
        terminal_worths: list[float],
        reference_df: Optional[pd.DataFrame],
    ) -> None:
        """Fan chart page with KPI strip."""
        fig = plt.figure(figsize=(18, 12), constrained_layout=True)
        fig.suptitle(
            f"Monte Carlo Analysis — {mc_results.n_runs} Runs  |  "
            f"Ruin Probability: {ruin_prob:.1%}",
            fontsize=14,
            fontweight="bold",
        )
        gs = GridSpec(5, 1, figure=fig)
        ax_chart = fig.add_subplot(gs[0:4, 0])
        ax_kpi = fig.add_subplot(gs[4, 0])
        ax_kpi.axis("off")

        if mc_results.has_trajectories():
            trajectories = mc_results.trajectory_array()
            n_periods = max(len(t) for t in trajectories)
            # Pad shorter trajectories with NaN
            arr = np.full((len(trajectories), n_periods), np.nan)
            for i, t in enumerate(trajectories):
                arr[i, : len(t)] = t

            x_axis: object
            if reference_df is not None and "Date" in reference_df.columns:
                x_axis = reference_df["Date"].values
                if len(x_axis) > n_periods:
                    x_axis = x_axis[:n_periods]
            else:
                x_axis = np.arange(n_periods)

            # Grey individual trajectories
            for row in arr:
                valid = ~np.isnan(row)
                if valid.any():
                    x_vals = x_axis[: np.sum(valid)] if hasattr(x_axis, "__len__") else x_axis
                    ax_chart.plot(x_vals, row[valid], color="grey", alpha=0.03, linewidth=0.5)

            # Percentile bands
            p10 = np.nanpercentile(arr, 10, axis=0)
            p25 = np.nanpercentile(arr, 25, axis=0)
            p50 = np.nanpercentile(arr, 50, axis=0)
            p75 = np.nanpercentile(arr, 75, axis=0)
            p90 = np.nanpercentile(arr, 90, axis=0)
            x_len = min(n_periods, len(x_axis) if hasattr(x_axis, "__len__") else n_periods)
            x_plot = x_axis[:x_len] if hasattr(x_axis, "__len__") else np.arange(x_len)

            ax_chart.fill_between(
                x_plot, p10[:x_len], p90[:x_len], alpha=0.2, color=PALETTE["percentile_band"], label="P10–P90"
            )
            ax_chart.fill_between(
                x_plot, p25[:x_len], p75[:x_len], alpha=0.35, color=PALETTE["equity_asset"], label="P25–P75"
            )
            ax_chart.plot(x_plot, p50[:x_len], color=PALETTE["median_line"], linewidth=2.0, label="P50 (Median)")
            ax_chart.plot(x_plot, p10[:x_len], color=PALETTE["percentile_band"], linewidth=1.0, linestyle="--", label="P10")
            ax_chart.plot(x_plot, p90[:x_len], color=PALETTE["percentile_band"], linewidth=1.0, linestyle="--", label="P90")

            # Ruin zone
            ax_chart.axhspan(
                ax_chart.get_ylim()[0] if ax_chart.get_ylim()[0] < 0 else -1,
                0,
                alpha=0.08,
                color=PALETTE["expenses"],
                label="Ruin Zone",
            )

            if reference_df is not None and "retirement_withdrawal" in reference_df.columns:
                ret_date = _find_retirement_date(reference_df)
                if ret_date is not None:
                    _add_retirement_vline(ax_chart, ret_date)

            ax_chart.set_title("Net Worth Trajectory Fan Chart")
            ax_chart.set_xlabel("Date" if reference_df is not None else "Period")
            _fmt_dollar_axis(ax_chart)
            ax_chart.legend(fontsize=8)
        else:
            # Fallback: histogram
            ax_chart.hist(
                terminal_worths,
                bins=40,
                color=PALETTE["equity_asset"],
                edgecolor="white",
                alpha=0.85,
            )
            ax_chart.set_title(
                "Terminal Net Worth Distribution\n"
                "(Run with store_trajectories=True for fan chart)"
            )
            ax_chart.set_xlabel("Terminal Net Worth ($)")
            ax_chart.set_ylabel("Frequency")
            for p, v in pct_values.items():
                ax_chart.axvline(v, linestyle="--", label=f"P{int(p)}: ${v:,.0f}")
            ax_chart.legend(fontsize=8)
            _fmt_dollar_axis(ax_chart, axis="x")

        # KPI strip
        median_tw = pct_values.get(50, np.median(terminal_worths) if terminal_worths else 0)
        p10_tw = pct_values.get(10, np.percentile(terminal_worths, 10) if terminal_worths else 0)
        kpi_texts = [
            f"Ruin Probability\n{ruin_prob:.1%}",
            f"Median Terminal Wealth\n${median_tw:,.0f}",
            f"P10 Terminal Wealth\n${p10_tw:,.0f}",
        ]
        for j, txt in enumerate(kpi_texts):
            ax_kpi.text(
                0.15 + j * 0.33,
                0.5,
                txt,
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                transform=ax_kpi.transAxes,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#F5F5F5", edgecolor="#BDBDBD"),
            )

        pdf.savefig(fig)
        plt.close(fig)

    def _mc_page2_terminal(
        self,
        pdf: PdfPages,
        mc_results: MonteCarloResults,
        percentiles: list[float],
        pct_values: dict[float, float],
        ruin_prob: float,
        terminal_worths: list[float],
    ) -> None:
        """Terminal wealth analysis: 2×2."""
        fig = plt.figure(figsize=(18, 10), constrained_layout=True)
        fig.suptitle("Terminal Wealth Analysis", fontsize=14, fontweight="bold")
        gs = GridSpec(2, 2, figure=fig)

        # [0, 0] Histogram + percentile vlines
        ax_hist = fig.add_subplot(gs[0, 0])
        if terminal_worths:
            pos_vals = [v for v in terminal_worths if v >= 0]
            neg_vals = [v for v in terminal_worths if v < 0]
            bins = 50
            if pos_vals:
                ax_hist.hist(pos_vals, bins=bins, color=PALETTE["equity_asset"], edgecolor="white", alpha=0.85)
            if neg_vals:
                ax_hist.hist(neg_vals, bins=max(5, bins // 5), color=PALETTE["expenses"], edgecolor="white", alpha=0.85)
        for p, v in pct_values.items():
            ax_hist.axvline(v, linestyle="--", linewidth=1.0, label=f"P{int(p)}: ${v:,.0f}")
        ax_hist.set_title("Terminal Net Worth Distribution")
        ax_hist.set_xlabel("Terminal Net Worth ($)")
        ax_hist.set_ylabel("Frequency")
        ax_hist.legend(fontsize=7)
        _fmt_dollar_axis(ax_hist, axis="x")

        # [0, 1] Ruin gauge
        ax_gauge = fig.add_subplot(gs[0, 1])
        survival_prob = 1.0 - ruin_prob
        ax_gauge.barh(
            [0], [ruin_prob], color=PALETTE["expenses"], alpha=0.85, label=f"Ruin {ruin_prob:.1%}", height=0.4
        )
        ax_gauge.barh(
            [0], [survival_prob], left=[ruin_prob], color=PALETTE["income"], alpha=0.85,
            label=f"Survive {survival_prob:.1%}", height=0.4
        )
        ax_gauge.set_xlim(0, 1)
        ax_gauge.set_yticks([])
        ax_gauge.set_xlabel("Probability")
        ax_gauge.set_title("Ruin vs Survival")
        ax_gauge.text(ruin_prob / 2, 0, f"{ruin_prob:.1%}", ha="center", va="center", fontsize=14, fontweight="bold", color="white")
        ax_gauge.text(ruin_prob + survival_prob / 2, 0, f"{survival_prob:.1%}", ha="center", va="center", fontsize=14, fontweight="bold", color="white")
        ax_gauge.legend(fontsize=8)

        # [1, 0] Percentile waterfall — horizontal bars
        ax_water = fig.add_subplot(gs[1, 0])
        all_pcts = [5, 10, 25, 50, 75, 90, 95]
        all_pct_vals = mc_results.terminal_wealth_percentiles(all_pcts)
        sorted_pcts = sorted(all_pct_vals.keys())
        bar_vals = [all_pct_vals[p] for p in sorted_pcts]
        bar_labels = [f"P{int(p)}" for p in sorted_pcts]
        bar_colors = [PALETTE["expenses"] if v < 0 else PALETTE["equity_asset"] for v in bar_vals]
        ax_water.barh(bar_labels, bar_vals, color=bar_colors, edgecolor="white", alpha=0.85)
        for i, (p, v) in enumerate(zip(sorted_pcts, bar_vals)):
            ax_water.text(
                v,
                i,
                f" ${v:,.0f}",
                ha="left" if v >= 0 else "right",
                va="center",
                fontsize=7,
            )
        ax_water.axvline(0, color="black", linewidth=0.8)
        ax_water.set_title("Terminal Wealth by Percentile")
        ax_water.set_xlabel("Net Worth ($)")
        _fmt_dollar_axis(ax_water, axis="x")

        # [1, 1] Ruin period histogram
        ax_ruin = fig.add_subplot(gs[1, 1])
        ruin_periods = [r.ruin_period for r in mc_results.results if r.ruin_period is not None]
        if ruin_periods:
            ax_ruin.hist(ruin_periods, bins=30, color=PALETTE["expenses"], edgecolor="white", alpha=0.85)
            ax_ruin.set_title("Ruin Period Distribution")
            ax_ruin.set_xlabel("Period of First Ruin")
            ax_ruin.set_ylabel("Count")
        else:
            ax_ruin.text(
                0.5, 0.5, "No ruin events\nacross all runs",
                ha="center", va="center", transform=ax_ruin.transAxes,
                fontsize=13, color=PALETTE["income"],
            )
            ax_ruin.set_title("Ruin Period Distribution")
            ax_ruin.axis("off")

        pdf.savefig(fig)
        plt.close(fig)

    # ------------------------------------------------------------------
    # Report 3: tax_optimization_report
    # ------------------------------------------------------------------

    def tax_optimization_report(
        self,
        scenario_df: pd.DataFrame,
        asset_dfs: Optional[dict[str, Optional[pd.DataFrame]]] = None,
    ) -> Path:
        """Generate a two-page tax strategy analysis PDF.

        Page 1 — Tax overview (2×2).
        Page 2 — RMD deep dive (2×1) if age >= 73 reached, else single notice panel.

        Args:
            scenario_df: Scenario-level DataFrame from get_scenario_dataframe().
            asset_dfs: Optional asset DataFrames for income-by-tax-class breakdown.

        Returns:
            Path to the generated PDF.
        """
        output_path = self.output_dir / "tax_optimization_report.pdf"
        retirement_date = _find_retirement_date(scenario_df)
        rmd_date = _find_rmd_date(scenario_df)

        with PdfPages(str(output_path)) as pdf:
            self._tax_page1_overview(pdf, scenario_df, asset_dfs, retirement_date, rmd_date)
            self._tax_page2_rmd(pdf, scenario_df, rmd_date)

        logging.info(f"Tax optimisation report written to {output_path}")
        return output_path

    def _tax_page1_overview(
        self,
        pdf: PdfPages,
        scenario_df: pd.DataFrame,
        asset_dfs: Optional[dict[str, Optional[pd.DataFrame]]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        """Tax overview page: 2×2."""
        fig = plt.figure(figsize=(18, 10), constrained_layout=True)
        fig.suptitle("Tax Optimisation Analysis", fontsize=14, fontweight="bold")
        gs = GridSpec(2, 2, figure=fig)
        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None

        # [0, 0] Taxes vs Income over time
        ax_tv = fig.add_subplot(gs[0, 0])
        if dates is not None:
            if "taxes_paid" in scenario_df.columns:
                ax_tv.fill_between(
                    dates,
                    scenario_df["taxes_paid"],
                    alpha=0.4,
                    color=PALETTE["taxes"],
                    label="Taxes Paid",
                )
                ax_tv.plot(dates, scenario_df["taxes_paid"], color=PALETTE["taxes"], linewidth=1.2)
            if "monthly_taxable_income" in scenario_df.columns:
                ax_tv.plot(
                    dates,
                    scenario_df["monthly_taxable_income"],
                    color=PALETTE["income"],
                    linewidth=1.5,
                    label="Taxable Income",
                )
        ax_tv.set_title("Taxes vs Income")
        ax_tv.set_xlabel("Date")
        _fmt_dollar_axis(ax_tv)
        _annotate_axes(ax_tv, scenario_df, retirement_date, rmd_date, shade=False)
        ax_tv.legend(fontsize=8)

        # [0, 1] Effective Tax Rate %
        ax_eff = fig.add_subplot(gs[0, 1])
        if (
            dates is not None
            and "taxes_paid" in scenario_df.columns
            and "monthly_taxable_income" in scenario_df.columns
        ):
            income = scenario_df["monthly_taxable_income"].replace(0, np.nan)
            eff_rate = (scenario_df["taxes_paid"] / income * 100).fillna(0)
            ax_eff.fill_between(dates, eff_rate, alpha=0.4, color=PALETTE["taxes"], label="Eff. Rate")
            ax_eff.plot(dates, eff_rate, color=PALETTE["taxes"], linewidth=1.2)
            # Annotate RMD rate jump
            if rmd_date is not None:
                rmd_mask = scenario_df["age"] >= 73 if "age" in scenario_df.columns else pd.Series(False, index=scenario_df.index)
                if rmd_mask.any() and not rmd_mask.all():
                    pre_rate = eff_rate[~rmd_mask].mean()
                    post_rate = eff_rate[rmd_mask].mean()
                    ax_eff.annotate(
                        f"RMD: +{post_rate - pre_rate:.1f}pp",
                        xy=(rmd_date, post_rate),
                        xytext=(10, 10),
                        textcoords="offset points",
                        fontsize=8,
                        arrowprops=dict(arrowstyle="->", color="black"),
                    )
        ax_eff.set_title("Effective Tax Rate (%)")
        ax_eff.set_xlabel("Date")
        ax_eff.set_ylabel("%")
        _annotate_axes(ax_eff, scenario_df, retirement_date, rmd_date, shade=False)
        ax_eff.legend(fontsize=8)

        # [1, 0] Income by Tax Class
        ax_cls = fig.add_subplot(gs[1, 0])
        self._plot_income_by_tax_class(ax_cls, scenario_df, asset_dfs)
        ax_cls.set_title("Income by Tax Class")
        ax_cls.set_xlabel("Date")
        _fmt_dollar_axis(ax_cls)
        _annotate_axes(ax_cls, scenario_df, retirement_date, rmd_date, shade=False)

        # [1, 1] Pre / Post / RMD Tax Comparison — grouped bar
        ax_cmp = fig.add_subplot(gs[1, 1])
        self._plot_phase_tax_comparison(ax_cmp, scenario_df, retirement_date, rmd_date)
        ax_cmp.set_title("Avg Monthly Taxes by Phase")
        ax_cmp.set_ylabel("Avg Monthly Taxes ($)")
        _fmt_dollar_axis(ax_cmp)

        pdf.savefig(fig)
        plt.close(fig)

    def _plot_income_by_tax_class(
        self,
        ax: plt.Axes,
        scenario_df: pd.DataFrame,
        asset_dfs: Optional[dict[str, Optional[pd.DataFrame]]],
    ) -> None:
        """Stacked area if asset_dfs available, else single line."""
        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None
        if dates is None:
            return

        if asset_dfs:
            class_colors = {
                "ordinary": PALETTE["income"],
                "capital_gains": PALETTE["equity_asset"],
                "social_security": PALETTE["social_security"],
            }
            stacks: dict[str, np.ndarray] = {}
            for name, df in asset_dfs.items():
                if df is None or df.empty or "Income" not in df.columns or "Date" not in df.columns:
                    continue
                merged = pd.merge(
                    pd.DataFrame({"Date": dates}), df[["Date", "Income"]], on="Date", how="left"
                ).fillna(0)
                tax_class = "ordinary"
                if hasattr(df, "attrs") and "tax_class" in df.attrs:
                    tax_class = df.attrs["tax_class"]
                elif "social_security" in name.lower() or "ss" in name.lower():
                    tax_class = "social_security"
                elif "capital" in name.lower() or "equity" in name.lower():
                    tax_class = "capital_gains"
                stacks[tax_class] = stacks.get(tax_class, np.zeros(len(dates))) + merged["Income"].values

            if stacks:
                labels = list(stacks.keys())
                data = [stacks[k] for k in labels]
                colors = [class_colors.get(k, PALETTE["income"]) for k in labels]
                ax.stackplot(dates, *data, labels=labels, colors=colors, alpha=0.75)
                ax.legend(fontsize=7)
                return

        # Fallback — single income line
        if "monthly_taxable_income" in scenario_df.columns:
            ax.plot(
                dates,
                scenario_df["monthly_taxable_income"],
                color=PALETTE["income"],
                linewidth=1.5,
                label="Taxable Income",
            )
            ax.legend(fontsize=7)
            ax.text(
                0.02, 0.02, "No asset tax-class breakdown available",
                transform=ax.transAxes, fontsize=7, color="grey"
            )

    def _plot_phase_tax_comparison(
        self,
        ax: plt.Axes,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        """Grouped bar: average monthly taxes in pre-ret / post-ret / RMD phases."""
        if "taxes_paid" not in scenario_df.columns or "Date" not in scenario_df.columns:
            ax.text(0.5, 0.5, "No tax data", ha="center", va="center", transform=ax.transAxes)
            return

        phases: dict[str, pd.Series] = {}
        taxes = scenario_df["taxes_paid"]
        dates = scenario_df["Date"]

        if retirement_date is not None:
            pre_mask = dates < retirement_date
            if pre_mask.any():
                phases["Pre-Retirement"] = taxes[pre_mask]
            post_mask = dates >= retirement_date
            if rmd_date is not None:
                post_mask = post_mask & (dates < rmd_date)
            if post_mask.any():
                phases["Post-Retirement"] = taxes[post_mask]
        else:
            if taxes.any():
                phases["All Periods"] = taxes

        if rmd_date is not None:
            rmd_mask = dates >= rmd_date
            if rmd_mask.any():
                phases["RMD Period"] = taxes[rmd_mask]

        if not phases:
            phases["All Periods"] = taxes

        phase_names = list(phases.keys())
        avgs = [phases[k].mean() for k in phase_names]
        phase_colors = [PALETTE["salary"], PALETTE["social_security"], PALETTE["taxes"]]
        bars = ax.bar(
            phase_names,
            avgs,
            color=[phase_colors[i % len(phase_colors)] for i in range(len(phase_names))],
            edgecolor="white",
            alpha=0.85,
        )
        for bar, val in zip(bars, avgs):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"${val:,.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        ax.set_xticks(range(len(phase_names)))
        ax.set_xticklabels(phase_names, rotation=15, ha="right", fontsize=8)

    def _tax_page2_rmd(
        self,
        pdf: PdfPages,
        scenario_df: pd.DataFrame,
        rmd_date: Optional[object],
    ) -> None:
        """RMD deep-dive page or notice if RMD period not reached."""
        has_rmd = "age" in scenario_df.columns and scenario_df["age"].max() >= 73

        if not has_rmd:
            fig, ax = plt.subplots(1, 1, figsize=(18, 4), constrained_layout=True)
            fig.suptitle("RMD Deep Dive", fontsize=14, fontweight="bold")
            ax.text(
                0.5,
                0.5,
                "RMD period not reached in this simulation\n(age never reaches 73)",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=14,
                color="grey",
            )
            ax.axis("off")
            pdf.savefig(fig)
            plt.close(fig)
            return

        fig = plt.figure(figsize=(18, 8), constrained_layout=True)
        fig.suptitle("RMD Deep Dive (Age 73+)", fontsize=14, fontweight="bold")
        gs = GridSpec(2, 1, figure=fig)

        dates = scenario_df["Date"] if "Date" in scenario_df.columns else None
        rmd_mask = scenario_df["age"] >= 73 if "age" in scenario_df.columns else pd.Series(False, index=scenario_df.index)

        # [0] Taxes during RMD period
        ax_rmd = fig.add_subplot(gs[0, 0])
        if dates is not None and "taxes_paid" in scenario_df.columns and rmd_mask.any():
            rmd_dates = dates[rmd_mask]
            rmd_taxes = scenario_df.loc[rmd_mask, "taxes_paid"]
            ax_rmd.fill_between(rmd_dates, rmd_taxes, alpha=0.5, color=PALETTE["taxes"], label="Taxes (RMD period)")
            ax_rmd.plot(rmd_dates, rmd_taxes, color=PALETTE["taxes"], linewidth=1.5)
            total_rmd_taxes = rmd_taxes.sum()
            ax_rmd.text(
                0.98, 0.95,
                f"Total RMD taxes: ${total_rmd_taxes:,.0f}",
                ha="right", va="top", transform=ax_rmd.transAxes,
                fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF3E0", edgecolor=PALETTE["taxes"]),
            )
        ax_rmd.set_title("Taxes During RMD Period")
        ax_rmd.set_xlabel("Date")
        _fmt_dollar_axis(ax_rmd)
        if rmd_date is not None:
            _add_rmd_vline(ax_rmd, rmd_date)
        ax_rmd.legend(fontsize=8)

        # [1] Cumulative taxes by phase
        ax_cum = fig.add_subplot(gs[1, 0])
        if dates is not None and "taxes_paid" in scenario_df.columns:
            pre_mask = ~rmd_mask
            retirement_date = _find_retirement_date(scenario_df)
            if retirement_date is not None:
                pre_ret_mask = dates < retirement_date
                post_ret_mask = (dates >= retirement_date) & ~rmd_mask
            else:
                pre_ret_mask = pre_mask
                post_ret_mask = pd.Series(False, index=scenario_df.index)

            taxes = scenario_df["taxes_paid"]
            if pre_ret_mask.any():
                cumsum_pre = taxes[pre_ret_mask].cumsum().reset_index(drop=True)
                ax_cum.plot(
                    dates[pre_ret_mask].values,
                    cumsum_pre.values,
                    color=PALETTE["salary"],
                    linewidth=1.5,
                    label="Pre-Retirement",
                )
            if post_ret_mask.any():
                cumsum_post = taxes[post_ret_mask].cumsum().reset_index(drop=True)
                ax_cum.plot(
                    dates[post_ret_mask].values,
                    cumsum_post.values,
                    color=PALETTE["social_security"],
                    linewidth=1.5,
                    label="Post-Ret (pre-RMD)",
                )
            if rmd_mask.any():
                cumsum_rmd = taxes[rmd_mask].cumsum().reset_index(drop=True)
                ax_cum.plot(
                    dates[rmd_mask].values,
                    cumsum_rmd.values,
                    color=PALETTE["taxes"],
                    linewidth=1.5,
                    label="RMD Period",
                )
        ax_cum.set_title("Cumulative Taxes by Phase")
        ax_cum.set_xlabel("Date")
        _fmt_dollar_axis(ax_cum)
        ax_cum.legend(fontsize=8)

        pdf.savefig(fig)
        plt.close(fig)
