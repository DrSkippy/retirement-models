---
title: REST API
tags: [api, flask, endpoints]
sources: [api-init-py, blueprints]
updated: 2026-06-14
---

# REST API

## Overview

A Flask application factory (`api/__init__.py` → `create_app()`) registers six blueprints, all mounted under `/api`. CORS is enabled globally via `flask-cors`. JSON serialization handles `Decimal` → float and `date`/`datetime` → ISO string via a custom `_DecimalDateEncoder`.[^1]

## App Factory

```python
from api import create_app
app = create_app()
```

Error handlers: 404 → `{"error": "not found", "code": 404}`, 500 → `{"error": "internal server error", "code": 500}`.

## Endpoints

| Method | Path | Blueprint | Description |
|---|---|---|---|
| GET | `/health` | (app-level) | Health check — `{"status": "ok"}` |
| GET | `/api/runs` | `runs_bp` | List simulation runs; supports `?tag=`, `?limit=`, `?offset=` |
| GET | `/api/runs/<id>` | `runs_bp` | Run summary + full scenario time-series |
| GET | `/api/runs/<id>/assets` | `assets_bp` | Per-asset time-series; supports `?asset=` filter |
| GET | `/api/runs/<id>/tax` | `tax_bp` | Tax breakdown per period |
| GET | `/api/mc` | `mc_bp` | List Monte Carlo run sets |
| GET | `/api/mc/<id>` | `mc_bp` | MC detail with percentile bands; `?include_runs=true` for individual results |
| GET | `/api/config/<id>` | `config_bp` | Configuration snapshot for a historical run |
| GET | `/api/configuration` | `configuration_bp` | Read live `configuration/config.json` |
| PUT | `/api/configuration` | `configuration_bp` | Overwrite `configuration/config.json` |
| GET | `/api/configuration/assets` | `configuration_bp` | List all asset JSON files with parsed data |
| GET | `/api/configuration/assets/<filename>` | `configuration_bp` | Read a single asset file |
| PUT | `/api/configuration/assets/<filename>` | `configuration_bp` | Create or overwrite an asset file |
| DELETE | `/api/configuration/assets/<filename>` | `configuration_bp` | Delete an asset file |

## Blueprints

| Blueprint | File | Prefix |
|---|---|---|
| `runs_bp` | `api/blueprints/runs.py` | `/api` |
| `assets_bp` | `api/blueprints/assets.py` | `/api` |
| `tax_bp` | `api/blueprints/tax.py` | `/api` |
| `mc_bp` | `api/blueprints/mc.py` | `/api` |
| `config_bp` | `api/blueprints/config_bp.py` | `/api` |
| `configuration_bp` | `api/blueprints/configuration_bp.py` | `/api` |

## Configuration Blueprint Security

`configuration_bp` reads and writes files on disk directly. Filenames submitted to `PUT`/`DELETE /api/configuration/assets/<filename>` are validated against `^[\w\-]+\.json$` to prevent path traversal. The blueprint resolves the project root at import time via `Path(__file__).resolve().parent.parent.parent`; both `config.json` and the `assets/` directory are pinned to absolute paths.[^2]

## Running

**Development (Python):**
```bash
poetry run flask --app "api:create_app()" run --port 8000
```

**Development (Docker):**
```bash
docker run --rm -p 8000:8000 -e DB_HOST=... -e DB_PASSWORD=... retirement-api
```

**Production:** Gunicorn inside the `Dockerfile.api` container, bound to `0.0.0.0:8000`.

## Backend: PostgreSQL

The API reads from/writes to PostgreSQL at `192.168.1.91:5434`, database `retirement-models`. Credentials come from environment variables (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

Schema defined in `migrations/001_initial_schema.sql`.

## Related

- [[deployment]] — how the API is containerized and proxied
- [[frontend]] — React UI that consumes these endpoints
- [[simulation-engine]] — CLI `--save-db` flag persists runs for the API to serve

---

[^1]: `api/__init__.py` `create_app()` — `CORS(app)` and `_DecimalDateEncoder` registered on the Flask app
[^2]: `api/blueprints/configuration_bp.py` — `_SAFE_FILENAME = re.compile(r"^[\w\-]+\.json$")`; `_ROOT = Path(__file__).resolve().parent.parent.parent`
