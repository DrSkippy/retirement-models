"""Typed configuration models for WorldConfig and asset configs."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Optional, Union

from pydantic import BaseModel, model_validator

FMT = "%Y-%m-%d"
DAYS_IN_YEAR = 365.25


class TaxConfig(BaseModel):
    """Tax rates for each income class."""

    income: float
    capital_gain: float
    social_security: float


class AllocationConfig(BaseModel):
    """Portfolio allocation between stocks and bonds."""

    stock_allocation: float
    bond_allocation: float

    @model_validator(mode="after")
    def allocations_sum_to_one(self) -> "AllocationConfig":
        """Validate that allocations sum to 1.0."""
        total = self.stock_allocation + self.bond_allocation
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"stock_allocation + bond_allocation must equal 1.0, got {total}"
            )
        return self


class WorldConfig(BaseModel):
    """Top-level simulation world configuration."""

    birth_date: date
    spouse_birth_date: date
    retirement_age: int
    start_date: date
    end_date: date
    inflation_rate: float
    savings_rate: float
    withdrawal_rate: float
    tax_classes: TaxConfig
    allocation: AllocationConfig
    retirement_date: Optional[date] = None

    @model_validator(mode="after")
    def compute_retirement_date(self) -> "WorldConfig":
        """Compute retirement_date from birth_date + retirement_age if not supplied."""
        if self.retirement_date is None:
            self.retirement_date = self.birth_date + timedelta(
                days=self.retirement_age * DAYS_IN_YEAR
            )
        return self

    @classmethod
    def from_json(cls, path: str) -> "WorldConfig":
        """Load a WorldConfig from the existing flat config.json format.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            A fully validated WorldConfig instance.
        """
        with open(path, "r") as f:
            data = json.load(f)
        tax_classes = TaxConfig(**data["tax_classes"])
        allocation = AllocationConfig(
            stock_allocation=data["stock_allocation"],
            bond_allocation=data["bond_allocation"],
        )
        return cls(
            birth_date=datetime.strptime(data["birth_date"], FMT).date(),
            spouse_birth_date=datetime.strptime(data["spouse_birth_date"], FMT).date(),
            retirement_age=data["retirement_age"],
            start_date=datetime.strptime(data["start_date"], FMT).date(),
            end_date=datetime.strptime(data["end_date"], FMT).date(),
            inflation_rate=data["inflation_rate"],
            savings_rate=data["savings_rate"],
            withdrawal_rate=data["withdrawal_rate"],
            tax_classes=tax_classes,
            allocation=allocation,
        )


class BaseAssetConfig(BaseModel):
    """Common fields present in every asset JSON file."""

    name: str
    description: str
    type: str
    start_date: str
    end_date: str
    tax_class: str


class RealEstateConfig(BaseAssetConfig):
    """Configuration for a RealEstate asset."""

    initial_value: float
    initial_debt: float
    appreciation_rate: float
    property_tax_rate: float
    insurance_cost: float
    management_fee_rate: float
    monthly_rental_income: float
    rental_expense_rate: float
    interest_rate: float
    payment: float


class EquityConfig(BaseAssetConfig):
    """Configuration for an Equity asset."""

    initial_value: float
    initial_expense_rate: float
    appreciation_rate: float
    appreciation_rate_volatility: float
    dividend_rate: float
    sampled_monthly_sp500_returns: Optional[str] = None


class SalaryConfig(BaseAssetConfig):
    """Configuration for a SalaryIncome asset."""

    salary: Optional[float] = None
    cola: float
    retirement_age: str
    retirement_age_based_benefit: Optional[dict[str, float]] = None
    initial_debt: float = 0.0
