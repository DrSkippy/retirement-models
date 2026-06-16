import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
from pydantic import ValidationError

from models.assets import (  # noqa: F401 — re-exported for wildcard consumers
    DAYS_IN_YEAR,
    FMT,
    MONTHS_IN_YEAR,
    Asset,
    Equity,
    REAsset,
    SalaryIncome,
)
from models.config import EquityConfig, RealEstateConfig, SalaryConfig


def create_datetime_sequence(
    start_date: str | date, end_date: str | date
) -> list[date]:
    """Create a monthly date sequence from start_date to end_date.

    Each step advances to the first day of the next calendar month, so the
    sequence contains exactly one entry per month with no day-of-month drift.

    Args:
        start_date: Simulation start as a date object or "YYYY-MM-DD" string.
        end_date: Simulation end as a date object or "YYYY-MM-DD" string.

    Returns:
        List of date objects, one per month from start_date through end_date.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()  # type: ignore[arg-type]

    current_date: date = start_date  # type: ignore[assignment]
    date_sequence: list[date] = []

    while current_date <= end_date:  # type: ignore[operator]
        date_sequence.append(current_date)
        next_date = current_date + timedelta(days=32)
        current_date = next_date.replace(day=1)

    return date_sequence


def create_assets(
    path: str = "./configuration/assets",
    asset_name_filter: list[str] | None = None,
) -> list[Asset]:
    """Load and validate asset objects from JSON files in a directory.

    Supported asset types: RealEstate, Equity, Salary.  Each JSON file is
    validated against its typed Pydantic config before the asset object is
    constructed.  Files that fail validation are skipped and an error is logged.

    Args:
        path: Directory containing the asset JSON files.
        asset_name_filter: Optional list of name substrings.  An asset is
            included only if at least one substring matches its ``name`` field
            (case-insensitive).  Pass None to load all assets.

    Returns:
        List of initialised Asset subclass instances.

    Raises:
        FileNotFoundError: If *path* does not exist.
    """
    if asset_name_filter is not None:
        logging.info(f"Asset filter applied: {asset_name_filter}")
        asset_name_filter = [x.lower() for x in asset_name_filter]

    _validators: dict[str, type] = {
        "RealEstate": RealEstateConfig,
        "Equity": EquityConfig,
        "Salary": SalaryConfig,
    }

    assets: list[Asset] = []
    for filename in os.listdir(path):
        if not filename.endswith(".json"):
            continue
        fpath = os.path.join(path, filename)
        with open(fpath, "r") as file:
            asset_data = json.load(file)

        if asset_name_filter:
            matches = [x.lower() in asset_data["name"].lower() for x in asset_name_filter]
            if not any(matches):
                logging.info(
                    f"Skipping asset {asset_data['name']} due to filter: {asset_name_filter}"
                )
                continue

        asset_type = asset_data.get("type", "")
        validator = _validators.get(asset_type)
        if validator is None:
            logging.warning(f"Unknown asset type in {fpath}, skipping.")
            continue

        try:
            validator(**asset_data)
        except ValidationError as e:
            logging.error(f"Invalid {asset_type} config in {fpath}: {e}")
            continue

        if asset_type == "RealEstate":
            logging.debug(f"Loading {fpath} as RE")
            asset: Asset = REAsset(fpath)
        elif asset_type == "Equity":
            logging.debug(f"Loading {fpath} as Equity")
            asset = Equity(fpath)
        else:
            logging.debug(f"Loading {fpath} as SalaryIncome")
            asset = SalaryIncome(fpath)

        assets.append(asset)
    return assets


def persist_metric(
    name: str,
    columns: list[str],
    df: pd.DataFrame,
    output_path: str = "./output/metrics",
) -> None:
    """Save a subset of DataFrame columns to a timestamped CSV file.

    Args:
        name: Metric label used as the filename prefix.
        columns: Column names to include (Period and Date are prepended).
        df: Source DataFrame.
        output_path: Directory where the CSV will be written.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    file_path = os.path.join(output_path, f"{name}_{uuid.uuid1()}.csv")
    columns = ["Period", "Date"] + columns
    df = df[columns]
    df.reset_index(drop=True, inplace=True)
    df.to_csv(file_path, index=False)
    logging.info(f"Metric {name} saved to {file_path}")
