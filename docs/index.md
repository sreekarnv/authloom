# AuthLoom

AuthLoom is a Python 3.12 authentication library for FastAPI applications.

It currently provides email/password signup and signin, cookie-backed database
sessions, required and optional current-user dependencies, Argon2 password
hashing, normalized email handling, hashed session tokens, expiry, signout
revocation, password reset, password change, and email verification request and
completion.

AuthLoom is pre-release software. APIs and database integration details may change before the first stable release.

## Install

Using `uv`:

```bash
uv add authloom
```

Using `pip`:

```bash
pip install authloom
```

## Start Here

If you installed AuthLoom from PyPI and want to wire it into an application, start with the [Consumer Integration Guide](consumer-integration.md).

## Documentation

- [Consumer Integration Guide](consumer-integration.md)
- [Configuration](configuration.md)
- [Account Security Flows](account-security-flows.md)
- [Database And Migrations](database-and-migrations.md)
- [Security](security-model.md)

## Reference Implementations

- [FastAPI credentials-auth reference implementation](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth)
  that can run with SQLite by default or PostgreSQL via `DATABASE_URL` and
  Docker Compose. It is a reference implementation, not a production template.
