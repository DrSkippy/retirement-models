---
title: Configuration System
tags: [config, pydantic, assets]
sources: [config-py, config-json, config-yaml]
updated: 2026-06-14
---

# Configuration System

Two distinct config layers: **system config** (`config.yaml`) controls paths and logging for the CLI runner; **simulation config** (`configuration/config.json` + `configuration/assets/`) controls the financial model.

## System Config (`config.yaml`)

Used only by `bin/runner.py`. Not consumed by the Flask API.

```yaml
paths:
  model_config: ./configuration/config.json
  assets_dir: ./configuration/assets
  output_dir: ./output

logging:
  level: DEBUG
  file: ./log/assets.log
  max_bytes: 2500000
  backup_count: 3
  format: "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
```

## World Config (`configuration/config.json`)

Loaded and validated as `WorldConfig` (Pydantic `BaseModel`) via `WorldConfig.from_json()`.

### Fields

| Field | Type | Description |
|---|---|---|
| `birth_date` | ISO date | Owner's date of birth |
| `spouse_birth_date` | ISO date | Spouse's date of birth |
| `retirement_age` | int | Age at retirement (used to compute `retirement_date`) |
| `start_date` | ISO date | Simulation start |
| `end_date` | ISO date | Simulation end |
| `inflation_rate` | float | Annual inflation (stored; application not visible in main loop) |
| `savings_rate` | float | Fraction of free cash flow invested pre-retirement |
| `withdrawal_rate` | float | Annual draw rate from 401k post-retirement (4% = 0.04) |
| `stock_allocation` | float | Fraction of investments/withdrawals into stocks |
| `bond_allocation` | float | Fraction of investments/withdrawals into bonds |
| `tax_classes` | object | `{income, capital_gain, social_security}` flat rates |

**Validation rules (Pydantic):**
- `stock_allocation + bond_allocation` must equal exactly 1.0 (enforced by `AllocationConfig.allocations_sum_to_one`).[^1]
- `retirement_date` is auto-computed as `birth_date + retirement_age × 365.25` if not supplied.

### Current values (`configuration/config.json`)

```json
{
  "birth_date": "1966-05-25",
  "spouse_birth_date": "1969-05-22",
  "retirement_age": 67,
  "savings_rate": 0.20,
  "inflation_rate": 0.025,
  "withdrawal_rate": 0.04,
  "stock_allocation": 0.6,
  "bond_allocation": 0.4,
  "start_date": "2025-06-01",
  "end_date": "2056-05-25",
  "tax_classes": { "income": 0.37, "capital_gain": 0.20, "social_security": 0.153 }
}
```

## Asset Config Files (`configuration/assets/*.json`)

One JSON file per asset. The `"type"` field selects the Python class. All assets share common base fields:

| Field | Description |
|---|---|
| `name` | Display name and match key for `name_match` lookups |
| `description` | Human-readable description |
| `type` | `"Equity"`, `"RealEstate"`, or `"Salary"` |
| `start_date` | When asset becomes active (ISO date or placeholder) |
| `end_date` | When asset deactivates (ISO date or placeholder) |
| `tax_class` | `"income"`, `"capital_gain"`, or `"social_security"` |

### Date Placeholders

| Placeholder | Resolves to |
|---|---|
| `"first_date"` | World config `start_date` |
| `"retirement"` | Computed `retirement_date` |
| `"end_date"` | World config `end_date` |

### Equity Asset Fields

```json
{
  "initial_value": 1239553,
  "initial_expense_rate": 0.0005,
  "appreciation_rate": 0.06,
  "appreciation_rate_volatility": 0.02,
  "dividend_rate": 0.002,
  "sampled_monthly_sp500_returns": "../sp500-historical-portfolio-returns/out_data/monthly_returns.csv"
}
```

`sampled_monthly_sp500_returns` is optional; when present and non-null, replaces Gaussian sampling with historical return draws.[^2]

### RealEstate Asset Fields

```json
{
  "initial_value": 950000,
  "initial_debt": 304145.36,
  "appreciation_rate": 0.015,
  "property_tax_rate": 0.0058576,
  "insurance_cost": 2165.77,
  "interest_rate": 0.028813,
  "payment": 1405.25,
  "monthly_rental_income": 0,
  "management_fee_rate": 0.0,
  "rental_expense_rate": 0.0
}
```

Optional fields: `loan_origination_date`, `original_loan_amount` (for auto-computed amortization balance), `extra_principal_payment` (monthly extra paydown).

### Salary / Social Security Asset Fields

```json
{
  "cola": 0.015,
  "retirement_age": "retirement_age",
  "retirement_age_based_benefit": {
    "62": 2831.0,
    "67": 4018.0,
    "70": 5108.0
  }
}
```

For non-SS salary: provide `"salary"` (annual) instead of `retirement_age_based_benefit`.

## Configured Assets (current)

| File | Name | Type | Notes |
|---|---|---|---|
| `401k_stock.json` | 401k Stocks | Equity | Historical SP500 returns, 60% allocation target |
| `401k_bonds.json` | 401k Bonds | Equity | 40% allocation target |
| `brokerage_stock.json` | Brokerage Stocks | Equity | Taxable brokerage |
| `brokerage_bonds.json` | Brokerage Bonds | Equity | Taxable brokerage |
| `primary_residence.json` | Primary Residence | RealEstate | Owner-occupied, no rental income |
| `rental_114.json` | Rental Property | RealEstate | Rental income-generating |
| `F5.json` | F5 Income (salary) | Salary | Employment income |
| `SocSec.json` | Social Security | Salary | Age-based benefit table |

## Pydantic Config Models

Defined in `models/config.py`:

| Class | Purpose |
|---|---|
| `WorldConfig` | Top-level simulation parameters |
| `TaxConfig` | Tax rates (`income`, `capital_gain`, `social_security`) |
| `AllocationConfig` | `stock_allocation` + `bond_allocation` (must sum to 1.0) |
| `BaseAssetConfig` | Common asset fields (name, type, dates, tax_class) |
| `EquityConfig` | Equity-specific fields |
| `RealEstateConfig` | Real estate-specific fields |
| `SalaryConfig` | Salary/SS-specific fields |

## Environment Variables

DB credentials are loaded from `.envrc` via direnv and consumed by `models/db.py` via `pydantic-settings`:

```bash
DB_HOST=192.168.1.91
DB_PORT=5434
DB_NAME=retirement-models
DB_USER=scott
DB_PASSWORD=<secret>
```

## Modeling Gaps

- **No Roth account type.** All eight configured assets are traditional 401(k), taxable brokerage, real estate, or salary. Adding a Roth account would require a new asset JSON with a Roth-appropriate `tax_class` (e.g., `"roth"` at 0%) or exclusion from taxable income. See [[roth-ira]].
- **2026 contribution limits not enforced.** The `savings_rate` mechanism invests a flat fraction of free cash flow with no cap tied to IRS annual limits ($24,500 for 401k, $7,500 for IRA). Pre-retirement savings may be over- or under-stated relative to legal limits.
- **SS COLA underestimated.** `SocSec.json` uses `"cola": 0.015` (1.5%). The 2026 actual COLA is 2.8%. Over a 30-year simulation horizon this compounds to a significant understatement of SS income. See [[social-security-benefit-calculation]].
- **SS tax rate is a rough approximation.** `tax_classes.social_security: 0.153` appears to conflate the self-employment payroll tax rate with the income tax on SS benefits. Actual SS income taxation is threshold-based. See [[social-security-taxation]].

## Related

- [[simulation-engine]] — how `WorldConfig` is consumed
- [[asset-models]] — how asset JSON fields map to class attributes
- [[tax-model]] — `tax_classes` configuration
- [[roth-ira]] — unmodeled account type
- [[required-minimum-distributions]] — relevant to post-retirement withdrawal modeling
- [[social-security-benefit-calculation]] — COLA and benefit amount context
- [[social-security-taxation]] — why the 15.3% SS tax rate is an approximation

---

[^1]: `models/config.py` `AllocationConfig.allocations_sum_to_one()` — `if abs(total - 1.0) > 1e-6: raise ValueError(...)`
[^2]: `models/assets.py` `Equity._setup()` — `sampled_monthly_sp500_returns` path triggers CSV load and sets `sampled_flag = True`
