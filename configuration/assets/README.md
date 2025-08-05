## Readme


# Configuration Assets

This directory contains configuration files and assets used by the application. These files are essential for setting up the application environment and ensuring it runs smoothly.   

Rules:
1. All configuration files should be in JSON format.
2. Each configuration file should have a descriptive name that indicates its purpose.
3. Include these keys:
  - `name`: The name of the asset
  - `description`: A brief description of what the configuration file is for.
  - `type`: The type of asset (Equity, RE, Salary, ) 
  - `start_date`: The start date of the asset in ISO format (YYYY-MM-DD).
  - `end_date`: The end date of the asset in ISO format (YYYY-MM-DD)
  - `tax_class`: The tax class applicable to the asset (e.g., "income", "capital_gain", "social_security").
4. Don't Include these (set them in _setup function):
  - `value`
  - `debt`
  - `expenses`
  - `expense_rate`