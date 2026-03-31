"""Tax calculation engine extracted from scenarios.py."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from models.config import TaxConfig

if TYPE_CHECKING:
    pass


class TaxableIncomeBreakdown(BaseModel):
    """Categorised income components for tax calculation."""

    ordinary_income: float = 0.0
    capital_gains: float = 0.0
    social_security: float = 0.0


class TaxCalculator:
    """Stateless tax calculator backed by a TaxConfig."""

    def __init__(self, config: TaxConfig) -> None:
        """Initialise with tax rates.

        Args:
            config: Tax rate configuration for each income class.
        """
        self.config = config

    def calculate_monthly(self, breakdown: TaxableIncomeBreakdown) -> float:
        """Return total monthly taxes for the given income breakdown.

        Each income class is accumulated independently (+=) to prevent the
        last-class-overwrites-all bug present in the original implementation.

        Args:
            breakdown: Categorised monthly income amounts.

        Returns:
            Total monthly tax liability.
        """
        taxes = 0.0
        taxes += breakdown.ordinary_income * self.config.income
        taxes += breakdown.capital_gains * self.config.capital_gain
        taxes += breakdown.social_security * self.config.social_security
        logging.debug(
            f"Monthly taxes: ordinary={breakdown.ordinary_income * self.config.income:.2f}, "
            f"capital_gains={breakdown.capital_gains * self.config.capital_gain:.2f}, "
            f"social_security={breakdown.social_security * self.config.social_security:.2f}, "
            f"total={taxes:.2f}"
        )
        return taxes

    def build_breakdown_from_assets(
        self, assets: list[Any], withdrawal: float = 0.0
    ) -> TaxableIncomeBreakdown:
        """Build a TaxableIncomeBreakdown by aggregating asset income by tax class.

        Args:
            assets: List of Asset objects with .tax_class and .income attributes.
            withdrawal: Additional ordinary income from retirement withdrawals.

        Returns:
            Populated TaxableIncomeBreakdown ready for calculate_monthly().
        """
        by_class: dict[str, float] = {
            "income": 0.0,
            "capital_gain": 0.0,
            "social_security": 0.0,
        }
        for asset in assets:
            if asset.tax_class in by_class:
                by_class[asset.tax_class] += asset.income
        return TaxableIncomeBreakdown(
            ordinary_income=by_class["income"] + withdrawal,
            capital_gains=by_class["capital_gain"],
            social_security=by_class["social_security"],
        )
