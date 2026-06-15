---
title: Asset Models
tags: [models, assets, simulation]
sources: [assets-py, configuration-assets]
updated: 2026-06-14
---

# Asset Models

## Class Hierarchy

```
Asset (base)
├── REAsset        — real estate with mortgage amortization
├── Equity         — stocks, bonds, brokerage accounts
└── SalaryIncome   — employment income or Social Security
```

All classes live in `models/assets.py`. Assets are instantiated by `create_assets()` in `models/utils.py`, which reads JSON files from `configuration/assets/` and dispatches by the `"type"` field.

## Base Class: `Asset`

State is held in a separate `AssetState` dataclass (not on `self` directly) to prevent JSON-loaded keys from accidentally overwriting simulation state.[^1]

**State fields** (all delegate to `self._state`):

| Field | Description |
|---|---|
| `value` | Current market value |
| `debt` | Outstanding debt against the asset |
| `income` | Monthly income this period |
| `expenses` | Monthly expenses this period |
| `growth_rate` | Monthly appreciation rate |
| `growth_rate_volatility` | Std dev of monthly growth rate |
| `expense_rate` | Fractional expense rate on value |

**Per-period lifecycle:**

`period_update(period, period_date)` is called each month:
- If `period_date < start_date` → return zeros (asset not yet active).
- If `start_date ≤ period_date < end_date` → call `_setup()` once on first active period, then `_period_update_finalize_metrics()`, then compute all metric functions.
- If `period_date ≥ end_date` → call `initialize_asset_metrics()` (reset to zeros).

**Metric functions** registered in `metrics_functions` dict:

| Key | Method | Description |
|---|---|---|
| `appreciation` | `_asset_appreciation()` | Grow value by `growth_rate` (± volatility) |
| `cash_flow` | `cash_flow()` | `income - operating_expense()` |
| `operating_expense` | `operating_expense()` | `value * expense_rate + expenses` |
| `taxable_income` | `taxable_income()` | `income` (base; overridden by Equity) |

**Appreciation sampling:**

If `growth_rate_volatility == 0.0`, appreciation is deterministic. Otherwise, `np.random.normal(growth_rate, growth_rate_volatility)` is sampled.[^2]

## REAsset (Real Estate)

Adds mortgage amortization and rental-income-based expenses.

**`_setup()`** initialises:
- `growth_rate = appreciation_rate / 12`
- `income_based_expenses_rate = management_fee_rate + rental_expense_rate`
- `monthly_interest_rate = interest_rate / 12`
- Reads optional `extra_principal_payment` (default 0)

**`_period_update_finalize_metrics()`** per period:
1. Compute interest = `debt × monthly_interest_rate`.
2. `regular_payment = min(payment, debt + interest)`.
3. `principal_payment = regular_payment - interest`; reduce debt.
4. Apply optional `extra_principal_payment` (also reduces debt).
5. Expenses = `insurance_cost/12 + income_based_expenses_rate × income + regular_payment + extra`.[^3]

**`pre_calculate(start_date)`** — computes the amortization balance at `start_date` using the closed-form formula if `loan_origination_date` and `original_loan_amount` are present. Falls back to `initial_debt` if absent (backward-compatible).[^4]

## Equity

Stocks, bonds, brokerage accounts. Supports both Gaussian and historical-return sampling.

**`_setup()`** initialises:
- Annual rates divided by 12 for monthly compounding.
- If `sampled_monthly_sp500_returns` path is given, loads the CSV and sets `sampled_flag = True`.

**Per-period:** `income = value × dividend_rate / 12`. If `sampled_flag`, picks a random row from the historical returns CSV as `growth_rate` instead of using the Gaussian model.[^5]

**`taxable_income()`** = `income - expenses + capital_gains` (overrides base; capital gains currently always 0 in normal flow — `withdraw_income()` sets it but references an undefined `period` variable).

## SalaryIncome

Employment income or Social Security benefit.

**`_setup()`**:
- If `retirement_age_based_benefit` dict is present, looks up the benefit by `retirement_age` key.
- Otherwise uses `salary / 12` as monthly income.
- `growth_rate = cola / 12`.[^6]

**Per-period:** `income *= (1 + growth_rate)` — compound COLA growth each month.

**Social Security** is modelled as a `SalaryIncome` asset with `start_date = "retirement"` and a benefit lookup table keyed by claiming age (62, 67, 70). The lookup bypasses the SSA's AIME/PIA/bend-points formula entirely — see [[social-security-benefit-calculation]]. The earnings test (benefit reduction for pre-FRA workers who keep earning) is not modeled.

## Date Placeholder Resolution

Before simulation starts, `set_scenario_dates()` resolves string placeholders in `start_date`/`end_date`:

| Placeholder | Resolves to |
|---|---|
| `"first_date"` | `start_date` from world config |
| `"retirement"` | `birth_date + retirement_age × 365.25` |
| `"end_date"` | `end_date` from world config |

## Related

- [[configuration]] — JSON schema for each asset type
- [[simulation-engine]] — how `period_update()` is called
- [[tax-model]] — how `tax_class` is used
- [[simulation-flow]] — end-to-end pseudocode showing the per-period call sequence
- [[social-security-benefit-calculation]] — the actual SS formula that `SalaryIncome` approximates
- [[social-security-taxation]] — how SS income is actually taxed

---

[^1]: `models/assets.py` line ~57-61 — `self._state = AssetState()` created after `self.__dict__.update(data)` so JSON keys cannot overwrite it
[^2]: `models/assets.py` `_asset_appreciation()` — the original code had a misspelled `hasattr` check (`growth_rate_volatiliy`) that was always False; fixed to check `self.growth_rate_volatility == 0.0` directly
[^3]: `models/assets.py` `REAsset._period_update_finalize_metrics()` — full expense assembly including extra principal
[^4]: `models/assets.py` `REAsset.pre_calculate()` — closed-form: `B(n) = L*(1+r)^n - PMT*((1+r)^n - 1)/r`
[^5]: `models/assets.py` `Equity._period_update_finalize_metrics()` — `self.growth_rate = self.sampled_growth_rate[np.random.randint(0, len(self.sampled_growth_rate))]`
[^6]: `models/assets.py` `SalaryIncome._setup()` — `self.salary = self.retirement_age_based_benefit[str(self.retirement_age)]`
