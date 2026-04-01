-- =============================================================
-- Retirement Models — Initial Schema
-- Target: PostgreSQL 14+ on 192.168.1.91:5434
-- Database: retirement-models
-- =============================================================

-- Deduplicated config snapshots.
-- Multiple simulation runs with identical settings share one row.
CREATE TABLE config_snapshots (
    id              SERIAL       PRIMARY KEY,
    config_hash     CHAR(64)     NOT NULL,   -- SHA-256 of world config JSON
    asset_hash      CHAR(64)     NOT NULL,   -- SHA-256 of sorted asset configs JSON
    world_config    JSONB        NOT NULL,   -- WorldConfig fields
    asset_configs   JSONB        NOT NULL,   -- Array of per-asset config dicts
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (config_hash, asset_hash)
);
CREATE INDEX ix_config_snapshots_config_hash ON config_snapshots (config_hash);

-- One row per deterministic simulation run.
CREATE TABLE simulation_runs (
    id                 SERIAL       PRIMARY KEY,
    config_id          INTEGER      NOT NULL REFERENCES config_snapshots(id),
    label              TEXT,
    tags               TEXT[]       NOT NULL DEFAULT '{}',
    run_started_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    run_completed_at   TIMESTAMPTZ,
    n_periods          INTEGER      NOT NULL,
    terminal_net_worth NUMERIC(18,2),
    ruin_period        INTEGER,               -- NULL = solvent throughout
    notes              TEXT
);
CREATE INDEX ix_simulation_runs_config_id   ON simulation_runs (config_id);
CREATE INDEX ix_simulation_runs_tags        ON simulation_runs USING GIN (tags);
CREATE INDEX ix_simulation_runs_started_at  ON simulation_runs (run_started_at DESC);

-- One row per (run × period) — full scenario time-series.
-- Primary access pattern: WHERE run_id = $1 ORDER BY period
CREATE TABLE scenario_metrics (
    id                            BIGSERIAL     PRIMARY KEY,
    run_id                        INTEGER       NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    period                        SMALLINT      NOT NULL,
    period_date                   DATE          NOT NULL,
    age                           NUMERIC(6,3)  NOT NULL,
    retirement_withdrawal         NUMERIC(18,2) NOT NULL DEFAULT 0,
    net_worth                     NUMERIC(18,2) NOT NULL,
    debt                          NUMERIC(18,2) NOT NULL,
    monthly_taxable_income        NUMERIC(18,2) NOT NULL,
    monthly_operational_expenses  NUMERIC(18,2) NOT NULL,
    taxes_paid                    NUMERIC(18,2) NOT NULL,
    free_cash_flows               NUMERIC(18,2) NOT NULL,
    investment                    NUMERIC(18,2) NOT NULL,
    -- Tax breakdown derived from asset DataFrames at write time
    tax_ordinary_income           NUMERIC(18,2),
    tax_capital_gains             NUMERIC(18,2),
    tax_social_security           NUMERIC(18,2),
    UNIQUE (run_id, period)
);
CREATE INDEX ix_scenario_metrics_run_id ON scenario_metrics (run_id, period);

-- One row per (run × asset × period).
-- Dynamic extra columns (appreciation, cash_flow, etc.) land in JSONB extra.
CREATE TABLE asset_metrics (
    id           BIGSERIAL     PRIMARY KEY,
    run_id       INTEGER       NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    asset_name   TEXT          NOT NULL,
    description  TEXT,
    period       SMALLINT      NOT NULL,
    period_date  DATE          NOT NULL,
    value        NUMERIC(18,2) NOT NULL,
    debt         NUMERIC(18,2) NOT NULL,
    income       NUMERIC(18,2) NOT NULL,
    expenses     NUMERIC(18,2) NOT NULL,
    extra        JSONB,
    UNIQUE (run_id, asset_name, period)
);
CREATE INDEX ix_asset_metrics_run_id    ON asset_metrics (run_id, period);
CREATE INDEX ix_asset_metrics_run_asset ON asset_metrics (run_id, asset_name);

-- One row per Monte Carlo run set (N simulations).
-- percentile_bands is pre-computed at write time for fast fan chart serving:
--   {"p10": [float, ...], "p25": [...], "p50": [...], "p75": [...], "p90": [...]}
--   Each array has n_periods elements in period order.
-- terminal_percentiles maps percentile strings to terminal net worth values:
--   {"10": float, "25": float, "50": float, "75": float, "90": float}
CREATE TABLE mc_run_sets (
    id                   SERIAL        PRIMARY KEY,
    config_id            INTEGER       NOT NULL REFERENCES config_snapshots(id),
    label                TEXT,
    tags                 TEXT[]        NOT NULL DEFAULT '{}',
    n_runs               INTEGER       NOT NULL,
    random_seed          INTEGER,
    ruin_probability     NUMERIC(7,6)  NOT NULL,
    run_started_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    run_completed_at     TIMESTAMPTZ,
    percentile_bands     JSONB         NOT NULL,
    terminal_percentiles JSONB         NOT NULL,
    notes                TEXT
);
CREATE INDEX ix_mc_run_sets_config_id   ON mc_run_sets (config_id);
CREATE INDEX ix_mc_run_sets_tags        ON mc_run_sets USING GIN (tags);
CREATE INDEX ix_mc_run_sets_started_at  ON mc_run_sets (run_started_at DESC);

-- One row per individual simulation within an MC run set.
CREATE TABLE mc_run_results (
    id                  BIGSERIAL     PRIMARY KEY,
    mc_set_id           INTEGER       NOT NULL REFERENCES mc_run_sets(id) ON DELETE CASCADE,
    run_index           INTEGER       NOT NULL,
    terminal_net_worth  NUMERIC(18,2) NOT NULL,
    ruin_period         INTEGER,
    UNIQUE (mc_set_id, run_index)
);
CREATE INDEX ix_mc_run_results_set_id ON mc_run_results (mc_set_id);

-- Optional raw trajectories — only populated when store_trajectories=True.
-- trajectories is a JSON array-of-arrays: [[float, ...], ...], n_runs × n_periods.
CREATE TABLE mc_trajectories (
    mc_set_id    INTEGER  PRIMARY KEY REFERENCES mc_run_sets(id) ON DELETE CASCADE,
    trajectories JSONB    NOT NULL
);
