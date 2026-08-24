# Consumer Integration

This tutorial adds AuthLoom to an existing FastAPI app and gets to the first
successful signup, current-user request, signout, and signin.

It uses SQLite with `aiosqlite` for one clear path. If your app uses PostgreSQL,
install `asyncpg` instead and use a `postgresql+asyncpg://...` URL.

## 1. Install

AuthLoom requires Python `>=3.12`, FastAPI, and SQLAlchemy async sessions.

Using `uv`:

```bash
uv add authloom aiosqlite
```

Using `pip`:

```bash
pip install authloom aiosqlite
```

## 2. Create The Engine And Session Factory

AuthLoom uses the async SQLAlchemy session factory created by your app.

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

database_url = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(
    database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

Use async SQLAlchemy URLs. For example, use `sqlite+aiosqlite:///...`, not
`sqlite:///...`.

You may also reuse the same factory in application dependencies:

```python
from collections.abc import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

## 3. Create AuthLoom

Only `session_factory` is required.

```python
from authloom import AuthLoom, AuthLoomConfig

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
    )
)
```

## 4. Add The Minimum Migration Setup

Before signup can work, the database must contain AuthLoom's tables.

AuthLoom does not install Alembic or run migrations for you. Add AuthLoom metadata
to your application-owned Alembic `target_metadata`:

```python
from authloom.db import metadata as authloom_metadata

target_metadata = authloom_metadata
```

If your app also has its own models, include both metadata objects:

```python
from authloom.db import metadata as authloom_metadata
from myapp.db import Base

target_metadata = [authloom_metadata, Base.metadata]
```

Then generate, review, and apply a migration:

```bash
alembic revision --autogenerate -m "add authloom tables"
alembic upgrade head
```

See [Database and Migrations](database-and-migrations.md) for the complete
beginner migration guide.

## 5. Mount The Router Once

For the localhost-only curl smoke test below, mount AuthLoom's router once:

```python
from fastapi import FastAPI

from authloom import create_auth_router

app = FastAPI()
app.include_router(create_auth_router(auth))
```

The router defaults to `/auth`. To use another prefix, pass `prefix`:

```python
app.include_router(create_auth_router(auth, prefix="/accounts"))
```

Then use `/accounts/signup`, `/accounts/signin`, and the same prefix for the
other built-in routes. If your delivery hooks build password-reset or
email-verification links, use the same prefix in those URLs.

## 6. Localhost-Only Curl Smoke Test

This section is only for command-line testing on localhost. Do not use this
router setup in a browser or deployed app until you add CSRF protection in the
next section.

Start your app, then use a cookie jar so curl keeps the session cookie:

```bash
rm -f cookies.txt
```

Create an account. The password is 15 characters to satisfy the default minimum
length.

```bash
curl -i -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signup \
  -H 'content-type: application/json' \
  -d '{
    "name": "Example User",
    "email": "user@example.com",
    "password": "abcdefghijklmno",
    "password_confirm": "abcdefghijklmno"
  }'
```

Read the current user with the cookie saved by signup:

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/auth/me
```

Sign out and update the cookie jar:

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signout
```

Sign in again and save the new session cookie:

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signin \
  -H 'content-type: application/json' \
  -d '{
    "email": "user@example.com",
    "password": "abcdefghijklmno"
  }'
```

Confirm the new session works:

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/auth/me
```

## Mandatory CSRF For Browser Or Deployment Use

AuthLoom uses cookies for browser authentication. Before using AuthLoom from a
browser or deploying the app, add consumer-owned CSRF protection to every
browser-facing state-changing route.

For AuthLoom's built-in unsafe routes, pass your CSRF dependency when you create
the router. Replace the single `include_router` call above; do not mount the
router a second time.

```python
from fastapi import Depends

from authloom import create_auth_router

csrf_dependency = Depends(verify_csrf_request)

app.include_router(
    create_auth_router(
        auth,
        prefix="/auth",
        unsafe_route_dependencies=(csrf_dependency,),
    )
)
```

This applies to built-in state-changing routes such as signup, signin, signout,
password reset, password change, and token-request routes. Add the same kind of
protection separately to your application-owned HTML or JSON mutation routes.

AuthLoom does not require a specific CSRF library. The
[credentials-auth example](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth)
shows one complete implementation.

## Built-In Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/signup` | Create a user, create a session, and set the session cookie. |
| `POST` | `/auth/signin` | Verify credentials, create a session, and set the session cookie. |
| `POST` | `/auth/signout` | Revoke the current session and delete the session cookie. |
| `GET` | `/auth/me` | Return the current authenticated user. |
| `POST` | `/auth/request-password-reset` | Request a password-reset token and invoke the configured hook. |
| `POST` | `/auth/password-reset?token=...` | Complete password reset with a valid token. |
| `POST` | `/auth/password-change` | Change the authenticated user's password. |
| `POST` | `/auth/request-email-verification` | Request an email-verification token and invoke the configured hook. |
| `GET` | `/auth/email-verification?token=...` | Consume the submitted verification token and mark the email verified. |

`GET /auth/email-verification?token=...` is a clickable bearer-token link from
email. Use HTTPS, avoid logging full URLs, and do not require a browser CSRF
token for that route.

If you configured a custom router prefix, replace `/auth` with that prefix in the
paths above.

## Use Current-User Dependencies

Use `auth.require_current_user` when a route must have a valid session cookie. It
returns the AuthLoom `User` model or raises `401 Unauthorized`.

```python
from typing import Annotated

from fastapi import Depends

from authloom.db import User

@app.get("/me")
async def get_me(user: Annotated[User, Depends(auth.require_current_user)]):
    return {"id": user.id, "email": user.email, "name": user.name}
```

Use `auth.optional_current_user` when a route should work for both anonymous and
authenticated users. It returns `User | None`.

```python
@app.get("/homepage")
async def homepage(
    user: Annotated[User | None, Depends(auth.optional_current_user)],
):
    return {"authenticated": user is not None}
```

## Operations

### Clean Up Stale Sessions

AuthLoom checks session validity during authentication. Cleanup is separate: it
removes expired and revoked session rows to control database growth.

```python
deleted_count = await auth.delete_stale_sessions()
```

For deterministic cleanup, pass a timezone-aware cutoff:

```python
from datetime import UTC, datetime

deleted_count = await auth.delete_stale_sessions(
    before=datetime(2026, 1, 1, tzinfo=UTC)
)
```

Your application decides when to run cleanup. AuthLoom does not include cron, a
worker, a CLI, or a scheduler.

### Production Notes

- Use HTTPS and production cookie settings. See [Configuration](configuration.md).
- Keep migrations reviewed and application-owned. See
  [Database and Migrations](database-and-migrations.md).
- Read [Account Security Flows](account-security-flows.md) before enabling
  password reset, password change, or email verification.
- Route-level authorization for your own resources remains application-owned.
