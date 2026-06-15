---
title: Deployment
tags: [deployment, docker, nginx, infrastructure]
sources: [docker-compose, dockerfile-api, readme]
updated: 2026-06-14
---

# Deployment

## Stack

Two Docker containers behind a separately-managed Nginx reverse proxy. Images are stored in a local registry at `localhost:5000`. External access via Cloudflare Tunnel — no ports exposed directly to the internet.

## Port Layout

| Service | Container port | Host port |
|---|---|---|
| API (Gunicorn) | 8000 | 8185 |
| Frontend (Nginx static) | 80 | 8186 |
| Nginx reverse proxy | 8100 | 8100 |

Internal URL: `http://retirement.lambda-dual.home.lan:8100`

## Container Images

**API** (`Dockerfile.api`): Multi-stage build. Runs Gunicorn as WSGI server bound to `0.0.0.0:8000`.

**Frontend** (`frontend/Dockerfile.frontend`): Builds the Vite bundle, serves via Nginx static file server.

## Build & Push

```bash
docker build -f Dockerfile.api -t localhost:5000/retirement-api:latest .
docker push localhost:5000/retirement-api:latest

docker build -f frontend/Dockerfile.frontend -t localhost:5000/retirement-frontend:latest frontend
docker push localhost:5000/retirement-frontend:latest
```

## Deploy

```bash
docker compose up -d
```

DB credentials from `.envrc` (direnv) or passed as environment variables.

## Nginx Routing (`nginx/retirement.conf`)

Nginx listens on port 8100:

| Path pattern | Routed to |
|---|---|
| `/api/*` | API container (`192.168.1.91:8185`) |
| `/health` | API container (`192.168.1.91:8185`) |
| `/` (everything else) | Frontend container (`192.168.1.91:8186`) |

Nginx is deployed **outside** the Compose stack and managed separately (via Dockge).

## Database

PostgreSQL at `192.168.1.91:5434`, database `retirement-models`. Schema: `migrations/001_initial_schema.sql`.

## Verification

```bash
curl http://192.168.1.91:8185/health          # API direct
curl http://retirement.lambda-dual.home.lan:8100/health  # through Nginx
```

## Related

- [[rest-api]] — what the API container exposes
- [[frontend]] — what the frontend container serves
- [[configuration]] — environment variables and `.envrc`

---
