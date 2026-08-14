# Deployment Guide

## One-command installer (recommended)

`./install.sh` bootstraps the whole platform on any Ubuntu/Debian VPS **or**
Docker container with a custom domain through Cloudflare. It auto-detects the
environment:

- **Docker daemon reachable** → full Compose stack (Postgres + Redis +
  backend + worker + frontend + Caddy TLS).
- **No Docker** (or `--mode native`) → native install: SQLite (app degrades
  gracefully without Redis), Python venv for API/worker, static frontend
  build, Caddy binary (with `caddy-dns/cloudflare`) for TLS.

Either way it generates all secrets, creates/updates the Cloudflare DNS
records, provisions TLS and prints admin login. The installer self-heals
common VPS issues: broken dpkg state and, via `apt --no-upgrade`, `EXDEV`
hardlink failures on btrfs/overlay root filesystems.

```bash
# root on a fresh Ubuntu 22.04/24.04 VPS (or inside a container):
bash <(curl -fsSL https://raw.githubusercontent.com/FaaizJohar/CavrixDash/main/install.sh) \
    --domain cavrix.example.com \
    --email you@example.com \
    --cf-token <YOUR_CLOUDFLARE_DNS_TOKEN>
```

Force the mode with `--mode docker` or `--mode native`.
Full reference: `./install.sh --help`.

### Cloudflare setup (5 minutes)

1. Add your domain to Cloudflare (free plan) and let it import existing DNS.
2. Create an API token: **My Profile → API Tokens → Create Token →**
   *Edit zone DNS* template → select only your zone → **Permissions**:
   `Zone → DNS → Edit`. Copy the token.
3. Set the DNS record for your domain to point at the VPS IP (orange-cloud
   proxied is recommended). The installer can do this automatically when the
   token is passed.
4. (Optional) Under **SSL/TLS → Overview** set mode to **Full (strict)**.

The token powers two things: automatic `A` record creation and **DNS-01** TLS
challenge (`caddy` with the `caddy-dns/cloudflare` module), so HTTPS works even
while the record is proxied. Without a token, add the `A` record manually with
proxying **off** (grey cloud) and Caddy falls back to HTTP-01.

### Production stack (`docker-compose.prod.yml`)

Traffic flow: `Caddy (:80/:443, TLS) → frontend (Nginx, SPA + /api + /ws proxy)
→ backend (:8000)`. Postgres and Redis are **not exposed** to the internet.

```bash
./install.sh status     # service status + backend /healthz
./install.sh logs       # tail logs
./install.sh backup     # DB backup (pg_dump or sqlite copy) into ./backups/
./install.sh uninstall  # remove services + data (data loss!) — keeps .env
```

In native mode the same commands manage the Python venv services and Caddy via
pid files under `./run` (no Docker required); the DB is `./data/cavrix.db`.

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
