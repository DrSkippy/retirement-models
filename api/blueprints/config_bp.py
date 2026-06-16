"""Blueprint: configuration snapshot endpoint."""
from __future__ import annotations

import logging

from flask import Blueprint, Response, abort, jsonify

from models.db import get_connection, load_config

logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__)


@config_bp.get("/config/<int:config_id>")
def get_config(config_id: int) -> Response:
    """GET /api/config/<id> — configuration snapshot for a run."""
    logger.debug("GET /api/config/%d", config_id)
    with get_connection() as conn:
        cfg = load_config(conn, config_id)
    if cfg is None:
        abort(404)
    return jsonify(cfg)
