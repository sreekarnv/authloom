# AuthLoom

AuthLoom is a Python 3.12 authentication library for FastAPI applications.

It currently provides email/password signup and signin, cookie-backed database sessions, required and optional current-user dependencies, generic dependencies for built-in mutation routes, Argon2 password hashing, normalized email handling, hashed session tokens, expiry, signout revocation, password reset, password change, and email verification.

AuthLoom is pre-release software. APIs and database integration details may change before the first stable release.

## Installation

Using `uv`:

```bash
uv add authloom
```

Using `pip`:

```bash
pip install authloom
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
| `POST` | `/auth/request-password-reset` | Create a password-reset token and invoke the consumer hook when configured. |
| `POST` | `/auth/password-reset?token=<token_raw>` | Consume a valid reset token, update the password, and revoke every session. |
| `POST` | `/auth/password-change` | Verify the current password, change the password, and revoke other sessions while preserving the current session when supplied. |
| `POST` | `/auth/request-email-verification` | Create an email-verification token and invoke the consumer hook when configured. |
| `GET` | `/auth/email-verification?token=<token_raw>` | Consume a valid verification token and mark the user's email verified. |

Email delivery is consumer-owned. Password-reset and email-verification request
hooks receive raw one-time tokens so the application can construct and send
links. The email-verification completion route is a clickable bearer-token link;
use HTTPS and avoid logging full verification URLs.

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

See [`docs/configuration.md`](docs/configuration.md) for the full configuration reference.

For an end-to-end adoption guide, see [`docs/consumer-integration.md`](docs/consumer-integration.md).

## Database And Migrations

AuthLoom does not own migrations. Applications own Alembic setup and migration history.

Include AuthLoom metadata in the application Alembic configuration when generating migrations:

```python
from authloom.db import metadata as authloom_metadata

target_metadata = [authloom_metadata, your_app_metadata]
```

Do not rely on `metadata.create_all()` for production schema management.

See [`docs/database-and-migrations.md`](docs/database-and-migrations.md) for more detail.

## Session Cleanup

AuthLoom provides explicit cleanup for stale database sessions:

```python
deleted_count = await auth.delete_stale_sessions()
```

Expired and revoked sessions are deleted. AuthLoom provides the cleanup
operation, but the consuming application decides when to run it. AuthLoom does
not include cron, a worker, a CLI, or a scheduler.

## Security Model

AuthLoom currently provides:

- Argon2 password hashing.
- Email normalization before signup and signin.
- Random session tokens sent to clients only through cookies.
- SHA-256 hashes of session tokens stored in the database.
- Session expiry based on the configured cookie/session lifetime.
- Session revocation during signout.
- Manual cleanup of expired or revoked sessions.
- Password-reset token creation, single-use password reset, and automatic
  revocation of every active session after a successful reset.
- Password-change current-password verification and session invalidation that
  may preserve the current session.
- Email-verification token creation and single-use completion.
- `HttpOnly` cookie support.
- Generic invalid-credential responses for signin failures.
- Argon2 verification for both unknown-email and wrong-password signin failures.

For signin, unknown email and wrong password attempts return the same
invalid-credentials response. AuthLoom performs Argon2 verification in both
cases, using a dummy hash for unknown users, to reduce account-enumeration
timing differences. This does not replace rate limiting or brute-force
protection.

Production deployments should use HTTPS and `secure=True` cookies. AuthLoom uses
automatically submitted browser cookies for authentication, so applications that
authenticate browsers with those cookies must configure CSRF protection for unsafe
requests. `SameSite` reduces some cross-site request risks but is not a complete
CSRF defence for every browser flow.

AuthLoom does not provide a CSRF token format, CSRF cookie, issuance endpoint, or
global CSRF middleware. The consuming application selects and configures a CSRF
solution, such as `fastapi-csrf-protect`, another library, or an application-owned
implementation. AuthLoom provides a generic dependency hook for attaching that
solution to its built-in mutation routes. CORS and trusted-origin configuration
remain separate application responsibilities.

The `fastapi-csrf-protect` integration shown in the example application is an
optional example dependency. It is not installed by or required by core
AuthLoom.

See [`docs/security-model.md`](docs/security-model.md) for more detail.

## v0.1 Limitations

AuthLoom does not currently provide:

- Rate limiting or brute-force protection.
- Email delivery. Consumers own email providers and delivery hooks.
- Multi-factor authentication.
- OAuth or social login.
- JWT access or refresh tokens.
- Roles, permissions, organizations, or multi-tenancy.
- AuthLoom provides stale-session cleanup but does not schedule it automatically.
- Packaged database migrations or a migration CLI.

## Documentation

- Consumer integration guide: [`docs/consumer-integration.md`](docs/consumer-integration.md)
- Configuration reference: [`docs/configuration.md`](docs/configuration.md)
- Account security flows: [`docs/account-security-flows.md`](docs/account-security-flows.md)
- Database and migrations: [`docs/database-and-migrations.md`](docs/database-and-migrations.md)
- Security model: [`docs/security-model.md`](docs/security-model.md)

## Example Applications

See `examples/credentials_auth/` for a FastAPI credentials-auth reference
implementation that can run with SQLite by default or PostgreSQL via
`DATABASE_URL` and Docker Compose. It is a reference implementation, not a
production application template.

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
