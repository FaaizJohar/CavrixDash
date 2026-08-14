# API Reference

Base URL: `/api/v1`. OpenAPI/Swagger docs served at `/docs` (backend).

## Conventions

- JSON everywhere. Auth via `Authorization: Bearer <access_token>`.
- Refresh via `POST /auth/refresh` (rotates both tokens; previous refresh is invalidated).
- Errors: `{ "detail": { "message": "...", "code": "...", "ref": "CVX-XXXXXXXX" } }`.
  Frontends show the friendly message + reference, never raw tracebacks.
- Pagination: `?page=1&page_size=50` → `{ "items": [...], "total": n, "page": n, "pages": n }`.
- Admin endpoints require roles (`super_admin`, `admin`, `support`, `moderator`).

## Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | create account (email verify if enabled) |
| POST | `/auth/verify-email/{token}` | confirm email |
| POST | `/auth/login` | password login (device + rate limited) |
| POST | `/auth/login/2fa` | finish 2FA/TOTP step |
| POST | `/auth/refresh` | rotate access + refresh tokens |
| POST | `/auth/logout` | revoke session |
| GET  | `/auth/me` | current user + settings |
| POST | `/auth/forgot-password` | send reset email |
| POST | `/auth/reset-password` | reset with token |
| GET  | `/auth/sessions` | list sessions |
| DELETE | `/auth/sessions/{id}` | revoke device |
| GET  | `/auth/2fa/setup` | new TOTP secret + QR + backup codes |
| POST | `/auth/2fa/enable` | enable TOTP |
| POST | `/auth/2fa/disable` | disable TOTP |
| GET  | `/auth/security` | current security state |

## Core user API

| Method | Path | Description |
|---|---|---|
| GET | `/users/me` | profile + balance + stats |
| PATCH | `/users/me` | update profile |
| POST | `/users/me/avatar` | set avatar |
| POST | `/users/me/delete` | request account deletion |

## Offers / Tasks

| Method | Path | Description |
|---|---|---|
| GET | `/offers` | ranked, filtered offer feed |
| GET | `/offers/{id}` | offer detail (requirements, reward) |
| POST | `/offers/{id}/click` | start task → click + redirect |
| GET | `/tasks` | my tasks with statuses |
| GET | `/tasks/{click_id}` | single task status |

## Conversions / Postbacks (server-to-server)

| Method | Path | Description |
|---|---|---|
| POST | `/postbacks/{provider}` | provider callback → verify signature → ledger credit |
| GET | `/conversions` | my approved/pending conversions |

## CVX

| Method | Path | Description |
|---|---|---|
| GET | `/cvx/wallet` | balance + limits + max |
| GET | `/cvx/ledger` | paginated ledger |
| GET | `/cvx/rules` | public economy rules (prices, caps) |

## Minecraft

| Method | Path | Description |
|---|---|---|
| GET | `/servers` | my servers + live status |
| POST | `/servers` | claim server (deducts CVX) |
| GET | `/servers/{id}` | detail |
| POST | `/servers/{id}/action` | start/stop/restart/kill/reinstall |
| GET | `/servers/{id}/console` | websocket console |
| GET | `/servers/{id}/stats` | live resource usage |
| GET | `/servers/{id}/files` | file list |
| GET | `/servers/{id}/backups` | backups |
| POST | `/servers/{id}/backups/{bid}/restore` | restore |
| GET | `/servers/{id}/schedules` | schedules |
| GET | `/servers/{id}/network` | allocations |
| GET | `/servers/plans` | available plans + prices |
| GET | `/servers/templates` | templates/eggs + versions |
| POST | `/servers/{id}/upgrades/preview` | quote an upgrade |
| POST | `/servers/{id}/upgrades` | buy an upgrade (deduct CVX) |
| GET | `/servers/regions` | regions + node capacity |

## Referrals

| Method | Path | Description |
|---|---|---|
| GET | `/referrals` | my code, URL, stats, invitees |
| POST | `/referrals/redeem` | redeem invite code (on signup instead) |

## Analytics (user)

| Method | Path | Description |
|---|---|---|
| GET | `/analytics/overview` | user dashboard aggregates |

## Support

| Method | Path | Description |
|---|---|---|
| GET | `/support/tickets` | my tickets |
| POST | `/support/tickets` | open ticket |
| POST | `/support/tickets/{id}/messages` | reply |
| GET | `/support/tickets/{id}` | thread |

## Notifications

| Method | Path | Description |
|---|---|---|
| GET | `/notifications` | in-app feed |
| POST | `/notifications/read` | mark read |

## Admin (`/admin/*`, role-gated)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/overview` | KPIs (revenue, users, servers, cvx) |
| GET | `/admin/users` | user search/management |
| PATCH | `/admin/users/{id}` | status/roles/limits |
| GET/POST/PATCH/DELETE | `/admin/providers` | provider CRUD + credentials + test + sync |
| GET/POST/PATCH/DELETE | `/admin/offers` | offer management |
| GET/POST/PATCH | `/admin/conversions` | conversions + manual review |
| GET/POST/PATCH/DELETE | `/admin/plans` | server plans |
| GET/POST/PATCH/DELETE | `/admin/regions` | regions |
| GET/POST/PATCH/DELETE | `/admin/nodes` | pterodactyl nodes |
| GET/POST/PATCH/DELETE | `/admin/templates` | templates |
| GET/POST/PATCH | `/admin/cvx/settings` | global CVX rules |
| GET/POST/PATCH/DELETE | `/admin/cvx/campaigns` | bonus campaigns |
| GET | `/admin/cvx/ledger` | global ledger search |
| GET | `/admin/servers` | all servers |
| DELETE | `/admin/servers/{id}` | destroy server (confirm token) |
| GET | `/admin/revenue` | revenue breakdown |
| GET | `/admin/analytics` | time series |
| GET | `/admin/fraud/events` | risk events |
| GET | `/admin/fraud/users` | suspicious users |
| GET/PATCH | `/admin/fraud/rules` | fraud thresholds |
| GET/POST/PATCH | `/admin/announcements` | notifications/announcements |
| GET | `/admin/support` | ticket queue |
| GET | `/admin/audit` | audit log |
| GET/PATCH | `/admin/settings` | global configuration |
| GET/POST/PATCH | `/admin/secrets` | encrypted secrets management |
| POST | `/admin/pterodactyl/test` | test panel connection |

## WebSockets

- `WS /ws/console/{server_id}` — live Minecraft console (proxies Pterodactyl websocket).
- `WS /ws/notifications` — real-time in-app notifications.

## Postback security

Every provider postback verifies its HMAC signature / secret using the provider's stored
credential. Payloads are idempotent (conversion id + click id dedupe), replay-protected
(nonce/timestamp window), and risk-scored before CVX is credited.
