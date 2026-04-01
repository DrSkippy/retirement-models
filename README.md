# Retirement Financial Model

A monthly time-step simulation of personal retirement finances. Models asset growth, income, expenses, taxes, savings, and portfolio withdrawals from a configurable start date through end-of-plan. Supports deterministic single runs, Monte Carlo analysis with stochastic equity returns, PostgreSQL persistence, a REST API, and a React web UI for browsing and comparing simulation runs.

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
    db.py                ← SQLAlchemy persistence layer (PostgreSQL)
    utils.py             ← Asset factory, date utilities, plotting helpers
    expenses.py          ← Expense tracking utilities
api/
    __init__.py          ← Flask app factory (create_app)
    blueprints/          ← runs, assets, tax, mc, config endpoints
migrations/
    001_initial_schema.sql ← PostgreSQL DDL
frontend/
    src/                 ← React + TypeScript + Recharts web UI
nginx/
    retirement.conf      ← Nginx reverse proxy config
bin/
    runner.py            ← CLI entry point (single run or Monte Carlo)
    mortgage_adjustements.py ← Standalone mortgage payoff calculator
workbooks/              ← Jupyter notebooks for exploration
tests/                  ← pytest suite
config.yaml             ← System paths and logging configuration
Dockerfile.api          ← Multi-stage API container
docker-compose.yml      ← Full-stack deployment (API + frontend + Nginx)
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

## Setup

### Install dependencies

```bash
poetry install
```

### System configuration

`config.yaml` controls paths and logging for `runner.py`:

```yaml
paths:
  model_config: ./configuration/config.json
  assets_dir: ./configuration/assets
  output_dir: ./output

logging:
  level: DEBUG
  file: ./log/assets.log
  max_bytes: 2500000
  backup_count: 3
  format: "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
```

---

## Usage

### World Configuration

Edit `configuration/config.json`:

```json
{
  "birth_date": "1966-03-14",
  "spouse_birth_date": "1969-08-07",
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

Runs 1000 independent simulations and writes a fan-chart PDF to `./output/`. Progress and live ruin count are shown via `tqdm`.

Output includes:
- **Ruin probability**: fraction of runs where net worth goes negative
- **Terminal wealth percentiles**: P10, P25, P50, P75, P90
- **Fan chart**: shaded percentile bands of net worth trajectories over time

### Saving Runs to the Database

Add `--save-db` to persist any run to PostgreSQL. Requires the `DB_*` environment variables to be set (see [Database Setup](#database-setup)).

```bash
# Single run
poetry run python bin/runner.py --save-db --label "baseline" --tag v1

# Monte Carlo (trajectories are captured automatically for percentile bands)
poetry run python bin/runner.py --monte-carlo 500 --save-db --label "mc-baseline" --tag v1

# Repeatable with multiple tags
poetry run python bin/runner.py --monte-carlo 1000 --save-db \
    --label "early-retirement" --tag v2 --tag scenario-test \
    --notes "Testing retirement at 62 instead of 67"
```

| Flag | Description |
|------|-------------|
| `--save-db` | Persist output to PostgreSQL |
| `--label TEXT` | Human-readable name for the run |
| `--tag TAG` | Tag (repeatable) |
| `--notes TEXT` | Free-text notes stored with the run |

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

```bash
poetry run python bin/mortgage_adjustements.py \
    --current_balance 303318.79 \
    --monthly_payment 1405.25 \
    --annual_rate 0.02875 \
    --lump_sum 50000 \
    --target_date 2035-09-01
```

---

## Database Setup

PostgreSQL at `192.168.1.91:5434`, database `retirement-models`.

### 1. Apply the schema

```bash
psql -h 192.168.1.91 -p 5434 -U scott -d retirement-models \
     -f migrations/001_initial_schema.sql
```

### 2. Configure credentials

```bash
cp .envrc.example .envrc
# edit .envrc and set DB_PASSWORD
direnv allow
```

The `.envrc` exports:

```bash
export DB_HOST=192.168.1.91
export DB_PORT=5434
export DB_NAME=retirement-models
export DB_USER=scott
export DB_PASSWORD=your_password
```

These are picked up by `models/db.py` via `pydantic-settings` (`DB_HOST` → field `host`, etc.).

---

## REST API

The Flask API serves simulation data to the React frontend (and any other client).

### Running locally (Python)

```bash
poetry run flask --app "api:create_app()" run --port 8000
```

### Running locally (Docker)

```bash
docker build -f Dockerfile.api -t retirement-api .

docker run --rm -p 8000:8000 \
  -e DB_HOST=192.168.1.91 \
  -e DB_PORT=5434 \
  -e DB_NAME=retirement-models \
  -e DB_USER=scott \
  -e DB_PASSWORD=your_password \
  retirement-api
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/runs` | List simulation runs (`?tag=`, `?limit=`, `?offset=`) |
| GET | `/api/runs/<id>` | Run summary + full scenario time-series |
| GET | `/api/runs/<id>/assets` | Per-asset time-series (`?asset=` to filter) |
| GET | `/api/runs/<id>/tax` | Tax breakdown per period |
| GET | `/api/mc` | List Monte Carlo run sets |
| GET | `/api/mc/<id>` | MC detail with percentile bands (`?include_runs=true` for individual results) |
| GET | `/api/config/<id>` | Configuration snapshot for a run |

---

## Web UI (React Frontend)

### Running locally (development)

Requires Node 22+. The Vite dev server proxies `/api` to `localhost:8000`.

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
```

### Building for production

```bash
cd frontend
npm run build     # outputs to frontend/dist/
```

### Pages

| Path | Description |
|------|-------------|
| `/runs` | Sortable, filterable table of all simulation runs |
| `/runs/:id` | Full detail view: net worth, cash flow, tax analysis charts |
| `/mc` | List of Monte Carlo run sets with ruin probability summary |
| `/mc/:id` | Fan chart (P10–P90 bands), ruin gauge, terminal wealth distribution |
| `/compare?ids=1,2,3` | Side-by-side net worth chart comparison across runs |

---

## Full-Stack Deployment (Docker Compose)

Deploys three containers behind Nginx: the Flask API (Gunicorn), the React frontend (Nginx static), and the reverse proxy.

### Build and start

```bash
docker compose up --build
```

The stack listens on port `8080`. Set `DB_*` environment variables before running (direnv loads them from `.envrc` automatically):

```bash
# With direnv active:
docker compose up --build

# Or pass explicitly:
DB_HOST=192.168.1.91 DB_PORT=5434 DB_NAME=retirement-models \
DB_USER=scott DB_PASSWORD=your_password \
docker compose up --build
```

### Verify deployment

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/runs | jq '.[0]'
```

Browse to `http://localhost:8080` for the React UI.

### Nginx routing

| Path | Routed to |
|------|-----------|
| `/api/*` | Flask/Gunicorn (`api:8000`) |
| `/health` | Flask/Gunicorn (`api:8000`) |
| `/` | React SPA (`frontend:80`) |

External access is provided via Cloudflare Tunnel — no ports are exposed directly to the internet.

---

## Output

| File | Contents |
|---|---|
| `output/single_run_report.pdf` | 3-page PDF: executive summary, portfolio composition, per-asset detail |
| `output/monte_carlo_report.pdf` | 2-page PDF: fan chart with percentile bands, terminal wealth analysis |
| `output/tax_optimization_report.pdf` | 2-page PDF: tax overview, RMD deep dive |
| `output/single_run_summary.csv` | Full scenario DataFrame as CSV |
| `output/metrics/net_worth_*.csv` | Net worth time series (legacy, one file per run) |
| `log/assets.log` | Rotating debug log (3 × 2.5 MB files) |

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
| `matplotlib` | Charting and PDF reports |
| `pydantic` / `pydantic-settings` | Config validation and environment variable loading |
| `numpy` | Stochastic return sampling and percentile computation |
| `sqlalchemy` + `psycopg2-binary` | PostgreSQL persistence |
| `flask` + `gunicorn` | REST API and production WSGI server |
| `tqdm` | Progress bars |
| `pyyaml` | System config loading |
| `notebook` | Jupyter workbooks |

---

## License

MIT
