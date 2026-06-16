"""Blueprint: Monte Carlo run set endpoints."""
from __future__ import annotations

import logging

from flask import Blueprint, Response, abort, jsonify, request

from models.db import get_connection, load_mc_detail, load_mc_summary_list

logger = logging.getLogger(__name__)

mc_bp = Blueprint("mc", __name__)


def _int_param(name: str, default: int, max_val: int | None = None) -> int:
    """Parse an integer query parameter, returning 400 on invalid input."""
    try:
        val = int(request.args.get(name, default))
    except (ValueError, TypeError):
        abort(400, description=f"'{name}' must be an integer")
    if max_val is not None:
        val = min(val, max_val)
    return val


@mc_bp.get("/mc")
def list_mc_sets() -> Response:
    """GET /api/mc — list all Monte Carlo run sets.

    Query params:
        tag (str): Filter to sets with this tag.
        limit (int): Max rows (default 50, max 200).
        offset (int): Rows to skip (default 0).
    """
    tag = request.args.get("tag")
    limit = _int_param("limit", 50, max_val=200)
    offset = _int_param("offset", 0)
    logger.debug("GET /api/mc tag=%s limit=%d offset=%d", tag, limit, offset)
    with get_connection() as conn:
        sets = load_mc_summary_list(conn, tag=tag, limit=limit, offset=offset)
    logger.debug("Returning %d MC sets", len(sets))
    return jsonify(sets)


@mc_bp.get("/mc/<int:mc_set_id>")
def get_mc_set(mc_set_id: int) -> Response:
    """GET /api/mc/<id> — MC run set detail with percentile bands.

    Query params:
        include_runs (bool): If true, include individual run results.
    """
    include_runs = request.args.get("include_runs", "false").lower() == "true"
    logger.debug("GET /api/mc/%d include_runs=%s", mc_set_id, include_runs)
    with get_connection() as conn:
        detail = load_mc_detail(conn, mc_set_id, include_individual_runs=include_runs)
    if detail is None:
        abort(404)
    return jsonify(detail)
