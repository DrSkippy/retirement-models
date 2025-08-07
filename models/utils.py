from datetime import datetime
import os
from datetime import timedelta
from models.assets import *



def create_datetime_sequence(start_date, end_date):
    """
    Create a sequence of datetime objects from start_date to end_date with a specified step in days.
    
    :param start_date: The starting date as a datetime object.
    :param end_date: The ending date as a datetime object.
    :param step_days: The number of days to increment for each step in the sequence.
    :return: A list of datetime objects.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    dt = timedelta(days=32)

    current_date = start_date
    date_sequence = []

    while current_date <= end_date:
        date_sequence.append(current_date)
        current_date += dt
        current_date = current_date.replace(day=1)

    return date_sequence


def create_assets(path="./configuration/assets", asset_name_filter=None):
    """
    Processes JSON files in a specified directory to create asset objects based on their type. Supported
    asset types include 'RealEstate', 'Equity', and 'Salary'. Unrecognized asset types are logged and skipped.

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
    if asset_name_filter is not None:
        logging.info(f"Asset filter applied: {asset_name_filter}")
        asset_name_filter = [x.lower() for x in asset_name_filter]

    assets = []
    for filename in os.listdir(path):
        if filename.endswith('.json'):
            fpath = os.path.join(path, filename)
            with (open(fpath, 'r') as file):
                asset_data = json.load(file)
                if asset_name_filter and asset_data["name"].lower() not in asset_name_filter:
                    logging.info(f"Skipping asset {asset_data['name']} due to filter: {asset_name_filter}")
                    continue
                if asset_data['type'] == 'RealEstate':
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
            assets.append(asset)
    return assets
