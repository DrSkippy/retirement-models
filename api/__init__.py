"""Flask application factory for the retirement models API."""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

from api.blueprints.assets import assets_bp
from api.blueprints.config_bp import config_bp
from api.blueprints.configuration_bp import configuration_bp
from api.blueprints.mc import mc_bp
from api.blueprints.runs import runs_bp
from api.blueprints.tax import tax_bp

logger = logging.getLogger(__name__)


class _DecimalDateEncoder(Flask.json_provider_class):  # type: ignore[misc]
    """JSON provider that serialises Decimal as float and date/datetime as ISO strings."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)  # type: ignore[misc]


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__)
    CORS(app)
    app.json_provider_class = _DecimalDateEncoder
    app.json = _DecimalDateEncoder(app)

    app.register_blueprint(runs_bp,          url_prefix="/api")
    app.register_blueprint(assets_bp,        url_prefix="/api")
    app.register_blueprint(tax_bp,           url_prefix="/api")
    app.register_blueprint(mc_bp,            url_prefix="/api")
    app.register_blueprint(config_bp,        url_prefix="/api")
    app.register_blueprint(configuration_bp, url_prefix="/api")

    @app.before_request
    def log_request() -> None:
        logger.debug("%s %s", request.method, request.path)

    @app.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok"})

    @app.errorhandler(400)
    def bad_request(e: Exception) -> tuple[Response, int]:
        return jsonify({"error": str(e), "code": 400}), 400

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple[Response, int]:
        return jsonify({"error": "not found", "code": 404}), 404

    @app.errorhandler(500)
    def server_error(e: Exception) -> tuple[Response, int]:
        logger.exception("Unhandled server error")
        return jsonify({"error": "internal server error", "code": 500}), 500

    return app
