from logging.config import dictConfig

from models.scenarios import *

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
    # Initialize the model with the configuration file
    model = RetirementFinancialModel(CONFIG_FILE)

    # Load the assets and scenarios from the configurationdd
    model.setup("./configuration/assets")

    # Run the model with specified scenarios
    rm, rh, am, ah = model.run_model()
    #print(results)
    for asset in model.assets:
        logging.info(f"Asset: {asset.name}, Value: {asset.value}")
        df = model.get_asset_dataframe(asset.name, am, ah)
        model.plot_asset_model_data(df, asset.name)

# REPLACED     # Generate summary reports from the results
# REPLACED     summary_data = model.generate_reports(results)
# REPLACED
# REPLACED     # Save results to CSV for further analysis
# REPLACED     summary_data.to_csv('retirement_model_results.csv', index=False)
# REPLACED
# REPLACED     print(f"\nDetailed results saved to 'retirement_model_results.csv'")
# REPLACED     print(f"Total scenarios modeled: {len(results)}")
# REPLACED     print(f"Total quarters analyzed: {len(summary_data)}")
# REPLACED     model = RetirementFinancialModel(CONFIG_FILE)
# REPLACED     results = model.run_model(['base', 'delayed_ss'])
# REPLACED     summary_data = model.generate_reports(results)
# REPLACED
# REPLACED     # Save results to CSV for further analysis
# REPLACED     summary_data.to_csv('retirement_model_results.csv', index=False)
# REPLACED     print(f"\nDetailed results saved to 'retirement_model_results.csv'")
# REPLACED     print(f"Total scenarios modeled: {len(results)}")
# REPLACED     print(f"Total quarters analyzed: {len(summary_data)}")
