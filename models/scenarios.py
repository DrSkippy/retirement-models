import pandas as pd
from tqdm import tqdm

from models.config import TaxConfig, WorldConfig
from models.taxes import TaxCalculator
from models.utils import *


class RetirementFinancialModel:
    CONFIG_PATH = "./configuration/assets"
    CONFIG_FILE_PATH = "./configuration/config.json"

    def __init__(self, config_file_path: str = CONFIG_FILE_PATH) -> None:
        """Initialize the retirement model from a JSON config file.

        Attributes:
            today_date: The current date at time of initialization.
            birth_date: Individual's birth date.
            spouse_birth_date: Spouse's birth date.
            current_age: Current age in fractional years.
            spouse_current_age: Spouse's current age in fractional years.
            start_date: Simulation start date.
            end_date: Simulation end date.
            retirement_date: Computed retirement date.
            world_config: Typed WorldConfig view of the configuration.
        """
        if not config_file_path:
            logging.error("No configuration file provided, using default values.")
            return

        with open(config_file_path, "r") as rdr:
            self.__dict__ = json.loads(rdr.read())
        logging.info(f"Retirement model loaded from {config_file_path}")

        # Build typed WorldConfig for downstream consumers.
        self.world_config: WorldConfig = WorldConfig.from_json(config_file_path)

        # Initialise TaxCalculator — fixes Bug 3 by delegating to += accumulation.
        self._tax_calculator = TaxCalculator(self.world_config.tax_classes)

        self.today_date = datetime.now().date()
        logging.info(f"Today's date: {self.today_date}")

        self.birth_date = datetime.strptime(self.birth_date, FMT).date()
        self.spouse_birth_date = datetime.strptime(self.spouse_birth_date, FMT).date()
        self.current_age = (self.today_date - self.birth_date).days / DAYS_IN_YEAR
        self.spouse_current_age = (
            (self.today_date - self.spouse_birth_date).days / DAYS_IN_YEAR
        )
        logging.info(
            f"Current age: {self.current_age:.1f}, Spouse's age: {self.spouse_current_age:.1f}"
        )

        self.start_date = datetime.strptime(self.start_date, FMT).date()
        self.end_date = datetime.strptime(self.end_date, FMT).date()
        logging.info(f"Start date: {self.start_date}, End date: {self.end_date}")

        self.retirement_date = self.birth_date + timedelta(
            days=self.retirement_age * DAYS_IN_YEAR
        )
        logging.info(
            f"Retirement date: {self.retirement_date} at age {self.retirement_age:,.1f}"
        )

    @classmethod
    def from_json(cls, config_file_path: str = CONFIG_FILE_PATH) -> "RetirementFinancialModel":
        """Factory method — alias for the constructor.

        Args:
            config_file_path: Path to the JSON config file.

        Returns:
            An initialised RetirementFinancialModel.
        """
        return cls(config_file_path)

    def setup(self, config_path: str = CONFIG_PATH, asset_filter: list | None = None) -> None:
        """Load assets and build the simulation timeline.

        Args:
            config_path: Directory containing asset JSON files.
            asset_filter: Optional list of name substrings to include.
        """
        logging.info(f"Setting up retirement model with configuration from {config_path}")
        self.assets = create_assets(config_path, asset_filter)
        logging.info(f"Assets loaded: {[asset.name for asset in self.assets]}")
        for asset in self.assets:
            asset.set_scenario_dates(
                {
                    "first_date": self.start_date,
                    "retirement": self.retirement_date,
                    "end_date": self.end_date,
                    "retirement_date": self.retirement_date,
                    "retirement_age": int(self.retirement_age),
                }
            )
            logging.info(
                f"Asset {asset.name} scenario dates set: {asset.start_date} to {asset.end_date}"
                f" with retirement date {self.retirement_date}"
            )
            asset.pre_calculate(self.start_date)

        self.timeline = create_datetime_sequence(self.start_date, self.end_date)
        logging.info(
            f"Timeline (monthly) created from {self.start_date} to {self.end_date}"
        )

    def run_model(self, show_progress: bool = False) -> tuple:
        """Run the financial model simulation.

        Returns:
            (mdata, mheader, adata, aheader) where mdata is a list of per-period
            rows, mheader is the column names, adata is per-asset data keyed by
            asset name, and aheader is the asset snapshot column names.
        """
        mdata = []
        mheader = [
            "Period",
            "Date",
            "age",
            "retirement_withdrawal",
            "net_worth",
            "debt",
            "monthly_taxable_income",
            "monthly_operational_expenses",
            "taxes_paid",
            "free_cash_flows",
            "investment",
        ]
        adata: dict[str, list] = {a.name: [] for a in self.assets}

        timeline_iter = tqdm(
            enumerate(self.timeline),
            total=len(self.timeline),
            desc="Simulating periods",
            unit="mo",
            disable=not show_progress,
        )
        for p, pdate in timeline_iter:
            age = (pdate - self.birth_date).days / DAYS_IN_YEAR
            for asset in self.assets:
                _p, _pdate, addl = asset.period_update(p, pdate)
                snapshot = asset.period_snapshot(p, pdate, addl=addl)
                adata[asset.name].append(snapshot)

            # 401k withdrawals
            retirement_withdraw = 0.0
            if age >= self.retirement_age:
                retirement_withdraw = max(
                    [
                        0.0,
                        self.withdrawal_rate
                        * self.retirement_portfolio_value()
                        / MONTHS_IN_YEAR,
                    ]
                )
                self.allocate_investment_evenly(
                    -retirement_withdraw * self.stock_allocation, "stock"
                )
                self.allocate_investment_evenly(
                    -retirement_withdraw * self.bond_allocation, "bond"
                )
                logging.info(
                    f"Age: {age:,.1f}, Retirement withdrawal: {retirement_withdraw:.2f}"
                )

            net_worth, debt = self.net_worth_debt()
            monthly_taxable_income = (
                self.calculate_monthly_taxable_income() + retirement_withdraw
            )
            monthly_operational_expenses = self.calculate_operating_expenses()
            taxes_paid = self.calculate_monthly_taxes(retirement_withdraw)
            free_cash_flows = (
                monthly_taxable_income
                + self.calculate_free_cash_flows()
                - taxes_paid
            )

            investment = 0.0
            if age < self.retirement_age:
                logging.info(
                    f"Free cash flows: {free_cash_flows:,.2f}, Taxes: {taxes_paid:,.2f}, Age: {age:,.1f}"
                )
                investment = max([0.0, self.savings_rate * free_cash_flows])
                self.allocate_investment_evenly(
                    investment * self.stock_allocation, "401k stock"
                )
                self.allocate_investment_evenly(
                    investment * self.bond_allocation, "401k bond"
                )

            mdata.append(
                [
                    p,
                    pdate,
                    age,
                    retirement_withdraw,
                    net_worth,
                    debt,
                    monthly_taxable_income,
                    monthly_operational_expenses,
                    taxes_paid,
                    free_cash_flows,
                    investment,
                ]
            )

        aheader = self.assets[0].snapshot_header
        return mdata, mheader, adata, aheader

    def calculate_operating_expenses(self) -> float:
        """Return total operating expenses across all assets."""
        total_expenses = 0.0
        for asset in self.assets:
            total_expenses += asset.operating_expense()
        return total_expenses

    def retirement_portfolio_value(self, name_match: str = "401k") -> float:
        """Return net value of retirement portfolio assets matching name_match.

        Parameters:
            name_match: Case-insensitive substring to match asset names.
        """
        total_value = 0.0
        for asset in self.assets:
            if name_match in asset.name.lower():
                total_value += asset.value - asset.debt
        return total_value

    def allocate_investment_evenly(self, amount: float, name_match: str) -> float:
        """Distribute amount evenly across assets whose name contains name_match.

        Args:
            amount: Total amount to distribute (negative = withdrawal).
            name_match: Case-insensitive substring to match asset names.

        Returns:
            Total amount actually invested.
        """
        total_actual_investment = 0.0
        asset_list = [a for a in self.assets if name_match in a.name.lower()]
        equally_distributed_amount = amount / len(asset_list) if asset_list else 0.0
        if equally_distributed_amount != 0.0:
            for asset in asset_list:
                actual_investment = asset.update_value_with_investment(
                    equally_distributed_amount
                )
                if actual_investment != equally_distributed_amount:
                    equally_distributed_amount = (
                        2 * equally_distributed_amount - actual_investment
                    )
                    logging.info(
                        f"Adjusted investment amount for {asset.name} to ${equally_distributed_amount:,.2f}"
                    )
                logging.info(
                    f"Invested ${equally_distributed_amount:,.2f} in {asset.name}"
                )
                total_actual_investment += actual_investment
        return total_actual_investment

    def net_worth_debt(self) -> tuple[float, float]:
        """Return (total_net_worth, total_debt) across all assets."""
        total_net_worth = 0.0
        total_debt = 0.0
        for asset in self.assets:
            total_net_worth += asset.value - asset.debt
            total_debt += asset.debt
        return total_net_worth, total_debt

    def calculate_free_cash_flows(self) -> float:
        """Return sum of cash_flow() across all assets."""
        cash_flow = 0.0
        for asset in self.assets:
            cash_flow += asset.cash_flow()
        return cash_flow

    def calculate_monthly_taxable_income(self) -> float:
        """Return sum of taxable_income() across all assets."""
        monthly_income = 0.0
        for asset in self.assets:
            monthly_income += asset.taxable_income()
        return monthly_income

    def calculate_monthly_taxes(self, withdraw_amount: float = 0.0) -> float:
        """Calculate total monthly taxes using TaxCalculator.

        Delegates to TaxCalculator.build_breakdown_from_assets() and
        TaxCalculator.calculate_monthly(), which fixes the original += bug
        where the loop used = (assignment) instead of += (accumulation).

        Args:
            withdraw_amount: Retirement withdrawal to be taxed as ordinary income.

        Returns:
            Total monthly tax liability.
        """
        breakdown = self._tax_calculator.build_breakdown_from_assets(
            self.assets, withdraw_amount
        )
        return self._tax_calculator.calculate_monthly(breakdown)

    def get_asset_dataframe(
        self,
        asset_name: str,
        asset_model_dict: dict,
        asset_model_header: list,
    ) -> pd.DataFrame | None:
        """Return asset simulation data as a DataFrame.

        Args:
            asset_name: Name of the asset.
            asset_model_dict: Dict mapping asset names to row lists.
            asset_model_header: Column names for the DataFrame.
        """
        if asset_name in asset_model_dict:
            return pd.DataFrame(asset_model_dict[asset_name], columns=asset_model_header)
        logging.error(f"Asset {asset_name} not found in model data.")
        return None

    def get_scenario_dataframe(
        self, model_data: list, model_header: list
    ) -> pd.DataFrame:
        """Return scenario simulation data as a DataFrame."""
        return pd.DataFrame(model_data, columns=model_header)
