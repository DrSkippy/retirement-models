---
title: Simulation Flow
tags: [flows, architecture, simulation]
sources: [scenarios-py, assets-py, monte-carlo-py]
updated: 2026-06-14
---

# Simulation Flow

## End-to-End: Single Deterministic Run

```
bin/runner.py
  │
  ├── load config.yaml  (paths, logging)
  │
  ├── RetirementFinancialModel(config.json)
  │     ├── WorldConfig.from_json()        ← Pydantic validation
  │     ├── TaxCalculator(tax_classes)
  │     └── parse dates, compute retirement_date
  │
  ├── model.setup(assets_dir)
  │     ├── create_assets()                ← one Asset subclass per JSON file
  │     ├── asset.set_scenario_dates()     ← resolve placeholders
  │     ├── asset.pre_calculate()          ← mortgage balance at start_date
  │     └── create_datetime_sequence()     ← monthly timeline
  │
  ├── model.run_model()
  │     └── for each month:
  │           ├── asset.period_update()    ← for every asset
  │           │     ├── _setup() [first active period only]
  │           │     ├── _period_update_finalize_metrics()
  │           │     └── compute appreciation, cash_flow, operating_expense, taxable_income
  │           │
  │           ├── [if post-retirement] retirement_withdrawal → deduct from 401k assets
  │           ├── aggregate: net_worth, debt, taxable_income, expenses, taxes
  │           ├── [if pre-retirement]  investment = savings_rate × free_cash_flow → add to 401k assets
  │           └── append row to mdata
  │
  ├── scenario_df = get_scenario_dataframe()
  └── [optional] --save-db → persist via models/db.py
```

## Monte Carlo Variant

```
MonteCarloRunner.run()
  └── for run_id in range(n_runs):
        ├── fresh RetirementFinancialModel()   ← critical: new instance per run
        ├── model.setup()
        ├── model.run_model()
        ├── extract net_worth trajectory
        ├── detect ruin_period (first period where net_worth < 0)
        └── append SimulationResult
  └── return MonteCarloResults
        ├── ruin_probability()
        └── terminal_wealth_percentiles([10, 25, 50, 75, 90])
```

## Pre-retirement Investment Flow

Each period where `age < retirement_age`:

```
free_cash_flow = taxable_income + Σ asset.cash_flow() - taxes_paid
investment = max(0, savings_rate × free_cash_flow)

allocate_investment_evenly(investment × 0.6, "401k stock")
allocate_investment_evenly(investment × 0.4, "401k bond")
```

## Post-retirement Withdrawal Flow

Each period where `age ≥ retirement_age`:

```
retirement_portfolio = Σ (asset.value - asset.debt) for assets with "401k" in name
withdrawal = withdrawal_rate × retirement_portfolio / 12

allocate_investment_evenly(-withdrawal × 0.6, "401k stock")  ← negative = deduction
allocate_investment_evenly(-withdrawal × 0.4, "401k bond")

monthly_taxable_income += withdrawal  ← taxed as ordinary income
```

## Tax Calculation Flow (per period)

```
TaxCalculator.build_breakdown_from_assets(assets, withdrawal)
  └── for each asset: by_class[asset.tax_class] += asset.income
  └── return TaxableIncomeBreakdown(ordinary_income=income+withdrawal, capital_gains, social_security)

TaxCalculator.calculate_monthly(breakdown)
  └── ordinary × 0.37 + capital_gains × 0.20 + social_security × 0.153
```

## Related

- [[simulation-engine]] — `RetirementFinancialModel` details
- [[asset-models]] — per-asset `period_update()` internals
- [[tax-model]] — tax calculation details
- [[monte-carlo]] — Monte Carlo runner details
