import argparse
from logging.config import dictConfig

from models.monte_carlo import MonteCarloRunner
from models.reporting import ReportBuilder
from models.scenarios import *
from models.utils import plot_asset_model_data

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "level": "DEBUG",
                "filename": "assets.log",
                "mode": "a",
                "encoding": "utf-8",
                "maxBytes": 2500000,
                "backupCount": 3,
            }
        },
        "root": {"level": "DEBUG", "handlers": ["file"]},
    }
)

CONFIG_FILE = "./configuration/config.json"
ASSETS_DIR = "./configuration/assets"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Retirement Financial Model")
    parser.add_argument(
        "--asset-details",
        action="store_true",
        help="Generate per-asset plots",
    )
    parser.add_argument(
        "--monte-carlo",
        type=int,
        metavar="N",
        default=0,
        help="Run N Monte Carlo simulations and generate a fan-chart report",
    )
    args = parser.parse_args()

    if args.monte_carlo > 0:
        print(f"Running {args.monte_carlo} Monte Carlo simulations …")
        runner = MonteCarloRunner(
            config_file_path=CONFIG_FILE,
            asset_config_path=ASSETS_DIR,
            n_runs=args.monte_carlo,
        )
        mc_results = runner.run()
        ruin_pct = mc_results.ruin_probability()
        print(
            f"Done. Ruin probability: {ruin_pct:.1%}  "
            f"(terminal wealth P50: ${mc_results.terminal_wealth_percentiles([50])[50]:,.0f})"
        )
        report = ReportBuilder(output_dir="./output")
        path = report.monte_carlo_report(mc_results)
        print(f"Monte Carlo report: {path}")
    else:
        # Single deterministic run
        model = RetirementFinancialModel(CONFIG_FILE)
        model.setup(ASSETS_DIR)
        rm, rh, am, ah = model.run_model(show_progress=True)

        if args.asset_details:
            for asset in model.assets:
                logging.info(f"Asset: {asset.name}, Value: {asset.value}")
                df = model.get_asset_dataframe(asset.name, am, ah)
                plot_asset_model_data(df, asset.name)

        df = model.get_scenario_dataframe(rm, rh)
        plot_asset_model_data(df, "Retirement Model", 2)
        persist_metric("net_worth", ["net_worth"], df, output_path="./output/metrics")
