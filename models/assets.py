import json
import logging
import csv

from datetime import datetime

import numpy as np

FMT = "%Y-%m-%d"
DAYS_IN_YEAR = 365.25
MONTHS_IN_YEAR = 12


class Asset:

    def __init__(self, filename):
        """
        Initialize the asset object by loading its properties from a JSON file.

        The initializer reads the provided JSON file, parses its contents, and
        updates the object's dictionary with the values. After loading, a setup
        method ensures additional processing is completed

        Required fields in the JSON file or after _setup()
         - name
         - description
         - type # e.g., RE, Equity, Salary
         - start_date
         - end_date
         - initial_value
         - initial_debt
         - tax_class

        Parameters:
        filename: str
            The path to the JSON file that contains the asset data.
        """
        logging.debug(f" *** Initializing asset from {filename} ***")
        with open(filename, "r") as reader:
            self.__dict__.update(json.load(reader))
        self.initialize_asset_metrics()  # Ensure all financial attributes are initialized
        self._initialize_derived_metrics_functions()
        for key in ['start_date', 'end_date', 'retirement_date']:
            # Attempt to parse date strings into datetime.date objects
            if key in self.__dict__:
                try:
                    self.__dict__[key] = datetime.strptime(self.__dict__[key], FMT).date()
                    logging.info(f"Parsed date for {key} in {filename}: {e}")
                except ValueError as e:
                    logging.info(f"Did not parse date for {key} in {filename}: {e}")
        self.setup_run = False
        logging.debug(f"Initial values of required values: {str(self)}")

    def _initialize_derived_metrics_functions(self):
        self.metrics_functions = {
            "appreciation": self._asset_appreciation,
            "cash_flow": self.cash_flow,
            "operating_expense": self.operating_expense,
            "taxable_income": self.taxable_income
        }

    def initialize_asset_metrics(self):
        """
        Sets the asset's value, income, expenses, and debt to zero.

        This method is used to reset the financial state of the asset when
        necessary, such as when the asset is not applicable for a given period.
        It ensures that all financial attributes are set to zero, effectively
        clearing any previous values.

        """
        self.value = 0  # Asset value at period n
        self.debt = 0  # Asset debt at period n, impact on net value
        self.income = 0  # Taxable income from this asset at period n, impact on cash flow
        self.expenses = 0  # Fixed expenses for this asset at period n, impact on cash flow, not value
        self.growth_rate = 0  # Asset appreciation rate at period n, impact on value, not cash flow
        self.growth_rate_volatility = 0  # Asset appreciation rate at period n, impact on value, not cash flow
        self.expense_rate = 0  # Asset expense rate at period n, imppact on cash flow, not value

    def _setup(self):
        """
        Sets up initial configurations or state for the object.

        This method is internally used for setup purposes and should not be accessed
        directly by external code. All necessary configurations and preparations
        required for the object to function as intended can be managed using this
        method.

        """
        pass

    def update_value_with_investment(self, incremental_investment):
        """
        Invests a specified amount into the equity asset.

        This method updates the value of the equity asset by adding the specified
        investment amount to its current value.

        Parameters:
            incremental_investment (float): The amount to invest in the equity asset.
        """
        if self.value + incremental_investment < 0:
            incremental_investment = -self.value
            self.value = 0.0
            logging.warning(f"Investment amount is negative and exceeds current value of {self.name}")
        else:
            self.value += incremental_investment
        logging.info(f"Invested ${incremental_investment:,.2f} into {self.name}. New value: ${self.value:,.2f}")
        return incremental_investment  # return actual investment made

    def _period_update_finalize_metrics(self, period, period_date=None):
        """
        Represents a private or internal method used for execution of a specific
        step in the internal logic or algorithm. This method is not intended for
        public use and should only be called internally within the class or
        module.

        This method does not accept arguments nor does it return any value.
        It contains the implementation details specific to the step it performs.

        Raises:
            Not specified since this is an internal method.
        """
        pass

    def period_update(self, period, period_date=None):
        """
        Updates the asset for a specific period and optionally a specific date, recalculating values based
        on the asset's conditions and the provided inputs.

        If the period date is within the asset's valid range (start_date and end_date), the appreciation and
        cash flow are calculated. Otherwise, the values are reset.

        Parameters:
            period: int
                The period identifier for which the update is being applied.
            period_date: Optional[datetime.date]
                The specific date associated with the period. Defaults to None.

        Returns:
            tuple[int, Optional[float], Optional[float]]
                A tuple consisting of:
                - The period identifier (int).
                - The calculated appreciation value (float or None).
                - The cash flow value (float or None).
        """
        derived_metrics = {k: 0.0 for k in self.metrics_functions}
        if self.start_date is not None and self.end_date is not None:
            if period_date < self.start_date:
                logging.info(f"Asset {self.name} not applicable for period {period} on date {period_date}")
            elif self.start_date <= period_date < self.end_date:
                if not self.setup_run:
                    self._setup()
                    self.setup_run = True
                    logging.debug(f"Run asset setup: {str(self)}")
                logging.info(f"Updating asset {self.name} for period {period} on date {period_date}")
                self._period_update_finalize_metrics(period, period_date)
                for k, f in self.metrics_functions.items():
                    derived_metrics[k] = f()
                    logging.debug(f"Derived metrics for {self.name} at period {period}: {k} = {derived_metrics[k]:.2f}")
            else:
                # period_date >= self.end_date:
                logging.info(
                    f"Asset {self.name} not applicable for period {period} on date {period_date}, resetting values.")
                self.initialize_asset_metrics()
        else:
            logging.error(f"Invalid period_date: {period_date} or asset dates: {self.start_date}, {self.end_date}")
        return period, period_date, derived_metrics

    def period_snapshot(self, period, period_date=None, addl={}):
        """
        Generates a snapshot of the financial period with additional details.

        The method compiles data representing a specific financial period and returns
        it as a list. Optionally includes additional data or a formatted date if provided.

        Arguments:
            period: The financial period for which the snapshot is generated.
            addl: Optional, a dict containing additional data to include in the snapshot.
            date: Optional, a datetime object representing a specific date to include
                in the snapshot.

        Returns:
            A list containing the compiled snapshot of the financial period.
        """
        self.snapshot_header = ["Period", "Date", "Name", "Description", "Value",
                                "Debt", "Income", "Expenses"]
        res = [period, period_date,
               self.name, self.description,
               self.value, self.debt,
               self.income, self.expenses]
        if len(addl) > 0:
            for key, value in addl.items():
                res.append(value)
                self.snapshot_header.append(key)
        return res

    def _asset_appreciation(self):
        """
        Calculates and applies the appreciation of an asset's value based on its growth rate.

        The method updates the asset's value by calculating the increase based on the
        current value and growth rate. It then returns the amount of appreciation.

        Returns:
            float: The amount of appreciation added to the asset's value.
        """
        if hasattr(self, "growth_rate_volatiliy") and self.growth_rate_volatility == 0.0:
            rate = self.growth_rate
        else:
            rate = np.random.normal(self.growth_rate, self.growth_rate_volatility)
        inc = self.value * rate
        self.value += inc
        logging.info(f"Appreciation for {self.name} at rate {rate:.4f} is ${inc:,.2f}, new value is ${self.value:,.2f}")
        return inc

    def operating_expense(self):
        """
        Calculates the operating expense based on the provided value, expense rate,
        and additional expenses.

        Returns:
            The calculated operating expense as a numeric value.
        """
        op_exp = self.value * self.expense_rate + self.expenses
        return op_exp

    def cash_flow(self):
        """
        Calculates the net cash flow by subtracting operating expenses from income.

        The function determines the financial cash flow by considering
        income and operational expenses.

        Returns:
            float: The net cash flow calculated as income minus operating expenses.
        """
        return self.income - self.operating_expense()

    def taxable_income(self):
        """
        Calculates the taxable income for the asset.

        This method computes the taxable income by considering the income generated
        by the asset and subtracting any operating expenses. It is used to determine
        the financial performance of the asset for tax purposes.

        Returns:
            float: The taxable income calculated as income minus operating expenses.
        """
        return self.income

    def set_scenario_dates(self, date_dict):
        """
        Updates the start and end dates of the asset based on a provided dictionary.
        The dictionary should map specific keys to new date values. If the
        start_date or end_date matches a key in the dictionary, it will be updated
        to the corresponding value.
        Parameters:
            date_dict (dict): A dictionary mapping keys to new date values.
        The keys should correspond to the asset's start_date and end_date.

        Example keys are "retirement", "first_date", "last_date", etc.
        """
        for key, value in date_dict.items():
            if self.start_date == key:
                if isinstance(value, str):
                    self.start_date = datetime.strptime(value, FMT).date()
                else:
                    self.start_date = value
            elif self.end_date == key:
                if isinstance(value, str):
                    self.end_date = datetime.strptime(value, FMT).date()
                else:
                    self.end_date = value
            elif hasattr(self, "retirement_age") and self.retirement_age == key:
                self.retirement_age = int(value)
            elif hasattr(self, "retirement_date") and self.retirement_date == key:
                if isinstance(value, str):
                    self.retirement_date = datetime.strptime(value, FMT).date()
                else:
                    self.retirement_date = value

    def __repr__(self):
        return (f"{self.name}: ${self.value:,.2f}, ${self.debt:,.2f}, ${self.income:,.2f}, "
                f"${self.expenses:,.2f} ,{self.growth_rate:,.2f}, {self.expense_rate:,.2f}")


class REAsset(Asset):
    """
    Represents a real estate asset, inheriting from the Asset class.

    This class models the financial aspects of a real estate investment, including its growth,
    expenses, debt, and income-related dynamics. It provides an internal setup to initialize
    variables and a stepping mechanism for simulating its financial state over time.
    """

    def _setup(self):
        """
        Sets up the financial parameters for property investment simulation.

        This method calculates and initializes key financial rates and amounts
        based on provided class attribute values. It primarily divides annual
        rates into quarterly rates for growth, expenses, and income-based
        expenses. Additionally, it calculates quarterly insurance expenses and
        adjusts the monthly rental income for the simulated period.

        """
        self.value = self.initial_value  # Initial value of the property
        self.debt = self.initial_debt  # Initial debt on the property
        self.growth_rate = self.appreciation_rate / MONTHS_IN_YEAR
        self.expense_rate = self.property_tax_rate / MONTHS_IN_YEAR
        self.income_based_expenses_rate = self.management_fee_rate + self.rental_expense_rate
        self.income = self.monthly_rental_income
        self.monthly_interest_rate = self.interest_rate / MONTHS_IN_YEAR

    def _period_update_finalize_metrics(self, period, period_date=None):
        """
        Performs a step in the financial calculation process, updating the debt, payment, and
        expenses based on interest rates, payment limits, and associated costs.

        Raises
        ------
        No explicit errors are raised within this method.
        """
        interest = self.debt * self.monthly_interest_rate
        # regular payment or payoff
        self.payment = min(self.payment, self.debt + interest)
        self.principle_payment = self.payment - interest
        self.debt -= self.principle_payment
        # expenses include insurance, interest, income-based expenses, and payment, operating expenses calculated separately
        self.expenses = self.insurance_cost / MONTHS_IN_YEAR
        self.expenses += self.income_based_expenses_rate * self.income
        self.expenses += self.payment

        logging.info(
            f"mort_status, {self.name}, {period}, {period_date}, {self.payment}, {interest}, {self.principle_payment}, {self.debt}")


class Equity(Asset):
    """
    Represents an equity asset.

    The Equity class is a specialized form of an Asset that includes additional
    attributes and calculations related to managing financial equities. It carries
    specific financial rates such as growth, expense, and income rates to compute
    the financial performance across discrete time periods. The operations are based
    on the quarterly breakdown for the configured appreciation rate, expense rate,
    and dividend yield.

    Attributes:
        growth_rate: float
            The rate of growth for the equity, calculated quarterly.
        expense_rate: float
            The rate of expenses associated with the equity, calculated quarterly.
        dividend_rate: float
            The income rate (e.g., dividends) for the equity, calculated quarterly.
        expenses: float
            Represents the total incurred expenses for the equity.
        income: float
            Represents the total income generated by the equity.
    """

    def _setup(self):
        """
        Initializes quarterly rates for growth, expenses, and income based on
        annual rates. Also initializes related attributes for accumulated
        expenses and income.

        Attributes:
            growth_rate (float): Quarterly growth rate calculated from
                annual appreciation rate.
            expense_rate (float): Quarterly expense rate calculated from
                annual expense rate.
            income_rate (float): Quarterly income rate calculated from
                annual dividend yield.
            expenses (float): Accumulated expenses, initialized to zero.
            income (float): Accumulated income, initialized to zero.
        """
        self.sampled_flag = False
        self.growth_rate = self.appreciation_rate / MONTHS_IN_YEAR
        self.growth_rate_volatility = self.appreciation_rate_volatility
        if "sampled_monthly_sp500_returns" in self.__dict__ and self.sampled_monthly_sp500_returns is not None:
            with open(self.sampled_monthly_sp500_returns, "r") as f:
                self.sampled_growth_rate = []
                rdr = csv.reader(f)
                for row in rdr:
                    try:
                        self.sampled_growth_rate.append(float(row[0]))
                    except ValueError as e:
                        logging.error(f"Error parsing sampled monthly returns: {e}")
                        continue
            if len(self.sampled_growth_rate) > 0:
                # valid sampled growth rate structure
                self.sampled_flag = True
                self.growth_rate_volatility = 0.0
        self.expense_rate = self.initial_expense_rate / MONTHS_IN_YEAR
        self.dividend_rate /= MONTHS_IN_YEAR
        self.value = self.initial_value
        self.capital_gains = 0.0

    def _period_update_finalize_metrics(self, period, period_date=None):
        """
        Updates the income attribute based on the current value and income rate.

        Raises:
            AttributeError: If income_rate or value is not set or is not accessible.
        """
        self.income = self.value * self.dividend_rate  # Update income based on current value
        if self.sampled_flag:
            self.growth_rate = self.sampled_growth_rate[np.random.randint(0, len(self.sampled_growth_rate))]
            self.growth_rate_volatility = 0.0

    def withdraw_income(self, amount):
        """
        Withdraws a specified amount from the equity income.

        This method reduces the income by the specified amount, simulating a withdrawal
        from the equity asset. It ensures that the income does not go below zero.

        Parameters:
            amount (float): The amount to withdraw from the equity income.
        """
        self.value -= amount  # Adjust the value of the equity asset
        self.capital_gains = self.initial_value * self.growth_rate ** period  # Calculate capital gains based on growth rate
        logging.info(
            f"Withdrew ${amount:,.2f} from {self.name} value = {self.value:,.2f}, capital gains = {self.capital_gains:,.2}")

    def taxable_income(self):
        """
        Calculates the taxable income for the equity asset.

        This method computes the taxable income by considering the income generated
        by the equity and subtracting any operating expenses. It is used to determine
        the financial performance of the equity for tax purposes.

        Returns:
            float: The taxable income calculated as income minus operating expenses.
        """
        return self.income - self.expenses + self.capital_gains


class SalaryIncome(Asset):
    """
    Represents employment income as a type of financial asset.

    This class models the income derived from employment. It includes attributes
    to handle salary adjustments through a cost of living adjustment (COLA) rate,
    tracks its growth rate, accounts for related expenses, and computes the current
    income derived from employment in a periodic manner.
    """

    def _setup(self):
        """
        Sets up the financial parameters including growth rate, expenses, income, and value. This method
        initializes these attributes based on predefined logic.

        Private method that should not be called directly.

        Attributes:
            growth_rate (float): The rate of financial growth based on cola divided by 4.
            expenses (int): Initial expenses, which are set to 0.
            income (float): The initial income calculated as salary divided by 4.
            value (int): The initial value, set to 0.
        """
        self.growth_rate = self.cola / MONTHS_IN_YEAR  # No appreciation for employment income
        if "retirement_age_based_benefit" in self.__dict__:
            self.salary = self.retirement_age_based_benefit[str(self.retirement_age)]
            self.income = self.salary
            logging.info(f"Using benefit for retirement age {self.retirement_age}: {self.salary}")
        else:
            logging.info(f"No age based benefit found, using salary: {self.salary}")
            self.income = self.salary / MONTHS_IN_YEAR

    def _period_update_finalize_metrics(self, period, period_date=None):
        """
        Adjusts the income by applying the growth rate to account for cost of living adjustment (COLA).

        Raises:
            AttributeError: If `income` or `growth_rate` does not exist or cannot be modified.
        """
        self.income *= (1. + self.growth_rate)  # Adjust salary for cost of living adjustment (COLA)
