# Database and Migrations

AuthLoom uses async SQLAlchemy models, but your application owns the database and
schema migrations.

## Plain-Language Terms

- **Migration**: a reviewed file that changes the database schema, such as
  creating a table or adding a column.
- **Metadata**: SQLAlchemy's description of tables and columns in Python.
- **Autogenerate**: Alembic's command that compares metadata with the database
  and writes a draft migration.

## Responsibilities

AuthLoom provides:

- SQLAlchemy models for users, sessions, password-reset tokens, and
  email-verification tokens.
- Metadata exposed as `authloom.db.metadata`.
- Runtime database access through your `async_sessionmaker[AsyncSession]`.

Your application provides:

- The async SQLAlchemy engine.
- The async session factory.
- Alembic or another migration tool.
- Migration files and migration history.
- Application-owned models and metadata.

AuthLoom does not install Alembic, provide packaged migration files, or run schema
creation for you.

## Session Factory Naming

Use an async session factory and pass it to `AuthLoomConfig`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from authloom import AuthLoom, AuthLoomConfig

engine = create_async_engine("sqlite+aiosqlite:///./app.db")
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

auth = AuthLoom(config=AuthLoomConfig(session_factory=AsyncSessionLocal))
```

Synchronous SQLAlchemy sessions are not supported by AuthLoom's current public
API.

## Expected AuthLoom Tables

A migration that adds AuthLoom should create these tables:

- `authloom_users`
- `authloom_sessions`
- `authloom_reset_password_tokens`
- `authloom_email_verification_tokens`

Your migration may also include application-owned tables if they are new or
changed.

## If You Already Use Alembic

Open your Alembic `env.py` and set `target_metadata` so autogenerate can see
AuthLoom's tables.

For an AuthLoom-only app:

```python
from authloom.db import metadata as authloom_metadata

target_metadata = authloom_metadata
```

For an app with its own SQLAlchemy models:

```python
from authloom.db import metadata as authloom_metadata
from myapp.db import Base

# Import modules that define application models before autogenerate runs.
import myapp.models  # noqa: F401

target_metadata = [authloom_metadata, Base.metadata]
```

Importing application models matters. If a model class has not been imported,
SQLAlchemy may not have registered its table in `Base.metadata`, and Alembic may
miss it during autogenerate.

If your app uses async database URLs such as `sqlite+aiosqlite://...` or
`postgresql+asyncpg://...`, your Alembic environment should use Alembic's async
pattern. The credentials-auth example has a working async `alembic/env.py`:

<https://github.com/sreekarnv/authloom/blob/main/examples/credentials_auth/alembic/env.py>

## If You Do Not Use Alembic Yet

Install Alembic in your application environment. AuthLoom does not install it.

```bash
uv add --dev alembic
```

Or with `pip`:

```bash
pip install alembic
```

For async SQLAlchemy applications, start with Alembic's async template:

```bash
alembic init -t async alembic
```

Then configure your database URL and set `target_metadata` in `alembic/env.py` as
shown above.

## Generate And Apply A Migration

Generate a draft migration:

```bash
alembic revision --autogenerate -m "add authloom tables"
```

Open the generated file and review it before applying it. Confirm that it creates
the expected AuthLoom tables and does not drop or rename application tables by
mistake.

Apply the migration:

```bash
alembic upgrade head
```

For a new empty database, the first AuthLoom migration usually creates the four
AuthLoom tables. For an existing database, it should only add missing AuthLoom
schema objects and any intentional application changes.

## Do Not Use create_all For Production

`metadata.create_all()` can be useful for quick local experiments, but it is not
a production migration workflow. It does not give you reviewed, ordered,
repeatable schema changes.

Use Alembic or your application's normal migration process for production and
shared environments.

## Example Reference

The
[credentials-auth example](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth)
shows SQLite by default, optional PostgreSQL, app-owned Alembic migrations, and
combined AuthLoom/application metadata.
