# AuthLoom

AuthLoom is a Python 3.12 authentication library for FastAPI applications.

It currently provides email/password signup and signin, cookie-backed database sessions, required and optional current-user dependencies, Argon2 password hashing, normalized email handling, hashed session tokens, expiry, and signout revocation.

AuthLoom is pre-release software. APIs and database integration details may change before the first stable release.

## Installation

Using `uv`:

```bash
uv add "authloom==0.1.0a1"
```

Using `pip`:

```bash
pip install "authloom==0.1.0a1"
```

## Requirements

- Python `>=3.12`
- FastAPI `>=0.140.0`
- SQLAlchemy `>=2.0.51` with async sessions

## Basic Usage

Applications provide the async SQLAlchemy session factory and own database setup.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from authloom import AuthLoom, AuthLoomConfig, create_auth_router
from authloom.db import User

engine = create_async_engine("sqlite+aiosqlite:///./app.db")
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

auth = AuthLoom(config=AuthLoomConfig(session_factory=SessionLocal))

app = FastAPI()
app.include_router(create_auth_router(auth))


@app.get("/protected")
async def protected_route(
    user: Annotated[User, Depends(auth.require_current_user)],
):
    return {"id": user.id, "email": user.email}


@app.get("/optional")
async def optional_route(
    user: Annotated[User | None, Depends(auth.optional_current_user)],
):
    return {"authenticated": user is not None}
```

## Routes

`create_auth_router(auth)` creates a FastAPI router mounted at `/auth`.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/signup` | Create a user, create a session, and set the session cookie. |
| `POST` | `/auth/signin` | Verify credentials, create a session, and set the session cookie. |
| `POST` | `/auth/signout` | Revoke the current session and delete the session cookie when present. |
| `GET` | `/auth/me` | Return the current authenticated user. |

## Configuration

The required configuration value is `session_factory`.

```python
from authloom import AuthLoom, AuthLoomConfig
from authloom.settings import AuthLoomCookieSessionConfig, AuthLoomPasswordConfig

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=SessionLocal,
        cookie_session=AuthLoomCookieSessionConfig(
            cookie_name="authloom.auth",
            ttl=60 * 60 * 24 * 7,
            http_only=True,
            secure=True,
            samesite="lax",
            path="/",
        ),
        password_config=AuthLoomPasswordConfig(
            min_length=15,
            max_length=64,
        ),
    )
)
```

Cookie settings:

| Option | Default | Notes |
| --- | --- | --- |
| `cookie_name` | `"authloom.auth"` | Must not be empty. |
| `ttl` | `604800` | Lifetime in seconds. Must be greater than zero. |
| `http_only` | `True` | Prevents browser JavaScript from reading the cookie. |
| `secure` | `False` | Use `True` in HTTPS production deployments. |
| `samesite` | `"lax"` | One of `"lax"`, `"strict"`, or `"none"`. `"none"` requires `secure=True`. |
| `domain` | `None` | Optional cookie domain. |
| `path` | `"/"` | Must not be empty and must start with `/`. |

Password settings:

| Option | Default | Validation |
| --- | --- | --- |
| `min_length` | `15` | Cannot be less than `15` and cannot exceed `max_length`. |
| `max_length` | `64` | Cannot be less than `64` or greater than `128`. |

Use `secure=True` for HTTPS production deployments.

See `docs/configuration.md` for the full configuration reference.

For an end-to-end adoption guide, see `docs/consumer-integration.md`.

## Database And Migrations

AuthLoom does not own migrations. Applications own Alembic setup and migration history.

Include AuthLoom metadata in the application Alembic configuration when generating migrations:

```python
from authloom.db import metadata as authloom_metadata

target_metadata = [authloom_metadata, your_app_metadata]
```

Do not rely on `metadata.create_all()` for production schema management.

See `docs/database-and-migrations.md` for more detail.

## Security Model

AuthLoom currently provides:

- Argon2 password hashing.
- Email normalization before signup and signin.
- Random session tokens sent to clients only through cookies.
- SHA-256 hashes of session tokens stored in the database.
- Session expiry based on the configured cookie/session lifetime.
- Session revocation during signout.
- `HttpOnly` cookie support.
- Generic invalid-credential responses for signin failures.

Production deployments should use HTTPS and `secure=True` cookies. AuthLoom does not add a separate CSRF protection system beyond the configured cookie policy.

See `docs/security.md` for more detail.

## v0.1 Limitations

AuthLoom does not currently provide:

- Rate limiting or brute-force protection.
- Email verification.
- Password reset or password change flows.
- Multi-factor authentication.
- OAuth or social login.
- JWT access or refresh tokens.
- Roles, permissions, organizations, or multi-tenancy.
- Session cleanup jobs for expired or revoked sessions.
- Packaged database migrations or a migration CLI.

## Documentation

- Consumer integration guide: `docs/consumer-integration.md`
- Configuration reference: `docs/configuration.md`
- Database and migrations: `docs/database-and-migrations.md`
- Security model: `docs/security.md`

## Example Applications

See `examples/credentials_auth_basic/` for a SQLite FastAPI example.

See `examples/credentials_auth_postgres/` for a PostgreSQL FastAPI example.

## Development

Install development and test dependencies:

```bash
uv sync --locked --group dev --group test
```

Run Ruff:

```bash
uv run ruff check .
```

Run tests:

```bash
uv run pytest tests/unit
uv run pytest tests/integration
```

Build the package:

```bash
uv build
```

## License

This project is licensed under the Apache License 2.0. See `LICENSE` for details.
