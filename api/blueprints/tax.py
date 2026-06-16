"""Blueprint: tax analysis endpoint."""
from __future__ import annotations

import logging

from flask import Blueprint, Response, abort, jsonify
from sqlalchemy import text

from models.db import get_connection, load_run_tax

logger = logging.getLogger(__name__)

tax_bp = Blueprint("tax", __name__)


@tax_bp.get("/runs/<int:run_id>/tax")
def get_run_tax(run_id: int) -> Response:
    """GET /api/runs/<id>/tax — tax breakdown per period.

    Returns taxes_paid, taxable_income, tax class breakdown, and
    derived effective_rate for each simulation period.
    """
    logger.debug("GET /api/runs/%d/tax", run_id)
    with get_connection() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM simulation_runs WHERE id = :id"),
            {"id": run_id},
        ).fetchone()
        if exists is None:
            abort(404)
        rows = load_run_tax(conn, run_id)
    logger.debug("Returning %d tax rows for run %d", len(rows), run_id)
    return jsonify(rows)
