import json
import logging


class Asset:
    def __init__(self, filename):
        """
        name
        description
        type
        value
        growth_rate
        expense_rate
        income
        expenses
        """
        logging.debug(f"Initializing asset from {filename}")
        with open(filename, "r") as reader:
            self.__dict__.update(json.load(reader))
            self._setup()
            logging.debug(f"Asset {self.name} initialized with value: {self.value}, "
            f"growth_rate: {self.growth_rate}, expense_rate: {self.expense_rate}, "
            f"income: {self.income}, expenses: {self.expenses}")

    def _setup(self):
        pass

    def _step(self):
        pass

    def asset_manager(self, period):
        """
        Manage the asset by updating its value, income, and expenses.
        This method should be called periodically (e.g., quarterly).
        """
        appreciation = self.appreciation()
        self._step()
        cash_flow = self.cash_flow()
        return period, self.value, appreciation, cash_flow

    def appreciation(self):
        inc = self.value * self.growth_rate
        self.value += inc
        return inc

    def expense(self):
        dec = self.value * self.expense_rate + self.expenses
        return dec

    def cash_flow(self):
        return self.income - self.expense()

    def __repr__(self):
        return f"{self.name}: ${self.value:,.2f} (Growth Rate: {self.growth_rate:.2%} Expense Rate: {self.expense_rate:.2%})"


class REAsset(Asset):

    def _setup(self):
        self.growth_rate = self.appreciation_rate / 4.
        self.expense_rate = (self.property_tax_rate + self.management_fee + self.rental_expense_rate) / 4.
        self.expenses = self.insurance_cost / 4. + self.payment * 3
        self.income = self.rental_income * 3

    def _step(self):
        self.payment = min(3*self.payment, self.value) / 3.
        self.expenses = self.insurance_cost / 4. + self.payment * 3


class Equity(Asset):

    def _setup(self):
        self.growth_rate = self.appreciation_rate / 4.
        self.expense_rate = self.expense_rate / 4.
        self.income_rate = self.dividend_yield / 4.
        self.expenses = 0
        self.income = 0

    def _step(self):
        self.income = self.value * self.income_rate  # Update income based on current value

class EmploymentIncome(Asset):
    def _setup(self):
        self.growth_rate = self.cola /4.  # No appreciation for employment income
        self.expenses = 0  # No expenses
        self.income = self.salary /4.
        self.value = 0

    def _step(self):
        self.income*= 1 + self.growth_rate  # Adjust salary for cost of living adjustment (COLA)

def create_assets(path="./configuration/assets"):
    """All json files in the path are assets"""
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
                elif asset_data['type'] == 'salary':
                    logging.debug(f"Loading {fpath} as EmploymentIncome")
                    asset = EmploymentIncome(fpath)
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
    for period in range(0, 2*4):
        print(f"Period: {period}")
        print("-" * 40)
        for asset in assets:
            print(asset)
            _, value, appreciation, cash_flow = asset.asset_manager(period)
            print(f"Updated Value: ${value:,.2f}, Appreciation: ${appreciation:,.2f}, Cash Flow: ${cash_flow:,.2f}")
