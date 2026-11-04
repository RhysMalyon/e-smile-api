# e-smile API

Backend API for the e-smile teeth-whitening business: staff authentication, an admin back-office, and the public booking flow. Implemented so far: `auth` and `courses`. In progress: `time_off`, `customers`, `appointments` (including availability).

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
├── main.py                  # FastAPI app, lifespan, CORS, exception handlers, router registration (prefix + tags)
├── core/
│   ├── config.py             # Settings hierarchy (pydantic-settings)
│   ├── database.py           # DatabaseService — aiomysql pool singleton + ContextVar transaction guard
│   ├── dependencies.py       # get_transaction() — DI-based connection/transaction yield
│   ├── logging_config.py     # Structured logging unified with Uvicorn; correlation_id ContextVar
│   └── permissions.py        # Permission, Role enums; ROLE_PERMISSIONS mapping
├── dependencies/
│   └── db.py                 # (stub — future shared DB dependency layer)
├── auth/
│   ├── router.py             # /auth/login, /auth/refresh, /auth/logout
│   ├── service.py            # login(), refresh(), logout() orchestration
│   ├── repository.py         # PyPika queries against users / refresh_tokens
│   ├── schemas.py            # Request/response/internal Pydantic models
│   ├── security.py           # Password hashing, token hashing, JWT sign/verify
│   ├── dependencies.py       # get_current_user, require_permission
│   └── exceptions.py         # Custom exceptions + FastAPI exception handlers
├── courses/
│   ├── router.py             # /courses (public list), /courses/admin, /courses/{course_id}
│   ├── service.py            # Thin passthroughs; extracts dicts from request schemas
│   ├── repository.py         # PyPika queries; translates MySQL duplicate-key (1062) to a domain error
│   ├── schemas.py            # Course, PublicCourseResponse, Create/UpdateCourseRequest
│   └── exceptions.py         # CourseNotFoundError (404), CourseAlreadyExistsError (409) + handler
└── scripts/
    ├── login_test.py         # Manual integration test: insert user → login → rollback
    └── refresh_test.py       # Manual integration test: login → refresh → reuse detection → rollback
```

Planned: `time_off/`, `customers/`, `appointments/` (see [Domain model and business rules](#domain-model-and-business-rules)). Each feature module follows the same shape as `auth/` and `courses/`: router, service, repository, schemas, and an `exceptions.py` once it has errors raised across files.

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

Create the database and run the DDL for the tables, in dependency order: `users`, `refresh_tokens`, `courses`, `customers`, `time_off`, `appointments` (`appointments` has foreign keys to `courses` and `customers`). Tables use `ENGINE=InnoDB`, `utf8mb4`, `utf8mb4_0900_ai_ci`.

Repositories reference tables as `Table("<name>", schema="e-smile")`, so the schema name is currently hardcoded in code, not taken from `DB__DATABASE`.

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
DB__SSL_VERIFY=False   # set True in production when using SSL
DB__SSL_CA=            # path to CA certificate; leave empty to disable SSL

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

---

## Key Architectural Notes

Decisions that aren't obvious from reading the code alone — worth knowing before modifying related code.

### Domain model and business rules

- Every appointment starts on the hour and occupies a full one-hour slot, regardless of course length. There is a single operator, so two appointments cannot share a `date` (`UNIQUE` on `appointments.date`).
- `appointments.date` and `time_off.start_at`/`end_at` are hour-aligned via `CHECK` constraints; `time_off` also enforces `start_at < end_at`.
- `courses.length` is display/admin information only and is deliberately not snapshotted. `appointments.price_at_booking` is snapshotted so historical prices survive course edits.
- Courses are never hard-deleted (`is_active` soft delete); the `appointments.course_id` FK is `ON DELETE RESTRICT`.
- Customers have no login. `customers.email` is the sole unique identifier; `tel` is deliberately not unique. On booking, a customer is looked up by email only. A match is reused unchanged, and a differing `tel` is noted in `appointments.admin_notes` instead of overwriting. `appointments.customer_id` is nullable with `ON DELETE SET NULL` so a customer can be erased while keeping the appointment record.
- Business hours, lunch, weekly closed days (Thursday/Sunday) and national holidays are server-side config, not DB tables.
- Availability (planned): a public `GET /availability` in `appointments/router.py` (a second `APIRouter`), merging `appointments.date` and `time_off` ranges in Python into `{date: [ISO hour strings]}` for a requested range. `appointments` reads time-off through `time_off/service.py`, not its repository.

### Layer responsibilities and conventions

- **Repository** takes plain values or `dict`s, never request schemas. It returns domain objects, raises not-found errors itself, and translates known MySQL errors (for example error code 1062, duplicate entry) into domain exceptions. Any other `IntegrityError` is re-raised untouched.
- **Service** is thin: it extracts data from request schemas (`model_dump(exclude_unset=True)` for updates) and composes repository calls. Domain errors propagate unchanged.
- **Router** declares permissions with `dependencies=[Depends(require_permission(...))]`, sets explicit status codes only where the default is wrong (`201` on create, `204` on logout), and uses relative paths. The prefix and tags are applied in `main.py` via `include_router(..., prefix=..., tags=[...])`. Static routes (`/admin`) must be declared before parameterized ones (`/{course_id}`).
- **Exceptions** carry their own `status_code` and are rendered by one handler per feature, registered in `main.py` with `add_exception_handler`.
- **Update schemas** reject empty bodies with a `model_validator(mode="after")`, so no service or repository code needs to handle an empty `SET`.
- All routes, including read-only ones, use `get_transaction`. This gives multi-query reads a consistent snapshot, and the `BEGIN`/`COMMIT` overhead is negligible at this scale.

### Database pool details

- **`FOUND_ROWS`:** the pool is created with `client_flag=CLIENT.FOUND_ROWS`, so `cursor.rowcount` after an `UPDATE` means rows _matched_ rather than rows _changed_. Without it, a PATCH that re-sends the stored values would look like "not found".
- **Cancellation-safe rollback:** `transaction()` catches `BaseException`, rolls back, and re-raises, so `asyncio.CancelledError` also triggers an explicit rollback. The re-raise is mandatory.
- **Transaction guard:** `DatabaseService.transaction()` uses a `ContextVar` (`db_connection_ctx`) to detect if a connection is already active in the current async context. If `get_transaction()` is called while a transaction is already open, it raises `RuntimeError("Connection already present in context")` immediately — preventing silent nesting that could cause unexpected rollback or commit behaviour.

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
- This was a deliberate rejection of a fully-normalized DB-driven RBAC system — roles/permissions haven't changed in 3+ years for this business, and a permission only has effect once application code checks for it, meaning DB-editable permissions would still require a code change to matter. Revisit only if permissions genuinely become dynamic/runtime-editable by an admin.
- `require_permission(Permission.X)` (in `auth/dependencies.py`) is the enforcement point for any protected route in **any** feature module — it's cross-cutting infrastructure, safe to import from other feature modules without violating Locality of Reference (unlike, say, keeping `Permission` inside the `auth` module itself, which was deliberately avoided).

#### Current role → permission mapping

| Role    | Permissions                                           |
| ------- | ----------------------------------------------------- |
| `admin` | All permissions (inherits entire `Permission` enum)   |
| `staff` | `appointments:read`, `customers:read`, `courses:read` |

`courses:write` is admin only. `appointments:write` is public (the booking form), `appointments:delete` is admin only, and `time_off` permissions (admin write) will be added with that feature.

### `is_production` controls cookie security, not `debug`

`APP__IS_PRODUCTION` (not `APP__DEBUG`) drives the refresh-token cookie's `secure` flag. These were deliberately decoupled — "should I show verbose errors" and "should cookies require HTTPS" are different concerns that happened to correlate at first glance but shouldn't be tied together.

### CORS + credentials

`CORS__ALLOWED_ORIGINS` **must** be an explicit list, never `["*"]`, whenever `CORS__ALLOW_CREDENTIALS=True` — the CORS spec disallows combining a wildcard origin with credentialed requests. This fails silently on the backend (no Python error) and only surfaces as a browser-side rejection, so it's an easy thing to break without noticing if `allowed_origins` is ever "simplified" back to a wildcard.

### Timing-attack mitigation in `login()`

When a user is not found by email, `service.login()` still calls `verify_password()` with a dummy credential before raising `InvalidCredentialsError`. This ensures the response time for "user not found" and "wrong password" is indistinguishable, preventing timing-based user enumeration. Don't remove or short-circuit this dummy check.

### Logging: structured output with correlation ID

`app/core/logging_config.py` replaces default Uvicorn handlers with a single unified root logger so all output (app + Uvicorn) shares the same format:

```
2026-07-30 12:00:00,000 (-): INFO - app.auth.service - User not found.
```

A `correlation_id` `ContextVar` is injected into every log record via `CorrelationIdFilter`. It defaults to `"-"` — middleware that sets a per-request correlation ID (e.g. from an `X-Request-ID` header) can populate this for distributed tracing. The middleware does not exist yet but the hook is in place.

---

## Testing approach (current)

No `pytest` suite yet — deliberately deferred in favor of learning FastAPI/the domain first. Two complementary approaches are used instead.

### Standalone scripts

Scripts in `app/scripts/` use `db_service.transaction()` directly, run real logic against a real test DB connection, and deliberately raise at the end to force a rollback — leaving no residue.

Run them from the project root (with `.venv` active):

```bash
python -m app.scripts.login_test
python -m app.scripts.refresh_test
```

`refresh_test.py` specifically exercises token rotation and reuse detection — it asserts that presenting a previously-rotated token invalidates the entire session family. This pattern is worth reusing for new feature modules until a formal test suite is introduced.

### HTTP-level checks (Bruno)

A Bruno collection covers the API over HTTP: a login request stores the access token in a variable, collection-level Bearer auth applies it to protected requests, and each case is its own request with status assertions.

Cases covered for `courses`: create (201), duplicate name (409), empty PATCH (422), no-op PATCH (200), name collision on PATCH (409), missing id (404), deactivation visibility (public vs admin list), no token (401) and insufficient permission (403).
