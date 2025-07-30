from models.claude import *
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

CONFIG_FILE = "./config.json"
# Run the model
if __name__ == "__main__":
    model = RetirementFinancialModel(CONFIG_FILE)
    results = model.run_model(['base', 'delayed_ss'])
    summary_data = model.generate_reports(results)

    # Save results to CSV for further analysis
    summary_data.to_csv('retirement_model_results.csv', index=False)
    print(f"\nDetailed results saved to 'retirement_model_results.csv'")
    print(f"Total scenarios modeled: {len(results)}")
    print(f"Total quarters analyzed: {len(summary_data)}")