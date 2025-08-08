import argparse
from logging.config import dictConfig

from models.scenarios import *
from models.utils import plot_asset_model_data

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
            'maxBytes': 2500000,
            'backupCount': 3
        }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['file']
    }
})

CONFIG_FILE = "./configuration/config.json"
# Run the model
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Retirement Financial Model")
    parser.add_argument('--asset-details', action='store_true', help='Show details for each asset')
    args = parser.parse_args()
    asset_details = args.asset_details
    # Initialize the model with the configuration file
    model = RetirementFinancialModel(CONFIG_FILE)

    # Load the assets and scenarios from the configurationdd
    model.setup("./configuration/assets")

    # Run the model with specified scenarios
    rm, rh, am, ah = model.run_model()

    if asset_details:
        for asset in model.assets:
            logging.info(f"Asset: {asset.name}, Value: {asset.value}")
            df = model.get_asset_dataframe(asset.name, am, ah)
            plot_asset_model_data(df, asset.name)

    df = model.get_scenario_dataframe(rm, rh)
    plot_asset_model_data(df, 'Retirement Model', 2)

    persist_metric("net_worth", ["net_worth"], df, output_path="./output/metrics")
