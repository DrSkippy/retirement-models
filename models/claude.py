from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class RetirementFinancialModel:

    FMT = "%Y-%m-%d"
    FINAL_AGE = 90

    def __init__(self, filename=None):
        if not filename:
            print("No configuration file provided, using default values.")
            return
        else:
            with open(filename, "r") as rdr:
                self.__dict__ = json.loads(rdr.read())

        self.today_date = datetime.now()
        self.current_age = self.today_date - datetime.strptime(self.birth_date, self.FMT)
        self.spouse_current_age = self.today_date - datetime.strptime(self.spouse_birth_date, self.FMT)
        self.end_date = self.today_date + timedelta(days=(self.FINAL_AGE - self.current_age.days))



    def calculate_quarterly_taxes(self, income_sources, property_value, age):
        """Calculate quarterly taxes on various income sources"""
        quarterly_taxes = {}

        # Income taxes (federal + state)
        salary_income = income_sources.get('salary', 0)
        portfolio_income = income_sources.get('portfolio_withdrawal', 0)
        rental_income = income_sources.get('rental_net', 0)
        social_security = income_sources.get('social_security', 0)

        # Taxable income (85% of SS is taxable for high earners)
        taxable_income = salary_income + portfolio_income + rental_income + (social_security * 0.85)

        # Federal and state income taxes
        quarterly_income_tax = (taxable_income * (self.federal_income_tax_rate + self.state_income_tax_rate)) / 4

        # Payroll taxes (only on salary)
        quarterly_payroll_tax = (salary_income * self.ss_tax_rate_combined) / 4 if age < self.retirement_age else 0

        # Property taxes
        quarterly_property_tax = (property_value * self.property_tax_rate) / 4

        quarterly_taxes = {
            'income_tax': quarterly_income_tax,
            'payroll_tax': quarterly_payroll_tax,
            'property_tax': quarterly_property_tax,
            'total_taxes': quarterly_income_tax + quarterly_payroll_tax + quarterly_property_tax
        }

        return quarterly_taxes

    def calculate_rental_income(self, rental_property_value, quarter):
        """Calculate net rental income after expenses"""
        gross_monthly = self.rental_monthly_income * (1 + self.inflation_rate) ** (quarter // 4)
        gross_quarterly = gross_monthly * 3

        # Expenses
        property_mgmt = gross_quarterly * self.property_mgmt_fee
        maintenance = gross_quarterly * 0.05  # 5% for maintenance/repairs
        insurance = rental_property_value * 0.003 / 4  # 0.3% annually for insurance

        net_rental = gross_quarterly - property_mgmt - maintenance - insurance
        return {
            'gross': gross_quarterly,
            'net': net_rental,
            'expenses': property_mgmt + maintenance + insurance
        }

    def run_model(self, scenarios=['base', 'delayed_ss']):
        """Run the financial model with different scenarios"""
        results = {}

        for scenario in scenarios:
            print(f"Running scenario: {scenario}")
            results[scenario] = self.simulate_retirement(scenario)

        return results

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
