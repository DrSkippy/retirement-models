---
title: Social Security Benefit Calculation
tags: [concept, social-security, retirement-income]
sources: [thrivent-social-security]
updated: 2026-06-14
---

# Social Security Benefit Calculation

## Overview

SS retirement benefits are derived from lifetime earnings through a two-step formula: earnings history → AIME → PIA. The PIA is the monthly benefit at Full Retirement Age; actual payments scale up or down based on claiming age.

## Step 1: Average Indexed Monthly Earnings (AIME)

The SSA takes the worker's **35 highest-earning years**, adjusts for wage inflation, sums them, and divides by the total months worked to produce a monthly average.[^1]

Workers with fewer than 35 years of covered employment have zero-earning years averaged in, reducing AIME.

## Step 2: Primary Insurance Amount (PIA) — Bend Points Formula

A progressive formula converts AIME to PIA (2026 bend points):[^2]

| AIME range | Rate |
|---|---|
| First $1,286/month | 90% |
| $1,286 – $7,749/month | 32% |
| Above $7,749/month | 15% |

The formula is deliberately progressive — lower earners replace a higher fraction of their pre-retirement income than high earners.

## Step 3: Claiming-Age Adjustments

PIA is paid in full at Full Retirement Age (FRA). Claiming early permanently reduces the monthly benefit; delaying increases it.[^3]

| Claiming age | % of PIA | Example ($2,000 PIA) |
|---|---|---|
| 62 | 70% | $1,400 |
| 63 | 75% | $1,500 |
| 64 | 80% | $1,600 |
| 65 | 86.7% | $1,734 |
| 66 | 93.3% | $1,866 |
| **67 (FRA)** | **100%** | **$2,000** |
| 68 | 108% | $2,160 |
| 69 | 116% | $2,320 |
| 70 | 124% | $2,480 |

FRA for workers born in 1960 or later is age 67. Delayed credits stop accruing at 70.

## Full Retirement Age by Birth Year

| Birth year | FRA |
|---|---|
| 1954 or earlier | 66 |
| 1955 | 66 + 2 months |
| 1956 | 66 + 4 months |
| 1957 | 66 + 6 months |
| 1958 | 66 + 8 months |
| 1959 | 66 + 10 months |
| **1960 or later** | **67** |

## COLA

Benefits increase annually by the Social Security COLA. In 2026, COLA is 2.8%.[^4] The model's `SocSec.json` uses 1.5% — see [[configuration]] for the discrepancy.

## Earnings Test (Pre-FRA)

Workers who claim SS before FRA and continue earning are subject to an earnings test: benefit reduced $1 for every $2 earned above $24,480 (2026). Once FRA is reached, there is no earnings limit.[^5] This test is not modeled in [[simulation-engine]].

## How the Model Approximates This

`SalaryIncome._setup()` in `models/assets.py` bypasses AIME/PIA entirely. It reads a pre-specified `retirement_age_based_benefit` dict from `SocSec.json` and selects the benefit for the configured `retirement_age`. This is a reasonable approximation for a known individual (benefits are known from an SSA statement) but is not generalizable and does not model the earnings test or survivor reductions.

## Appearances in Sources

- [[thrivent-social-security]] — full AIME/PIA/bend-points explanation, claiming age table, COLA

## Related

- [[social-security-taxation]] — how SS benefits are taxed
- [[asset-models]] — `SalaryIncome` implementation
- [[configuration]] — `SocSec.json` parameters (COLA discrepancy)

---

[^1]: `raw/trivent_social_security.txt` §"How Social Security retirement benefits are calculated" — "The SSA takes your highest-earning 35 years of work and divides it by the number of months you worked."
[^2]: `raw/trivent_social_security.txt` §"How Social Security retirement benefits are calculated" — "90% of the first $1,286 of your AIME / 32% of AIME between $1,286 and $7,749 / 15% of AIME over $7,749"
[^3]: `raw/trivent_social_security.txt` §"Claiming Social Security retirement benefits early or late" — full claiming age table
[^4]: `raw/trivent_social_security.txt` §"Cost of living adjustments" — "In 2026, Social Security benefits will rise by 2.8%"
[^5]: `raw/trivent_social_security.txt` §"You're working while on Social Security" — "$1 for every $2 you earn beyond the annual limit of $24,480"
