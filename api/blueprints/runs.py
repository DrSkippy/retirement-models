"""Blueprint: simulation run list and detail endpoints."""
from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, request

from models.db import get_connection, load_run_scenario, load_run_summary_list

runs_bp = Blueprint("runs", __name__)


@runs_bp.get("/runs")
def list_runs() -> Response:
    """GET /api/runs — list all simulation runs.

    Query params:
        tag (str): Filter to runs with this tag.
        limit (int): Max rows (default 50).
        offset (int): Rows to skip (default 0).
    """
    tag = request.args.get("tag")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    with get_connection() as conn:
        runs = load_run_summary_list(conn, tag=tag, limit=limit, offset=offset)
    return jsonify(runs)


@runs_bp.get("/runs/<int:run_id>")
def get_run(run_id: int) -> Response:
    """GET /api/runs/<id> — run summary + full scenario time-series."""
    with get_connection() as conn:
        summaries = load_run_summary_list(conn, limit=1, offset=0)
        # Fetch the specific run
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
