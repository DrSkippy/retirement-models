# Wiki Log

Append-only. Format: `## [YYYY-MM-DD] <operation> | <title>`
Recent entries: `grep "^## \[" log.md | tail -10`

---

## [2026-06-14] init | retirement-models application wiki

## [2026-06-14] lint | 1 error, 2 warnings, 3 info items
Report: [[lint-2026-06-14]]
Fixed: none

## [2026-06-14] ingest | Fidelity: Roth IRA vs. 401(k)
Pages written: fidelity-401k-vs-roth, roth-ira, required-minimum-distributions
Pages updated: tax-model, simulation-engine, configuration, asset-models, monte-carlo, overview, index

## [2026-06-14] ingest | Thrivent: A Complete Guide to Social Security Benefits
Pages written: thrivent-social-security, social-security-benefit-calculation, social-security-taxation
Pages updated: tax-model, configuration, asset-models, overview, index

## [2026-06-14] implement | Roth IRA model
Code: TaxConfig.roth field, roth_ira_stock.json, roth_ira_bonds.json, roth_savings_rate, roth_portfolio_value(), roth_withdrawal output column
Pages updated: roth-ira, tax-model, simulation-engine, overview

## [2026-06-14] implement | Required Minimum Distributions
Code: _IRS_UNIFORM_LIFETIME_TABLE, WorldConfig.rmd_age, calculate_rmd_withdrawal(), rmd_required output column, max(flat, rmd) enforcement
Tests added: 7 new tests in tests/test_scenarios.py (121 total, all pass)
Pages updated: required-minimum-distributions, simulation-engine, tax-model, roth-ira, overview

## [2026-06-14] implement | Configuration UI
Code: api/blueprints/configuration_bp.py (6 endpoints), frontend/src/types/configuration.ts, frontend/src/api/configuration.ts, frontend/src/pages/ConfigPage.tsx, App.tsx (/config route), AppShell.tsx (Configuration nav item)
Pages updated: rest-api, frontend
