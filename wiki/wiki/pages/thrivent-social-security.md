---
title: "Thrivent: A Complete Guide to Social Security Benefits"
tags: [reference, social-security, tax, retirement-income]
sources: [thrivent-social-security]
updated: 2026-06-14
---

# Thrivent: A Complete Guide to Social Security Benefits

**Source:** `raw/trivent_social_security.txt`
**Date ingested:** 2026-06-14
**Type:** Reference article (Thrivent, updated Apr 22, 2026)

## Summary

Social Security retirement benefits are calculated from a worker's 35 highest-earning years. The SSA converts those earnings into an Average Indexed Monthly Earnings (AIME) figure, then applies a progressive "bend points" formula to produce the Primary Insurance Amount (PIA) — the benefit paid at Full Retirement Age (FRA). For workers born in 1960 or later, FRA is age 67.[^1] Claiming before FRA permanently reduces the benefit (down to 70% at age 62); delaying past FRA increases it by 8% per year, maxing out at 124% of PIA at age 70.[^2]

Benefits grow each year through Cost of Living Adjustments (COLAs). In 2026, the COLA is 2.8%, raising average payments by about $56/month.[^3] The model's `SocSec.json` uses a hardcoded `cola: 0.015` (1.5%) — significantly lower than the 2026 actual rate.

Federal income taxes on SS benefits are not a flat percentage. Benefits become taxable only when "combined income" (½ of SS benefit + other income + tax-exempt interest) exceeds $25,000 for single filers or $32,000 for married filing jointly, with up to 85% of benefits included in taxable income at high income levels.[^4] The model's flat `social_security: 0.153` rate does not correspond to this threshold-based treatment.

## Key Takeaways

- **Benefit formula**: AIME → PIA via bend points (90% / 32% / 15%). The model uses a hardcoded lookup table instead.[^5]
- **FRA for 1960+ birth years is 67** — matches `retirement_age: 67` in the model's config.[^1]
- **Claiming multipliers**: 70% at 62, 100% at 67, 124% at 70. The `SocSec.json` table ($2,831 / $4,018 / $5,108) reflects these approximately.[^2]
- **2026 COLA is 2.8%** — the model uses 1.5%, understating long-run SS income growth.[^3]
- **SS taxation is threshold-based**, not flat — 0% / up to 50% / up to 85% of benefits included in taxable income based on combined income thresholds. The model's 15.3% flat rate conflates payroll tax rates with income tax on benefits.[^4]
- **Earnings test** (pre-FRA workers): benefit reduced $1 per $2 earned above $24,480. Not modeled.[^6]
- **Survivor benefits**: surviving spouse can claim 71.5%–100% of deceased's benefit depending on age. Not modeled.
- **2026 SS wage base**: $184,500 (6.2% employee + 6.2% employer payroll tax).

## Entities & Concepts

- [[social-security-benefit-calculation]] — AIME, PIA, bend points formula, claiming-age adjustments
- [[social-security-taxation]] — threshold-based income inclusion vs. model's flat rate
- [[asset-models]] — `SalaryIncome` class models SS income; COLA and earnings test gaps
- [[tax-model]] — `social_security: 0.153` rate is a modeling approximation, not the IRS rule
- [[configuration]] — `SocSec.json` COLA discrepancy (1.5% modeled vs. 2.8% actual 2026)

## Relation to Other Wiki Pages

**[[tax-model]]:** The `social_security` tax class applies a flat 15.3% rate. The 15.3% figure is actually the self-employment payroll tax rate (12.4% SS + 2.9% Medicare), not the income tax rate on SS benefits. Actual federal income tax on SS follows a combined-income threshold test and could range from 0% to ~32%+ of the benefit (85% of benefit included × ordinary income rate). See [[social-security-taxation]].

**[[configuration]]:** `SocSec.json` has `"cola": 0.015`. The 2026 actual COLA is 2.8%. Over a 30-year simulation, this 1.3 percentage point gap compounds significantly.

**[[asset-models]]:** `SalaryIncome._setup()` selects the benefit from the `retirement_age_based_benefit` lookup table. This is a reasonable approximation but bypasses the AIME/PIA calculation and doesn't model the earnings test for pre-FRA workers who continue working.

---

[^1]: `raw/trivent_social_security.txt` §"Claiming Social Security retirement benefits early or late" — "Born in 1960 or later: Your FRA is 67."
[^2]: `raw/trivent_social_security.txt` §"Claiming Social Security retirement benefits early or late" — benefit table: 62→70%, 67→100%, 70→124%; "For every year you wait to claim benefits past full retirement age, your benefit amount increases by 8% per year"
[^3]: `raw/trivent_social_security.txt` §"Cost of living adjustments" — "In 2026, Social Security benefits will rise by 2.8%, boosting payments by about $56 per month on average."
[^4]: `raw/trivent_social_security.txt` §"You've opted to have taxes withheld" — "you must pay federal income taxes on your Social Security benefits if your combined annual income...is more than $25,000 ($32,000 if married and filing jointly). As your income increases, up to 85% of your benefits could be taxed."
[^5]: `raw/trivent_social_security.txt` §"How Social Security retirement benefits are calculated" — bend points formula: 90% of first $1,286 AIME + 32% of $1,286–$7,749 + 15% above $7,749
[^6]: `raw/trivent_social_security.txt` §"You're working while on Social Security" — "your benefit will be reduced by $1 for every $2 you earn beyond the annual limit of $24,480"
