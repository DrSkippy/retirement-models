"""Generate a Markdown report of all simulation parameters and initial conditions."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

FMT = "%Y-%m-%d"
DAYS_IN_YEAR = 365.25

# Placeholder strings that appear in asset JSON date fields
DATE_PLACEHOLDERS = {
    "first_date": "simulation start",
    "end_date": "simulation end",
    "retirement": "retirement date",
    "retirement_date": "retirement date",
    "retirement_age": "retirement age",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pct(v: float, decimals: int = 2) -> str:
    return f"{v * 100:.{decimals}f}%"


def _dollars(v: float) -> str:
    return f"${v:,.0f}"


def _resolve_date(value: str | None, dates: dict[str, date]) -> str:
    """Return a human-readable date string, resolving placeholders when possible."""
    if value is None:
        return "—"
    resolved = dates.get(value)
    if resolved is not None:
        label = DATE_PLACEHOLDERS.get(value, value)
        return f"{resolved.strftime(FMT)}  *(= {label})*"
    if value in DATE_PLACEHOLDERS:
        return f"*{DATE_PLACEHOLDERS[value]}*"
    return value


def _age_at(birth: date, target: date) -> float:
    return (target - birth).days / DAYS_IN_YEAR


def _load_json(path: str) -> dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def _load_assets(assets_dir: str) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for fname in sorted(os.listdir(assets_dir)):
        if fname.endswith(".json"):
            data = _load_json(os.path.join(assets_dir, fname))
            data["_source_file"] = fname
            assets.append(data)
    return assets


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _section_world(cfg: dict[str, Any], today: date) -> list[str]:
    lines: list[str] = ["## World Parameters\n"]

    birth = datetime.strptime(cfg["birth_date"], FMT).date()
    spouse_birth = datetime.strptime(cfg["spouse_birth_date"], FMT).date()
    start = datetime.strptime(cfg["start_date"], FMT).date()
    end = datetime.strptime(cfg["end_date"], FMT).date()
    ret_age: int = cfg["retirement_age"]
    ret_date = birth + timedelta(days=ret_age * DAYS_IN_YEAR)
    horizon_years = (end - start).days / DAYS_IN_YEAR

    lines += [
        "### People\n",
        "| | Date of Birth | Age at Simulation Start | Age at Simulation End |",
        "|---|---|---|---|",
        f"| **Primary** | {birth.strftime(FMT)} | {_age_at(birth, start):.1f} | {_age_at(birth, end):.1f} |",
        f"| **Spouse**  | {spouse_birth.strftime(FMT)} | {_age_at(spouse_birth, start):.1f} | {_age_at(spouse_birth, end):.1f} |",
        "",
        "### Simulation Window\n",
        "| Parameter | Value |",
        "|---|---|",
        f"| Start date | {start.strftime(FMT)} |",
        f"| End date   | {end.strftime(FMT)} |",
        f"| Horizon    | {horizon_years:.1f} years |",
        f"| Retirement age | {ret_age} |",
        f"| Retirement date | {ret_date.strftime(FMT)} *(age {_age_at(birth, ret_date):.1f})* |",
        f"| Years to retirement (from start) | {_age_at(birth, ret_date) - _age_at(birth, start):.1f} |",
        "",
        "### Rates\n",
        "| Parameter | Value |",
        "|---|---|",
        f"| Inflation rate    | {_pct(cfg['inflation_rate'])} |",
        f"| Savings rate      | {_pct(cfg['savings_rate'])} |",
        f"| Withdrawal rate   | {_pct(cfg['withdrawal_rate'])} |",
        "",
        "### Portfolio Allocation\n",
        "| Asset Class | Allocation |",
        "|---|---|",
        f"| Stocks | {_pct(cfg['stock_allocation'])} |",
        f"| Bonds  | {_pct(cfg['bond_allocation'])} |",
        "",
        "### Tax Rates\n",
        "| Income Class | Rate |",
        "|---|---|",
        f"| Ordinary income    | {_pct(cfg['tax_classes']['income'])} |",
        f"| Capital gains      | {_pct(cfg['tax_classes']['capital_gain'])} |",
        f"| Social Security    | {_pct(cfg['tax_classes']['social_security'])} |",
        "",
    ]
    return lines


def _section_summary(assets: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    birth = datetime.strptime(cfg["birth_date"], FMT).date()
    start = datetime.strptime(cfg["start_date"], FMT).date()
    end = datetime.strptime(cfg["end_date"], FMT).date()
    ret_age: int = cfg["retirement_age"]
    ret_date = birth + timedelta(days=ret_age * DAYS_IN_YEAR)

    date_map: dict[str, date] = {
        "first_date": start,
        "end_date": end,
        "retirement": ret_date,
        "retirement_date": ret_date,
    }

    lines: list[str] = ["## Asset Summary\n"]
    lines += [
        "| Asset | Type | Tax Class | Initial Value | Initial Debt | Active From | Active To |",
        "|---|---|---|---|---|---|---|",
    ]

    total_value = 0.0
    total_debt = 0.0

    for a in assets:
        atype = a.get("type", "?")
        iv = a.get("initial_value", 0.0)
        debt = a.get("initial_debt", 0.0)
        total_value += iv
        total_debt += debt
        sd = _resolve_date(a.get("start_date"), date_map)
        ed = _resolve_date(a.get("end_date"), date_map)
        lines.append(
            f"| {a['name']} | {atype} | {a.get('tax_class', '—')} "
            f"| {_dollars(iv)} | {_dollars(debt)} | {sd} | {ed} |"
        )

    lines += [
        f"| **Total** | | | **{_dollars(total_value)}** | **{_dollars(total_debt)}** | | |",
        "",
        f"> **Net initial value (value − debt):** {_dollars(total_value - total_debt)}",
        "",
    ]
    return lines


def _section_equity(assets: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    equity_assets = [a for a in assets if a.get("type") == "Equity"]
    if not equity_assets:
        return []

    birth = datetime.strptime(cfg["birth_date"], FMT).date()
    start = datetime.strptime(cfg["start_date"], FMT).date()
    end = datetime.strptime(cfg["end_date"], FMT).date()
    ret_date = birth + timedelta(days=cfg["retirement_age"] * DAYS_IN_YEAR)
    date_map: dict[str, date] = {
        "first_date": start,
        "end_date": end,
        "retirement": ret_date,
        "retirement_date": ret_date,
    }

    lines: list[str] = ["## Equity Assets\n"]
    for a in equity_assets:
        vol = a.get("appreciation_rate_volatility", 0.0)
        vol_str = f" ± {_pct(vol)}" if vol else " (deterministic)"
        sampled = a.get("sampled_monthly_sp500_returns")
        return_source = f"Historical S&P 500 samples (`{sampled}`)" if sampled else "Normal distribution"

        lines += [
            f"### {a['name']}\n",
            f"*{a.get('description', '')}*\n",
            "| Parameter | Value |",
            "|---|---|",
            f"| Source file        | `{a['_source_file']}` |",
            f"| Tax class          | {a.get('tax_class', '—')} |",
            f"| Initial value      | {_dollars(a.get('initial_value', 0))} |",
            f"| Expense rate (annual) | {_pct(a.get('initial_expense_rate', 0), 3)} |",
            f"| Appreciation rate  | {_pct(a.get('appreciation_rate', 0))}{vol_str} |",
            f"| Dividend rate      | {_pct(a.get('dividend_rate', 0), 3)} |",
            f"| Return source      | {return_source} |",
            f"| Active from        | {_resolve_date(a.get('start_date'), date_map)} |",
            f"| Active to          | {_resolve_date(a.get('end_date'), date_map)} |",
            "",
        ]
    return lines


def _section_real_estate(assets: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    re_assets = [a for a in assets if a.get("type") == "RealEstate"]
    if not re_assets:
        return []

    birth = datetime.strptime(cfg["birth_date"], FMT).date()
    start = datetime.strptime(cfg["start_date"], FMT).date()
    end = datetime.strptime(cfg["end_date"], FMT).date()
    ret_date = birth + timedelta(days=cfg["retirement_age"] * DAYS_IN_YEAR)
    date_map: dict[str, date] = {
        "first_date": start,
        "end_date": end,
        "retirement": ret_date,
        "retirement_date": ret_date,
    }

    lines: list[str] = ["## Real Estate Assets\n"]
    for a in re_assets:
        iv = a.get("initial_value", 0.0)
        debt = a.get("initial_debt", 0.0)
        equity = iv - debt
        rental = a.get("monthly_rental_income", 0.0)
        mgmt = a.get("management_fee_rate", 0.0)
        rental_exp = a.get("rental_expense_rate", 0.0)

        lines += [
            f"### {a['name']}\n",
            f"*{a.get('description', '')}*\n",
            "| Parameter | Value |",
            "|---|---|",
            f"| Source file              | `{a['_source_file']}` |",
            f"| Tax class                | {a.get('tax_class', '—')} |",
            f"| Initial value            | {_dollars(iv)} |",
            f"| Initial debt             | {_dollars(debt)} |",
            f"| Initial equity           | {_dollars(equity)} |",
            f"| Appreciation rate        | {_pct(a.get('appreciation_rate', 0))} |",
            f"| Property tax rate        | {_pct(a.get('property_tax_rate', 0), 4)} |",
            f"| Insurance (annual)       | {_dollars(a.get('insurance_cost', 0))} |",
            f"| Mortgage rate            | {_pct(a.get('interest_rate', 0), 4)} |",
            f"| Monthly payment          | {_dollars(a.get('payment', 0))} |",
            f"| Monthly rental income    | {_dollars(rental)} |",
            f"| Management fee rate      | {_pct(mgmt)} |",
            f"| Rental expense rate      | {_pct(rental_exp)} |",
            f"| Active from              | {_resolve_date(a.get('start_date'), date_map)} |",
            f"| Active to                | {_resolve_date(a.get('end_date'), date_map)} |",
            "",
        ]
    return lines


def _section_salary(assets: list[dict[str, Any]], cfg: dict[str, Any]) -> list[str]:
    sal_assets = [a for a in assets if a.get("type") == "Salary"]
    if not sal_assets:
        return []

    birth = datetime.strptime(cfg["birth_date"], FMT).date()
    start = datetime.strptime(cfg["start_date"], FMT).date()
    end = datetime.strptime(cfg["end_date"], FMT).date()
    ret_date = birth + timedelta(days=cfg["retirement_age"] * DAYS_IN_YEAR)
    date_map: dict[str, date] = {
        "first_date": start,
        "end_date": end,
        "retirement": ret_date,
        "retirement_date": ret_date,
    }

    lines: list[str] = ["## Salary / Benefit Assets\n"]
    for a in sal_assets:
        lines += [
            f"### {a['name']}\n",
            f"*{a.get('description', '')}*\n",
            "| Parameter | Value |",
            "|---|---|",
            f"| Source file   | `{a['_source_file']}` |",
            f"| Tax class     | {a.get('tax_class', '—')} |",
            f"| COLA          | {_pct(a.get('cola', 0))} |",
            f"| Active from   | {_resolve_date(a.get('start_date'), date_map)} |",
            f"| Active to     | {_resolve_date(a.get('end_date'), date_map)} |",
        ]

        salary = a.get("salary")
        if salary is not None:
            lines.append(f"| Annual salary | {_dollars(salary)} |")

        benefit_table = a.get("retirement_age_based_benefit")
        if benefit_table:
            lines += [
                "",
                "**Age-based benefit schedule:**\n",
                "| Claiming Age | Monthly Benefit |",
                "|---|---|",
            ]
            for age_key in sorted(benefit_table, key=lambda x: int(x)):
                lines.append(f"| {age_key} | {_dollars(benefit_table[age_key])} |")

        lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_report(config_path: str, assets_dir: str) -> str:
    cfg = _load_json(config_path)
    assets = _load_assets(assets_dir)
    today = date.today()

    header = [
        "# Retirement Model — Configuration Report\n",
        f"*Generated: {today.strftime(FMT)}*  ",
        f"*Config: `{config_path}`*  ",
        f"*Assets: `{assets_dir}`*\n",
        "---\n",
    ]

    sections = (
        header
        + _section_world(cfg, today)
        + _section_summary(assets, cfg)
        + _section_equity(assets, cfg)
        + _section_real_estate(assets, cfg)
        + _section_salary(assets, cfg)
    )
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown configuration report for the retirement model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        default="./configuration/config.json",
        metavar="FILE",
        help="Path to the world config JSON file",
    )
    parser.add_argument(
        "--assets",
        default="./configuration/assets",
        metavar="DIR",
        help="Directory containing asset JSON files",
    )
    parser.add_argument(
        "--output",
        default="-",
        metavar="FILE",
        help="Output file path (use '-' for stdout)",
    )
    args = parser.parse_args()

    report = build_report(args.config, args.assets)

    if args.output == "-":
        sys.stdout.write(report + "\n")
    else:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report + "\n")
        print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
