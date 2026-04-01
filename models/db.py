"""Database persistence layer for simulation runs and Monte Carlo results.

Uses SQLAlchemy Core (not ORM) with psycopg2 for bulk-insert performance.
Credentials are loaded from environment variables via pydantic-settings.
"""
from __future__ import annotations

import hashlib
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Generator, Optional

import numpy as np
import pandas as pd
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, Engine, create_engine, text

from models.config import WorldConfig
from models.monte_carlo import MonteCarloResults

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class DatabaseSettings(BaseSettings):
    """Database connection settings loaded from DB_* environment variables.

    With env_prefix="DB_", field `host` maps to env var `DB_HOST`, etc.
    """

    host: str
    port: int = 5434
    name: str
    user: str
    password: SecretStr

    model_config = SettingsConfigDict(env_prefix="DB_")

    @property
    def url(self) -> str:
        """Build a psycopg2 connection URL."""
        pw = self.password.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.user}:{pw}"
            f"@{self.host}:{self.port}/{self.name}"
        )


# ---------------------------------------------------------------------------
# Engine singleton
# ---------------------------------------------------------------------------

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Return the module-level SQLAlchemy engine, creating it on first call."""
    global _engine
    if _engine is None:
        settings = DatabaseSettings()  # type: ignore[call-arg]
        _engine = create_engine(settings.url, pool_pre_ping=True)
        logger.info("Database engine created: %s:%s/%s", settings.host, settings.port, settings.name)
    return _engine


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    """Yield a transactional database connection.

    Commits on clean exit, rolls back on exception.
    """
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _sha256(data: str) -> str:
    """Return the SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode()).hexdigest()


def _hash_configs(world_config: WorldConfig, asset_configs: list[dict[str, Any]]) -> tuple[str, str]:
    """Return (world_hash, asset_hash) for deduplication.

    World config is serialised via Pydantic's model_dump_json for
    deterministic key ordering. Asset configs are sorted by name.
    """
    world_json = world_config.model_dump_json(exclude_none=False)
    sorted_assets = sorted(asset_configs, key=lambda a: a.get("name", ""))
    asset_json = json.dumps(sorted_assets, sort_keys=True, default=str)
    return _sha256(world_json), _sha256(asset_json)


# ---------------------------------------------------------------------------
# Config snapshots
# ---------------------------------------------------------------------------


def save_config_snapshot(
    conn: Connection,
    world_config: WorldConfig,
    asset_configs: list[dict[str, Any]],
) -> int:
    """Upsert a config snapshot and return its id.

    Uses INSERT … ON CONFLICT DO NOTHING then SELECT so both the
    insert-new and already-exists paths return the same id.

    Args:
        conn: Active SQLAlchemy connection.
        world_config: Parsed WorldConfig for this run.
        asset_configs: List of raw asset config dicts (from JSON files).

    Returns:
        config_snapshots.id for the matching row.
    """
    config_hash, asset_hash = _hash_configs(world_config, asset_configs)
    world_json = json.loads(world_config.model_dump_json(exclude_none=False))
    sorted_assets = sorted(asset_configs, key=lambda a: a.get("name", ""))

    conn.execute(
        text(
            """
            INSERT INTO config_snapshots (config_hash, asset_hash, world_config, asset_configs)
            VALUES (:config_hash, :asset_hash, CAST(:world_config AS jsonb), CAST(:asset_configs AS jsonb))
            ON CONFLICT (config_hash, asset_hash) DO NOTHING
            """
        ),
        {
            "config_hash": config_hash,
            "asset_hash": asset_hash,
            "world_config": json.dumps(world_json, default=str),
            "asset_configs": json.dumps(sorted_assets, default=str),
        },
    )
    row = conn.execute(
        text(
            "SELECT id FROM config_snapshots WHERE config_hash = :ch AND asset_hash = :ah"
        ),
        {"ch": config_hash, "ah": asset_hash},
    ).fetchone()
    assert row is not None
    return int(row[0])


# ---------------------------------------------------------------------------
# Single-run persistence
# ---------------------------------------------------------------------------


def save_simulation_run(
    conn: Connection,
    scenario_df: pd.DataFrame,
    asset_dfs: dict[str, Optional[pd.DataFrame]],
    config_id: int,
    world_config: Optional[WorldConfig] = None,
    label: Optional[str] = None,
    tags: Optional[list[str]] = None,
    notes: Optional[str] = None,
) -> int:
    """Save a complete single-run simulation to the database.

    Inserts one row into simulation_runs, bulk-inserts scenario_metrics
    and asset_metrics.

    Args:
        conn: Active SQLAlchemy connection.
        scenario_df: Scenario-level DataFrame from get_scenario_dataframe().
        asset_dfs: Mapping of asset name → asset DataFrame.
        config_id: FK to config_snapshots.
        world_config: Used to derive tax breakdown columns (optional).
        label: Human-readable run label.
        tags: List of tag strings.
        notes: Free-text notes.

    Returns:
        simulation_runs.id for the new row.
    """
    n_periods = len(scenario_df)
    terminal_net_worth: Optional[float] = None
    ruin_period: Optional[int] = None

    if "net_worth" in scenario_df.columns:
        terminal_net_worth = float(scenario_df["net_worth"].iloc[-1])
    if "net_worth" in scenario_df.columns:
        ruin_rows = scenario_df[scenario_df["net_worth"] < 0]
        if not ruin_rows.empty:
            ruin_period = int(ruin_rows.iloc[0]["Period"]) if "Period" in scenario_df.columns else int(ruin_rows.index[0])

    now = datetime.now(timezone.utc)
    result = conn.execute(
        text(
            """
            INSERT INTO simulation_runs
                (config_id, label, tags, run_started_at, run_completed_at,
                 n_periods, terminal_net_worth, ruin_period, notes)
            VALUES
                (:config_id, :label, :tags, :started, :completed,
                 :n_periods, :terminal_net_worth, :ruin_period, :notes)
            RETURNING id
            """
        ),
        {
            "config_id": config_id,
            "label": label,
            "tags": tags or [],
            "started": now,
            "completed": now,
            "n_periods": n_periods,
            "terminal_net_worth": terminal_net_worth,
            "ruin_period": ruin_period,
            "notes": notes,
        },
    )
    run_id = int(result.fetchone()[0])  # type: ignore[index]

    _bulk_insert_scenario_metrics(conn, run_id, scenario_df, asset_dfs, world_config)
    _bulk_insert_asset_metrics(conn, run_id, asset_dfs)

    logger.info("Saved simulation run %d (%d periods, terminal_net_worth=%s)", run_id, n_periods, terminal_net_worth)
    return run_id


def _derive_tax_breakdown(
    scenario_df: pd.DataFrame,
    asset_dfs: dict[str, Optional[pd.DataFrame]],
    world_config: Optional[WorldConfig],
) -> tuple[list[Optional[float]], list[Optional[float]], list[Optional[float]]]:
    """Derive per-period tax breakdown from asset income and tax rates.

    Returns three parallel lists (ordinary, capital_gains, social_security),
    each with one float per scenario period. Returns (None-lists) if
    world_config is not provided.
    """
    n = len(scenario_df)
    nones: list[Optional[float]] = [None] * n

    if world_config is None:
        return nones, nones, nones

    # Build a period-indexed DataFrame of income by tax_class
    # by merging all asset DataFrames.
    tax_classes = world_config.tax_classes
    ordinary_rate = float(tax_classes.income)
    cg_rate = float(tax_classes.capital_gain)
    ss_rate = float(tax_classes.social_security)

    ordinary_income = np.zeros(n)
    capital_gains = np.zeros(n)
    social_security = np.zeros(n)

    for asset_name, df in asset_dfs.items():
        if df is None or df.empty or "Income" not in df.columns:
            continue
        # Determine tax class from asset name heuristics or config
        name_lower = asset_name.lower()
        income_vals = df["Income"].values[:n] if len(df) >= n else np.pad(df["Income"].values, (0, n - len(df)))

        if "social" in name_lower or "ss" in name_lower:
            social_security += income_vals.astype(float)
        elif "brokerage" in name_lower or "capital" in name_lower:
            capital_gains += income_vals.astype(float)
        else:
            ordinary_income += income_vals.astype(float)

    # Multiply by rates to get tax contribution
    ord_taxes = (ordinary_income * ordinary_rate).tolist()
    cg_taxes = (capital_gains * cg_rate).tolist()
    ss_taxes = (social_security * ss_rate).tolist()
    return ord_taxes, cg_taxes, ss_taxes


def _bulk_insert_scenario_metrics(
    conn: Connection,
    run_id: int,
    scenario_df: pd.DataFrame,
    asset_dfs: dict[str, Optional[pd.DataFrame]],
    world_config: Optional[WorldConfig],
) -> None:
    """Bulk-insert all scenario_metrics rows for one run."""
    ord_taxes, cg_taxes, ss_taxes = _derive_tax_breakdown(scenario_df, asset_dfs, world_config)

    col_map = {
        "period": "Period",
        "period_date": "Date",
        "age": "age",
        "retirement_withdrawal": "retirement_withdrawal",
        "net_worth": "net_worth",
        "debt": "debt",
        "monthly_taxable_income": "monthly_taxable_income",
        "monthly_operational_expenses": "monthly_operational_expenses",
        "taxes_paid": "taxes_paid",
        "free_cash_flows": "free_cash_flows",
        "investment": "investment",
    }

    records = []
    for i, (_, row) in enumerate(scenario_df.iterrows()):
        rec: dict[str, Any] = {"run_id": run_id}
        for db_col, df_col in col_map.items():
            rec[db_col] = row[df_col] if df_col in scenario_df.columns else None
        rec["tax_ordinary_income"] = ord_taxes[i]
        rec["tax_capital_gains"] = cg_taxes[i]
        rec["tax_social_security"] = ss_taxes[i]
        records.append(rec)

    conn.execute(
        text(
            """
            INSERT INTO scenario_metrics
                (run_id, period, period_date, age, retirement_withdrawal,
                 net_worth, debt, monthly_taxable_income,
                 monthly_operational_expenses, taxes_paid,
                 free_cash_flows, investment,
                 tax_ordinary_income, tax_capital_gains, tax_social_security)
            VALUES
                (:run_id, :period, :period_date, :age, :retirement_withdrawal,
                 :net_worth, :debt, :monthly_taxable_income,
                 :monthly_operational_expenses, :taxes_paid,
                 :free_cash_flows, :investment,
                 :tax_ordinary_income, :tax_capital_gains, :tax_social_security)
            """
        ),
        records,
    )


def _bulk_insert_asset_metrics(
    conn: Connection,
    run_id: int,
    asset_dfs: dict[str, Optional[pd.DataFrame]],
) -> None:
    """Bulk-insert all asset_metrics rows for one run."""
    known_cols = {"Period", "Date", "Name", "Description", "Value", "Debt", "Income", "Expenses"}
    records = []

    for asset_name, df in asset_dfs.items():
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            extra_cols = {c: row[c] for c in df.columns if c not in known_cols}
            # Convert non-serialisable types
            extra: Optional[str] = json.dumps(extra_cols, default=str) if extra_cols else None
            records.append(
                {
                    "run_id": run_id,
                    "asset_name": asset_name,
                    "description": row.get("Description") if "Description" in df.columns else None,
                    "period": int(row["Period"]) if "Period" in df.columns else None,
                    "period_date": row["Date"] if "Date" in df.columns else None,
                    "value": float(row["Value"]) if "Value" in df.columns else 0.0,
                    "debt": float(row["Debt"]) if "Debt" in df.columns else 0.0,
                    "income": float(row["Income"]) if "Income" in df.columns else 0.0,
                    "expenses": float(row["Expenses"]) if "Expenses" in df.columns else 0.0,
                    "extra": extra,
                }
            )

    if not records:
        return

    conn.execute(
        text(
            """
            INSERT INTO asset_metrics
                (run_id, asset_name, description, period, period_date,
                 value, debt, income, expenses, extra)
            VALUES
                (:run_id, :asset_name, :description, :period, :period_date,
                 :value, :debt, :income, :expenses, CAST(:extra AS jsonb))
            """
        ),
        records,
    )


# ---------------------------------------------------------------------------
# Monte Carlo persistence
# ---------------------------------------------------------------------------


def _compute_percentile_bands(
    mc_results: MonteCarloResults,
    percentiles: list[float] = [10.0, 25.0, 50.0, 75.0, 90.0],
) -> dict[str, list[float]]:
    """Compute per-period percentile bands across all MC trajectories.

    Requires store_trajectories=True on mc_results.
    Returns dict like {"p10": [...], "p25": [...], ..., "p90": [...]}.
    """
    trajectories = mc_results.trajectory_array()
    if not trajectories:
        return {}
    n_periods = max(len(t) for t in trajectories)
    arr = np.full((len(trajectories), n_periods), np.nan)
    for i, t in enumerate(trajectories):
        arr[i, : len(t)] = t

    bands: dict[str, list[float]] = {}
    for p in percentiles:
        key = f"p{int(p)}"
        bands[key] = np.nanpercentile(arr, p, axis=0).tolist()
    return bands


def _compute_terminal_percentiles(
    mc_results: MonteCarloResults,
    percentiles: list[float] = [10.0, 25.0, 50.0, 75.0, 90.0],
) -> dict[str, float]:
    """Compute terminal wealth percentiles from mc_results."""
    pct_map = mc_results.terminal_wealth_percentiles(percentiles)
    return {str(int(k)): float(v) for k, v in pct_map.items()}


def save_mc_run(
    conn: Connection,
    mc_results: MonteCarloResults,
    config_id: int,
    label: Optional[str] = None,
    tags: Optional[list[str]] = None,
    random_seed: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    """Save a completed MC run set to the database.

    Computes and stores percentile_bands (requires store_trajectories=True
    on mc_results for band computation). Bulk-inserts mc_run_results rows
    and optionally saves raw trajectories.

    Args:
        conn: Active SQLAlchemy connection.
        mc_results: Aggregated results from MonteCarloRunner.run().
        config_id: FK to config_snapshots.
        label: Human-readable label.
        tags: List of tag strings.
        random_seed: The seed used for this run, if any.
        notes: Free-text notes.

    Returns:
        mc_run_sets.id for the new row.
    """
    ruin_prob = mc_results.ruin_probability()
    terminal_pcts = _compute_terminal_percentiles(mc_results)

    if mc_results.has_trajectories():
        pct_bands = _compute_percentile_bands(mc_results)
    else:
        pct_bands = {}

    now = datetime.now(timezone.utc)
    result = conn.execute(
        text(
            """
            INSERT INTO mc_run_sets
                (config_id, label, tags, n_runs, random_seed, ruin_probability,
                 run_started_at, run_completed_at,
                 percentile_bands, terminal_percentiles, notes)
            VALUES
                (:config_id, :label, :tags, :n_runs, :random_seed, :ruin_prob,
                 :started, :completed,
                 CAST(:pct_bands AS jsonb), CAST(:terminal_pcts AS jsonb), :notes)
            RETURNING id
            """
        ),
        {
            "config_id": config_id,
            "label": label,
            "tags": tags or [],
            "n_runs": mc_results.n_runs,
            "random_seed": random_seed,
            "ruin_prob": ruin_prob,
            "started": now,
            "completed": now,
            "pct_bands": json.dumps(pct_bands),
            "terminal_pcts": json.dumps(terminal_pcts),
            "notes": notes,
        },
    )
    mc_set_id = int(result.fetchone()[0])  # type: ignore[index]

    # Bulk-insert individual run results
    run_records = [
        {
            "mc_set_id": mc_set_id,
            "run_index": r.run_id,
            "terminal_net_worth": float(r.terminal_net_worth),
            "ruin_period": r.ruin_period,
        }
        for r in mc_results.results
    ]
    conn.execute(
        text(
            """
            INSERT INTO mc_run_results (mc_set_id, run_index, terminal_net_worth, ruin_period)
            VALUES (:mc_set_id, :run_index, :terminal_net_worth, :ruin_period)
            """
        ),
        run_records,
    )

    # Optionally store raw trajectories
    if mc_results.has_trajectories():
        conn.execute(
            text(
                "INSERT INTO mc_trajectories (mc_set_id, trajectories) VALUES (:id, CAST(:traj AS jsonb))"
            ),
            {"id": mc_set_id, "traj": json.dumps(mc_results.trajectory_array())},
        )

    logger.info(
        "Saved MC run set %d: %d runs, ruin_prob=%.3f",
        mc_set_id,
        mc_results.n_runs,
        ruin_prob,
    )
    return mc_set_id


# ---------------------------------------------------------------------------
# Load functions (called by API blueprints)
# ---------------------------------------------------------------------------


def load_run_summary_list(
    conn: Connection,
    tag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return all simulation runs with summary metadata (no time-series).

    Args:
        conn: Active SQLAlchemy connection.
        tag: Optional tag to filter by.
        limit: Maximum rows to return.
        offset: Rows to skip.

    Returns:
        List of dicts matching the simulation_runs schema.
    """
    where = ":tag = ANY(tags)" if tag else "TRUE"
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if tag:
        params["tag"] = tag

    rows = conn.execute(
        text(
            f"""
            SELECT id, config_id, label, tags, run_started_at, run_completed_at,
                   n_periods, terminal_net_worth, ruin_period, notes
            FROM simulation_runs
            WHERE {where}
            ORDER BY run_started_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def load_run_scenario(conn: Connection, run_id: int) -> list[dict[str, Any]]:
    """Return scenario_metrics rows for one run, ordered by period."""
    rows = conn.execute(
        text(
            """
            SELECT period, period_date, age, retirement_withdrawal,
                   net_worth, debt, monthly_taxable_income,
                   monthly_operational_expenses, taxes_paid,
                   free_cash_flows, investment,
                   tax_ordinary_income, tax_capital_gains, tax_social_security
            FROM scenario_metrics
            WHERE run_id = :run_id
            ORDER BY period
            """
        ),
        {"run_id": run_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def load_run_assets(
    conn: Connection,
    run_id: int,
    asset_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return asset_metrics rows for one run.

    Args:
        conn: Active SQLAlchemy connection.
        run_id: FK to simulation_runs.
        asset_name: Optional filter to a single asset.

    Returns:
        List of asset metric dicts ordered by (asset_name, period).
    """
    where = "run_id = :run_id" + (" AND asset_name = :asset_name" if asset_name else "")
    params: dict[str, Any] = {"run_id": run_id}
    if asset_name:
        params["asset_name"] = asset_name

    rows = conn.execute(
        text(
            f"""
            SELECT asset_name, description, period, period_date,
                   value, debt, income, expenses, extra
            FROM asset_metrics
            WHERE {where}
            ORDER BY asset_name, period
            """
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def load_run_tax(conn: Connection, run_id: int) -> list[dict[str, Any]]:
    """Return tax-focused columns plus derived effective_rate for one run."""
    rows = conn.execute(
        text(
            """
            SELECT period, period_date,
                   taxes_paid, monthly_taxable_income,
                   tax_ordinary_income, tax_capital_gains, tax_social_security
            FROM scenario_metrics
            WHERE run_id = :run_id
            ORDER BY period
            """
        ),
        {"run_id": run_id},
    ).mappings().all()

    result = []
    for r in rows:
        d = dict(r)
        income = float(d["monthly_taxable_income"] or 0)
        taxes = float(d["taxes_paid"] or 0)
        d["effective_rate"] = (taxes / income) if income != 0 else 0.0
        result.append(d)
    return result


def load_config(conn: Connection, config_id: int) -> Optional[dict[str, Any]]:
    """Return config_snapshot for the given config_id."""
    row = conn.execute(
        text(
            "SELECT id, config_hash, asset_hash, world_config, asset_configs, created_at "
            "FROM config_snapshots WHERE id = :id"
        ),
        {"id": config_id},
    ).mappings().fetchone()
    return dict(row) if row else None


def load_mc_summary_list(
    conn: Connection,
    tag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return all MC run sets with summary metadata."""
    where = ":tag = ANY(tags)" if tag else "TRUE"
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if tag:
        params["tag"] = tag

    rows = conn.execute(
        text(
            f"""
            SELECT id, config_id, label, tags, n_runs, random_seed,
                   ruin_probability, run_started_at, run_completed_at,
                   terminal_percentiles, notes
            FROM mc_run_sets
            WHERE {where}
            ORDER BY run_started_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def load_mc_detail(
    conn: Connection,
    mc_set_id: int,
    include_individual_runs: bool = False,
) -> Optional[dict[str, Any]]:
    """Return MC run set detail including percentile bands.

    Args:
        conn: Active SQLAlchemy connection.
        mc_set_id: PK of the mc_run_sets row.
        include_individual_runs: If True, also join mc_run_results rows.

    Returns:
        Dict with summary and percentile_bands, or None if not found.
    """
    row = conn.execute(
        text(
            """
            SELECT id, config_id, label, tags, n_runs, random_seed,
                   ruin_probability, run_started_at, run_completed_at,
                   percentile_bands, terminal_percentiles, notes
            FROM mc_run_sets
            WHERE id = :id
            """
        ),
        {"id": mc_set_id},
    ).mappings().fetchone()
    if row is None:
        return None

    detail: dict[str, Any] = dict(row)
    if include_individual_runs:
        run_rows = conn.execute(
            text(
                """
                SELECT run_index, terminal_net_worth, ruin_period
                FROM mc_run_results
                WHERE mc_set_id = :id
                ORDER BY run_index
                """
            ),
            {"id": mc_set_id},
        ).mappings().all()
        detail["individual_runs"] = [dict(r) for r in run_rows]
    else:
        detail["individual_runs"] = None

    return detail
