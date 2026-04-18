import argparse
import json
from logging.config import dictConfig
from pathlib import Path

import yaml

from models.html_report import HtmlReportBuilder
from models.monte_carlo import MonteCarloRunner
from models.scenarios import *

_cfg = yaml.safe_load(Path("config.yaml").read_text())

_log = _cfg["logging"]
Path(_log["file"]).parent.mkdir(parents=True, exist_ok=True)
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {"format": _log["format"]},
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "level": _log["level"],
                "filename": _log["file"],
                "mode": "a",
                "encoding": "utf-8",
                "maxBytes": _log["max_bytes"],
                "backupCount": _log["backup_count"],
            }
        },
        "root": {"level": _log["level"], "handlers": ["file"]},
    }
)

CONFIG_FILE = _cfg["paths"]["model_config"]
ASSETS_DIR = _cfg["paths"]["assets_dir"]
OUTPUT_DIR = _cfg["paths"]["output_dir"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Retirement Financial Model")
    parser.add_argument(
        "--monte-carlo",
        type=int,
        metavar="N",
        default=0,
        help="Run N Monte Carlo simulations and generate a fan-chart report",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Save simulation output to PostgreSQL after the run completes",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Human-readable label for this run",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="TAG",
        help="Tag for this run (repeatable: --tag baseline --tag v2)",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Free-text notes stored with the run",
    )
    args = parser.parse_args()

    # Load asset config dicts once — used for DB config snapshot
    asset_config_dicts = [
        json.loads(Path(f).read_text())
        for f in sorted(Path(ASSETS_DIR).glob("*.json"))
    ]

    if args.monte_carlo > 0:
        print(f"Running {args.monte_carlo} Monte Carlo simulations …")
        runner = MonteCarloRunner(
            config_file_path=CONFIG_FILE,
            asset_config_path=ASSETS_DIR,
            n_runs=args.monte_carlo,
            store_trajectories=args.save_db,  # trajectories needed for percentile bands
        )
        mc_results = runner.run()
        ruin_pct = mc_results.ruin_probability()
        print(
            f"Done. Ruin probability: {ruin_pct:.1%}  "
            f"(terminal wealth P50: ${mc_results.terminal_wealth_percentiles([50])[50]:,.0f})"
        )
        from models.config import WorldConfig
        world_config = WorldConfig.from_json(CONFIG_FILE)
        report = HtmlReportBuilder(output_dir=OUTPUT_DIR, label=args.label)
        run_dir = report.monte_carlo_report(
            mc_results,
            world_config=world_config,
            asset_config_dicts=asset_config_dicts,
        )
        print(f"Monte Carlo mini-site: {run_dir / 'index.html'}")

        if args.save_db:
            from models.db import get_connection, save_config_snapshot, save_mc_run

            # Load a single model just to get the WorldConfig
            _model = RetirementFinancialModel(CONFIG_FILE)
            with get_connection() as conn:
                config_id = save_config_snapshot(conn, _model.world_config, asset_config_dicts)
                mc_set_id = save_mc_run(
                    conn,
                    mc_results=mc_results,
                    config_id=config_id,
                    label=args.label,
                    tags=args.tag or [],
                    notes=args.notes,
                )
            print(f"Saved MC run set #{mc_set_id} to database.")

    else:
        # Single deterministic run
        model = RetirementFinancialModel(CONFIG_FILE)
        model.setup(ASSETS_DIR)
        rm, rh, am, ah = model.run_model(show_progress=True)

        df = model.get_scenario_dataframe(rm, rh)
        persist_metric("net_worth", ["net_worth"], df, output_path=f"{OUTPUT_DIR}/metrics")

        asset_dfs = {
            asset.name: model.get_asset_dataframe(asset.name, am, ah)
            for asset in model.assets
        }
        report = HtmlReportBuilder(output_dir=OUTPUT_DIR, label=args.label)
        run_dir = report.single_run_report(
            df,
            asset_dfs,
            world_config=model.world_config,
            asset_config_dicts=asset_config_dicts,
        )
        print(f"Single-run mini-site: {run_dir / 'index.html'}")

        if args.save_db:
            from models.db import get_connection, save_config_snapshot, save_simulation_run

            asset_dfs = {
                asset.name: model.get_asset_dataframe(asset.name, am, ah)
                for asset in model.assets
            }
            with get_connection() as conn:
                config_id = save_config_snapshot(conn, model.world_config, asset_config_dicts)
                run_id = save_simulation_run(
                    conn,
                    scenario_df=df,
                    asset_dfs=asset_dfs,
                    config_id=config_id,
                    world_config=model.world_config,
                    label=args.label,
                    tags=args.tag or [],
                    notes=args.notes,
                )
            print(f"Saved run #{run_id} to database.")
