---
title: Simulation Engine
tags: [architecture, simulation, core]
sources: [scenarios-py, assets-py]
updated: 2026-06-14
---

# Simulation Engine

## Overview

`RetirementFinancialModel` in `models/scenarios.py` is the central orchestrator. It loads world config and assets, builds a monthly timeline, then steps through it period by period.

## Initialisation Sequence

1. Load `configuration/config.json` into `self.__dict__` (flat dict merge).
2. Build typed `WorldConfig` via `WorldConfig.from_json()` for downstream consumers.
3. Instantiate `TaxCalculator` with `world_config.tax_classes`.
4. Parse `birth_date`, `spouse_birth_date`, `start_date`, `end_date` as `date` objects.
5. Compute `retirement_date = birth_date + timedelta(days=retirement_age * 365.25)`.[^1]

## Setup (`setup()`)

Called separately from `__init__` to allow deferred asset loading:

1. `create_assets(config_path)` — instantiates all assets from JSON files in `configuration/assets/`.
2. For each asset: `set_scenario_dates()` resolves placeholder strings (`"first_date"`, `"retirement"`, `"end_date"`) to actual `date` objects.
3. `asset.pre_calculate(start_date)` — called once per asset before simulation; used by `REAsset` to compute the mortgage balance at the simulation start date from amortization math rather than a hardcoded figure.
4. `create_datetime_sequence(start_date, end_date)` builds the monthly `self.timeline`.

## Main Loop (`run_model()`)

Per-period columns captured in `mdata`:[^2]

| Column | Description |
|---|---|
| `Period` | Zero-based period index |
| `Date` | Calendar date |
| `age` | Owner age in fractional years |
| `retirement_withdrawal` | 401k portfolio draw this period |
| `rmd_required` | IRS-required monthly RMD (0 before `rmd_age`) |
| `roth_withdrawal` | Roth IRA draw this period (tax-free) |
| `net_worth` | Total asset value minus debt |
| `debt` | Total outstanding debt |
| `monthly_taxable_income` | Sum of asset taxable income + 401k withdrawal |
| `monthly_operational_expenses` | Sum of all asset operating expenses |
| `taxes_paid` | Monthly tax liability |
| `free_cash_flows` | Income + cash flows - taxes |
| `investment` | Amount invested into 401k + Roth IRA this period |

### Pre-retirement (age < `retirement_age`)

- Free cash flow × `savings_rate` is invested evenly across `"401k stock"` (60%) and `"401k bond"` (40%) assets.[^3]
- If `roth_savings_rate > 0`, an additional fraction of free cash flow is invested into `"roth ira stock"` and `"roth ira bond"` assets.

### Post-retirement (age ≥ `retirement_age`)

- **401k withdrawal**: `flat_withdrawal = withdrawal_rate × retirement_portfolio_value() / 12`.
  - If `age >= rmd_age` (default 73): `rmd_required = calculate_rmd_withdrawal(age, portfolio)`.
  - `retirement_withdraw = max(flat_withdrawal, rmd_required)` — never less than IRS minimum.[^4]
  - Added to `monthly_taxable_income` and taxed as ordinary income.
- **Roth withdrawal**: `withdrawal_rate × roth_portfolio_value() / 12` — drawn from `"roth ira"` assets, **not** added to taxable income (tax-free).

## Key Methods

| Method | Purpose |
|---|---|
| `retirement_portfolio_value(name_match)` | Sum net value of 401k assets (default: `"401k"` match) |
| `roth_portfolio_value(name_match)` | Sum net value of Roth IRA assets (default: `"roth ira"` match) |
| `calculate_rmd_withdrawal(age, portfolio)` | IRS monthly RMD from Uniform Lifetime Table |
| `allocate_investment_evenly(amount, name_match)` | Distribute amount across matching assets equally |
| `net_worth_debt()` | Return `(total_net_worth, total_debt)` |
| `calculate_operating_expenses()` | Sum `operating_expense()` across all assets |
| `calculate_monthly_taxes(withdrawal)` | Delegate to `TaxCalculator` |
| `calculate_free_cash_flows()` | Sum `cash_flow()` across all assets |

## Output

`run_model()` returns `(mdata, mheader, adata, aheader)`:
- `mdata` — list of per-period scenario rows
- `mheader` — column names for `mdata`
- `adata` — dict mapping asset name → list of snapshot rows
- `aheader` — column names for asset snapshots

Both can be converted to DataFrames via `get_scenario_dataframe()` / `get_asset_dataframe()`.

## Known Gaps

- **`inflation_rate` stored but not applied.** `WorldConfig` includes `inflation_rate` but the main loop does not visibly apply it to expenses or thresholds.
- **Contribution limits not enforced.** `savings_rate` and `roth_savings_rate` invest a flat fraction of free cash flow; IRS annual limits ($24,500 for 401k, $7,500 for Roth IRA) are not capped.
- **RMD balance approximation.** `calculate_rmd_withdrawal()` uses the current period balance rather than the prior December 31 balance as IRS rules technically require. See [[required-minimum-distributions]].

## Related

- [[asset-models]] — what each asset's `period_update()` does
- [[tax-model]] — how `calculate_monthly_taxes()` works
- [[monte-carlo]] — how the engine is run N times with fresh state
- [[simulation-flow]] — end-to-end pseudocode for the full loop
- [[required-minimum-distributions]] — RMD schedule (implemented)
- [[roth-ira]] — Roth IRA model (implemented)

---

[^1]: `models/scenarios.py` line ~58 — `self.retirement_date = self.birth_date + timedelta(days=self.retirement_age * DAYS_IN_YEAR)`
[^2]: `models/scenarios.py` `run_model()` — `mheader` list defined at top of method
[^3]: `models/scenarios.py` `run_model()` — `allocate_investment_evenly(investment * self.stock_allocation, "401k stock")`
[^4]: `models/scenarios.py` `run_model()` — `monthly_taxable_income = self.calculate_monthly_taxable_income() + retirement_withdraw`
