"""Blueprint: per-asset time-series endpoint."""
from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, request
from sqlalchemy import text

from models.db import get_connection, load_run_assets

assets_bp = Blueprint("assets", __name__)


@assets_bp.get("/runs/<int:run_id>/assets")
def get_run_assets(run_id: int) -> Response:
    """GET /api/runs/<id>/assets — asset metrics for one run.

    Query params:
        asset (str): Filter to a single asset name.
    """
    asset_name = request.args.get("asset")
    with get_connection() as conn:
        # Verify run exists
        exists = conn.execute(
            text("SELECT 1 FROM simulation_runs WHERE id = :id"),
            {"id": run_id},
        ).fetchone()
        if exists is None:
            abort(404)
        rows = load_run_assets(conn, run_id, asset_name=asset_name)
    return jsonify(rows)
