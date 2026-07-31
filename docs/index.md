# AuthLoom

AuthLoom is a Python 3.12 authentication library for FastAPI applications.

It currently provides email/password signup and signin, cookie-backed database sessions, required and optional current-user dependencies, Argon2 password hashing, normalized email handling, hashed session tokens, expiry, and signout revocation.

AuthLoom is pre-release software. APIs and database integration details may change before the first stable release.

## Install

Using `uv`:

```bash
uv add "authloom==0.1.0a1"
```

Using `pip`:

```bash
pip install "authloom==0.1.0a1"
```

## Start Here

If you installed AuthLoom from PyPI and want to wire it into an application, start with the [Consumer Integration Guide](consumer-integration.md).

## Documentation

- [Consumer Integration Guide](consumer-integration.md)
- [Configuration](configuration.md)
- [Database And Migrations](database-and-migrations.md)
- [Security](security.md)

## Reference Implementations

- [SQLite FastAPI example](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_basic)
- [PostgreSQL FastAPI example](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth_postgres)
