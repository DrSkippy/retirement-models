---
title: "Fidelity: Roth IRA vs. 401(k)"
tags: [reference, tax, retirement-accounts, roth, 401k]
sources: [fidelity-401k-vs-roth]
updated: 2026-06-14
---

# Fidelity: Roth IRA vs. 401(k)

**Source:** `raw/fidelity_401k_v_roth.txt`
**Date ingested:** 2026-06-14
**Type:** Reference article (Fidelity Learn)

## Summary

This Fidelity article compares the two most common tax-advantaged retirement account types. The core structural difference is timing of taxation: traditional 401(k) contributions are pre-tax (reducing current taxable income), grow tax-deferred, and are taxed as ordinary income on withdrawal; Roth IRA contributions are after-tax, grow tax-free, and qualified withdrawals are entirely tax-free. Both allow catch-up contributions for savers 50 and older, but under SECURE 2.0 rules effective 2026, high earners (FICA wages >$150k in the prior year) must designate their catch-up contributions as Roth regardless of account type.[^1]

Contribution limits are substantially different: 401(k) plans allow $24,500 annually (2026), versus only $7,500 for IRAs. Roth IRAs also carry an income eligibility ceiling — full contributions phase out above $153,000 MAGI for single filers and $242,000 for married filing jointly, phasing out completely at $168,000/$252,000. No such income limit applies to 401(k) participation.[^2]

Required minimum distributions (RMDs) are a key divergence in post-retirement mechanics. Traditional 401(k) holders must begin taking RMDs at age 73; Roth IRAs have no RMD requirement, allowing tax-free assets to compound indefinitely. The practical strategy most cited is: maximize 401(k) contributions first to capture any employer match, then fund a Roth IRA for tax diversification and RMD flexibility.[^3]

## Key Takeaways

- Traditional 401(k): pre-tax contributions, tax-deferred growth, ordinary income tax on withdrawal, RMDs begin at 73.[^4]
- Roth IRA: after-tax contributions, tax-free growth, qualified withdrawals tax-free after 59½ (and 5-year rule met), no RMDs.[^5]
- 2026 401(k) limit: $24,500 employee; catch-up $8,000 (age 50+), $11,250 (age 60–63).[^6]
- 2026 Roth IRA limit: $7,500; catch-up $1,100 (age 50+). Income phase-out: $153k–$168k single, $242k–$252k MFJ.[^7]
- SECURE 2.0 (2026): catch-up contributions for earners with prior-year FICA wages >$150k must be Roth.[^8]
- Backdoor Roth IRA is available for high earners above the income ceiling, via nondeductible traditional IRA contributions converted to Roth.

## Entities & Concepts

- [[roth-ira]] — tax-free growth account with income limits and no RMDs
- [[required-minimum-distributions]] — mandatory withdrawals from 401(k) beginning at age 73
- [[tax-model]] — current model taxes all 401k withdrawals as ordinary income; no Roth modeled
- [[configuration]] — no Roth account type exists in the asset config system

## Relation to Other Wiki Pages

**[[tax-model]]:** The current model applies a flat 37% rate to all 401k withdrawals as ordinary income. This is correct for traditional 401(k) but the model has no Roth withdrawal type (which would be 0%). Adding a Roth account type would require a new `tax_class` value (e.g., `"roth"`) with a 0% rate, or exclusion from taxable income calculation.

**[[simulation-engine]]:** The model triggers withdrawals at `retirement_age` at a flat 4% rate. It has no RMD schedule — RMDs at age 73 are a legal requirement with a specific IRS formula (account balance ÷ life expectancy factor), not a flat rate. For high-balance 401(k) accounts, modeled withdrawals may significantly understate or overstate actual required distributions.

**[[configuration]]:** The eight configured assets include no Roth account. All equity assets are either traditional 401(k) or taxable brokerage. Adding Roth modeling would require new asset files with a Roth-appropriate tax treatment.

---

[^1]: `raw/fidelity_401k_v_roth.txt` p.2 — "According to the SECURE 2.0 Act's higher earner rule, in 2026, catch-up contributions for earners whose FICA wages...exceed $150,000 in the previous tax year, must be designated as Roth after-tax contributions."
[^2]: `raw/fidelity_401k_v_roth.txt` p.2 — "The annual contribution limit for a 401(k) is much higher than what you can contribute to a Roth IRA" and "a Roth IRA has an income cap, making some higher earners ineligible to contribute."
[^3]: `raw/fidelity_401k_v_roth.txt` p.3 — "prioritizing contributions to your 401(k) to capture the full employer match...Once you're getting the maximum employer match, you could contribute to a Roth IRA to benefit from tax-free withdrawals in retirement."
[^4]: `raw/fidelity_401k_v_roth.txt` p.1 — "Contributions to traditional 401(k)s are usually made before paying taxes...you pay income taxes on withdrawals in retirement, but the money grows tax-deferred"
[^5]: `raw/fidelity_401k_v_roth.txt` p.1 — "A Roth IRA allows eligible contributors to invest money they've already paid taxes on...withdrawals of earnings are tax-free after age 59½ and once the Roth IRA 5-year rule has been met"
[^6]: `raw/fidelity_401k_v_roth.txt` p.2 — "In 2026, you can contribute up to $24,500 pre-tax or Roth to your 401(k)...catch-up contribution of $8,000 (or $11,250 if age 60–63)"
[^7]: `raw/fidelity_401k_v_roth.txt` p.1 — "The annual contribution limit for IRAs...is $7,500 for 2026. If you're age 50 or older, you can contribute an additional $1,100 for 2026." and income limits at p.2.
[^8]: `raw/fidelity_401k_v_roth.txt` p.2 — "catch-up contributions for earners whose FICA wages...exceed $150,000 in the previous tax year, must be designated as Roth after-tax contributions"
