---
title: Social Security Taxation
tags: [concept, social-security, tax]
sources: [thrivent-social-security]
updated: 2026-06-14
---

# Social Security Taxation

## How SS Benefits Are Actually Taxed

Federal income tax on SS benefits is **not a flat rate**. It is determined by a "combined income" threshold test that controls what fraction of benefits is included in taxable income:[^1]

**Combined income** = ½ × SS benefit + adjusted gross income + tax-exempt interest

| Combined income (single) | Combined income (MFJ) | SS inclusion |
|---|---|---|
| Under $25,000 | Under $32,000 | 0% of benefits taxed |
| $25,000 – $34,000 | $32,000 – $44,000 | Up to 50% of benefits |
| Over $34,000 | Over $44,000 | Up to 85% of benefits |

The included portion is then taxed at the taxpayer's ordinary income rate (not a flat SS-specific rate).

## The Model's Approximation and Its Problems

The model applies `tax_class: "social_security"` with a flat rate of **15.3%** to all SS income every period.[^2]

The 15.3% figure is the **self-employment payroll tax rate** (12.4% Social Security + 2.9% Medicare) — not the income tax rate on SS benefits. This appears to conflate two different taxes:

| Tax | Who pays | Rate | On what |
|---|---|---|---|
| SS payroll tax (employee) | Worker, during career | 6.2% | Wages up to $184,500 |
| SS payroll tax (self-employed) | Self-employed, during career | 12.4% | Net earnings |
| Federal income tax on SS benefits | Retiree | 0–37% × 0–85% inclusion | SS benefit received |

**Practical impact:** A retiree with high combined income could have 85% of their SS benefit included in ordinary income and taxed at 37% = ~31.5% effective rate on the benefit. A retiree with low income owes 0%. The model's flat 15.3% is in the right ballpark for moderate-income retirees but is systematically wrong at both extremes and doesn't vary with income level.

## State Taxes

This article covers only federal taxation. Many states also tax SS benefits; others exempt them. Not discussed further here as the model has no state tax layer.

## Recommendation

To accurately model SS taxation, the flat `social_security` rate should be replaced with a calculation that:
1. Computes combined income each period.
2. Determines the inclusion percentage (0% / 50% / 85%).
3. Applies the ordinary income rate to the included portion.

This would require the `TaxCalculator` to be aware of total income context, not just per-asset buckets.

## Appearances in Sources

- [[thrivent-social-security]] — threshold-based taxation description
- [[fidelity-401k-vs-roth]] — does not discuss SS taxation directly

## Related

- [[tax-model]] — where `social_security: 0.153` is configured and applied
- [[social-security-benefit-calculation]] — the benefit amount that gets taxed
- [[configuration]] — `tax_classes` in `config.json`

---

[^1]: `raw/trivent_social_security.txt` §"You've opted to have taxes withheld" — "you must pay federal income taxes on your Social Security benefits if your combined annual income (50% of your benefit amount plus any other earned income plus tax-exempt interest) is more than $25,000 ($32,000 if married and filing jointly). As your income increases, up to 85% of your benefits could be taxed."
[^2]: `configuration/config.json` — `"social_security": 0.153` in `tax_classes`; `models/taxes.py` `calculate_monthly()` applies this as a flat multiplier on all SS income
