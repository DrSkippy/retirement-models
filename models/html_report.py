"""HTML mini-site report builder for retirement model simulation runs."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from jinja2 import Environment, PackageLoader, select_autoescape
from markupsafe import Markup

from models.config import WorldConfig
from models.monte_carlo import MonteCarloResults

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

PALETTE: dict[str, str] = {
    "net_worth": "#3b82f6",
    "debt": "#dc2626",
    "income": "#059669",
    "expenses": "#dc2626",
    "taxes": "#f59e0b",
    "investment": "#1e3a5f",
    "free_cash_flow": "#3b82f6",
    "withdrawal": "#7c3aed",
    "retirement_line": "#f59e0b",
    "rmd_line": "#dc2626",
    "equity_asset": "#3b82f6",
    "real_estate": "#059669",
    "social_security": "#6ee7b7",
    "salary": "#34d399",
    "median_line": "#1e3a5f",
    "percentile_band": "#93c5fd",
}

_ASSET_COLORS = [
    "#3b82f6",
    "#059669",
    "#7c3aed",
    "#f59e0b",
    "#1e3a5f",
    "#dc2626",
    "#6ee7b7",
]

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _find_retirement_date(scenario_df: pd.DataFrame) -> Optional[object]:
    """Return first Date where retirement_withdrawal > 0."""
    if "retirement_withdrawal" not in scenario_df.columns:
        return None
    mask = scenario_df["retirement_withdrawal"] > 0
    if not mask.any():
        return None
    return scenario_df.loc[mask, "Date"].iloc[0]


def _find_rmd_date(scenario_df: pd.DataFrame) -> Optional[object]:
    """Return first Date where age >= 73."""
    if "age" not in scenario_df.columns:
        return None
    mask = scenario_df["age"] >= 73
    if not mask.any():
        return None
    return scenario_df.loc[mask, "Date"].iloc[0]


def _find_ss_start_date(asset_dfs: dict) -> Optional[object]:
    """Return first Date where Social Security income > 0."""
    for name, df in asset_dfs.items():
        if df is None or df.empty or "social" not in name.lower():
            continue
        if "Income" not in df.columns or "Date" not in df.columns:
            continue
        mask = df["Income"] > 0
        if mask.any():
            return df.loc[mask, "Date"].iloc[0]
    return None


def _build_debt_analysis(
    asset_dfs: dict,
    asset_config_dicts: list,
) -> list[dict]:
    """Return per-loan debt analysis records for RE assets with non-zero debt.

    Each record contains the asset DataFrame plus computed interest/principal
    series derived from the debt trajectory and the loan config.
    """
    config_by_name = {c.get("name", ""): c for c in asset_config_dicts}
    result = []
    for name, df in asset_dfs.items():
        if df is None or df.empty or "Debt" not in df.columns:
            continue
        if df["Debt"].max() <= 0.01:
            continue
        cfg = config_by_name.get(name, {})
        if cfg.get("type") != "RealEstate":
            continue
        interest_rate: float = cfg.get("interest_rate", 0.0)
        monthly_rate: float = interest_rate / 12.0
        payment: float = cfg.get("payment", 0.0)
        extra_principal: float = cfg.get("extra_principal_payment", 0.0)
        initial_debt: float = float(cfg.get("initial_debt", df["Debt"].iloc[0]))

        # Starting balance each period: initial_debt for period 0, prior ending
        # balance thereafter.  Clip at 0 so post-payoff periods contribute nothing.
        prior_debt = (
            pd.concat([pd.Series([initial_debt]), df["Debt"].iloc[:-1]])
            .clip(lower=0.0)
            .reset_index(drop=True)
        )
        monthly_interest = prior_debt * monthly_rate
        monthly_principal = (payment - monthly_interest).clip(lower=0.0)

        # Stop accumulating after payoff
        active_mask = prior_debt > 0.01
        monthly_interest = monthly_interest.where(active_mask, 0.0)
        monthly_principal = monthly_principal.where(active_mask, 0.0)

        cum_interest = monthly_interest.cumsum()
        cum_principal = monthly_principal.cumsum()

        payoff_mask = df["Debt"] <= 0.01
        payoff_date = df.loc[payoff_mask, "Date"].iloc[0] if payoff_mask.any() else None
        total_interest = float(monthly_interest.sum())
        total_principal = float(monthly_principal.sum())

        result.append(
            {
                "name": name,
                "df": df,
                "cfg": cfg,
                "interest_rate": interest_rate,
                "monthly_rate": monthly_rate,
                "payment": payment,
                "extra_principal": extra_principal,
                "initial_debt": initial_debt,
                "monthly_interest": monthly_interest,
                "monthly_principal": monthly_principal,
                "cum_interest": cum_interest,
                "cum_principal": cum_principal,
                "payoff_date": payoff_date,
                "total_interest": total_interest,
                "total_principal": total_principal,
                "payoff_date_fmt": str(payoff_date) if payoff_date else "Beyond simulation",
                "rate_fmt": f"{interest_rate:.3%}",
                "total_interest_fmt": _fmt_dollar(total_interest) if total_interest else "N/A",
                "total_cost_fmt": _fmt_dollar(total_interest + total_principal),
            }
        )
    return result


def _fmt_dollar(x: Optional[float]) -> str:
    """Format a dollar value as $1.2m / $500k / -$200k / N/A."""
    if x is None:
        return "N/A"
    neg = x < 0
    ax = abs(x)
    if ax >= 1_000_000:
        s = f"${ax / 1_000_000:.2f}m"
    elif ax >= 1_000:
        s = f"${ax / 1_000:.0f}k"
    else:
        s = f"${ax:.0f}"
    return f"-{s}" if neg else s


def _fmt_pct(x: float) -> str:
    return f"{x:.1%}"


def _compute_summary_metrics(scenario_df: pd.DataFrame) -> dict:
    """Compute summary KPI metrics from scenario_df."""
    nw = scenario_df["net_worth"]
    peak_idx = nw.idxmax()
    ret_mask = scenario_df["retirement_withdrawal"] > 0 if "retirement_withdrawal" in scenario_df.columns else pd.Series(False, index=scenario_df.index)

    min_post = nw[ret_mask].min() if ret_mask.any() else None
    retirement_date = scenario_df.loc[ret_mask, "Date"].iloc[0] if ret_mask.any() else None

    metrics: dict = {
        "peak_net_worth": nw.max(),
        "peak_net_worth_fmt": _fmt_dollar(nw.max()),
        "peak_age": scenario_df.loc[peak_idx, "age"] if "age" in scenario_df.columns else None,
        "peak_age_fmt": f"{scenario_df.loc[peak_idx, 'age']:.1f}" if "age" in scenario_df.columns else "N/A",
        "min_post_retirement_raw": min_post,
        "min_post_retirement_net_worth_fmt": _fmt_dollar(min_post),
        "terminal_net_worth": nw.iloc[-1],
        "terminal_net_worth_fmt": _fmt_dollar(nw.iloc[-1]),
        "retirement_date": retirement_date,
    }
    for target_age in [70, 75, 80, 85]:
        mask = scenario_df["age"] >= target_age if "age" in scenario_df.columns else pd.Series(False, index=scenario_df.index)
        val = scenario_df.loc[mask, "net_worth"].iloc[0] if mask.any() else None
        metrics[f"net_worth_at_{target_age}"] = val
        metrics[f"net_worth_at_{target_age}_fmt"] = _fmt_dollar(val)
    return metrics


def _run_dir_name(label: Optional[str], is_mc: bool) -> str:
    prefix = "run_mc" if is_mc else "run"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if label:
        safe_label = label.replace(" ", "_")
        return f"{prefix}_{stamp}_{safe_label}"
    return f"{prefix}_{stamp}"


def _serialize(fig: go.Figure, height: int = 420, right_margin: int = 20) -> Markup:
    """Convert a Plotly figure to an embeddable HTML div."""
    fig.update_layout(height=height, margin=dict(l=48, r=right_margin, t=36, b=96))
    html = pio.to_html(fig, full_html=False, include_plotlyjs=False, config={"responsive": True})
    return Markup(html)


def _add_vline_date(
    fig: go.Figure,
    date_val: object,
    color: str,
    width: float = 1.5,
    dash: str = "solid",
    label: str = "",
) -> None:
    """Add a vertical line at a date position using add_shape (avoids Plotly annotation bug on date axes)."""
    x_str = str(date_val)
    fig.add_shape(
        type="line",
        x0=x_str, x1=x_str,
        y0=0, y1=1,
        yref="paper",
        line=dict(color=color, width=width, dash=dash),
    )
    if label:
        fig.add_annotation(
            x=x_str,
            y=1,
            yref="paper",
            text=label,
            showarrow=False,
            font=dict(size=9, color=color),
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.7)",
        )


def _apply_retirement_markers(
    fig: go.Figure,
    retirement_date: Optional[object],
    rmd_date: Optional[object],
    end_date: Optional[object] = None,
) -> None:
    """Add retirement and RMD vertical markers to a figure."""
    if retirement_date is not None:
        _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.5, label="Retirement")
        if end_date is not None:
            fig.add_vrect(
                x0=str(retirement_date),
                x1=str(end_date),
                fillcolor="rgba(100,116,139,0.05)",
                layer="below",
                line_width=0,
            )
    if rmd_date is not None:
        _add_vline_date(fig, rmd_date, PALETTE["rmd_line"], width=1.2, dash="dash", label="RMD 73")


def _base_layout(title: str = "") -> dict:
    return dict(
        title=dict(text=title, font=dict(size=13, color="#1e3a5f"), x=0, xanchor="left", pad=dict(b=4)),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size=11, color="#0f172a"),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, font=dict(size=10)),
        xaxis=dict(gridcolor="#e2e8f0", linecolor="#cbd5e1", showgrid=True, gridwidth=0.5),
        yaxis=dict(gridcolor="#e2e8f0", linecolor="#cbd5e1", showgrid=True, gridwidth=0.5, tickprefix="$"),
        hovermode="x unified",
    )


# ---------------------------------------------------------------------------
# Parameters data builder
# ---------------------------------------------------------------------------


def _fmt_pct_plain(x: float) -> str:
    return f"{x * 100:.2f}%"


def _build_parameters_data(world_config: WorldConfig, asset_config_dicts: list[dict]) -> dict:
    """Assemble structured data for the parameters page template."""
    wc = world_config

    # Duration in years
    duration_days = (wc.end_date - wc.start_date).days
    duration_years = round(duration_days / 365.25, 1)

    timeline = [
        {"label": "Birth Date", "value": str(wc.birth_date)},
        {"label": "Spouse Birth Date", "value": str(wc.spouse_birth_date)},
        {"label": "Projection Start", "value": str(wc.start_date)},
        {"label": "Projection End", "value": str(wc.end_date)},
        {"label": "Projection Duration", "value": f"{duration_years} years"},
        {"label": "Retirement Age", "value": str(wc.retirement_age)},
        {"label": "Estimated Retirement Date", "value": str(wc.retirement_date)},
    ]

    behavior = {
        "savings": [
            {"label": "Savings Rate", "value": _fmt_pct_plain(wc.savings_rate)},
            {"label": "Withdrawal Rate (4% rule)", "value": _fmt_pct_plain(wc.withdrawal_rate)},
            {"label": "Inflation Rate", "value": _fmt_pct_plain(wc.inflation_rate)},
        ],
        "allocation": [
            {"label": "Stock Allocation", "value": _fmt_pct_plain(wc.allocation.stock_allocation)},
            {"label": "Bond Allocation", "value": _fmt_pct_plain(wc.allocation.bond_allocation)},
        ],
        "taxes": [
            {"label": "Ordinary Income", "value": _fmt_pct_plain(wc.tax_classes.income)},
            {"label": "Capital Gains", "value": _fmt_pct_plain(wc.tax_classes.capital_gain)},
            {"label": "Social Security", "value": _fmt_pct_plain(wc.tax_classes.social_security)},
        ],
    }

    _type_badge = {
        "Equity": "badge-equity",
        "RealEstate": "badge-realestate",
        "Salary": "badge-salary",
    }

    assets = []
    for cfg in sorted(asset_config_dicts, key=lambda d: d.get("type", ""), reverse=True):
        atype = cfg.get("type", "")
        initial: list[dict] = []
        beh: list[dict] = []
        schedule = None

        if atype == "Equity":
            iv = cfg.get("initial_value")
            initial = [
                {"label": "Initial Value", "value": _fmt_dollar(iv), "color": ""},
                {"label": "Expense Rate", "value": _fmt_pct_plain(cfg.get("initial_expense_rate", 0))},
            ]
            beh = [
                {"label": "Appreciation Rate", "value": _fmt_pct_plain(cfg.get("appreciation_rate", 0))},
                {"label": "Appreciation Volatility", "value": _fmt_pct_plain(cfg.get("appreciation_rate_volatility", 0))},
                {"label": "Dividend Rate", "value": _fmt_pct_plain(cfg.get("dividend_rate", 0))},
                {"label": "SP500 Historical Returns", "value": "Yes" if cfg.get("sampled_monthly_sp500_returns") else "No"},
                {"label": "Active", "value": f"{cfg.get('start_date','?')} → {cfg.get('end_date','?')}"},
            ]

        elif atype == "RealEstate":
            iv = cfg.get("initial_value", 0)
            debt = cfg.get("initial_debt", 0)
            ltv = (debt / iv * 100) if iv else 0
            orig_date = cfg.get("loan_origination_date")
            orig_amount = cfg.get("original_loan_amount")
            initial = [
                {"label": "Initial Value", "value": _fmt_dollar(iv), "color": ""},
                {"label": "Initial Debt (manual)", "value": _fmt_dollar(debt), "color": "neg"},
                {"label": "LTV Ratio", "value": f"{ltv:.1f}%", "color": ""},
                {"label": "Net Equity", "value": _fmt_dollar(iv - debt), "color": "pos"},
            ]
            if orig_date:
                initial.append({"label": "Loan Origination Date", "value": str(orig_date), "color": ""})
            if orig_amount:
                initial.append({"label": "Original Loan Amount", "value": _fmt_dollar(orig_amount), "color": ""})
            extra_pp = cfg.get("extra_principal_payment", 0)
            beh = [
                {"label": "Appreciation Rate", "value": _fmt_pct_plain(cfg.get("appreciation_rate", 0))},
                {"label": "Appreciation Volatility (monthly σ)", "value": _fmt_pct_plain(cfg.get("appreciation_rate_volatility", 0))},
                {"label": "Property Tax Rate", "value": _fmt_pct_plain(cfg.get("property_tax_rate", 0))},
                {"label": "Insurance / yr", "value": _fmt_dollar(cfg.get("insurance_cost", 0))},
                {"label": "Management Fee", "value": _fmt_pct_plain(cfg.get("management_fee_rate", 0))},
                {"label": "Monthly Rental Income", "value": _fmt_dollar(cfg.get("monthly_rental_income", 0))},
                {"label": "Rental Expense Rate", "value": _fmt_pct_plain(cfg.get("rental_expense_rate", 0))},
                {"label": "Mortgage Rate", "value": _fmt_pct_plain(cfg.get("interest_rate", 0))},
                {"label": "Monthly Payment", "value": _fmt_dollar(cfg.get("payment", 0))},
                {"label": "Extra Principal / mo", "value": _fmt_dollar(extra_pp)},
                {"label": "Active", "value": f"{cfg.get('start_date','?')} → {cfg.get('end_date','?')}"},
            ]

        elif atype == "Salary":
            if "retirement_age_based_benefit" in cfg:
                schedule = [
                    {"age": age, "amount": _fmt_dollar(amt)}
                    for age, amt in sorted(cfg["retirement_age_based_benefit"].items(), key=lambda x: int(x[0]))
                ]
                beh = [
                    {"label": "COLA", "value": _fmt_pct_plain(cfg.get("cola", 0))},
                    {"label": "Starts", "value": str(cfg.get("start_date", "?"))},
                ]
            else:
                salary = cfg.get("salary", 0)
                initial = [
                    {"label": "Annual Salary", "value": _fmt_dollar(salary), "color": ""},
                    {"label": "Monthly Salary", "value": _fmt_dollar(salary / 12), "color": ""},
                ]
                beh = [
                    {"label": "COLA", "value": _fmt_pct_plain(cfg.get("cola", 0))},
                    {"label": "Active", "value": f"{cfg.get('start_date','?')} → {cfg.get('end_date','?')}"},
                ]

        assets.append({
            "name": cfg.get("name", "Unknown"),
            "description": cfg.get("description", ""),
            "type": atype,
            "type_badge": _type_badge.get(atype, "badge-muted"),
            "tax_class": cfg.get("tax_class", ""),
            "initial_conditions": initial,
            "behavior": beh,
            "schedule": schedule,
        })

    return {
        "behavior": behavior,
        "initial": {
            "timeline": timeline,
            "assets": assets,
        },
    }


# ---------------------------------------------------------------------------
# HtmlReportBuilder
# ---------------------------------------------------------------------------


class HtmlReportBuilder:
    """Generates HTML mini-site directories for simulation runs."""

    def __init__(self, output_dir: str = "./output", label: Optional[str] = None) -> None:
        """Initialise with output directory and optional label.

        Args:
            output_dir: Parent directory under which run subdirectories are created.
            label: Human-readable label incorporated into the run directory name.
        """
        self.base_output_dir = Path(output_dir)
        self.label = label
        self._jinja_env = self._build_jinja_env()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def single_run_report(
        self,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        world_config: Optional[WorldConfig] = None,
        asset_config_dicts: Optional[list[dict]] = None,
    ) -> Path:
        """Generate a single-run HTML mini-site.

        Creates output/<run_dir>/ containing index.html, timeseries.html,
        portfolio.html, tax.html, and parameters.html (if world_config supplied).

        Args:
            scenario_df: Scenario-level DataFrame from get_scenario_dataframe().
            asset_dfs: Mapping of asset name → asset DataFrame.
            world_config: WorldConfig instance for the parameters page.
            asset_config_dicts: Raw asset JSON dicts for the parameters page.

        Returns:
            Path to the generated run directory.
        """
        run_dir = self.base_output_dir / _run_dir_name(self.label, is_mc=False)
        run_dir.mkdir(parents=True, exist_ok=True)

        retirement_date = _find_retirement_date(scenario_df)
        rmd_date = _find_rmd_date(scenario_df)
        ss_start_date = _find_ss_start_date(asset_dfs)
        start_date = scenario_df["Date"].iloc[0] if "Date" in scenario_df.columns and len(scenario_df) else None
        metrics = _compute_summary_metrics(scenario_df)

        self._write_index(run_dir, scenario_df, metrics, retirement_date, rmd_date, start_date, ss_start_date)
        self._write_timeseries(run_dir, scenario_df, asset_dfs, retirement_date, rmd_date)
        self._write_portfolio(run_dir, scenario_df, asset_dfs, retirement_date, rmd_date)
        self._write_tax(run_dir, scenario_df, asset_dfs, retirement_date, rmd_date)
        debt_assets = _build_debt_analysis(asset_dfs, asset_config_dicts or [])
        if debt_assets:
            self._write_debt(run_dir, debt_assets, self._run_name(run_dir))
        if world_config is not None:
            self._write_parameters(run_dir, world_config, asset_config_dicts or [], is_mc=False)

        logging.info(f"Single-run mini-site written to {run_dir}")
        return run_dir

    def monte_carlo_report(
        self,
        mc_results: MonteCarloResults,
        percentiles: list[float] = None,
        reference_df: Optional[pd.DataFrame] = None,
        world_config: Optional[WorldConfig] = None,
        asset_config_dicts: Optional[list[dict]] = None,
    ) -> Path:
        """Generate a Monte Carlo HTML mini-site.

        Creates output/<run_mc_dir>/ containing index.html, distribution.html,
        and parameters.html (if world_config supplied).

        Args:
            mc_results: MonteCarloResults from MonteCarloRunner.run().
            percentiles: Percentile points to compute and display.
            reference_df: Optional deterministic scenario_df for overlay on fan chart.
            world_config: WorldConfig instance for the parameters page.
            asset_config_dicts: Raw asset JSON dicts for the parameters page.

        Returns:
            Path to the generated run directory.
        """
        if percentiles is None:
            percentiles = [5, 10, 25, 50, 75, 90, 95]

        run_dir = self.base_output_dir / _run_dir_name(self.label, is_mc=True)
        run_dir.mkdir(parents=True, exist_ok=True)

        ruin_prob = mc_results.ruin_probability()
        pct_values = mc_results.terminal_wealth_percentiles(percentiles)
        retirement_date = _find_retirement_date(reference_df) if reference_df is not None else None

        self._write_mc_index(run_dir, mc_results, pct_values, ruin_prob, percentiles, retirement_date)
        self._write_distribution(run_dir, mc_results, pct_values, ruin_prob, percentiles)
        if world_config is not None:
            self._write_parameters(run_dir, world_config, asset_config_dicts or [], is_mc=True)

        logging.info(f"Monte Carlo mini-site written to {run_dir}")
        return run_dir

    # ------------------------------------------------------------------
    # Jinja2 environment
    # ------------------------------------------------------------------

    def _build_jinja_env(self) -> Environment:
        return Environment(
            loader=PackageLoader("models", "templates"),
            autoescape=select_autoescape(["html"]),
        )

    def _render(self, template_name: str, **ctx: object) -> str:
        tmpl = self._jinja_env.get_template(template_name)
        return tmpl.render(**ctx)

    def _run_name(self, run_dir: Path) -> str:
        return run_dir.name

    # ------------------------------------------------------------------
    # Single-run page writers
    # ------------------------------------------------------------------

    def _write_index(
        self,
        run_dir: Path,
        scenario_df: pd.DataFrame,
        metrics: dict,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
        start_date: Optional[object] = None,
        ss_start_date: Optional[object] = None,
    ) -> None:
        chart_nw = _serialize(
            self._chart_net_worth_debt(scenario_df, retirement_date, rmd_date), height=380, right_margin=70
        )
        html = self._render(
            "index_single.html",
            run_name=self._run_name(run_dir),
            metrics=metrics,
            start_date=str(start_date) if start_date else None,
            retirement_date=str(retirement_date) if retirement_date else None,
            rmd_date=str(rmd_date) if rmd_date else None,
            ss_start_date=str(ss_start_date) if ss_start_date else None,
            chart_net_worth=chart_nw,
        )
        (run_dir / "index.html").write_text(html, encoding="utf-8")

    def _write_timeseries(
        self,
        run_dir: Path,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        html = self._render(
            "timeseries.html",
            run_name=self._run_name(run_dir),
            chart_net_worth=_serialize(self._chart_net_worth_debt(scenario_df, retirement_date, rmd_date), height=400, right_margin=70),
            chart_income=_serialize(self._chart_income_stack(scenario_df, asset_dfs, retirement_date), height=360),
            chart_fcf=_serialize(self._chart_free_cash_flow(scenario_df, retirement_date), height=360),
            chart_investment=_serialize(self._chart_investment_flow(scenario_df, retirement_date), height=360),
            chart_tax_rate=_serialize(self._chart_effective_tax_rate(scenario_df, retirement_date, rmd_date), height=360),
        )
        (run_dir / "timeseries.html").write_text(html, encoding="utf-8")

    def _write_portfolio(
        self,
        run_dir: Path,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        html = self._render(
            "portfolio.html",
            run_name=self._run_name(run_dir),
            chart_stacked_assets=_serialize(self._chart_stacked_assets(scenario_df, asset_dfs, retirement_date), height=380),
            chart_equity_growth=_serialize(self._chart_equity_growth(asset_dfs, retirement_date), height=380),
            chart_real_estate=_serialize(self._chart_real_estate(asset_dfs, retirement_date), height=380),
            chart_annual_income=_serialize(self._chart_annual_income_bars(scenario_df, asset_dfs, retirement_date), height=380),
        )
        (run_dir / "portfolio.html").write_text(html, encoding="utf-8")

    def _write_tax(
        self,
        run_dir: Path,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> None:
        has_rmd = rmd_date is not None
        html = self._render(
            "tax.html",
            run_name=self._run_name(run_dir),
            chart_taxes_income=_serialize(self._chart_taxes_vs_income(scenario_df, retirement_date, rmd_date), height=380),
            chart_eff_rate=_serialize(self._chart_effective_tax_rate(scenario_df, retirement_date, rmd_date), height=380),
            chart_tax_class=_serialize(self._chart_income_by_tax_class(scenario_df, retirement_date), height=380),
            chart_phase_comparison=_serialize(self._chart_phase_tax_comparison(scenario_df, retirement_date, rmd_date), height=380),
            has_rmd=has_rmd,
            chart_rmd_taxes=_serialize(self._chart_rmd_taxes(scenario_df, rmd_date), height=380) if has_rmd else Markup(""),
            chart_cumulative_taxes=_serialize(self._chart_cumulative_taxes(scenario_df, retirement_date, rmd_date), height=380) if has_rmd else Markup(""),
        )
        (run_dir / "tax.html").write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Parameters page writer
    # ------------------------------------------------------------------

    def _write_parameters(
        self,
        run_dir: Path,
        world_config: WorldConfig,
        asset_config_dicts: list[dict],
        is_mc: bool = False,
    ) -> None:
        data = _build_parameters_data(world_config, asset_config_dicts)
        html = self._render(
            "parameters.html",
            run_name=self._run_name(run_dir),
            is_mc=is_mc,
            **data,
        )
        (run_dir / "parameters.html").write_text(html, encoding="utf-8")

    # Debt analysis page writer + charts
    # ------------------------------------------------------------------

    def _write_debt(
        self,
        run_dir: Path,
        debt_assets: list[dict],
        run_name: str,
    ) -> None:
        colors = _ASSET_COLORS
        html = self._render(
            "debt.html",
            run_name=run_name,
            debt_assets=debt_assets,
            fmt_dollar=_fmt_dollar,
            chart_balance=_serialize(
                self._chart_debt_balance(debt_assets, colors), height=400, right_margin=20
            ),
            chart_monthly_interest=_serialize(
                self._chart_monthly_interest(debt_assets, colors), height=360
            ),
            chart_cumulative=_serialize(
                self._chart_cumulative_cost(debt_assets, colors), height=360
            ),
            chart_total_cost=_serialize(
                self._chart_total_cost_bars(debt_assets, colors), height=280
            ),
        )
        (run_dir / "debt.html").write_text(html, encoding="utf-8")

    def _chart_debt_balance(self, debt_assets: list[dict], colors: list[str]) -> go.Figure:
        """Debt balance timeline — one trace per loan, drops to zero at payoff."""
        fig = go.Figure()
        for i, a in enumerate(debt_assets):
            col = colors[i % len(colors)]
            df = a["df"]
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=df["Debt"].clip(lower=0),
                name=a["name"],
                line=dict(color=col, width=2),
                fill="tozeroy",
                fillcolor=f"rgba({_hex_to_rgb(col)},0.10)",
                hovertemplate="%{y:$,.0f}<extra>" + a["name"] + "</extra>",
            ))
            if a["payoff_date"] is not None:
                _add_vline_date(fig, a["payoff_date"], col, dash="dash",
                                label=f"Payoff: {a['name']}")
        layout = _base_layout("Debt Balance Over Time")
        layout["yaxis"]["tickformat"] = "~s"
        fig.update_layout(**layout)
        return fig

    def _chart_monthly_interest(self, debt_assets: list[dict], colors: list[str]) -> go.Figure:
        """Monthly interest cost for each loan over the simulation."""
        fig = go.Figure()
        for i, a in enumerate(debt_assets):
            col = colors[i % len(colors)]
            df = a["df"]
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=a["monthly_interest"],
                name=a["name"],
                line=dict(color=col, width=2),
                fill="tozeroy",
                fillcolor=f"rgba({_hex_to_rgb(col)},0.10)",
                hovertemplate="%{y:$,.0f}/mo<extra>" + a["name"] + "</extra>",
            ))
        layout = _base_layout("Monthly Interest Cost")
        layout["yaxis"]["tickformat"] = "~s"
        fig.update_layout(**layout)
        return fig

    def _chart_cumulative_cost(self, debt_assets: list[dict], colors: list[str]) -> go.Figure:
        """Cumulative principal paid vs cumulative interest paid, per loan."""
        fig = go.Figure()
        for i, a in enumerate(debt_assets):
            col_p = colors[i % len(colors)]
            col_i = PALETTE["taxes"]
            suffix = f" – {a['name']}" if len(debt_assets) > 1 else ""
            df = a["df"]
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=a["cum_principal"],
                name=f"Principal{suffix}",
                line=dict(color=col_p, width=2),
                hovertemplate="%{y:$,.0f}<extra>Cumulative Principal" + suffix + "</extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["Date"],
                y=a["cum_interest"],
                name=f"Interest{suffix}",
                line=dict(color=col_i, width=2, dash="dash"),
                fill="tozeroy",
                fillcolor="rgba(245,158,11,0.10)",
                hovertemplate="%{y:$,.0f}<extra>Cumulative Interest" + suffix + "</extra>",
            ))
        layout = _base_layout("Cumulative Principal & Interest Paid")
        layout["yaxis"]["tickformat"] = "~s"
        fig.update_layout(**layout)
        return fig

    def _chart_total_cost_bars(self, debt_assets: list[dict], colors: list[str]) -> go.Figure:
        """Grouped bar showing total principal vs total interest per loan."""
        names = [a["name"] for a in debt_assets]
        principals = [a["total_principal"] for a in debt_assets]
        interests = [a["total_interest"] for a in debt_assets]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Principal",
            x=names,
            y=principals,
            marker_color=PALETTE["net_worth"],
            hovertemplate="%{y:$,.0f}<extra>Principal</extra>",
        ))
        fig.add_trace(go.Bar(
            name="Interest",
            x=names,
            y=interests,
            marker_color=PALETTE["taxes"],
            hovertemplate="%{y:$,.0f}<extra>Interest</extra>",
        ))
        layout = _base_layout("Total Cost of Borrowing")
        layout["barmode"] = "group"
        layout["yaxis"]["tickformat"] = "~s"
        fig.update_layout(**layout)
        return fig

    # Monte Carlo page writers
    # ------------------------------------------------------------------

    def _write_mc_index(
        self,
        run_dir: Path,
        mc_results: MonteCarloResults,
        pct_values: dict,
        ruin_prob: float,
        percentiles: list[float],
        retirement_date: Optional[object],
    ) -> None:
        pct_table = [
            {
                "label": f"P{int(p)}",
                "raw": pct_values.get(p, 0),
                "formatted": _fmt_dollar(pct_values.get(p)),
            }
            for p in sorted(percentiles)
        ]
        pct_table_map = {
            f"p{int(p)}": _fmt_dollar(pct_values.get(p)) for p in percentiles
        }
        ruin_color_class = "negative" if ruin_prob > 0.05 else "positive"

        html = self._render(
            "index_mc.html",
            run_name=self._run_name(run_dir),
            n_runs=mc_results.n_runs,
            ruin_prob=ruin_prob,
            ruin_prob_pct=_fmt_pct(ruin_prob),
            ruin_color_class=ruin_color_class,
            pct_table=pct_table,
            pct_table_map=pct_table_map,
            chart_fan=_serialize(self._chart_mc_fan(mc_results, pct_values, retirement_date, percentiles), height=480),
        )
        (run_dir / "index.html").write_text(html, encoding="utf-8")

    def _write_distribution(
        self,
        run_dir: Path,
        mc_results: MonteCarloResults,
        pct_values: dict,
        ruin_prob: float,
        percentiles: list[float],
    ) -> None:
        html = self._render(
            "distribution.html",
            run_name=self._run_name(run_dir),
            n_runs=mc_results.n_runs,
            chart_hist=_serialize(self._chart_terminal_hist(mc_results, pct_values, percentiles), height=380),
            chart_ruin_gauge=_serialize(self._chart_ruin_gauge(ruin_prob), height=380),
            chart_waterfall=_serialize(self._chart_percentile_waterfall(pct_values, percentiles), height=380),
            chart_ruin_timing=_serialize(self._chart_ruin_timing(mc_results), height=380),
        )
        (run_dir / "distribution.html").write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Single-run Plotly chart builders
    # ------------------------------------------------------------------

    def _chart_net_worth_debt(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        if "net_worth" in scenario_df.columns:
            fig.add_trace(go.Scatter(
                x=dates, y=scenario_df["net_worth"],
                name="Net Worth",
                fill="tozeroy",
                fillcolor="rgba(59,130,246,0.12)",
                line=dict(color=PALETTE["net_worth"], width=2),
                hovertemplate="%{y:$,.0f}<extra>Net Worth</extra>",
            ))
        if "debt" in scenario_df.columns:
            fig.add_trace(go.Scatter(
                x=dates, y=scenario_df["debt"],
                name="Debt",
                yaxis="y2",
                line=dict(color=PALETTE["debt"], width=2, dash="dot"),
                hovertemplate="%{y:$,.0f}<extra>Debt</extra>",
            ))
        _apply_retirement_markers(fig, retirement_date, rmd_date, end_date=dates.iloc[-1] if len(dates) else None)
        layout = _base_layout()
        layout["yaxis"]["tickformat"] = "~s"
        layout["yaxis2"] = dict(
            title="Debt",
            overlaying="y",
            side="right",
            showgrid=False,
            tickprefix="$",
            tickformat="~s",
            tickfont=dict(color=PALETTE["debt"]),
            title_font=dict(color=PALETTE["debt"]),
        )
        fig.update_layout(**layout)
        return fig

    def _chart_income_stack(
        self,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        plotted = False
        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Income" not in df.columns or "Date" not in df.columns:
                continue
            merged = pd.merge(
                pd.DataFrame({"Date": dates}), df[["Date", "Income"]], on="Date", how="left"
            ).fillna(0)
            fig.add_trace(go.Scatter(
                x=dates, y=merged["Income"],
                name=name,
                stackgroup="one",
                fillcolor=f"rgba({_hex_to_rgb(_ASSET_COLORS[i % len(_ASSET_COLORS)])},0.6)",
                line=dict(color=_ASSET_COLORS[i % len(_ASSET_COLORS)], width=0.5),
                hovertemplate="%{y:$,.0f}<extra>" + name + "</extra>",
            ))
            plotted = True
        if not plotted and "monthly_taxable_income" in scenario_df.columns:
            fig.add_trace(go.Scatter(
                x=dates, y=scenario_df["monthly_taxable_income"],
                name="Taxable Income",
                fill="tozeroy",
                fillcolor="rgba(5,150,105,0.15)",
                line=dict(color=PALETTE["income"], width=2),
                hovertemplate="%{y:$,.0f}<extra>Taxable Income</extra>",
            ))
        if "retirement_withdrawal" in scenario_df.columns:
            fig.add_trace(go.Scatter(
                x=dates, y=scenario_df["retirement_withdrawal"],
                name="Withdrawal",
                line=dict(color=PALETTE["withdrawal"], width=1.5, dash="dash"),
                hovertemplate="%{y:$,.0f}<extra>Withdrawal</extra>",
            ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_free_cash_flow(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        if "free_cash_flows" in scenario_df.columns:
            fcf = scenario_df["free_cash_flows"]
            colors = [PALETTE["free_cash_flow"] if v >= 0 else PALETTE["expenses"] for v in fcf]
            fig.add_trace(go.Bar(
                x=dates, y=fcf,
                name="Free Cash Flow",
                marker_color=colors,
                hovertemplate="%{y:$,.0f}<extra>FCF</extra>",
            ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout(), barmode="relative")
        return fig

    def _chart_investment_flow(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        if "investment" in scenario_df.columns:
            fig.add_trace(go.Bar(
                x=dates, y=scenario_df["investment"],
                name="Investment",
                marker_color=PALETTE["investment"],
                opacity=0.85,
                hovertemplate="%{y:$,.0f}<extra>Investment</extra>",
            ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_effective_tax_rate(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        if "taxes_paid" in scenario_df.columns and "monthly_taxable_income" in scenario_df.columns:
            income = scenario_df["monthly_taxable_income"].replace(0, np.nan)
            eff_rate = (scenario_df["taxes_paid"] / income * 100).fillna(0)
            fig.add_trace(go.Scatter(
                x=dates, y=eff_rate,
                name="Effective Tax Rate",
                fill="tozeroy",
                fillcolor="rgba(245,158,11,0.15)",
                line=dict(color=PALETTE["taxes"], width=2),
                hovertemplate="%{y:.1f}%<extra>Eff. Tax Rate</extra>",
            ))
        _apply_retirement_markers(fig, retirement_date, rmd_date)
        layout = _base_layout()
        layout["yaxis"]["ticksuffix"] = "%"
        layout["yaxis"]["tickprefix"] = ""
        fig.update_layout(**layout)
        return fig

    def _chart_taxes_vs_income(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        if "monthly_taxable_income" in scenario_df.columns:
            fig.add_trace(go.Scatter(
                x=dates, y=scenario_df["monthly_taxable_income"],
                name="Income",
                line=dict(color=PALETTE["income"], width=2),
                hovertemplate="%{y:$,.0f}<extra>Income</extra>",
            ))
        if "taxes_paid" in scenario_df.columns:
            fig.add_trace(go.Scatter(
                x=dates, y=scenario_df["taxes_paid"],
                name="Taxes",
                fill="tozeroy",
                fillcolor="rgba(245,158,11,0.2)",
                line=dict(color=PALETTE["taxes"], width=2),
                hovertemplate="%{y:$,.0f}<extra>Taxes</extra>",
            ))
        _apply_retirement_markers(fig, retirement_date, rmd_date)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_income_by_tax_class(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        tax_classes = {
            "tax_ordinary_income": ("Ordinary Income", "#1e3a5f"),
            "tax_capital_gains": ("Capital Gains", "#3b82f6"),
            "tax_social_security": ("Social Security", "#6ee7b7"),
        }
        for col, (label, color) in tax_classes.items():
            if col in scenario_df.columns:
                fig.add_trace(go.Scatter(
                    x=dates, y=scenario_df[col],
                    name=label,
                    stackgroup="one",
                    fillcolor=f"rgba({_hex_to_rgb(color)},0.6)",
                    line=dict(color=color, width=0.5),
                    hovertemplate="%{y:$,.0f}<extra>" + label + "</extra>",
                ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_phase_tax_comparison(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> go.Figure:
        if "taxes_paid" not in scenario_df.columns:
            return go.Figure()

        phases: list[tuple[str, pd.DataFrame, str]] = []
        ret_mask = scenario_df["retirement_withdrawal"] > 0 if "retirement_withdrawal" in scenario_df.columns else pd.Series(False, index=scenario_df.index)
        rmd_mask = scenario_df["age"] >= 73 if "age" in scenario_df.columns else pd.Series(False, index=scenario_df.index)

        phases.append(("Pre-Retirement", scenario_df[~ret_mask], "#1e3a5f"))
        if ret_mask.any():
            phases.append(("Post-Retirement", scenario_df[ret_mask & ~rmd_mask], "#3b82f6"))
        if rmd_mask.any():
            phases.append(("RMD Period", scenario_df[rmd_mask], "#dc2626"))

        fig = go.Figure()
        for label, sub_df, color in phases:
            if sub_df.empty:
                continue
            avg = sub_df["taxes_paid"].mean()
            fig.add_trace(go.Bar(
                name=label,
                x=[label],
                y=[avg],
                marker_color=color,
                text=[_fmt_dollar(avg)],
                textposition="outside",
                hovertemplate=f"{label}: %{{y:$,.0f}}/mo<extra></extra>",
            ))
        layout = _base_layout()
        layout["hovermode"] = "closest"
        layout["xaxis"]["gridcolor"] = "rgba(0,0,0,0)"
        fig.update_layout(**layout)
        return fig

    def _chart_rmd_taxes(
        self,
        scenario_df: pd.DataFrame,
        rmd_date: Optional[object],
    ) -> go.Figure:
        if rmd_date is None or "taxes_paid" not in scenario_df.columns or "age" not in scenario_df.columns:
            return go.Figure()
        rmd_df = scenario_df[scenario_df["age"] >= 73]
        if rmd_df.empty:
            return go.Figure()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=rmd_df["Date"], y=rmd_df["taxes_paid"],
            name="Taxes (RMD Period)",
            fill="tozeroy",
            fillcolor="rgba(220,38,38,0.18)",
            line=dict(color=PALETTE["rmd_line"], width=2),
            hovertemplate="%{y:$,.0f}<extra>Taxes</extra>",
        ))
        cumulative = rmd_df["taxes_paid"].sum()
        fig.add_annotation(
            text=f"Cumulative: {_fmt_dollar(cumulative)}",
            xref="paper", yref="paper",
            x=0.02, y=0.95,
            showarrow=False,
            font=dict(size=12, color="#991b1b"),
            bgcolor="rgba(254,226,226,0.8)",
            bordercolor="#dc2626",
            borderwidth=1,
            borderpad=4,
        )
        fig.update_layout(**_base_layout())
        return fig

    def _chart_cumulative_taxes(
        self,
        scenario_df: pd.DataFrame,
        retirement_date: Optional[object],
        rmd_date: Optional[object],
    ) -> go.Figure:
        if "taxes_paid" not in scenario_df.columns:
            return go.Figure()
        ret_mask = scenario_df["retirement_withdrawal"] > 0 if "retirement_withdrawal" in scenario_df.columns else pd.Series(False, index=scenario_df.index)
        rmd_mask = scenario_df["age"] >= 73 if "age" in scenario_df.columns else pd.Series(False, index=scenario_df.index)

        fig = go.Figure()
        phases = [
            ("Pre-Retirement", ~ret_mask, "#1e3a5f"),
            ("Post-Retirement", ret_mask & ~rmd_mask, "#3b82f6"),
            ("RMD Period", rmd_mask, "#dc2626"),
        ]
        for label, mask, color in phases:
            sub = scenario_df[mask]
            if sub.empty:
                continue
            cumsum = sub["taxes_paid"].cumsum().reset_index(drop=True)
            fig.add_trace(go.Scatter(
                x=sub["Date"].values,
                y=cumsum.values,
                name=label,
                line=dict(color=color, width=2),
                hovertemplate="%{y:$,.0f}<extra>" + label + "</extra>",
            ))
        fig.update_layout(**_base_layout())
        return fig

    # ------------------------------------------------------------------
    # Portfolio chart builders
    # ------------------------------------------------------------------

    def _chart_stacked_assets(
        self,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        fig = go.Figure()
        stacks: list[np.ndarray] = []
        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Value" not in df.columns or "Date" not in df.columns:
                continue
            merged = pd.merge(
                pd.DataFrame({"Date": dates}), df[["Date", "Value"]], on="Date", how="left"
            ).fillna(0)
            color = _ASSET_COLORS[i % len(_ASSET_COLORS)]
            fig.add_trace(go.Scatter(
                x=dates, y=merged["Value"],
                name=name,
                stackgroup="one",
                fillcolor=f"rgba({_hex_to_rgb(color)},0.55)",
                line=dict(color=color, width=0.5),
                hovertemplate="%{y:$,.0f}<extra>" + name + "</extra>",
            ))
            stacks.append(merged["Value"].values)
        if stacks:
            total = np.sum(stacks, axis=0)
            fig.add_trace(go.Scatter(
                x=dates, y=total,
                name="Total",
                line=dict(color="black", width=1.5, dash="dot"),
                hovertemplate="%{y:$,.0f}<extra>Total</extra>",
            ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_equity_growth(
        self,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
    ) -> go.Figure:
        fig = go.Figure()
        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Value" not in df.columns or "Date" not in df.columns:
                continue
            fig.add_trace(go.Scatter(
                x=df["Date"], y=df["Value"],
                name=name,
                line=dict(color=_ASSET_COLORS[i % len(_ASSET_COLORS)], width=2),
                hovertemplate="%{y:$,.0f}<extra>" + name + "</extra>",
            ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_real_estate(
        self,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
    ) -> go.Figure:
        fig = go.Figure()
        for name, df in asset_dfs.items():
            if df is None or df.empty or "Value" not in df.columns or "Date" not in df.columns:
                continue
            fig.add_trace(go.Scatter(
                x=df["Date"], y=df["Value"],
                name=f"{name} Value",
                line=dict(color=PALETTE["real_estate"], width=2),
                hovertemplate="%{y:$,.0f}<extra>Value</extra>",
            ))
            if "Debt" in df.columns:
                fig.add_trace(go.Scatter(
                    x=df["Date"], y=df["Debt"],
                    name=f"{name} Debt",
                    fill="tozeroy",
                    fillcolor="rgba(220,38,38,0.12)",
                    line=dict(color=PALETTE["debt"], width=1.5, dash="dot"),
                    hovertemplate="%{y:$,.0f}<extra>Debt</extra>",
                ))
                net_equity = df["Value"] - df["Debt"]
                fig.add_trace(go.Scatter(
                    x=df["Date"], y=net_equity,
                    name=f"{name} Equity",
                    line=dict(color=PALETTE["income"], width=1.5, dash="dash"),
                    hovertemplate="%{y:$,.0f}<extra>Equity</extra>",
                ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout())
        return fig

    def _chart_annual_income_bars(
        self,
        scenario_df: pd.DataFrame,
        asset_dfs: dict[str, Optional[pd.DataFrame]],
        retirement_date: Optional[object],
    ) -> go.Figure:
        dates = scenario_df.get("Date", pd.Series(dtype=object))
        sampled_dates = dates.iloc[::12]
        fig = go.Figure()
        for i, (name, df) in enumerate(asset_dfs.items()):
            if df is None or df.empty or "Income" not in df.columns or "Date" not in df.columns:
                continue
            merged = pd.merge(
                pd.DataFrame({"Date": sampled_dates}), df[["Date", "Income"]], on="Date", how="left"
            ).fillna(0)
            # Annualise: multiply monthly income by 12
            fig.add_trace(go.Bar(
                x=merged["Date"], y=merged["Income"] * 12,
                name=name,
                marker_color=_ASSET_COLORS[i % len(_ASSET_COLORS)],
                hovertemplate="%{y:$,.0f}/yr<extra>" + name + "</extra>",
            ))
        if retirement_date is not None:
            _add_vline_date(fig, retirement_date, PALETTE["retirement_line"], width=1.2)
        fig.update_layout(**_base_layout(), barmode="stack")
        return fig

    # ------------------------------------------------------------------
    # Monte Carlo chart builders
    # ------------------------------------------------------------------

    def _chart_mc_fan(
        self,
        mc_results: MonteCarloResults,
        pct_values: dict,
        retirement_date: Optional[object],
        percentiles: list[float],
    ) -> go.Figure:
        fig = go.Figure()

        if mc_results.has_trajectories():
            trajectories = mc_results.trajectory_array()
            n_traj = len(trajectories)
            sample_size = min(200, n_traj)
            sampled = random.sample(trajectories, sample_size)
            x_idx = list(range(len(sampled[0])))

            for traj in sampled:
                fig.add_trace(go.Scatter(
                    x=x_idx, y=traj,
                    mode="lines",
                    line=dict(color="rgba(150,150,150,0.04)", width=1),
                    showlegend=False,
                    hoverinfo="skip",
                ))

            all_traj = np.array(trajectories)
            p_low = [10, 25]
            p_high = [90, 75]
            band_colors = ["rgba(147,197,253,0.25)", "rgba(59,130,246,0.35)"]
            band_names = ["P10–P90", "P25–P75"]

            for pl, ph, bcolor, bname in zip(p_low, p_high, band_colors, band_names):
                p_lo_vals = np.percentile(all_traj, pl, axis=0)
                p_hi_vals = np.percentile(all_traj, ph, axis=0)
                fig.add_trace(go.Scatter(
                    x=x_idx + x_idx[::-1],
                    y=list(p_hi_vals) + list(p_lo_vals[::-1]),
                    fill="toself",
                    fillcolor=bcolor,
                    line=dict(color="rgba(0,0,0,0)"),
                    name=bname,
                    hoverinfo="skip",
                ))

            p50_vals = np.percentile(all_traj, 50, axis=0)
            fig.add_trace(go.Scatter(
                x=x_idx, y=p50_vals,
                name="Median (P50)",
                line=dict(color=PALETTE["median_line"], width=2.5),
                hovertemplate="Period %{x}: %{y:$,.0f}<extra>Median</extra>",
            ))
        else:
            terminal_values = sorted(r.terminal_net_worth for r in mc_results.results)
            fig.add_trace(go.Histogram(
                x=terminal_values,
                name="Terminal Net Worth",
                marker_color=PALETTE["net_worth"],
                nbinsx=40,
            ))
            fig.update_layout(yaxis_title="Count", yaxis=dict(tickprefix=""))

        fig.add_hline(y=0, line_color=PALETTE["debt"], line_width=1.5, line_dash="dot")
        layout = _base_layout()
        layout["yaxis"]["tickprefix"] = "$"
        layout["xaxis"]["title"] = "Simulation Period"
        fig.update_layout(**layout)
        return fig

    def _chart_terminal_hist(
        self,
        mc_results: MonteCarloResults,
        pct_values: dict,
        percentiles: list[float],
    ) -> go.Figure:
        terminal = [r.terminal_net_worth for r in mc_results.results]
        pos = [v for v in terminal if v >= 0]
        neg = [v for v in terminal if v < 0]

        fig = go.Figure()
        if pos:
            fig.add_trace(go.Histogram(
                x=pos, name="Positive", marker_color=PALETTE["net_worth"], nbinsx=30, opacity=0.8,
            ))
        if neg:
            fig.add_trace(go.Histogram(
                x=neg, name="Ruin", marker_color=PALETTE["debt"], nbinsx=10, opacity=0.8,
            ))
        for p in percentiles:
            val = pct_values.get(p)
            if val is not None:
                fig.add_vline(
                    x=val,
                    line_color="#64748b",
                    line_width=1,
                    line_dash="dot",
                    annotation_text=f"P{int(p)}",
                    annotation_font_size=9,
                )
        layout = _base_layout()
        layout["yaxis"]["tickprefix"] = ""
        layout["yaxis"]["title"] = "Count"
        layout["barmode"] = "overlay"
        fig.update_layout(**layout)
        return fig

    def _chart_ruin_gauge(self, ruin_prob: float) -> go.Figure:
        survival = 1.0 - ruin_prob
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[ruin_prob * 100],
            y=[""],
            orientation="h",
            name="Ruin",
            marker_color=PALETTE["debt"],
            text=[f"Ruin {ruin_prob:.1%}"],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"Ruin: {ruin_prob:.1%}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=[survival * 100],
            y=[""],
            orientation="h",
            name="Survival",
            marker_color=PALETTE["income"],
            text=[f"Survival {survival:.1%}"],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"Survival: {survival:.1%}<extra></extra>",
        ))
        layout = _base_layout()
        layout["barmode"] = "stack"
        layout["xaxis"]["ticksuffix"] = "%"
        layout["xaxis"]["tickprefix"] = ""
        layout["xaxis"]["range"] = [0, 100]
        layout["yaxis"]["tickprefix"] = ""
        layout["yaxis"]["showticklabels"] = False
        layout["hovermode"] = "closest"
        fig.update_layout(**layout, height=220)
        return fig

    def _chart_percentile_waterfall(
        self,
        pct_values: dict,
        percentiles: list[float],
    ) -> go.Figure:
        labels = [f"P{int(p)}" for p in sorted(percentiles)]
        values = [pct_values.get(p, 0) for p in sorted(percentiles)]
        colors = [PALETTE["income"] if v >= 0 else PALETTE["debt"] for v in values]
        text = [_fmt_dollar(v) for v in values]

        fig = go.Figure(go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=text,
            textposition="outside",
            hovertemplate="%{y}: %{x:$,.0f}<extra></extra>",
        ))
        layout = _base_layout()
        layout["xaxis"]["tickprefix"] = "$"
        layout["yaxis"]["tickprefix"] = ""
        layout["hovermode"] = "closest"
        fig.update_layout(**layout)
        return fig

    def _chart_ruin_timing(self, mc_results: MonteCarloResults) -> go.Figure:
        ruin_periods = [r.ruin_period for r in mc_results.results if r.ruin_period is not None]
        fig = go.Figure()
        if ruin_periods:
            fig.add_trace(go.Histogram(
                x=ruin_periods,
                name="Ruin Period",
                marker_color=PALETTE["debt"],
                nbinsx=20,
            ))
        else:
            fig.add_annotation(
                text="No ruin events in this simulation set",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color=PALETTE["income"]),
            )
        layout = _base_layout()
        layout["xaxis"]["title"] = "Period"
        layout["xaxis"]["tickprefix"] = ""
        layout["yaxis"]["tickprefix"] = ""
        layout["yaxis"]["title"] = "Count"
        fig.update_layout(**layout)
        return fig


# ---------------------------------------------------------------------------
# Colour utility
# ---------------------------------------------------------------------------


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #rrggbb to 'r,g,b' for rgba() strings."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
