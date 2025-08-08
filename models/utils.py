import os
import uuid
from datetime import timedelta

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

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


def plot_asset_model_data(df, name, offset=4):
    """Plot asset model data"""
    if df.empty:
        logging.error("No data to plot.")
        return

    plt.style.use('seaborn-v0_8')
    cols, rows = 3, 3
    FONT_SIZE = 16
    fig, axes = plt.subplots(cols, rows, figsize=(20, MONTHS_IN_YEAR))
    fig.suptitle('Retirement Financial Model - Comprehensive Analysis', fontsize=26, fontweight='bold')

    header_list = df.columns.tolist()[offset:]  # Exclude 'Date' and 'Period' columns
    # plot indexes
    with PdfPages(f'./output/scenario_{name}.pdf') as pdf:
        for i in range(cols):
            for j in range(rows):
                try:
                    column = header_list.pop()
                    axes[i, j].plot(df['Date'], df[column], label=column)
                    axes[i, j].set_title(f'{name} Asset Model Data Over Time', fontsize=FONT_SIZE)
                    axes[i, j].set_xlabel('Date', fontsize=FONT_SIZE)
                    axes[i, j].set_ylabel('Value', fontsize=FONT_SIZE)
                    axes[i, j].legend(fontsize=FONT_SIZE)
                    axes[i, j].grid()
                except IndexError:
                    break
        pdf.savefig()  # saves the current figure into a pdf page
        plt.close()

def persist_metric(name, columns, df, output_path="./output/metrics"):
    """
    Save a DataFrame to a CSV file in the specified output path.

    :param name: The name of the metric to be saved.
    :param df: The DataFrame containing the metric data.
    :param output_path: The directory where the CSV file will be saved.
    """
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    file_path = os.path.join(output_path, f"{name}_{uuid.uuid1()}.csv")
    columns = ["Period", "Date"] + columns  # Ensure columns is a list
    df = df[columns]  # Filter the DataFrame to include only the specified columns
    df.reset_index(drop=True, inplace=True)  # Reset index to ensure clean CSV output
    df.to_csv(file_path, index=False)
    logging.info(f"Metric {name} saved to {file_path}")
