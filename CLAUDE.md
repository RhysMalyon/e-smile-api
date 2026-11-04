# e-smile API: working agreements

FastAPI backend for a teeth-whitening business (not a dental practice). Read `README.md` first: it documents the stack, structure, conventions and architectural decisions. This file covers how we work and the conventions to follow.

## How we work

- The user is a front-end developer (Vue/Node/Express) moving to full-stack Python. Where useful, relate concepts to Node/Express equivalents.
- **Write the code and explain why** each decision was made. Don't make the user draft it (earlier sessions were Socratic tutoring; that mode is over).
- Work **one feature at a time**, in dependency order, layer by layer: DDL → schemas → repository → service → router/exceptions → registration in `main.py` → test.
- Be warm and educational, never combative or condescending. Be direct about mistakes, including your own.
- **Design for now, not hypothetical futures.** Don't add abstractions, extra models or generality until a real need appears. The user tends to over-prepare, so push back if they drift that way.
- **Proofread your own code before presenting it** (brackets, imports, naming mismatches). Verify against the real files in the repo rather than assuming. Say so when unsure of something, such as library behaviour.
- At natural stopping points (a feature finished), recap decisions made, current status and what's next. The user often returns after gaps.
- Update `README.md` when conventions or features change.
- Security matters: parameterized queries only (PyPika `FormatParameter`), no ORM, and keep user data protected.

## Conventions

- Feature-based folders: `router.py`, `service.py`, `repository.py`, `schemas.py`, `exceptions.py`.
- **Repository** takes plain values/dicts (never request schemas), uses `DictCursor` for reads and `Model.model_validate(row)`, and raises not-found errors itself. It also translates MySQL error 1062 (duplicate entry) into a domain exception, and re-raises any other `IntegrityError` unchanged.
- **Service** is thin: `model_dump()` / `model_dump(exclude_unset=True)`, composes repository calls, and lets domain errors propagate.
- **Router** uses relative paths. The prefix and tags are applied in `main.py` (`include_router(..., prefix="/x", tags=["x"])`). Permissions go in `dependencies=[Depends(require_permission(permission=Permission.X))]`. Explicit status codes only where the default is wrong (201 on create, 204 on logout/delete). Static routes (e.g. `/admin`) come before `/{id}` routes. Import service functions with aliases to avoid name collisions.
- **Exceptions** are classes with a `status_code`, rendered by one shared handler (`app/core/exceptions.py`) and registered per class with `add_exception_handler`. Default messages are set in `__init__`.
- **Schemas:** a full-row model (e.g. `Course`) reused as `response_model` wherever the whole row is returned. A separate model only where the shape genuinely differs (e.g. `PublicCourseResponse`). `Create...Request` / `Update...Request` have `Field` constraints mirroring DB limits. Update requests have an "at least one field" `model_validator`. The service takes request schemas directly. A separate Payload model is only for real divergence (e.g. session-derived fields).
- All routes use `get_transaction`, including reads. `database.py` has `FOUND_ROWS` (so `rowcount` means rows matched), a `BaseException` rollback with a bare `raise`, `charset` from settings, and an optional SSL context from `DB__SSL_CA` / `DB__SSL_VERIFY`.
- No pytest yet. Testing is rollback-wrapped scripts in `app/scripts/` plus a Bruno collection for HTTP checks.
