"""Blueprint: live read/write of configuration/config.json and asset JSON files."""
from __future__ import annotations

import json
import re
from pathlib import Path

from flask import Blueprint, Response, abort, jsonify, request

configuration_bp = Blueprint("configuration", __name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_FILE = _ROOT / "configuration" / "config.json"
_ASSETS_DIR = _ROOT / "configuration" / "assets"

_SAFE_FILENAME = re.compile(r"^[\w\-]+\.json$")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2))


@configuration_bp.get("/configuration")
def get_world_config() -> Response:
    """GET /api/configuration — current config.json."""
    return jsonify(_read_json(_CONFIG_FILE))


@configuration_bp.put("/configuration")
def put_world_config() -> Response:
    """PUT /api/configuration — overwrite config.json."""
    data = request.get_json(force=True)
    if data is None:
        abort(400)
    _write_json(_CONFIG_FILE, data)
    return jsonify({"status": "ok"})


@configuration_bp.get("/configuration/assets")
def list_assets() -> Response:
    """GET /api/configuration/assets — list all asset JSON files."""
    assets = []
    for path in sorted(_ASSETS_DIR.glob("*.json")):
        try:
            assets.append({"filename": path.name, "data": _read_json(path)})
        except (json.JSONDecodeError, OSError):
            pass
    return jsonify(assets)


@configuration_bp.get("/configuration/assets/<filename>")
def get_asset(filename: str) -> Response:
    """GET /api/configuration/assets/<filename>."""
    if not _SAFE_FILENAME.match(filename):
        abort(400)
    path = _ASSETS_DIR / filename
    if not path.exists():
        abort(404)
    return jsonify(_read_json(path))


@configuration_bp.put("/configuration/assets/<filename>")
def put_asset(filename: str) -> Response:
    """PUT /api/configuration/assets/<filename> — create or overwrite."""
    if not _SAFE_FILENAME.match(filename):
        abort(400)
    data = request.get_json(force=True)
    if data is None:
        abort(400)
    _write_json(_ASSETS_DIR / filename, data)
    return jsonify({"status": "ok"})


@configuration_bp.delete("/configuration/assets/<filename>")
def delete_asset(filename: str) -> Response:
    """DELETE /api/configuration/assets/<filename>."""
    if not _SAFE_FILENAME.match(filename):
        abort(400)
    path = _ASSETS_DIR / filename
    if not path.exists():
        abort(404)
    path.unlink()
    return jsonify({"status": "ok"})
