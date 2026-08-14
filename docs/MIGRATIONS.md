# Migrations

Alembic is wired up (`backend/alembic/`, initial revision `04713c9ef6a6`). For rapid development
the app auto-creates tables on startup (`DB_AUTO_CREATE=true`, default in dev); production schema
is managed purely by Alembic. To migrate manually:

```bash
cd backend
alembic upgrade head
```

## Generating a new revision after model changes

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Dev → Production note

Keep `DB_AUTO_CREATE=false` in production. In `docker-compose.yml` the `migrate` service runs
`alembic upgrade head` before `backend`/`worker` start. Alembic revision `04713c9ef6a6` is the
initial baseline; the canonical schema always comes from `app/models/` (SQLAlchemy 2.0 metadata).
