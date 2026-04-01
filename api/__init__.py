"""Flask application factory for the retirement models API."""
from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime

from flask import Flask, Response, jsonify

from api.blueprints.assets import assets_bp
from api.blueprints.config_bp import config_bp
from api.blueprints.mc import mc_bp
from api.blueprints.runs import runs_bp
from api.blueprints.tax import tax_bp


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
    app.json_provider_class = _DecimalDateEncoder
    app.json = _DecimalDateEncoder(app)

    app.register_blueprint(runs_bp,   url_prefix="/api")
    app.register_blueprint(assets_bp, url_prefix="/api")
    app.register_blueprint(tax_bp,    url_prefix="/api")
    app.register_blueprint(mc_bp,     url_prefix="/api")
    app.register_blueprint(config_bp, url_prefix="/api")

    @app.get("/health")
    def health() -> Response:
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(e: Exception) -> tuple[Response, int]:
        return jsonify({"error": "not found", "code": 404}), 404

    @app.errorhandler(500)
    def server_error(e: Exception) -> tuple[Response, int]:
        return jsonify({"error": "internal server error", "code": 500}), 500

    return app
