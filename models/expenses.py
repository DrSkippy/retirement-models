"""First-class expense model: categorised ledger for one simulation period."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ExpenseCategory(str, Enum):
    """High-level expense categories for budgeting and reporting."""

    HOUSING = "housing"
    FOOD = "food"
    HEALTHCARE = "healthcare"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    ASSET_OPERATING = "asset_operating"  # property tax, insurance, management fees
    DEBT_SERVICE = "debt_service"  # mortgage payments
    OTHER = "other"


class ExpenseLedger:
    """Collects categorised expenses for one simulation period.

    Each asset populates the ledger with the correct category via add().
    The ledger is created fresh every period; there is no state carried
    between periods.
    """

    def __init__(self) -> None:
        self._entries: dict[ExpenseCategory, float] = {
            cat: 0.0 for cat in ExpenseCategory
        }

    def add(self, category: ExpenseCategory, amount: float) -> None:
        """Add an expense amount to the given category.

        Args:
            category: The expense category.
            amount: The expense amount (positive = outflow).
        """
        self._entries[category] += amount

    def total(self) -> float:
        """Return the sum of all expenses across all categories."""
        return sum(self._entries.values())

    def by_category(self) -> dict[ExpenseCategory, float]:
        """Return a copy of the per-category expense map."""
        return dict(self._entries)

    def living_expenses_total(self) -> float:
        """Return total excluding asset_operating and debt_service categories."""
        excluded = {ExpenseCategory.ASSET_OPERATING, ExpenseCategory.DEBT_SERVICE}
        return sum(v for k, v in self._entries.items() if k not in excluded)

    def asset_operating_total(self) -> float:
        """Return the total of asset operating expenses only."""
        return self._entries[ExpenseCategory.ASSET_OPERATING]


class LivingExpenseConfig(BaseModel):
    """Optional user-supplied budget for non-asset living expenses."""

    monthly_amount: float
    inflation_rate: float = 0.025
    start_date: Optional[date] = None
    end_date: Optional[date] = None
