# Retirement Financial Model

A monthly time-step simulation of personal retirement finances. Models asset growth, income, expenses, taxes, savings, and portfolio withdrawals from a configurable start date through end-of-plan. Supports both deterministic single runs and Monte Carlo analysis with stochastic equity returns.

## Design

### Architecture

```
configuration/
    config.json          ← world-level parameters
    assets/              ← one JSON file per asset
models/
    config.py            ← Pydantic config models (WorldConfig, asset configs)
    assets.py            ← Asset base class + REAsset, Equity, SalaryIncome
    scenarios.py         ← RetirementFinancialModel: orchestrates the simulation
    monte_carlo.py       ← MonteCarloRunner, MonteCarloResults, SimulationResult
    taxes.py             ← TaxCalculator, TaxableIncomeBreakdown
    reporting.py         ← ReportBuilder: PDF charts and Monte Carlo fan plots
    utils.py             ← Asset factory, date utilities, plotting helpers
    expenses.py          ← Expense tracking utilities
bin/
    runner.py            ← CLI entry point (single run or Monte Carlo)
    mortgage_adjustements.py ← Standalone mortgage payoff calculator
workbooks/              ← Jupyter notebooks for exploration
tests/                  ← pytest suite
```

### Simulation Loop

`RetirementFinancialModel.run_model()` steps monthly from `start_date` to `end_date`:

1. Each asset's `period_update()` is called, advancing its internal state (appreciation, income, debt service).
2. Scenario-level aggregates are computed: net worth, taxable income, operating expenses, taxes.
3. **Pre-retirement**: free cash flows × `savings_rate` are invested evenly across 401k stock/bond assets per the configured allocation.
4. **Post-retirement**: a 4% (configurable) annual withdrawal is drawn from the retirement portfolio and split across stock/bond assets, then added to taxable income.
5. All per-asset and scenario-level values are recorded as rows for downstream DataFrames.

### Asset Types

| Type | Class | Key Fields |
|---|---|---|
| `Equity` | Stocks, bonds, brokerage accounts | `initial_value`, `appreciation_rate`, `appreciation_rate_volatility`, `dividend_rate` |
| `RealEstate` | Primary residence, rental properties | `initial_value`, `initial_debt`, `appreciation_rate`, `interest_rate`, `payment`, `monthly_rental_income` |
| `Salary` | Employment income, Social Security | `salary` or `retirement_age_based_benefit` table, `cola` |

**Equity stochasticity**: If `sampled_monthly_sp500_returns` points to a CSV of historical monthly returns, each period randomly samples from that dataset (used for Monte Carlo). Otherwise, appreciation is drawn from `N(appreciation_rate, appreciation_rate_volatility)` if volatility > 0, or applied deterministically.

**Social Security**: A `Salary` asset with a `retirement_age_based_benefit` dict keyed by claiming age. The benefit is selected at runtime based on `retirement_age` from world config.

### Tax Model

Three income classes, each with a flat rate defined in `config.json`:

| Class | Applies to |
|---|---|
| `income` | Salary, 401k withdrawals, rental income |
| `capital_gain` | Equity capital gains |
| `social_security` | Social Security income |

`TaxCalculator` aggregates asset income by tax class each period and returns a monthly liability.

### Configuration Validation

All config objects are Pydantic `BaseModel` subclasses (`WorldConfig`, `TaxConfig`, `AllocationConfig`, `EquityConfig`, `RealEstateConfig`, `SalaryConfig`). Validation errors surface at load time with field-level messages. `AllocationConfig` enforces that `stock_allocation + bond_allocation == 1.0`.

---

## Usage

### Setup

```bash
poetry install
```

### World Configuration

Edit `configuration/config.json`:

```json
{
  "birth_date": "1966-05-25",
  "spouse_birth_date": "1969-05-22",
  "retirement_age": 67,
  "savings_rate": 0.20,
  "inflation_rate": 0.025,
  "withdrawal_rate": 0.04,
  "stock_allocation": 0.6,
  "bond_allocation": 0.4,
  "tax_classes": {
    "income": 0.37,
    "capital_gain": 0.20,
    "social_security": 0.153
  },
  "start_date": "2025-06-01",
  "end_date": "2056-05-25"
}
```

### Asset Configuration

Each file in `configuration/assets/` defines one asset. The `start_date` / `end_date` fields accept either an ISO date string or a scenario placeholder:

| Placeholder | Resolves to |
|---|---|
| `"first_date"` | `start_date` from world config |
| `"retirement"` | Computed retirement date (`birth_date + retirement_age`) |
| `"end_date"` | `end_date` from world config |

**Equity example** (`401k_stock.json`):
```json
{
  "name": "401k Stocks",
  "type": "Equity",
  "initial_value": 1239553,
  "initial_expense_rate": 0.0005,
  "appreciation_rate": 0.06,
  "appreciation_rate_volatility": 0.02,
  "dividend_rate": 0.002,
  "sampled_monthly_sp500_returns": "../sp500-historical-portfolio-returns/out_data/monthly_returns.csv",
  "start_date": "first_date",
  "end_date": "end_date",
  "tax_class": "income"
}
```

**Real estate example** (`primary_residence.json`):
```json
{
  "name": "Primary Residence",
  "type": "RealEstate",
  "initial_value": 950000,
  "initial_debt": 304145.36,
  "appreciation_rate": 0.015,
  "property_tax_rate": 0.0058576,
  "insurance_cost": 2165.77,
  "interest_rate": 0.028813,
  "payment": 1405.25,
  "monthly_rental_income": 0,
  "management_fee_rate": 0,
  "rental_expense_rate": 0,
  "start_date": "first_date",
  "end_date": "end_date",
  "tax_class": "income"
}
```

**Social Security example** (`SocSec.json`):
```json
{
  "name": "Social Security Income",
  "type": "Salary",
  "retirement_age_based_benefit": {
    "62": 2831.0,
    "67": 4018.0,
    "70": 5108.0
  },
  "retirement_age": "retirement_age",
  "cola": 0.015,
  "start_date": "retirement",
  "end_date": "end_date",
  "tax_class": "social_security"
}
```

### Single Deterministic Run

```bash
poetry run python bin/runner.py
```

Produces a net worth trajectory chart in `./output/` and saves a `net_worth` metrics CSV under `./output/metrics/`.

To also generate per-asset plots:

```bash
poetry run python bin/runner.py --asset-details
```

### Monte Carlo Simulation

```bash
poetry run python bin/runner.py --monte-carlo 1000
```

Runs 1000 independent simulations (each with a fresh model instance) and writes a fan-chart PDF to `./output/`. Progress and live ruin count are shown via `tqdm`.

Output includes:
- **Ruin probability**: fraction of runs where net worth goes negative
- **Terminal wealth percentiles**: P10, P25, P50, P75, P90
- **Fan chart**: shaded percentile bands of net worth trajectories over time

### Programmatic Usage

```python
from models.scenarios import RetirementFinancialModel
from models.monte_carlo import MonteCarloRunner

# Single run
model = RetirementFinancialModel("./configuration/config.json")
model.setup("./configuration/assets")
mdata, mheader, adata, aheader = model.run_model(show_progress=True)

scenario_df = model.get_scenario_dataframe(mdata, mheader)
asset_df = model.get_asset_dataframe("401k Stocks", adata, aheader)

# Monte Carlo
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

### Mortgage Payoff Calculator

Standalone tool for analyzing extra principal payments or lump-sum payoffs:

```bash
poetry run python bin/mortgage_adjustements.py \
    --current_balance 303318.79 \
    --monthly_payment 1405.25 \
    --annual_rate 0.02875 \
    --lump_sum 50000 \
    --target_date 2035-09-01
```

Prints a summary table and full amortization schedule.

---

## Output

| File | Contents |
|---|---|
| `output/retirement_model_*.pdf` | Single-run charts (net worth, income, expenses, taxes) |
| `output/monte_carlo_*.pdf` | Fan chart with percentile bands and ruin probability |
| `output/metrics/net_worth_*.csv` | Net worth time series (single run) |
| `assets.log` | Rotating debug log (3 × 2.5 MB files) |

---

## Tests

```bash
poetry run pytest --cov=models --cov-report=term-missing tests/
```

Test modules cover: `assets`, `config`, `expenses`, `monte_carlo`, `reporting`, `scenarios`, `taxes`, `utils`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `pandas` | DataFrames for simulation output |
| `matplotlib` / `seaborn` | Charting and PDF reports |
| `pydantic` | Config validation |
| `numpy` | Stochastic return sampling |
| `tqdm` | Progress bars |
| `notebook` | Jupyter workbooks |

---

## License

MIT
