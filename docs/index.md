# AuthLoom

AuthLoom is a Python 3.12 or newer authentication library for FastAPI applications.

It provides email/password signup and signin, cookie-backed database sessions,
current-user dependencies, password reset, password change, and email
verification. AuthLoom is pre-release software; APIs and database integration
details may change before the first stable release.

## Mental Model

AuthLoom owns authentication behavior and its database models: users, sessions,
password-reset tokens, and email-verification tokens.

Your application owns the FastAPI app, database engine, async session factory,
migrations, CSRF protection, email delivery, UI, deployment settings, and
authorization rules for your own resources.

## Prerequisites

You should already have, or be ready to add:

- Python 3.12 or newer.
- FastAPI.
- SQLAlchemy 2 with async sessions.
- One async database driver, such as `aiosqlite` or `asyncpg`.
- Alembic or another migration workflow.

## Choose A Starting Path

- Existing app: follow the [Consumer Integration Guide](consumer-integration.md).
- Reference example: run
  [`examples/credentials_auth`](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth)
  to see HTML forms, CSRF protection, migrations, and local email delivery in one
  small app.

## Recommended Reading Order

1. [Consumer Integration](consumer-integration.md) - install, configure, migrate,
   mount routes, and test first authentication.
2. [Database and Migrations](database-and-migrations.md) - make AuthLoom tables
   part of your application-owned migration history.
3. [Configuration](configuration.md) - required setting first, then optional
   cookies, password policy, and hooks.
4. [Account Security Flows](account-security-flows.md) - password reset, password
   change, email verification, hooks, and CSRF boundaries.
5. [Security Model](security-model.md) - security guarantees and application
   responsibilities.
