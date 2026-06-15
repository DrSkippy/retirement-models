---
title: Required Minimum Distributions (RMDs)
tags: [concept, tax, retirement-accounts, rmd]
sources: [fidelity-401k-vs-roth]
updated: 2026-06-14
---

# Required Minimum Distributions (RMDs)

## Description

RMDs are mandatory annual withdrawals the IRS requires from traditional 401(k) and traditional IRA accounts beginning the year the account holder turns age 73 (under SECURE 2.0 rules). The withdrawal amount is calculated as the account balance divided by an IRS life expectancy factor from the Uniform Lifetime Table. Failure to take RMDs results in a 25% excise tax on the shortfall.[^1]

Roth IRAs are exempt from RMDs during the original owner's lifetime. Roth 401(k)s were also exempted from RMDs starting in 2024 under SECURE 2.0.

## Implementation (as of 2026-06-14)

RMDs are now modeled in `RetirementFinancialModel`. The IRS Uniform Lifetime Table (Publication 590-B, 2022 update) is embedded as `_IRS_UNIFORM_LIFETIME_TABLE` in `models/scenarios.py` (ages 70–120).[^2]

Each month when `age >= rmd_age` (default 73), the engine:
1. Computes `rmd_required = retirement_portfolio_value() / (distribution_period × 12)` via `calculate_rmd_withdrawal(age, portfolio)`.
2. Takes `retirement_withdraw = max(flat_withdrawal, rmd_required)` — the withdrawal is never less than the IRS minimum.
3. Records both values (`retirement_withdrawal`, `rmd_required`) as separate output columns for audit.

The `rmd_age` threshold is configurable in `configuration/config.json` and `WorldConfig` (default: 73). Roth IRA assets (matched by `"roth ira"` substring) are not included in the RMD portfolio — they are tracked and withdrawn separately via `roth_portfolio_value()`.

This is a monthly approximation: the IRS rule technically uses the prior December 31 balance; the model uses the current period balance instead. The difference is small in steady-state but will diverge if portfolio value swings sharply month-to-month.

## Key Facts (2026)

- RMD start age: **73** (SECURE 2.0; was 72 under prior law, 70½ before 2020)[^1]
- Applies to: traditional 401(k), traditional IRA, SEP IRA, SIMPLE IRA
- Exempt: Roth IRA (owner's lifetime), Roth 401(k) (since 2024)
- Penalty for missing RMD: 25% excise tax on the shortfall (reduced to 10% if corrected within 2 years)

## Appearances in Sources

- [[fidelity-401k-vs-roth]] — "you generally need to start taking RMDs from your 401(k) account the year you turn age 73"

## Related Concepts

- [[roth-ira]] — no RMDs required
- [[simulation-engine]] — current withdrawal logic (flat rate, no RMD schedule)
- [[tax-model]] — RMD withdrawals taxed as ordinary income

---

[^1]: `raw/fidelity_401k_v_roth.txt` p.2 — "You generally need to start taking RMDs from your 401(k) account the year you turn age 73. RMDs could increase taxable income in retirement."
[^2]: `models/scenarios.py` `_IRS_UNIFORM_LIFETIME_TABLE` + `calculate_rmd_withdrawal()` + `run_model()` [synthesis] — table embedded at module level; `run_model()` uses `max(flat_withdrawal, rmd_required)` when `age >= rmd_age`
