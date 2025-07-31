import json
import logging
from datetime import datetime

class Asset:

    FMT = "%Y-%m-%d"

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
         - value # Sum of all assets values is net equity
         - growth_rate # quarterly appreciation rate
         - expense_rate # quarterly expense rate
         - income # quarterly income from the asset
         - expenses # quarterly expenses from the asset
         - debt # e.g., mortgage, loan, etc.


        Parameters:
        filename: str
            The path to the JSON file that contains the asset data.
        """
        logging.debug(f"Initializing asset from {filename}")
        with open(filename, "r") as reader:
            self.__dict__.update(json.load(reader))
        for key in ['start_date', 'end_date']:
            if key in self.__dict__:
                try:
                    self.__dict__[key] = datetime.strptime(self.__dict__[key], self.FMT).date()
                    logging.info(f"Parsed date for {key} in {filename}: {e}")
                except ValueError as e:
                    logging.info(f"Did not parse date for {key} in {filename}: {e}")
        self._setup()
        logging.debug(f"Asset {self.name} initialized with value: {self.value}, "
                      f"growth_rate: {self.growth_rate}, expense_rate: {self.expense_rate}, "
                      f"income: {self.income}, expenses: {self.expenses}")

    def _set_zeros(self):
        """
        Sets the asset's value, income, expenses, and debt to zero.

        This method is used to reset the financial state of the asset when
        necessary, such as when the asset is not applicable for a given period.
        It ensures that all financial attributes are set to zero, effectively
        clearing any previous values.

        """
        self.value = 0
        self.income = 0
        self.expenses = 0
        self.debt = 0

    def _setup(self):
        """
        Sets up initial configurations or state for the object.

        This method is internally used for setup purposes and should not be accessed
        directly by external code. All necessary configurations and preparations
        required for the object to function as intended can be managed using this
        method.

        """
        pass

    def _step(self, period, period_date=None):
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
        if self.start_date is not None and self.end_date is not None:
            if period_date is None or (self.start_date <= period_date <= self.end_date):
                logging.info(f"Updating asset {self.name} for period {period} on date {period_date}")
                appreciation = self.asset_appreciation()
                self._step(period, period_date)
                cash_flow = self.cash_flow()
            else:
                logging.info(
                    f"Asset {self.name} not applicable for period {period} on date {period_date}, resetting values.")
                self._set_zeros()
                appreciation = 0
                cash_flow = 0
        else:
            logging.error(f"Invalid period_date: {period_date} or asset dates: {self.start_date}, {self.end_date}")
            appreciation = None
            cash_flow = None
        return period, appreciation, cash_flow

    def period_snapshot(self, period, period_date=None, addl=None):
        """
        Generates a snapshot of the financial period with additional details.

        The method compiles data representing a specific financial period and returns
        it as a list. Optionally includes additional data or a formatted date if provided.

        Arguments:
            period: The financial period for which the snapshot is generated.
            addl: Optional, a list containing additional data to include in the snapshot.
            date: Optional, a datetime object representing a specific date to include
                in the snapshot.

        Returns:
            A list containing the compiled snapshot of the financial period.
        """
        res = [period,
               period_date,
               self.name,
               self.description,
               self.value,
               self.debt,
               self.income,
               self.expenses]
        if addl is not None:
            res.extend(addl)
        return res

    def asset_appreciation(self):
        """
        Calculates and applies the appreciation of an asset's value based on its growth rate.

        The method updates the asset's value by calculating the increase based on the
        current value and growth rate. It then returns the amount of appreciation.

        Returns:
            float: The amount of appreciation added to the asset's value.
        """
        inc = self.value * self.growth_rate
        self.value += inc
        return inc

    def operating_expense(self):
        """
        Calculates the operating expense based on the provided value, expense rate,
        and additional expenses.

        Returns:
            The calculated operating expense as a numeric value.
        """
        dec = self.value * self.expense_rate + self.expenses
        return dec

    def cash_flow(self):
        """
        Calculates the net cash flow by subtracting operating expenses from income.

        The function determines the financial cash flow by considering
        income and operational expenses.

        Returns:
            float: The net cash flow calculated as income minus operating expenses.
        """
        return self.income - self.operating_expense()

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
                self.start_date = datetime.strptime(value, self.FMT).date()
            elif self.end_date == key:
                self.end_date = datetime.strptime(value, self.FMT).date()

    def __repr__(self):
        return f"{self.name}: ${self.value:,.2f} (Growth Rate: {self.growth_rate:.2%} Expense Rate: {self.expense_rate:.2%})"


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
        self.growth_rate = self.appreciation_rate / 12.
        self.expense_rate = self.property_tax_rate / 12.
        self.income_based_expenses = (self.management_fee + self.rental_expense_rate) / 12.
        self.expenses = self.insurance_cost / 12.
        self.income = self.monthly_rental_income

    def _step(self, period, period_date=None):
        """
        Performs a step in the financial calculation process, updating the debt, payment, and
        expenses based on interest rates, payment limits, and associated costs.

        Raises
        ------
        No explicit errors are raised within this method.
        """
        interest = self.debt * self.interest_rate / 12.
        self.payment = min(self.payment, self.debt + interest)
        principle = self.payment - interest
        self.debt -= principle
        self.expenses = self.insurance_cost / 12. + interest + self.income_based_expenses * self.payment


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
        self.growth_rate = self.appreciation_rate / 12.
        self.expense_rate /= 12.
        self.dividend_rate /= 12.
        self.expenses = 0
        self.income = 0

    def _step(self, period, period_date=None):
        """
        Updates the income attribute based on the current value and income rate.

        Raises:
            AttributeError: If income_rate or value is not set or is not accessible.
        """
        self.income = self.value * self.dividend_rate  # Update income based on current value


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
        self.growth_rate = self.cola / 12.  # No appreciation for employment income
        self.expenses = 0  # No expenses
        self.income = self.salary / 12.

    def _step(self, period, period_date=None):
        """
        Adjusts the income by applying the growth rate to account for cost of living adjustment (COLA).

        Raises:
            AttributeError: If `income` or `growth_rate` does not exist or cannot be modified.
        """
        self.income *= (1 + self.growth_rate)  # Adjust salary for cost of living adjustment (COLA)


def create_assets(path="./configuration/assets"):
    """
    Processes JSON files in a specified directory to create asset objects based on their type. Supported
    asset types include 'RE', 'Equity', and 'Salary'. Unrecognized asset types are logged and skipped.

    Parameters:
        path: str
            The directory path containing the JSON files. Defaults to "./configuration/assets".

    Returns:
        list
            A list of asset objects loaded from the JSON files.

    Raises:
        FileNotFoundError
            If the specified path does not exist.
        JSONDecodeError
            If a JSON file is malformed or contains invalid JSON data.
    """
    import os
    assets = []
    for filename in os.listdir(path):
        if filename.endswith('.json'):
            fpath = os.path.join(path, filename)
            with (open(fpath, 'r') as file):
                asset_data = json.load(file)
                if asset_data['type'] == 'RE':
                    logging.debug(f"Loading {fpath} as RE")
                    asset = REAsset(fpath)
                elif asset_data['type'] == 'Equity':
                    logging.debug(f"Loading {fpath} as Equity")
                    asset = Equity(fpath)
                elif asset_data['type'] == 'Salary':
                    logging.debug(f"Loading {fpath} as SalaryIncome")
                    asset = SalaryIncome(fpath)
                else:
                    logging.warning(f"Unknown asset type in {fpath}, skipping.")
                    continue
                asset.__dict__.update(asset_data)
                assets.append(asset)
    return assets


if __name__ == "__main__":
    from logging.config import dictConfig

    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }},
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'default',
                'level': 'DEBUG',
                'filename': 'assets.log',
                'mode': 'a',
                'encoding': 'utf-8',
                'maxBytes': 900000,
                'backupCount': 3
            }},
        'root': {
            'level': 'DEBUG',
            'handlers': ['file']
        }
    })

    assets = create_assets()
    for period in range(0, 3 * 4):
        print(f"Period: {period}")
        print("-" * 40)
        for asset in assets:
            print(asset)
            _, appreciation, cash_flow = asset.period_update(period)
            print(f"{asset.period_snapshot(period, addl=[appreciation, cash_flow])}")
