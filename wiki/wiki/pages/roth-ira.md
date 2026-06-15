---
title: Roth IRA
tags: [concept, tax, retirement-accounts, roth]
sources: [fidelity-401k-vs-roth]
updated: 2026-06-14
---

# Roth IRA

## Description

A Roth IRA is an individual retirement account funded with after-tax contributions. Qualified withdrawals of both contributions and earnings are entirely tax-free (after age 59½ and once the 5-year rule is met). Unlike a traditional 401(k), there are no required minimum distributions — assets can compound tax-free indefinitely.[^1]

Roth IRAs are self-managed and not tied to an employer. Contributions can be withdrawn at any time without taxes or penalties (earnings face taxes and a 10% penalty if withdrawn before 59½).[^2]

## 2026 Contribution Limits

| Status | Full contribution below | Phase-out range | No contribution above |
|---|---|---|---|
| Single filer | $153,000 MAGI | $153k–$168k | $168,000 |
| Married filing jointly | $242,000 MAGI | $242k–$252k | $252,000 |

Annual limit: $7,500 (age 49 and under), $8,600 ($7,500 + $1,100 catch-up, age 50+).[^3]

## Key Differences from Traditional 401(k)

| Feature | Roth IRA | Traditional 401(k) |
|---|---|---|
| Contribution tax treatment | After-tax | Pre-tax |
| Withdrawal tax treatment | Tax-free (qualified) | Ordinary income |
| Annual limit (2026) | $7,500 | $24,500 |
| Income limit | Yes ($168k/$252k phase-out) | No |
| Employer match | No | Yes (if offered) |
| RMDs | None | Required at age 73 |
| Investment choice | Broad (self-directed) | Employer plan options only |

## Implementation (as of 2026-06-14)

Roth IRA support was added to the simulation engine. Key changes:

- **`"roth"` tax class** added to `TaxConfig` (rate: 0.0). Roth asset income routes to the `roth` bucket in `TaxableIncomeBreakdown` and contributes zero tax.
- **Asset files**: `configuration/assets/roth_ira_stock.json` and `roth_ira_bonds.json` — both `type: "Equity"`, `tax_class: "roth"`, named `"Roth IRA Stock"` / `"Roth IRA Bonds"` so they match the `"roth ira"` substring used in `roth_portfolio_value()`.
- **`roth_savings_rate`** config field: fraction of pre-retirement free cash flow invested into Roth IRA assets (default: 0.0).
- **`roth_portfolio_value()`** method: sums net value of all assets whose name contains `"roth ira"`.
- **Post-retirement Roth withdrawal**: each month after `retirement_age`, `withdrawal_rate × roth_portfolio_value() / 12` is drawn from Roth IRA assets and recorded in the `roth_withdrawal` output column. This amount is **not** added to `monthly_taxable_income`.

Income limits and the backdoor Roth conversion strategy are not modeled — contributions are not capped at IRS limits.

## Appearances in Sources

- [[fidelity-401k-vs-roth]] — full comparison with 401(k); 2026 limits and income phase-outs

## Related Concepts

- [[required-minimum-distributions]] — Roth IRAs are exempt from RMDs; traditional 401(k)s are not
- [[tax-model]] — how the current model handles withdrawal taxation
- [[configuration]] — asset types currently configured (no Roth)

---

[^1]: `raw/fidelity_401k_v_roth.txt` p.1 — "There are no required minimum distributions or RMDs, an amount you're obligated to take out of certain tax-advantaged accounts each year after you reach a certain age."
[^2]: `raw/fidelity_401k_v_roth.txt` p.1 — "Before age 59½, you could withdraw your contributions anytime from your Roth IRA—but not investment earnings—without paying taxes or penalties."
[^3]: `raw/fidelity_401k_v_roth.txt` p.1 — "The annual contribution limit for IRAs, including Roth and traditional IRAs, is $7,500 for 2026. If you're age 50 or older, you can contribute an additional $1,100 for 2026."
