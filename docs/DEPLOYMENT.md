# Deployment Guide

## Stack

- **Backend**: FastAPI (uvicorn), PostgreSQL 16, Redis 7
- **Frontend**: React SPA served behind Nginx (or any static host / CDN)
- **Workers**: background processes for offer sync, analytics, server health

## Production checklist

1. **Secrets** — set `SECRET_KEY`, `ENCRYPTION_KEY`, provider keys, Pterodactyl key. Never commit `.env`.
2. **TLS** — terminate at the load balancer / reverse proxy; set `SECURE_COOKIES=true`.
3. **SMTP** — configure a real relay and `EMAIL_VERIFICATION_REQUIRED=true`.
4. **Migrations** — run `alembic upgrade head` before starting the API.
5. **Workers** — run `python -m app.workers.worker` (one or more instances).
6. **Providers** — disable the Mock provider (`MOCK_PROVIDER_ENABLED=false`); connect real providers via the Super Admin → Earning System → Providers panel and test the connection.
7. **Pterodactyl** — configure panel URL + Application API key in Super Admin → Minecraft → Pterodactyl and use **Test Connection**.

## Docker Compose (single host)

```bash
docker compose up -d --build
```

- `db` PostgreSQL on 5432
- `redis` on 6379
- `backend` FastAPI on 8000 (health: `GET /healthz`)
- `worker` background jobs
- `frontend` Nginx serving the SPA on 5173

For Nginx routing to the backend (`/api`, `/ws`, `/postbacks`) from the frontend origin, mount a config. The SPA calls the API relative to its origin; point `/api` and `/ws` to the backend service.

## Scaling

- Horizontally scale API behind a load balancer (sessions are stateless JWTs; refresh tokens stored in DB + Redis allowlist).
- WebSocket servers for the Minecraft console can be scaled behind sticky sessions or by routing through Pterodactyl's own websocket.
- Run analytics aggregation as a scheduled worker; dashboard reads aggregated tables.

## Observability

- Structured JSON logs to stdout; files in `logs/` when `LOG_FORMAT=text`.
- `GET /healthz` — liveness.
- `GET /healthz/ready` — DB + Redis connectivity.

## Backups

- Daily `pg_dump` of the `cavrix` database (includes CVX ledger, conversions — do not lose).
- Encrypted backup of `.env`.
