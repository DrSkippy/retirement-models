"""Blueprint: simulation run list and detail endpoints."""
from __future__ import annotations

import logging

from flask import Blueprint, Response, abort, jsonify, request

from models.db import get_connection, load_run_scenario, load_run_summary_list

logger = logging.getLogger(__name__)

runs_bp = Blueprint("runs", __name__)


def _int_param(name: str, default: int, max_val: int | None = None) -> int:
    """Parse an integer query parameter, returning 400 on invalid input."""
    try:
        val = int(request.args.get(name, default))
    except (ValueError, TypeError):
        abort(400, description=f"'{name}' must be an integer")
    if max_val is not None:
        val = min(val, max_val)
    return val


@runs_bp.get("/runs")
def list_runs() -> Response:
    """GET /api/runs — list all simulation runs.

    Query params:
        tag (str): Filter to runs with this tag.
        limit (int): Max rows (default 50, max 200).
        offset (int): Rows to skip (default 0).
    """
    tag = request.args.get("tag")
    limit = _int_param("limit", 50, max_val=200)
    offset = _int_param("offset", 0)
    logger.debug("GET /api/runs tag=%s limit=%d offset=%d", tag, limit, offset)
    with get_connection() as conn:
        runs = load_run_summary_list(conn, tag=tag, limit=limit, offset=offset)
    logger.debug("Returning %d runs", len(runs))
    return jsonify(runs)


@runs_bp.get("/runs/<int:run_id>")
def get_run(run_id: int) -> Response:
    """GET /api/runs/<id> — run summary + full scenario time-series."""
    logger.debug("GET /api/runs/%d", run_id)
    with get_connection() as conn:
        from sqlalchemy import text

        row = conn.execute(
            text(
                """
                SELECT id, config_id, label, tags, run_started_at, run_completed_at,
                       n_periods, terminal_net_worth, ruin_period, notes
                FROM simulation_runs WHERE id = :id
                """
            ),
            {"id": run_id},
        ).mappings().fetchone()
        if row is None:
            abort(404)
        metrics = load_run_scenario(conn, run_id)
    return jsonify({"run": dict(row), "metrics": metrics})
