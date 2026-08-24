# AuthLoom

AuthLoom is a Python 3.12 or newer authentication library for FastAPI applications.

It provides email/password signup and signin, cookie-backed database sessions,
password reset, password change, email verification, and current-user
dependencies. AuthLoom is pre-release software; APIs and database integration
details may change before the first stable release.

## Installation

Using `uv`:

```bash
uv add authloom aiosqlite
```

Using `pip`:

```bash
pip install authloom aiosqlite
```

`aiosqlite` is only for the SQLite quickstart below. Install the async database
driver your application uses, such as `asyncpg` for PostgreSQL.

## Quickstart

Minimal application wiring. This is not a complete production setup.
Applications provide the async SQLAlchemy session factory and own database setup.

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from authloom import AuthLoom, AuthLoomConfig, create_auth_router
from authloom.db import User

engine = create_async_engine("sqlite+aiosqlite:///./app.db")
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

auth = AuthLoom(config=AuthLoomConfig(session_factory=AsyncSessionLocal))

app = FastAPI()
app.include_router(create_auth_router(auth))


@app.get("/protected")
async def protected_route(
    user: Annotated[User, Depends(auth.require_current_user)],
):
    return {"id": user.id, "email": user.email}
```

Before using this in an application:

- Add AuthLoom metadata to your application-owned
  [Alembic migrations](https://sreekarnv.github.io/authloom/database-and-migrations/).
- Configure consumer-owned
  [CSRF protection](https://sreekarnv.github.io/authloom/consumer-integration/#mandatory-csrf-for-browser-or-deployment-use)
  before browser or deployment use.
- Use HTTPS and
  [`secure=True` cookies](https://sreekarnv.github.io/authloom/configuration/#production-cookie-settings)
  in production.

## Documentation

- Full documentation: <https://sreekarnv.github.io/authloom/>
- Consumer integration: <https://sreekarnv.github.io/authloom/consumer-integration/>
- Configuration: <https://sreekarnv.github.io/authloom/configuration/>
- Account security flows: <https://sreekarnv.github.io/authloom/account-security-flows/>
- Database and migrations: <https://sreekarnv.github.io/authloom/database-and-migrations/>
- Security model: <https://sreekarnv.github.io/authloom/security-model/>
- Changelog: <https://github.com/sreekarnv/authloom/blob/main/CHANGELOG.md>

## Example Application

See the FastAPI credentials-auth reference implementation at
<https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth>. It
runs with SQLite by default or PostgreSQL via `DATABASE_URL` and Docker Compose.

## Development

```bash
uv sync --locked --group dev --group test --group docs
uv run ruff check .
uv run pytest tests/unit tests/integration
uv run --locked --group docs mkdocs build --strict
uv build --no-sources
```

## License

AuthLoom is licensed under the Apache License 2.0. See
<https://github.com/sreekarnv/authloom/blob/main/LICENSE>.
