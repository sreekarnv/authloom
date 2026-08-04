# Consumer Integration Guide

This guide shows how to add AuthLoom to an existing FastAPI application after installing the published package from PyPI.

It does not create another example application. For complete reference implementations, see the SQLite example in [`examples/credentials_auth_basic/`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_basic) and the PostgreSQL example in [`examples/credentials_auth_postgres/`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_postgres).

## Install AuthLoom

Using `uv`:

```bash
uv add authloom
```

Using `pip`:

```bash
pip install authloom
```

Install the async database driver your application uses:

```bash
uv add aiosqlite
uv add asyncpg
```

Or with `pip`:

```bash
pip install aiosqlite
pip install asyncpg
```

Use `aiosqlite` for SQLite URLs and `asyncpg` for PostgreSQL URLs.

## Configure The Database URL

AuthLoom uses your application's async SQLAlchemy engine and session factory. Store the database URL in your normal application settings.

SQLite for local development:

```python
database_url = "sqlite+aiosqlite:///./app.db"
```

PostgreSQL:

```python
database_url = "postgresql+asyncpg://user:password@localhost:5432/app"
```

Use SQLAlchemy's async dialect names. `sqlite:///...` and `postgresql://...` are synchronous URLs and are not supported by AuthLoom's current public API.

## Create The Async Engine

Create the engine in your application, not inside AuthLoom.

SQLite:

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "sqlite+aiosqlite:///./app.db",
    echo=False,
    connect_args={"check_same_thread": False},
)
```

PostgreSQL:

```python
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost:5432/app",
    echo=False,
)
```

## Create The Session Factory

AuthLoom requires an `async_sessionmaker[AsyncSession]`.

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

You can use the same factory for your own application dependencies:

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

## Configure AuthLoom

Create one `AuthLoom` instance with your session factory.

```python
from authloom import AuthLoom, AuthLoomConfig

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
    )
)
```

To customize cookie settings, pass `AuthLoomCookieSessionConfig`:

```python
from authloom import AuthLoom, AuthLoomConfig
from authloom.settings import AuthLoomCookieSessionConfig

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
        cookie_session=AuthLoomCookieSessionConfig(
            cookie_name="authloom.auth",
            ttl=60 * 60 * 24 * 7,
            http_only=True,
            secure=False,
            samesite="lax",
            path="/",
        ),
    )
)
```

## Mount The Authentication Router

Mount AuthLoom's router on your FastAPI app:

```python
from fastapi import FastAPI

from authloom import create_auth_router

app = FastAPI()
app.include_router(create_auth_router(auth))
```

### Add CSRF Protection

AuthLoom does not provide CSRF protection. If your application uses cookie
authentication, pass your own FastAPI dependency to the mutation routes:

```python
from fastapi import Depends

from authloom import create_auth_router

csrf_dependency = Depends(verify_csrf_request)

app.include_router(
    create_auth_router(
        auth,
        unsafe_route_dependencies=(csrf_dependency,),
    )
)
```

The dependency runs before signup, signin, and signout. It does not apply to
`GET /auth/me`. Add the same dependency to your own mutation routes.

You may use [`fastapi-csrf-protect`](https://pypi.org/project/fastapi-csrf-protect/),
another library, or your own implementation. Configure CORS separately.

The router is mounted at `/auth` and provides:

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/signup` | Create a user, create a session, and set the session cookie. |
| `POST` | `/auth/signin` | Verify credentials, create a session, and set the session cookie. |
| `POST` | `/auth/signout` | Revoke the current session and delete the session cookie when present. |
| `GET` | `/auth/me` | Return the current authenticated user. |

## Use Required Authentication

Use `auth.require_current_user` when a route must have a valid session cookie. It returns the AuthLoom `User` model or raises `401 Unauthorized`.

```python
from typing import Annotated

from fastapi import Depends

from authloom.db import User

@app.get("/me")
async def get_me(user: Annotated[User, Depends(auth.require_current_user)]):
    return {"id": user.id, "email": user.email, "name": user.name}
```

## Use Optional Authentication

Use `auth.optional_current_user` when a route should work for both anonymous and authenticated users. It returns `User | None`.

```python
from typing import Annotated

from fastapi import Depends

from authloom.db import User

@app.get("/homepage")
async def homepage(
    user: Annotated[User | None, Depends(auth.optional_current_user)],
):
    return {"authenticated": user is not None}
```

## Clean Up Stale Sessions

AuthLoom provides explicit cleanup for stale database sessions:

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

Expired and revoked sessions are deleted. AuthLoom provides the cleanup operation, but the consuming application decides when to run it. AuthLoom does not include cron, a worker, a CLI, or a scheduler.

Revoked sessions are deleted immediately by this cleanup method. If your application needs security auditing, record the relevant signout or revocation events elsewhere before deleting session rows.

## Combine Metadata

AuthLoom owns the `authloom_users` and `authloom_sessions` SQLAlchemy models. Your application still owns Alembic and migration files.

If your application has its own declarative base:

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

Combine AuthLoom metadata with application metadata in Alembic's `env.py`:

```python
from authloom.db import metadata as authloom_metadata
from myapp.schema import Base

target_metadata = [authloom_metadata, Base.metadata]
```

This lets Alembic autogenerate migrations for both AuthLoom tables and your application tables.

If your application models reference AuthLoom users, import `User` and use its ID column in foreign keys:

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from authloom.db import User
from myapp.schema import Base

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey(User.id), nullable=False)
```

## Create Consumer-Owned Alembic Migrations

AuthLoom does not ship migrations and does not run schema creation for you.

Create migrations with your application's Alembic workflow:

```bash
alembic revision --autogenerate -m "add authloom tables"
alembic upgrade head
```

Review the generated migration before applying it. It should include AuthLoom's `authloom_users` and `authloom_sessions` tables, plus any application tables that are new or changed.

Do not rely on `metadata.create_all()` for production. It can be useful for quick local experiments, but it is not a reviewed, ordered, repeatable migration history.

## Cookie Settings

AuthLoom's default cookie settings are intended for local development.

Local HTTP development:

```python
AuthLoomCookieSessionConfig(
    cookie_name="authloom.auth",
    http_only=True,
    secure=False,
    samesite="lax",
    path="/",
)
```

HTTPS production:

```python
AuthLoomCookieSessionConfig(
    cookie_name="authloom.auth",
    http_only=True,
    secure=True,
    samesite="lax",
    path="/",
)
```

Use `samesite="none"` only when the browser must send cookies in a cross-site context. AuthLoom requires `secure=True` with `samesite="none"`.

Set `domain` only when you need the cookie shared across a specific domain or subdomains. Leave it as `None` for most single-host applications.

## Common Integration Mistakes

- Using a synchronous SQLAlchemy URL such as `sqlite:///./app.db` or `postgresql://...` instead of an async URL.
- Passing a synchronous `sessionmaker` instead of `async_sessionmaker`.
- Forgetting to install the matching async database driver, such as `aiosqlite` or `asyncpg`.
- Creating AuthLoom tables with `create_all()` locally and then forgetting to add real Alembic migrations.
- Omitting `authloom.db.metadata` from Alembic `target_metadata`, which prevents autogenerate from seeing AuthLoom tables.
- Setting `secure=True` during plain HTTP local development, which prevents browsers from sending the cookie.
- Leaving `secure=False` in HTTPS production.
- Using `samesite="none"` without `secure=True`, which AuthLoom rejects during configuration validation.
- Mounting the router more than once or creating multiple `AuthLoom` instances with inconsistent cookie settings.
- Expecting AuthLoom to provide authorization rules; route-level authorization remains application-owned.

## Current Limitations

AuthLoom provides credentials signup/signin, cookie-backed database sessions, required and optional current-user dependencies, password hashing, email normalization, session expiry, and signout revocation.

It does not currently provide:

- Rate limiting or brute-force protection.
- Email verification.
- Password reset or password change flows.
- Multi-factor authentication.
- OAuth or social login.
- JWT access or refresh tokens.
- Roles, permissions, organizations, or multi-tenancy.
- Packaged database migrations or a migration CLI.
- A CSRF token or cookie mechanism; configure consumer-owned protection for
  cookie-authenticated browser applications.

## Reference Implementations

- SQLite: [`examples/credentials_auth_basic/`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_basic)
- PostgreSQL: [`examples/credentials_auth_postgres/`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_postgres)
- Migration details: [Database And Migrations](database-and-migrations.md)
- Cookie and security details: [Security](security-model.md)
