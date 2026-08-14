# Cavrix Cloud

**Earn CVX → Unlock Minecraft → Upgrade Your Server**

Cavrix Cloud is a premium Minecraft cloud platform where users complete legitimate tasks/offers, earn **CVX credits**, and spend them to claim and upgrade Minecraft servers (managed through the Pterodactyl API).

```
Register → Verify → Earn (tasks/offers/rewarded ads) → Track → Provider verifies
→ CVX credited → Claim free Minecraft server → Play → Upgrade → Earn more
```

## Architecture

```
frontend/  React 19 + TypeScript + Vite + Tailwind + shadcn-style UI + TanStack Query
backend/   Python FastAPI + SQLAlchemy 2 + PostgreSQL + Redis + background workers
providers  Clean adapter layer (CPAlead, AdGem, Google Ad Manager, ShrinkMe, Mock/dev)
infra      Pterodactyl client (application + client API)
```

Flow:

```
React Dashboard → Cavrix FastAPI → CVX validation → Pterodactyl API → Pterodactyl Panel → Node → Minecraft Server
```

Provider credentials and the Pterodactyl API key are **never** exposed to the frontend. They are encrypted at rest with Fernet and read only server-side.

## Repo layout

```
backend/
  app/
    core/          config, security, crypto, database, redis, logging, errors
    models/        SQLAlchemy ORM (users, offers, tracking, cvx, servers, fraud...)
    schemas/       Pydantic v2 request/response models
    api/v1/        user-facing + admin namespaces
    services/      business logic (cvx ledger, tasks, fraud, pterodactyl...)
    providers/     provider adapter system
    pterodactyl/   Pterodactyl API client
    workers/       background workers (offer sync, analytics, health)
    seed.py        bootstrap: roles, super admin, providers, plans, demo data
  alembic/         DB migrations (scaffolding; dev auto-creates schema)
frontend/
  src/
    components/    UI kit + shared feature components
    pages/         dashboard, earn, rewards, minecraft, admin...
    lib/           api client, queries, socket, formatting
```

## Quickstart (development)

Requirements: Python 3.11+, Node 20+, PostgreSQL 16, Redis 7 (or `docker compose up db redis`).

```bash
# 1. Infrastructure
docker compose up -d db redis

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # PowerShell
pip install -r requirements.txt
copy ..\.env.example .env         # then edit .env
python -m app.seed                # create schema + super admin + demo data
uvicorn app.main:app --reload     # http://localhost:8000/docs

# 3. Frontend
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Docker all-in-one: `docker compose up --build` (backend :8000, frontend :5173, db, redis).

## Super Admin

Seeded via `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` in `.env` (defaults `admin@cavrix.cloud` / `ChangeMe!12345`). Log in and click **Super Admin** from the profile menu, or visit `/admin`.

## Production

See `docs/DEPLOYMENT.md`. Notes:

- Always run behind TLS. Set `SECURE_COOKIES=true`.
- Configure a real SMTP relay for email verification/notifications.
- Put secrets in your secret manager / env, never in code.
- Run migrations with `alembic upgrade head` (see `docs/MIGRATIONS.md`).
- Keep `MOCK_PROVIDER_ENABLED=false` in production — the mock provider is development-only.
- Enable the providers you actually have credentials for; verify terms for rewarded-ad / link models.

## Policy

The platform is built to reward **legitimate user actions** (real installs, real trials, real registrations). It does not generate fake clicks, impressions, installs, referrals, or conversions, and does not reward ordinary ad clicks. Provider terms must be respected per-offer.

## License

Proprietary — Cavrix Core Technologies.
