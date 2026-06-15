---
title: Tax Model
tags: [models, taxes, simulation]
sources: [taxes-py, config-py]
updated: 2026-06-14
---

# Tax Model

## Overview

Tax calculation is handled by `TaxCalculator` in `models/taxes.py`. It is stateless — constructed once with a `TaxConfig` and called each period with a fresh `TaxableIncomeBreakdown`.

## Income Classes

Four flat-rate classes, configured in `configuration/config.json` under `tax_classes`:[^1]

| Class | Field in `TaxConfig` | Applies to |
|---|---|---|
| Ordinary income | `income` | Salary, 401k withdrawals, rental income |
| Capital gains | `capital_gain` | Equity capital gains |
| Social Security | `social_security` | Social Security benefit income |
| Roth | `roth` | Roth IRA withdrawals (always 0%) |

Current rates (from `configuration/config.json`):
- `income`: 37%
- `capital_gain`: 20%
- `social_security`: 15.3%
- `roth`: 0.0%

## Data Flow

Each period in `RetirementFinancialModel.calculate_monthly_taxes(withdrawal)`:

1. `TaxCalculator.build_breakdown_from_assets(assets, withdrawal)` — iterates all assets, accumulates `asset.income` into the bucket matching `asset.tax_class`. Adds `withdrawal` to ordinary income.[^2]
2. `TaxCalculator.calculate_monthly(breakdown)` — multiplies each bucket by its rate and sums.

```
ordinary_income × income_rate
+ capital_gains × capital_gain_rate
+ social_security × social_security_rate
= monthly_tax_liability
```

## `TaxableIncomeBreakdown` (Pydantic model)

| Field | Type | Default |
|---|---|---|
| `ordinary_income` | float | 0.0 |
| `capital_gains` | float | 0.0 |
| `social_security` | float | 0.0 |
| `roth` | float | 0.0 |

## Tax Class Mapping (per asset)

Each asset JSON file carries a `"tax_class"` field that routes its income:

| Asset | `tax_class` |
|---|---|
| 401k stocks / bonds | `"income"` |
| Roth IRA stocks / bonds | `"roth"` |
| Brokerage accounts | `"income"` or `"capital_gain"` |
| Primary residence | `"income"` |
| Rental properties | `"income"` |
| Social Security | `"social_security"` |
| Salary | `"income"` |

## Known Limitations

- Rates are flat — no brackets, standard deduction, or AMT.
- `inflation_rate` is stored in `WorldConfig` but there is no evidence it is applied to tax thresholds.
- Capital gains on equity assets are not correctly populated in the normal simulation flow (the `withdraw_income()` path references an undefined `period` variable).[^3]
- **SS taxation is not a flat rate.** The `social_security: 0.153` rate conflates the self-employment payroll tax (12.4% SS + 2.9% Medicare = 15.3%) with the income tax on SS benefits, which is threshold-based (0% / up to 50% / up to 85% inclusion in ordinary income). See [[social-security-taxation]].
- **Roth class always 0%.** The `"roth"` tax class and `roth` breakdown field exist but the rate is hardcoded to 0.0; Roth withdrawals are routed through the `roth` bucket but contribute zero tax, which is correct behavior. The reason the `roth` field exists in `TaxableIncomeBreakdown` is symmetry — it allows future non-zero rates without changing the data model.

## Related

- [[configuration]] — `tax_classes` in `config.json`
- [[simulation-engine]] — where `calculate_monthly_taxes()` is called
- [[asset-models]] — `tax_class` field on each asset
- [[simulation-flow]] — full per-period tax calculation sequence
- [[roth-ira]] — unmodeled account type with 0% withdrawal tax
- [[required-minimum-distributions]] — unmodeled mandatory withdrawal schedule
- [[social-security-taxation]] — how SS benefits are actually taxed (threshold-based, not flat)

---

[^1]: `configuration/config.json` — `"tax_classes": {"income": 0.37, "capital_gain": 0.2, "social_security": 0.153}`
[^2]: `models/taxes.py` `build_breakdown_from_assets()` — `by_class[asset.tax_class] += asset.income` for each asset
[^3]: `models/assets.py` `Equity.withdraw_income()` — `self.capital_gains = self.initial_value * self.growth_rate ** period` references `period` which is not in scope
