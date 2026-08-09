# Database And Migrations

AuthLoom uses async SQLAlchemy models for users, sessions, password-reset
tokens, and email-verification tokens, but the consuming application owns
database setup and schema migrations.

## Responsibilities

AuthLoom provides:

- SQLAlchemy models for AuthLoom users, sessions, password-reset tokens, and
  email-verification tokens.
- SQLAlchemy metadata exposed as `authloom.db.metadata`.
- Runtime access through an application-provided `async_sessionmaker[AsyncSession]`.

The application provides:

- The SQLAlchemy async engine.
- The async session factory.
- Alembic configuration.
- Migration files and migration history.
- Application-owned models and metadata.

AuthLoom does not currently provide a migration CLI or packaged migration files.

## Session Factory

Pass an async SQLAlchemy session factory to `AuthLoomConfig`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from authloom import AuthLoom, AuthLoomConfig

engine = create_async_engine("sqlite+aiosqlite:///./app.db")
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

auth = AuthLoom(config=AuthLoomConfig(session_factory=SessionLocal))
```

AuthLoom expects async SQLAlchemy sessions. Synchronous SQLAlchemy sessions are not supported by the current public API.

## Alembic Metadata

If the application uses Alembic autogenerate, include AuthLoom metadata in `target_metadata` alongside application metadata:

```python
from authloom.db import metadata as authloom_metadata
from myapp.db import Base

target_metadata = [authloom_metadata, Base.metadata]
```

This lets Alembic see both AuthLoom tables and application-owned tables when generating migrations.

The AuthLoom user model includes nullable `email_verified_at`. It remains
`NULL` until the application completes email verification, then records the
verification timestamp. Token tables include expiry and single-use state.

## Production Migrations

Use Alembic or the application's normal migration workflow for production schema changes.

`metadata.create_all()` can be useful for quick local experiments, but it is not a replacement for migrations in production because it does not provide reviewed, ordered, repeatable schema changes.

## SQLite And PostgreSQL

The repository includes a SQLite example at [`examples/credentials_auth_basic/`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_basic). It demonstrates local development setup, app-owned Alembic migrations, and combining AuthLoom metadata with application metadata.

The repository also includes a PostgreSQL example at [`examples/credentials_auth_postgres/`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_postgres). It demonstrates using `postgresql+asyncpg://...`, async Alembic migrations, and a Docker Compose PostgreSQL database for local development.
