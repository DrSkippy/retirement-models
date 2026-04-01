"""Blueprint: Monte Carlo run set endpoints."""
from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, request

from models.db import get_connection, load_mc_detail, load_mc_summary_list

mc_bp = Blueprint("mc", __name__)


@mc_bp.get("/mc")
def list_mc_sets() -> Response:
    """GET /api/mc — list all Monte Carlo run sets.

    Query params:
        tag (str): Filter to sets with this tag.
        limit (int): Max rows (default 50).
        offset (int): Rows to skip (default 0).
    """
    tag = request.args.get("tag")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    with get_connection() as conn:
        sets = load_mc_summary_list(conn, tag=tag, limit=limit, offset=offset)
    return jsonify(sets)


@mc_bp.get("/mc/<int:mc_set_id>")
def get_mc_set(mc_set_id: int) -> Response:
    """GET /api/mc/<id> — MC run set detail with percentile bands.

    Query params:
        include_runs (bool): If true, include individual run results.
    """
    include_runs = request.args.get("include_runs", "false").lower() == "true"
    with get_connection() as conn:
        detail = load_mc_detail(conn, mc_set_id, include_individual_runs=include_runs)
    if detail is None:
        abort(404)
    return jsonify(detail)
