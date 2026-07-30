# e-smile API

Backend API for the e-smile dental practice admin back-office. Handles staff authentication and (in progress) practice management features — appointments, customers, holidays.

## Tech Stack

- **Framework:** FastAPI (async-first)
- **Validation:** Pydantic V2
- **Database:** MySQL
- **DB Access:** aiomysql (async connection pooling) + PyMySQL (driver) + PyPika (query building) — **no ORM**
- **Config:** pydantic-settings, `.env`-driven with nested delimiter support
- **Auth:** RS256-signed JWT access tokens, rotating hashed refresh tokens (see [Key Architectural Notes](#key-architectural-notes) below)
- **Package management:** pip + virtualenv + `requirements.txt`
- **Code style:** Black (line length 100) + isort (`black` profile), configured in `pyproject.toml`

---

## Project Structure

Organized by **feature/domain**, not by technical layer (Locality of Reference) — each feature owns its own router, service, repository, and schemas.

```
app/
├── main.py                  # FastAPI app, lifespan, CORS, exception handlers, router registration
├── core/
│   ├── config.py             # Settings hierarchy (pydantic-settings)
│   ├── database.py           # DatabaseService — aiomysql pool singleton + ContextVar transaction guard
│   ├── dependencies.py       # get_transaction() — DI-based connection/transaction yield
│   ├── logging_config.py     # Structured logging unified with Uvicorn; correlation_id ContextVar
│   └── permissions.py        # Permission, Role enums; ROLE_PERMISSIONS mapping
├── dependencies/
│   └── db.py                 # (stub — future shared DB dependency layer)
├── auth/
│   ├── router.py              # /auth/login, /auth/refresh, /auth/logout
│   ├── service.py              # login(), refresh(), logout() orchestration
│   ├── repository.py           # PyPika queries against users / refresh_tokens
│   ├── schemas.py               # Request/response/internal Pydantic models
│   ├── security.py              # Password hashing, token hashing, JWT sign/verify
│   ├── dependencies.py          # get_current_user, require_permission
│   └── exceptions.py            # Custom exceptions + FastAPI exception handlers
└── scripts/
    ├── login_test.py            # Manual integration test: insert user → login → rollback
    └── refresh_test.py          # Manual integration test: login → refresh → reuse detection → rollback
```

Each future feature module (`appointments`, `customers`, `holidays`, ...) follows the same shape as `auth/`.

---

## Setup

### 1. Prerequisites

- Python 3.11+ (uses `StrEnum` from the standard library)
- MySQL 8+ (InnoDB, `utf8mb4`)
- An RS256 key pair for JWT signing (unencrypted PEM — see [JWT Keys](#jwt-keys) below)

### 2. Environment

```bash
python -m venv .venv
source .venv/bin/activate     # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Database

Create the database and run the DDL for the `users` and `refresh_tokens` tables. Both tables must exist before the app can start meaningfully.

### 4. Environment Variables

Copy `.env.example` (create one if it doesn't exist yet) to `.env` and populate:

```env
# App
APP__HOST=0.0.0.0
APP__PORT=8000
APP__TITLE=e-smile API
APP__VERSION=0.1.0
APP__DEBUG=True
APP__IS_PRODUCTION=False   # controls cookie `secure` flag — set True in production

# Database
DB__HOST=localhost
DB__PORT=3306
DB__USER=
DB__PASSWORD=
DB__DATABASE=e-smile
DB__CHARSET=utf8mb4
DB__COLLATE=utf8mb4_unicode_ci
DB__SSL_VERIFY=False
DB__SSL_CA=

# JWT
JWT__PUBLIC_KEY=
JWT__PRIVATE_KEY=
JWT__ACCESS_TOKEN_SECRET=
JWT__REFRESH_TOKEN_SECRET=
JWT__ACCESS_TOKEN_LIFETIME_SECONDS=900        # 15 minutes
JWT__REFRESH_TOKEN_EXPIRE_SECONDS=2592000     # 30 days

# CORS
CORS__ALLOWED_ORIGINS=["http://localhost:5173"]   # must be explicit — NOT "*" — required for allow_credentials
CORS__ALLOW_CREDENTIALS=True
CORS__ALLOWED_HEADERS=["Content-Type","Authorization"]
CORS__ALLOWED_METHODS=["GET","POST","PUT","PATCH","DELETE"]
CORS__EXPOSE_HEADERS=["Content-Disposition"]

# Mail
MAIL__HOST=
MAIL__SERVICE=
MAIL__PORT=
MAIL__USER=
MAIL__PASSWORD=
```

`AuthSettings` (role → permission mapping) is **not** environment-driven — it's hardcoded in `app/core/permissions.py` and wired into config via a `BaseModel` default. No `AUTH__*` env vars exist or are needed.

> **Important:** All five setting groups (`APP__*`, `DB__*`, `JWT__*`, `CORS__*`, `MAIL__*`) are required. The app will fail to start if any are missing — pydantic-settings raises a `ValidationError` at import time.

#### JWT Keys

Keys must be **unencrypted** PEM (no passphrase) — PyJWT's `encode()`/`decode()` are called directly with the raw PEM string, with no passphrase-decryption step in `security.py`. Newline-escaped keys (`\n` literals, common when pasting a multi-line PEM into a single-line `.env` value) are automatically unescaped by a `field_validator` on `JwtSettings`.

### 5. Run

```bash
python -m app.main
# or, for development with reload:
uvicorn app.main:app --reload
```

Docs available at `/docs` (Swagger UI) once running.

---

## Dependencies

`requirements.txt` is a fully pinned `pip freeze` output. Key direct dependencies:

```
fastapi==0.139.0
uvicorn==0.51.0
pydantic==2.13.4
pydantic-settings==2.14.1
aiomysql==0.3.2
PyMySQL==1.2.0
PyPika==0.51.1
bcrypt==5.0.0
PyJWT==2.13.0
email-validator==2.3.0
```

Regenerate with `pip freeze > requirements.txt` after adding or upgrading packages.


## Key Architectural Notes

Decisions that aren't obvious from reading the code alone — worth knowing before modifying auth-adjacent code.

### `get_current_user` is deliberately stateless — no DB lookup per request

`app/auth/dependencies.py`'s `get_current_user` decodes and trusts the access token's own claims (`sub`, `role`) without querying the database. This is **intentional**, not an oversight:

- Access tokens are short-lived (15 min default) — the blast radius of a stale claim (e.g. a just-blocked user still passing checks) is bounded to that window.
- `is_blocked` **is** enforced at `/auth/refresh` (via `find_user_by_id` in the refresh flow), so a blocked user is caught the next time they need a new access token — at most 15 minutes after being blocked.
- Adding a DB lookup here would reintroduce the exact per-request cost the access/refresh token split was designed to avoid.

**If you're tempted to "fix" this by adding a DB call:** don't, without first deciding whether the tradeoff has actually changed (e.g. access token lifetime got much longer, or the app's risk tolerance changed) — this was a conscious choice, not a gap.

### Refresh tokens: hashed at rest, rotated, with reuse detection

- The raw refresh token is only ever known to the client (in an `HttpOnly` cookie) and momentarily server-side at issuance/verification. Only its SHA-256 hash is stored (`refresh_tokens.token_hash`).
- Every `/auth/refresh` call **rotates** the token — the old one is marked `is_valid = 0` and a new one is inserted, sharing the same `session_id`.
- If an already-invalidated token is ever presented again (replay), the **entire session family** (every row sharing that `session_id`) is invalidated — treated as a compromise signal, not just a rejected single request.
- `session_id` is a per-login UUID (`str(uuid.uuid4())`), stable across rotations within one login session, unique per device/login.

### Access token vs. refresh token — different storage, different purpose

- **Access token:** returned in the JSON response body, managed client-side (memory/state), attached manually as `Authorization: Bearer <token>`.
- **Refresh token:** set as an `HttpOnly`, `Secure` (prod only), `SameSite=Lax` cookie, scoped to `path=/auth` — never touches JavaScript, never appears in any response body.
- This split was a deliberate choice over storing both tokens the same way — see conversation history / Obsidian notes for the full XSS vs. CSRF tradeoff reasoning if revisiting this decision.

### Permissions are config, not database, by design

- `Role` and `Permission` are fixed `StrEnum`s in `app/core/permissions.py`. `ROLE_PERMISSIONS` maps role → allowed permissions, hardcoded.
- This was a deliberate rejection of a fully-normalized DB-driven RBAC system — roles/permissions haven't changed in 3+ years for this practice, and a permission only has effect once application code checks for it, meaning DB-editable permissions would still require a code change to matter. Revisit only if permissions genuinely become dynamic/runtime-editable by an admin.
- `require_permission(Permission.X)` (in `auth/dependencies.py`) is the enforcement point for any protected route in **any** feature module — it's cross-cutting infrastructure, safe to import from other feature modules without violating Locality of Reference (unlike, say, keeping `Permission` inside the `auth` module itself, which was deliberately avoided).

### `is_production` controls cookie security, not `debug`

`APP__IS_PRODUCTION` (not `APP__DEBUG`) drives the refresh-token cookie's `secure` flag. These were deliberately decoupled — "should I show verbose errors" and "should cookies require HTTPS" are different concerns that happened to correlate at first glance but shouldn't be tied together.

### CORS + credentials

`CORS__ALLOWED_ORIGINS` **must** be an explicit list, never `["*"]`, whenever `CORS__ALLOW_CREDENTIALS=True` — the CORS spec disallows combining a wildcard origin with credentialed requests. This fails silently on the backend (no Python error) and only surfaces as a browser-side rejection, so it's an easy thing to break without noticing if `allowed_origins` is ever "simplified" back to a wildcard.

### Timing-attack mitigation in `login()`

When a user is not found by email, `service.login()` still calls `verify_password()` with a dummy credential before raising `InvalidCredentialsError`. This ensures the response time for "user not found" and "wrong password" is indistinguishable, preventing timing-based user enumeration. Don't remove or short-circuit this dummy check.

### Permissions: current role → permission mapping

| Role    | Permissions                                                   |
|---------|---------------------------------------------------------------|
| `admin` | All permissions (inherits entire `Permission` enum)           |
| `staff` | `appointments:read`, `customers:read`                         |

### Logging: structured output with correlation ID

`app/core/logging_config.py` replaces default Uvicorn handlers with a single unified root logger so all output (app + Uvicorn) shares the same format:

```
2026-07-30 12:00:00,000 (-): INFO - app.auth.service - User not found.
```

A `correlation_id` `ContextVar` is injected into every log record via `CorrelationIdFilter`. It defaults to `"-"` — middleware that sets a per-request correlation ID (e.g. from an `X-Request-ID` header) can populate this for distributed tracing. The middleware does not exist yet but the hook is in place.

### Transaction guard: nested transactions are rejected

`DatabaseService.transaction()` uses a `ContextVar` (`db_connection_ctx`) to detect if a connection is already active in the current async context. If `get_transaction()` is called while a transaction is already open, it raises `RuntimeError("Connection already present in context")` immediately — preventing silent nesting that could cause unexpected rollback or commit behaviour.

### Testing approach (current)

No `pytest` suite yet — deliberately deferred in favor of learning FastAPI/the domain first. In its place: standalone scripts in `app/scripts/` that use `db_service.transaction()` directly, run real logic against a real test DB connection, and deliberately raise at the end to force a rollback — leaving no residue.

Run them from the project root (with `.venv` active):

```bash
python -m app.scripts.login_test
python -m app.scripts.refresh_test
```

`refresh_test.py` specifically exercises token rotation and reuse detection — it asserts that presenting a previously-rotated token invalidates the entire session family. This pattern is worth reusing for new feature modules until a formal test suite is introduced.
