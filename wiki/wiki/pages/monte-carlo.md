---
title: Monte Carlo Simulation
tags: [models, monte-carlo, stochastic]
sources: [monte-carlo-py]
updated: 2026-06-14
---

# Monte Carlo Simulation

## Overview

`MonteCarloRunner` in `models/monte_carlo.py` runs N independent copies of the retirement model to quantify uncertainty in outcomes. Stochasticity comes from equity assets sampling historical or Gaussian returns each period.

## Key Design: State Isolation

Each run creates a **fresh `RetirementFinancialModel` instance** to prevent mutable asset state (accumulated portfolio values, mortgage balances, etc.) from leaking across runs.[^1] This is the critical correctness property.

## `MonteCarloRunner` Configuration

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config_file_path` | str | — | Path to world config JSON |
| `asset_config_path` | str | — | Path to assets directory |
| `n_runs` | int | 1000 | Number of simulation runs |
| `random_seed` | Optional[int] | None | Seed for reproducibility |
| `store_trajectories` | bool | False | Capture net_worth per period per run |

## Output Types

### `SimulationResult`

Per-run result dataclass:

| Field | Description |
|---|---|
| `run_id` | Zero-based run index |
| `terminal_net_worth` | Net worth at final period |
| `ruin_period` | First period index where net_worth < 0; `None` if solvent |
| `net_worth_trajectory` | List of net_worth values (only if `store_trajectories=True`) |

### `MonteCarloResults`

Aggregated results:

| Method | Description |
|---|---|
| `ruin_probability()` | Fraction of runs where `ruin_period is not None` |
| `terminal_wealth_percentiles(percentiles)` | Dict of percentile → terminal net worth |
| `trajectory_array()` | List of per-run net worth trajectories (if stored) |
| `has_trajectories()` | Whether trajectory data was captured |

`terminal_wealth_percentiles([10, 25, 50, 75, 90])` is the primary summary statistic used for fan charts.[^2]

## Stochasticity Sources

Equity assets drive all variance:
- If `sampled_monthly_sp500_returns` CSV is configured: each period samples a random historical monthly return from the dataset.
- Otherwise: each period samples from `N(appreciation_rate / 12, appreciation_rate_volatility)`.

Real estate has optional `appreciation_rate_volatility` but defaults to 0 (deterministic).

## CLI Usage

```bash
poetry run python bin/runner.py --monte-carlo 1000
poetry run python bin/runner.py --monte-carlo 500 --save-db --label "mc-baseline"
```

Progress bar (tqdm) shows live ruin count and latest terminal wealth.

## Programmatic Usage

```python
runner = MonteCarloRunner(
    config_file_path="./configuration/config.json",
    asset_config_path="./configuration/assets",
    n_runs=500,
    random_seed=42,
    store_trajectories=True,
)
results = runner.run()
print(f"Ruin probability: {results.ruin_probability():.1%}")
print(results.terminal_wealth_percentiles([10, 25, 50, 75, 90]))
```

## Related

- [[asset-models]] — stochastic appreciation in `Equity._asset_appreciation()`
- [[simulation-engine]] — what each MC run executes
- [[simulation-flow]] — full end-to-end pseudocode for a single run
- [[rest-api]] — MC results served via `/api/mc` endpoints
- [[frontend]] — fan chart and ruin gauge visualization

---

[^1]: `models/monte_carlo.py` `MonteCarloRunner.run()` line ~126 — "Fresh model instance per run — essential for state isolation"
[^2]: `models/monte_carlo.py` `MonteCarloResults.terminal_wealth_percentiles()` — sorts terminal values and indexes by percentile fraction
