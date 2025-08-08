import pandas as pd

from models.utils import *


class RetirementFinancialModel:
    CONFIG_PATH = "./configuration/assets"
    CONFIG_FILE_PATH = "./configuration/config.json"

    def __init__(self, config_file_path=CONFIG_FILE_PATH):
        """
        Initializes the retirement model with configuration parameters and calculates derived attributes such
        as current age, spouse's age, and retirement date.

        Attributes:
            today_date (date): The current date at the time of initialization.
            birth_date (date): The birth date of the individual parsed from the configuration file.
            spouse_birth_date (date): The birth date of the spouse parsed from the configuration file.
            current_age (float): The current age of the individual calculated based on the birth date.
            spouse_current_age (float): The current age of the spouse calculated based on their birth date.
            start_date (date): The start date of the retirement plan parsed from the configuration file.
            end_date (date): The end date of the retirement plan parsed from the configuration file.
            retirement_date (date): The calculated retirement date based on the birth date and retirement age.
        """
        if not config_file_path:
            logging.error("No configuration file provided, using default values.")
            return
        else:
            with open(config_file_path, "r") as rdr:
                self.__dict__ = json.loads(rdr.read())
            logging.info(f"Retirement model loaded from {config_file_path}")

        self.today_date = datetime.now().date()
        logging.info(f"Today's date: {self.today_date}")

        self.birth_date = datetime.strptime(self.birth_date, FMT).date()
        self.spouse_birth_date = datetime.strptime(self.spouse_birth_date, FMT).date()
        self.current_age = (self.today_date - self.birth_date).days / DAYS_IN_YEAR
        self.spouse_current_age = (self.today_date - self.spouse_birth_date).days / DAYS_IN_YEAR
        logging.info(f"Current age: {self.current_age:.1f}, Spouse's age: {self.spouse_current_age:.1f}")

        self.start_date = datetime.strptime(self.start_date, FMT).date()
        self.end_date = datetime.strptime(self.end_date, FMT).date()
        logging.info(f"Start date: {self.start_date}, End date: {self.end_date}")

        self.retirement_date = self.birth_date + timedelta(days=self.retirement_age * DAYS_IN_YEAR)
        logging.info(f"Retirement date: {self.retirement_date} at age {self.retirement_age:,.1f}")

    def setup(self, config_path=CONFIG_PATH, asset_filter=None):
        """
        Sets up the retirement model by loading assets configuration and initializing scenario dates and timeline.

        This method initializes the retirement model using the configuration file specified and the optional
        asset filter provided. It loads assets, sets scenario dates for each asset based on the retirement model's
        parameters, and creates the timeline for the model.

        Args:
            config_path (str): Path to the configuration file containing asset details.
            asset_filter (optional): Filter to determine which assets to include.

        Returns:
            None
        """
        logging.info(f"Setting up retirement model with configuration from {config_path}")
        self.assets = create_assets(config_path, asset_filter)
        logging.info(f"Assets loaded: {[asset.name for asset in self.assets]}")
        for asset in self.assets:
            asset.set_scenario_dates({
                "first_date": self.start_date,
                "retirement": self.retirement_date,
                "end_date": self.end_date,
                "retirement_date": self.retirement_date,
                "retirement_age": int(self.retirement_age)
            })
            logging.info(
                f"Asset {asset.name} scenario dates set: {asset.start_date} to {asset.end_date}"
                f"with retirement date {self.retirement_date}")

        self.timeline = create_datetime_sequence(self.start_date, self.end_date)
        logging.info(f"Timeline (monthly) created from {self.start_date} to {self.end_date}")

    def run_model(self):
        """Run the financial model simulation"""
        mdata = []
        mheader = ["Period", "Date", "age",
                   "retirement_withdrawal",
                   "net_worth", "debt",
                   "monthly_taxable_income",
                   "monthly_operational_expenses", "taxes_paid",
                   "free_cash_flows",
                   "investment"
                   ]
        adata = {a.name: [] for a in self.assets}

        for p, pdate in enumerate(self.timeline):
            age = (pdate - self.birth_date).days / DAYS_IN_YEAR
            for asset in self.assets:
                _p, _pdate, addl = asset.period_update(p, pdate)
                snapshot = asset.period_snapshot(p, pdate, addl=addl)
                adata[asset.name].append(snapshot)  # add header below
            ####################################################################
            # Aggregate actions and metrics
            ####################################################################
            # 401k withdrawals
            retirement_withdraw = 0.0
            if age >= self.retirement_age:
                retirement_withdraw = max(
                    [0.0, self.withdrawal_rate * self.retirement_portfolio_value() / MONTHS_IN_YEAR])
                # decrement asset values by withdrawal
                self.allocate_investment_evenly(-retirement_withdraw * self.stock_allocation, "stock")
                self.allocate_investment_evenly(-retirement_withdraw * self.bond_allocation, "bond")
                logging.info(f"Age: {age:,.1f}, Retirement withdrawal: {retirement_withdraw:.2f}")

            # net_worth and debt
            net_worth, debt = self.net_worth_debt()
            # tax basis
            monthly_taxable_income = self.calculate_monthly_taxable_income() + retirement_withdraw
            # operational expenses
            monthly_operational_expenses = self.calculate_operating_expenses()
            # Calculate taxes on total income
            taxes_paid = self.calculate_monthly_taxes(retirement_withdraw)
            # Calculate free cash flows after asset-specific taxes and expenses
            free_cash_flows = monthly_taxable_income + self.calculate_free_cash_flows() - taxes_paid

            # Calculate investment allocation (before retirement)
            investment = 0.0
            if age < self.retirement_age:
                logging.info(f"Free cash flows: {free_cash_flows:,.2f}, Taxes: {taxes_paid:,.2f}, Age: {age:,.1f}")
                investment = max([0.0, self.savings_rate * free_cash_flows])
                self.allocate_investment_evenly(investment * self.stock_allocation, "401k stock")
                self.allocate_investment_evenly(investment * self.bond_allocation, "401k bond")

            # track model data
            mdata.append([p, pdate, age,
                          retirement_withdraw,
                          net_worth, debt,
                          monthly_taxable_income,
                          monthly_operational_expenses, taxes_paid,
                          free_cash_flows,
                          investment
                          ])

        aheader = self.assets[0].snapshot_header

        return mdata, mheader, adata, aheader

    def calculate_operating_expenses(self):
        """
        Calculates the total operating expenses for all assets.

        This method iterates through a list of assets and sums up their operating
        expenses. Each asset is expected to have a method `operating_expense`
        that returns its individual expense. The final total is returned as the
        result of this calculation.

        Returns:
            float: The total operating expenses for all assets.
        """
        total_expenses = 0.0
        for asset in self.assets:
            total_expenses += asset.operating_expense()
        return total_expenses

    def retirement_portfolio_value(self, name_match="401k"):
        """
        Calculate the total value of retirement portfolio assets.

        This method computes the total value of assets in the portfolio that match
        a specific name substring. It subtracts any debt associated with those
        assets to provide a net value. The matching is case-insensitive and based
        on the `name_match` parameter.

        Parameters:
        name_match: str
            The substring to match against the names of assets. Defaults to "401k".

        Returns:
        float
            The total net value of the matching retirement assets.
        """
        total_value = 0.0
        for asset in self.assets:
            if name_match in asset.name.lower():
                total_value += asset.value - asset.debt
        return total_value

    def allocate_investment_evenly(self, amount, name_match):
        """
        Distributes a specified investment amount evenly across assets matching a given name pattern.

        This method identifies all assets in the portfolio whose names contain a specified
        string pattern (case-insensitive), and distributes the given investment amount
        equally among these assets. If any asset cannot fully accept its allocated share
        of the investment, the investment amount may be adjusted to ensure full distribution.

        Args:
            amount (float): The total investment amount to be distributed.
            name_match (str): A substring to search for in asset names (case-insensitive).

        Returns:
            float: The total actual amount successfully invested across all selected assets.

        Raises:
            ZeroDivisionError: If there are no matching assets and an attempt is made to divide by zero.
        """
        total_actual_investment = 0.0
        asset_list = []
        for asset in self.assets:
            if name_match in asset.name.lower():
                asset_list.append(asset)
        equally_distributed_amount = amount / len(asset_list) if asset_list else 0.0
        if equally_distributed_amount != 0.0:
            for asset in asset_list:
                actual_investment = asset.update_value_with_investment(equally_distributed_amount)
                if actual_investment != equally_distributed_amount:
                    equally_distributed_amount = 2 * equally_distributed_amount - actual_investment
                    logging.info(f"Adjusted investment amount for {asset.name} to ${equally_distributed_amount:,.2f}")
                logging.info(f"Invested ${equally_distributed_amount:,.2f} in {asset.name}")
                total_actual_investment += actual_investment
        return total_actual_investment

    def net_worth_debt(self):
        """
        Calculates the total net worth and total debt based on the assets.

        This method computes the total net worth by summing up the net value
        of all assets, which is calculated as the value of each asset minus
        its debt. It also calculates the total debt by summing up the debt
        from all assets.

        Returns:
            tuple[float, float]: A tuple where the first element is the total net
            worth and the second element is the total debt.
        """
        total_net_worth = 0.0
        total_debt = 0.0
        for asset in self.assets:
            total_net_worth += asset.value - asset.debt
            total_debt += asset.debt
        return total_net_worth, total_debt

    def calculate_free_cash_flows(self):
        """
        Calculates the total free cash flows from all assets.

        This method iterates through a collection of assets, invoking the `cash_flow`
        method for each asset and summing up their values to calculate the total free
        cash flow.

        Returns:
            float: The total free cash flow from all assets.
        """
        cash_flow = 0.0
        for asset in self.assets:
            cash_flow += asset.cash_flow()
        return cash_flow

    def calculate_monthly_taxable_income(self):
        """
        Calculates the total monthly taxable income by aggregating the taxable income
        from all assets.

        Raises:
            Any exceptions raised by the `taxable_income` method of an asset, if
            applicable.

        Returns:
            float: The total monthly taxable income calculated by summing up the
            taxable income from all assets.
        """
        monthly_income = 0
        for asset in self.assets:
            monthly_income += asset.taxable_income()
        return monthly_income

    def calculate_monthly_taxes(self, withdraw_amount=0.0):
        """
        Calculates the monthly taxes based on the income from assets and withdrawal amount.

        This method determines the total taxes that need to be paid monthly by aggregating
        income across various tax classes from the assets and applying corresponding tax rates.
        It also accounts for income taxes on an optional withdrawal amount if specified.

        Args:
            withdraw_amount (float, optional): The withdrawal amount to be taxed. Defaults to 0.0.

        Returns:
            float: The total monthly taxes calculated.
        """
        income_classes = {"income": 0.0, "capital_gain": 0.0, "social_security": 0.0}
        for asset in self.assets:
            income_classes[asset.tax_class] += asset.income
        monthly_taxes = 0.0
        for tax_class in income_classes:
            monthly_taxes = income_classes[tax_class] * self.tax_classes[tax_class]
        if withdraw_amount > 0:
            # If there is a withdrawal, apply income tax on the withdrawal amount
            logging.info(f"Applying income tax on withdrawal amount: {withdraw_amount}")
            monthly_taxes += withdraw_amount * self.tax_classes["income"]
        return monthly_taxes

    def get_asset_dataframe(self, asset_name, asset_model_dict, asset_model_header):
        """Get asset data as a DataFrame"""
        if asset_name in asset_model_dict:
            asset_data = asset_model_dict[asset_name]
            return pd.DataFrame(asset_data, columns=asset_model_header)
        logging.error(f"Asset {asset_name} not found in model data.")

    def get_scenario_dataframe(self, model_data, model_header):
        """Get model data as a DataFrame"""
        return pd.DataFrame(model_data, columns=model_header)
