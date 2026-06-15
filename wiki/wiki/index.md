# Wiki Index — Retirement Models

## Architecture
- [Simulation Flow](pages/simulation-flow.md) — End-to-end data flow: single run and Monte Carlo variants, investment/withdrawal loops
- [Deployment](pages/deployment.md) — Docker containers, Nginx reverse proxy, Cloudflare Tunnel, local registry

## Models
- [Simulation Engine](pages/simulation-engine.md) — `RetirementFinancialModel`: initialisation, setup, main monthly loop, aggregation methods
- [Asset Models](pages/asset-models.md) — `Asset` base class, `REAsset` (mortgage), `Equity` (stocks/bonds), `SalaryIncome` (salary/SS)
- [Tax Model](pages/tax-model.md) — `TaxCalculator`, income classes, flat-rate calculation, known limitations
- [Monte Carlo](pages/monte-carlo.md) — `MonteCarloRunner`, state isolation, output types, ruin probability

## Config
- [Configuration System](pages/configuration.md) — `config.yaml`, `config.json` (WorldConfig), asset JSON schemas, Pydantic models, env vars

## API
- [REST API](pages/rest-api.md) — Flask app factory, blueprints, endpoint reference, PostgreSQL backend

## Flows
- [Simulation Flow](pages/simulation-flow.md) — Step-by-step pseudocode for single run, MC run, investment, withdrawal, and tax flows
- [Frontend](pages/frontend.md) — React pages, chart components, API client, dev/prod build

## Reference
- [Fidelity: Roth IRA vs. 401(k)](pages/fidelity-401k-vs-roth.md) — 2026 contribution limits, income phase-outs, RMD rules _(ingested 2026-06-14)_
- [Thrivent: Social Security Guide](pages/thrivent-social-security.md) — AIME/PIA formula, claiming age multipliers, COLA, taxation _(ingested 2026-06-14)_
- [Roth IRA](pages/roth-ira.md) — after-tax account with tax-free withdrawals, no RMDs, income limits
- [Required Minimum Distributions](pages/required-minimum-distributions.md) — IRS mandatory withdrawals from 401(k) at age 73; not currently modeled
- [Social Security Benefit Calculation](pages/social-security-benefit-calculation.md) — AIME, PIA, bend points, claiming age table, COLA, earnings test
- [Social Security Taxation](pages/social-security-taxation.md) — threshold-based inclusion (0–85%); vs. model's flat 15.3% approximation

## Maintenance
- [Lint 2026-06-14](pages/lint-2026-06-14.md) — 1 error, 2 warnings, 3 info items
