import json

import matplotlib.pyplot as plt
import pandas as pd

from models.assets import *
from models.utils import *


class RetirementFinancialModel:
    FMT = "%Y-%m-%d"
    CONFIG_PATH = "./configuration/assets"

    def __init__(self, filename=None):
        if not filename:
            logging.error("No configuration file provided, using default values.")
            return
        else:
            with open(filename, "r") as rdr:
                self.__dict__ = json.loads(rdr.read())
            logging.info(f"Retirement model loaded from {filename}")

        self.today_date = datetime.now().date()
        logging.info(f"Today's date: {self.today_date}")
        self.birth_date = datetime.strptime(self.birth_date, self.FMT).date()
        self.spouse_birth_date = datetime.strptime(self.spouse_birth_date, self.FMT).date()
        self.current_age = (self.today_date - self.birth_date).days / 365.25
        self.spouse_current_age = (self.today_date - self.spouse_birth_date).days / 365.25
        logging.info(f"Current age: {self.current_age:.2f}, Spouse's age: {self.spouse_current_age:.2f}")

        self.start_date = datetime.strptime(self.start_date, self.FMT).date()
        self.end_date = datetime.strptime(self.end_date, self.FMT).date()
        logging.info(f"Start date: {self.start_date}, End date: {self.end_date}")

        self.retirement_date = self.birth_date + timedelta(days=self.retirement_age*365.25)
        logging.info(f"Retirement date: {self.retirement_date}")

    def setup(self, config_path=CONFIG_PATH):
        logging.info(f"Setting up retirement model with configuration from {config_path}")
        self.assets = create_assets(config_path)
        logging.info(f"Assets loaded: {[asset.name for asset in self.assets]}")
        for asset in self.assets:
            asset.set_scenario_dates({
                "first_date": self.start_date,
                "retirement": self.retirement_date,
                "end_date": self.end_date
            })
            logging.info(f"Asset {asset.name} scenario dates set: {asset.start_date} to {asset.end_date}")

        self.timeline = create_datetime_sequence(self.start_date, self.end_date)
        logging.info(f"Timeline (monthly) created from {self.start_date} to {self.end_date}")

    def run_model(self):
        """Run the financial model simulation"""
        mdata = []
        mheader = ["Period",
                   "Date",
                   "age",
                   "net_worth",
                   "monthly_income",
                   "taxes",
                   "free_cash_flows",
                   "investment",
                   "unallocated_cash"
                   ]
        adata = {a.name: [] for a in self.assets}
        for p, pdate in enumerate(self.timeline):
            age = (pdate - self.birth_date).days / 365.25
            for asset in self.assets:
                addl = asset.period_update(p, pdate)
                snapshot = asset.period_snapshot(p, pdate, addl=addl[1:])
                adata[asset.name].append(snapshot)
            # tax basis
            monthly_income = self.calculate_monthly_income()
            # 401k withdrawals
            withdraw_amount = 0.0
            if age >= self.retirement_age:
                withdraw_amount = self.withdrawal_rate * self.calculate_retirement_portfolio_value()/ 12.
                # decrement asset values by withdrawal
                self.invest_evenly(withdraw_amount * self.stock_allocation, "stock")
                self.invest_evenly(withdraw_amount * self.bond_allocation, "bond")
                monthly_income += withdraw_amount
            # Calculate taxes on total income
            taxes = self.calculate_monthly_taxes(withdraw_amount)
            # Calculate free cash flows after asset-specific taxes and expenses
            free_cash_flows = self.calculate_free_cash_flows() - taxes
            investment = 0.0
            if free_cash_flows > 0 and age < self.retirement_age:
                logging.info(f"Free cash flows: {free_cash_flows}, Taxes: {taxes}, Age: {age}")
                investment = self.savings_rate * free_cash_flows
                self.invest_evenly(investment * self.stock_allocation, "stock")
                self.invest_evenly(investment * self.bond_allocation,  "bond")
            unallocated_cash = free_cash_flows - taxes - investment
            net_worth = self.net_worth()
            mdata.append([p, pdate, age, net_worth, monthly_income, taxes, free_cash_flows, investment, unallocated_cash])
        aheader = self.assets[0].snapshot_header
        return mdata, mheader, adata, aheader

    def calculate_retirement_portfolio_value(self, name_match="401k"):
        """Calculate the total value of the retirement portfolio"""
        total_value = 0.0
        for asset in self.assets:
            if name_match in asset.name.lower():
                total_value += asset.value - asset.debt
        return total_value

    def invest_evenly(self, amount, name_match ):
        """Invest in stocks"""
        asset_list = []
        for asset in self.assets:
            if name_match in asset.name.lower():
                asset_list.append(asset)
        equally_distributed_amount = amount / len(asset_list) if asset_list else 0.0
        for asset in asset_list:
            if equally_distributed_amount > 0:
                asset.investment(equally_distributed_amount)
                logging.info(f"Invested ${equally_distributed_amount:.2f} in {asset.name}")


    def net_worth(self):
        total_net_worth = 0.0
        for asset in self.assets:
            total_net_worth += asset.value - asset.debt
        return total_net_worth


    def calculate_free_cash_flows(self):
        cash_flow = 0.0
        for asset in self.assets:
            cash_flow += asset.cash_flow()
        return cash_flow


    def calculate_monthly_income(self):
        monthly_income = 0
        for asset in self.assets:
            if asset.tax_class == "income":
                monthly_income += asset.income
        return monthly_income


    def calculate_monthly_taxes(self, withdraw_amount=0.0):
        income_classes = {"income": 0.0, "capital_gain": 0.0, "social_security": 0.0}
        for asset in self.assets:
            income_classes[asset.tax_class] += asset.income
        monthly_taxes = 0.0
        for tax_class in income_classes:
            monthly_taxes = income_classes[tax_class] * self.tax_classes[tax_class]
        monthly_taxes += withdraw_amount*self.tax_classes["income"]
        return monthly_taxes

    def get_asset_dataframe(self, asset_name, asset_model_dict, asset_model_header):
        """Get asset data as a DataFrame"""
        if asset_name in asset_model_dict:
            asset_data = asset_model_dict[asset_name]
            return pd.DataFrame(asset_data, columns=asset_model_header)
        logging.error(f"Asset {asset_name} not found in model data.")

    def plot_asset_model_data(self, df, name):
        """Plot asset model data"""
        if df.empty:
            logging.error("No data to plot.")
            return

        print(df)
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(3, 3, figsize=(20, 12))
        fig.suptitle('Retirement Financial Model - Comprehensive Analysis', fontsize=16, fontweight='bold')

        header_list = df.columns.tolist()[4:]  # Exclude 'Date' and 'Period' columns
        # plot indexes
        for i in range(2):
            for j in range(3):
                try:
                    column = header_list.pop()
                    axes[i, j].plot(df['Date'], df[column], label=column)
                    axes[i, j].set_title(f'{name} Asset Model Data Over Time')
                    axes[i, j].set_xlabel('Date')
                    axes[i, j].set_ylabel('Value')
                    axes[i, j].legend()
                    axes[i, j].grid()
                except IndexError:
                    break
        plt.show()

# REPLACED def calculate_quarterly_taxes(self, income_sources, property_value, age):
# REPLACED     """Calculate quarterly taxes on various income sources"""
# REPLACED     quarterly_taxes = {}
# REPLACED
# REPLACED     # Income taxes (federal + state)
# REPLACED     salary_income = income_sources.get('salary', 0)
# REPLACED     portfolio_income = income_sources.get('portfolio_withdrawal', 0)
# REPLACED     rental_income = income_sources.get('rental_net', 0)
# REPLACED     social_security = income_sources.get('social_security', 0)
# REPLACED
# REPLACED     # Taxable income (85% of SS is taxable for high earners)
# REPLACED     taxable_income = salary_income + portfolio_income + rental_income + (social_security * 0.85)
# REPLACED
# REPLACED     # Federal and state income taxes
# REPLACED     quarterly_income_tax = (taxable_income * (self.federal_income_tax_rate + self.state_income_tax_rate)) / 4
# REPLACED
# REPLACED     # Payroll taxes (only on salary)
# REPLACED     quarterly_payroll_tax = (salary_income * self.ss_tax_rate_combined) / 4 if age < self.retirement_age else 0
# REPLACED
# REPLACED     # Property taxes
# REPLACED     quarterly_property_tax = (property_value * self.property_tax_rate) / 4
# REPLACED
# REPLACED     quarterly_taxes = {
# REPLACED         'income_tax': quarterly_income_tax,
# REPLACED         'payroll_tax': quarterly_payroll_tax,
# REPLACED         'property_tax': quarterly_property_tax,
# REPLACED         'total_taxes': quarterly_income_tax + quarterly_payroll_tax + quarterly_property_tax
# REPLACED     }
# REPLACED
# REPLACED     return quarterly_taxes
# REPLACED

# REPLACED def calculate_rental_income(self, rental_property_value, quarter):
# REPLACED     """Calculate net rental income after expenses"""
# REPLACED     gross_monthly = self.rental_monthly_income * (1 + self.inflation_rate) ** (quarter // 4)
# REPLACED     gross_quarterly = gross_monthly * 3
# REPLACED
# REPLACED     # Expenses
# REPLACED     property_mgmt = gross_quarterly * self.property_mgmt_fee
# REPLACED     maintenance = gross_quarterly * 0.05  # 5% for maintenance/repairs
# REPLACED     insurance = rental_property_value * 0.003 / 4  # 0.3% annually for insurance
# REPLACED
# REPLACED     net_rental = gross_quarterly - property_mgmt - maintenance - insurance
# REPLACED     return {
# REPLACED         'gross': gross_quarterly,
# REPLACED         'net': net_rental,
# REPLACED         'expenses': property_mgmt + maintenance + insurance
# REPLACED     }
# REPLACED

# REPLACED def run_model(self, scenarios=['base', 'delayed_ss']):
# REPLACED     """Run the financial model with different scenarios"""
# REPLACED     results = {}
# REPLACED
# REPLACED     for scenario in scenarios:
# REPLACED         print(f"Running scenario: {scenario}")
# REPLACED         results[scenario] = self.simulate_retirement(scenario)
# REPLACED
# REPLACED     return results


def simulate_retirement(self, scenario='base'):
    """Simulate retirement with quarterly granularity"""
    data = []

    # Initial conditions
    #        portfolio_value = self.initial_portfolio
    #        property_value = self.rental_property_value + self.primary_property_value
    #        rental_property_value = self.rental_property_value
    #        rental_property_debt = self.rental_debt
    #        primary_property_value = self.primary_property_value
    #        primary_property_debt = self.primary_debt

    # Simulate quarterly from current age to age 85
    total_quarters = (85 - self.current_age) * 4

    for quarter in range(total_quarters):
        current_age = self.current_age + (quarter / 4)
        year = self.current_year + (quarter // 4)
        quarter_in_year = (quarter % 4) + 1

        # Determine if working or retired
        is_working = current_age < self.retirement_age
        is_retired = not is_working

        # Calculate income sources
        income_sources = {}

        # Salary income (only while working)
        if is_working:
            annual_salary = self.current_income * (1 + self.inflation_rate) ** (quarter // 4)
            income_sources['salary'] = annual_salary / 4

            # 401k contributions
            annual_contribution = min(annual_salary * self.savings_rate, self.annual_401k_limit)
            quarterly_contribution = annual_contribution / 4
            portfolio_value += quarterly_contribution
        else:
            income_sources['salary'] = 0

        # Social Security (starts at retirement age or delayed)
        if scenario == 'delayed_ss':
            ss_start_age = 70
            annual_ss = self.ss_delayed_benefit_70
        else:
            ss_start_age = self.retirement_age
            annual_ss = self.ss_full_benefit_67

        if current_age >= ss_start_age:
            income_sources['social_security'] = (annual_ss * (1 + self.inflation_rate) ** max(0, (
                    quarter // 4) - 2)) / 4
        else:
            income_sources['social_security'] = 0

        # Portfolio growth and withdrawals
        quarterly_return = (1 + self.portfolio_annual_return) ** 0.25 - 1
        portfolio_value *= (1 + quarterly_return)

        if is_retired:
            withdrawal_rate = self.withdrawal_rate_later if current_age >= 75 else self.withdrawal_rate_early
            quarterly_withdrawal = portfolio_value * (withdrawal_rate / 4)
            portfolio_value -= quarterly_withdrawal
            income_sources['portfolio_withdrawal'] = quarterly_withdrawal
        else:
            income_sources['portfolio_withdrawal'] = 0

        # TODO Make multiple separate real estate property models

        # Real estate
        property_quarterly_return = (1 + self.real_estate_appreciation) ** 0.25 - 1
        property_value *= (1 + property_quarterly_return)

        # Pay down rental property debt (assuming it's paid off in 1 year)
        if rental_property_debt > 0 and quarter < 4:  # Pay off in first year
            debt_payment = min(rental_property_debt, 3000)  # $1000/month payment
            rental_property_debt -= debt_payment

        # Pay down property debt (assuming it's paid off in 1 year)
        if primary_property_debt > 0 and quarter < 4:  # Pay off in first year
            debt_payment = min(primary_property_debt, 7000)  # $2300/month payment
            primary_property_debt -= debt_payment

        property_value = primary_property_value + rental_property_value
        property_debt = primary_property_debt + rental_property_debt
        # Rental income
        rental_data = self.calculate_rental_income(rental_property_value, quarter)
        income_sources['rental_net'] = rental_data['net']

        # Calculate taxes
        taxes = self.calculate_quarterly_taxes(income_sources, property_value, current_age)

        # Net income after taxes
        gross_income = sum(income_sources.values())
        net_income = gross_income - taxes['total_taxes']

        # Store results
        data.append({
            'quarter': quarter + 1,
            'year': year,
            'quarter_in_year': quarter_in_year,
            'age': round(current_age, 2),
            'is_working': is_working,
            'portfolio_value': portfolio_value,
            'property_value': property_value,
            'property_debt': property_debt,
            'total_net_worth': portfolio_value + property_value - property_debt,
            'salary_income': income_sources['salary'],
            'social_security': income_sources['social_security'],
            'portfolio_withdrawal': income_sources['portfolio_withdrawal'],
            'rental_net_income': income_sources['rental_net'],
            'gross_income': gross_income,
            'income_tax': taxes['income_tax'],
            'payroll_tax': taxes['payroll_tax'],
            'property_tax': taxes['property_tax'],
            'total_taxes': taxes['total_taxes'],
            'net_income': net_income,
            'scenario': scenario
        })

    return pd.DataFrame(data)


def generate_reports(self, results):
    """Generate comprehensive reports and visualizations"""

    # Combine all scenarios
    all_data = pd.concat([df for df in results.values()], ignore_index=True)

    # Create summary report
    print("=== RETIREMENT FINANCIAL MODEL SUMMARY ===\n")

    for scenario in results.keys():
        df = results[scenario]
        retirement_data = df[df['is_working'] == False]

        if len(retirement_data) > 0:
            first_retirement_year = retirement_data.iloc[0]
            age_75_data = df[df['age'] >= 75].iloc[0] if len(df[df['age'] >= 75]) > 0 else None

            print(f"SCENARIO: {scenario.upper()}")
            print(
                f"Portfolio at Retirement (Age {self.retirement_age}): ${first_retirement_year['portfolio_value']:,.0f}")
            print(f"First Year Retirement Net Income: ${first_retirement_year['net_income'] * 4:,.0f}")
            print(f"First Year Retirement Gross Income: ${first_retirement_year['gross_income'] * 4:,.0f}")
            print(f"First Year Total Taxes: ${first_retirement_year['total_taxes'] * 4:,.0f}")

            if age_75_data is not None:
                print(f"Net Worth at Age 75: ${age_75_data['total_net_worth']:,.0f}")

            print(f"Average Annual Net Income in Retirement: ${retirement_data['net_income'].mean() * 4:,.0f}")
            print("-" * 50)

    # Create visualizations
    self.create_visualizations(all_data)

    return all_data


def create_visualizations(self, data):
    """Create comprehensive visualizations"""
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle('Retirement Financial Model - Comprehensive Analysis', fontsize=16, fontweight='bold')

    # 1. Net Worth Over Time
    for scenario in data['scenario'].unique():
        scenario_data = data[data['scenario'] == scenario]
        axes[0, 0].plot(scenario_data['age'], scenario_data['total_net_worth'] / 1000000,
                        label=f'{scenario}', linewidth=2)
    axes[0, 0].set_title('Total Net Worth Over Time')
    axes[0, 0].set_xlabel('Age')
    axes[0, 0].set_ylabel('Net Worth ($ Millions)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # 2. Annual Net Income
    for scenario in data['scenario'].unique():
        scenario_data = data[data['scenario'] == scenario]
        annual_income = scenario_data.groupby('year')['net_income'].sum()
        axes[0, 1].plot(annual_income.index, annual_income / 1000,
                        label=f'{scenario}', linewidth=2)
    axes[0, 1].set_title('Annual Net Income After Taxes')
    axes[0, 1].set_xlabel('Year')
    axes[0, 1].set_ylabel('Net Income ($000s)')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # 3. Income Sources in Retirement (Base Scenario)
    base_data = data[data['scenario'] == 'base']
    retirement_data = base_data[base_data['is_working'] == False]
    if len(retirement_data) > 0:
        income_sources = retirement_data.groupby('year')[
            ['social_security', 'portfolio_withdrawal', 'rental_net_income']
        ].sum()

        axes[0, 2].stackplot(income_sources.index,
                             income_sources['social_security'] / 1000,
                             income_sources['portfolio_withdrawal'] / 1000,
                             income_sources['rental_net_income'] / 1000,
                             labels=['Social Security', 'Portfolio', 'Rental'],
                             alpha=0.8)
        axes[0, 2].set_title('Annual Income Sources in Retirement (Base)')
        axes[0, 2].set_xlabel('Year')
        axes[0, 2].set_ylabel('Income ($000s)')
        axes[0, 2].legend(loc='upper right')
        axes[0, 2].grid(True, alpha=0.3)

    # 4. Tax Burden Over Time
    for scenario in data['scenario'].unique():
        scenario_data = data[data['scenario'] == scenario]
        annual_taxes = scenario_data.groupby('year')['total_taxes'].sum()
        axes[1, 0].plot(annual_taxes.index, annual_taxes / 1000,
                        label=f'{scenario}', linewidth=2)
    axes[1, 0].set_title('Annual Tax Burden')
    axes[1, 0].set_xlabel('Year')
    axes[1, 0].set_ylabel('Total Taxes ($000s)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # 5. Portfolio Value vs Real Estate
    base_data = data[data['scenario'] == 'base']
    axes[1, 1].plot(base_data['age'], base_data['portfolio_value'] / 1000000,
                    label='Portfolio', linewidth=2)
    axes[1, 1].plot(base_data['age'], base_data['property_value'] / 1000000,
                    label='Real Estate', linewidth=2)
    axes[1, 1].set_title('Asset Values Over Time (Base Scenario)')
    axes[1, 1].set_xlabel('Age')
    axes[1, 1].set_ylabel('Value ($ Millions)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    # 6. Quarterly Cash Flow in First 5 Years of Retirement
    retirement_data = data[(data['is_working'] == False) & (data['age'] <= 72)]
    if len(retirement_data) > 0:
        cash_flow_data = retirement_data.groupby(['scenario', 'quarter'])[
            ['gross_income', 'total_taxes', 'net_income']
        ].mean()

        for scenario in retirement_data['scenario'].unique():
            scenario_cash = cash_flow_data.loc[scenario]
            quarters = range(len(scenario_cash))
            axes[1, 2].plot(quarters, scenario_cash['net_income'] / 1000,
                            label=f'{scenario} - Net', linewidth=2)
            axes[1, 2].plot(quarters, scenario_cash['gross_income'] / 1000,
                            label=f'{scenario} - Gross', linewidth=1, linestyle='--', alpha=0.7)

    axes[1, 2].set_title('Quarterly Cash Flow (First 5 Years of Retirement)')
    axes[1, 2].set_xlabel('Quarter')
    axes[1, 2].set_ylabel('Income ($000s)')
    axes[1, 2].legend()
    axes[1, 2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    # Additional detailed table for key years
    self.create_summary_table(data)


def create_summary_table(self, data):
    """Create a detailed summary table for key retirement years"""
    print("\n=== DETAILED QUARTERLY BREAKDOWN (First 3 Years of Retirement) ===\n")

    # Filter for first 3 years of retirement for base scenario
    base_retirement = data[(data['scenario'] == 'base') &
                           (data['is_working'] == False) &
                           (data['age'] <= 70)]

    if len(base_retirement) > 0:
        summary_cols = ['year', 'quarter_in_year', 'age', 'gross_income', 'total_taxes',
                        'net_income', 'portfolio_value', 'total_net_worth']

        summary_table = base_retirement[summary_cols].copy()

        # Format for display
        for col in ['gross_income', 'total_taxes', 'net_income', 'portfolio_value', 'total_net_worth']:
            summary_table[col] = summary_table[col].apply(lambda x: f"${x:,.0f}")

        summary_table['age'] = summary_table['age'].apply(lambda x: f"{x:.1f}")

        print(summary_table.to_string(index=False))
