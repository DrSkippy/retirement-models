---
title: Overview
tags: [overview, synthesis]
sources: []
updated: 2026-06-14

---

# Retirement Models — Overview

> Evolving synthesis of everything in the wiki. Updated by wiki-ingest when sources shift the understanding.

## Current Understanding

A monthly time-step personal finance simulator that models asset growth, income, expenses, taxes, savings, and portfolio withdrawals across a configurable retirement horizon. The system supports both deterministic single runs and stochastic Monte Carlo analysis (1000s of runs), persists results to PostgreSQL, and exposes them through a Flask REST API consumed by a React web UI.

The architecture has three distinct layers:
- **Simulation core** (`models/`) — pure Python financial models with no I/O dependencies
- **Persistence + API** (`api/`, `models/db.py`) — Flask + SQLAlchemy + PostgreSQL
- **UI** (`frontend/`) — React 19 + TypeScript + Recharts, served as a static SPA behind Nginx

The central simulation loop lives in `RetirementFinancialModel.run_model()`. Each period calls every asset's `period_update()`, then aggregates net worth, income, taxes, and cash flows at the scenario level. Pre-retirement free cash flow is reinvested into the 401k portfolio; post-retirement a configurable withdrawal rate draws down the portfolio.

## Known Model Gaps

Three significant real-world retirement mechanics remain unmodeled or approximated:

1. **Contribution limits not enforced** — `savings_rate` and `roth_savings_rate` invest a flat fraction of free cash flow with no cap tied to IRS annual limits ($24,500 for 401k, $7,500 for Roth IRA).
2. **SS COLA underestimated** — `SocSec.json` uses 1.5% COLA; the 2026 actual is 2.8%. See [[social-security-benefit-calculation]].
3. **SS taxation is a rough approximation** — the flat 15.3% rate conflates payroll tax with income tax on benefits. Actual SS taxation is threshold-based (0–85% inclusion). See [[social-security-taxation]].

## Implemented (formerly gaps)

- **Roth IRA model** _(implemented 2026-06-14)_ — `"roth"` tax class (0% rate) added to `TaxConfig`; `roth_ira_stock.json` and `roth_ira_bonds.json` asset files; `roth_savings_rate` config field for pre-retirement contributions; Roth withdrawals tracked separately and excluded from taxable income. See [[roth-ira]].
- **RMD schedule** _(implemented 2026-06-14)_ — IRS Uniform Lifetime Table (Publication 590-B, 2022) embedded in `models/scenarios.py`; `calculate_rmd_withdrawal()` computes monthly minimum; `run_model()` enforces `max(flat_withdrawal, rmd_required)` when `age >= rmd_age` (default 73). `rmd_required` column added to output. See [[required-minimum-distributions]].

## Open Questions

- Is there an inflation adjustment applied to expenses? The `inflation_rate` field is in `WorldConfig` but its application in the simulation loop is not immediately visible.
- The `capital_gains` field in `Equity.withdraw_income()` references an undefined `period` variable — this appears to be a latent bug.
- How does the DB persistence layer relate to the CLI `--save-db` flag? (`models/db.py` not yet documented)

## Key Entities / Concepts

- [[simulation-engine]] — `RetirementFinancialModel`, the main loop
- [[asset-models]] — `Asset`, `REAsset`, `Equity`, `SalaryIncome`
- [[tax-model]] — `TaxCalculator`, `TaxableIncomeBreakdown`
- [[monte-carlo]] — `MonteCarloRunner`, `MonteCarloResults`, `SimulationResult`
- [[configuration]] — `WorldConfig`, asset JSON schema, `config.yaml`
- [[rest-api]] — Flask blueprints, endpoints
- [[frontend]] — React pages, chart components
- [[deployment]] — Docker, Nginx, Cloudflare Tunnel
- [[roth-ira]] — tax-free retirement account (not currently modeled)
- [[required-minimum-distributions]] — mandatory IRS withdrawals at age 73 (not currently modeled)
- [[social-security-benefit-calculation]] — AIME/PIA/bend-points formula; claiming age multipliers
- [[social-security-taxation]] — threshold-based SS income taxation (model uses flat approximation)
