# Retirement Financial Model

This application simulates retirement financial scenarios by modeling various assets, incomes, and expenses over time. It helps users analyze net worth, cash flows, and investment strategies throughout retirement planning.

## Usage

1. **Configuration**  
   - The main configuration file (`./configuration/config.json`) contains personal and scenario parameters (birth dates, retirement age, start/end dates, tax rates, etc.).
   - Asset configuration files (e.g., `./configuration/assets/*.json`) define individual assets such as employment income, social security, real estate, and equities.

2. **Asset JSON Inputs**  
   Each asset JSON file should specify:
   - `name`: Asset name (e.g., "401k Stocks", "Primary Residence")
   - `start_date` / `end_date`: Keys referencing scenario dates (e.g., "first_date", "retirement", "end_date")
   - `retirement_age`: Key referencing retirement age
   - Asset-specific fields:
     - **SalaryIncome**: `salary`, `growth_rate`, `tax_class`
     - **REAsset**: `initial_value`, `debt`, `growth_rate`, `operating_expense`, `tax_class`
     - **Equity**: `value`, `growth_rate`, `tax_class`
     - **SocSec**: `income`, `retirement_age_based_benefit`, `tax_class`
   - See example files in `./configuration/assets/` for templates.

3. **Algorithm Overview (`run_model` method)**  
   - Initializes scenario dates and asset parameters.
   - Iterates monthly from start to end date:
     - Updates each asset for the current period.
     - Aggregates asset snapshots.
     - Calculates retirement withdrawals, net worth, debt, taxable income, operating expenses, taxes, free cash flows, and investments.
     - Allocates investments across assets according to user-defined strategies.
   - Returns detailed time-series data for analysis and visualization.

## Output

- Generates time-series data for each asset and overall scenario.
- Provides Pandas DataFrames for further analysis.
- Includes plotting utilities for visualizing asset performance and scenario outcomes.

## Requirements

- Python 3.x
- pandas
- matplotlib

## Running Tests

Unit tests are provided in `poetry run pytest tests` to validate asset logic and scenario calculations.

## License

MIT License
```