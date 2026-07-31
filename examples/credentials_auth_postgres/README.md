# Credentials Auth PostgreSQL Example

This example shows how a FastAPI application can consume AuthLoom for basic email/password authentication with session cookies and PostgreSQL.

It demonstrates:

- Signup, signin, signout, and AuthLoom's built-in `/auth/me` route.
- An application-owned protected `/me` route.
- An application-owned `/optional-auth` route that works with or without a session.
- AuthLoom configuration through public APIs.
- AuthLoom database metadata combined with application-owned SQLAlchemy models.
- Consumer-owned Alembic migrations against PostgreSQL.
- Local PostgreSQL setup through Docker Compose.

## Responsibilities

AuthLoom owns:

- Authentication routes mounted with `create_auth_router(auth)`.
- User and session models exposed through `authloom.db`.
- Session cookie creation, validation, revocation, and deletion.
- Password hashing and credential verification.

The consuming application owns:

- Database engine and session factory setup.
- Alembic migration history.
- Application models, such as `Post`.
- Application routes that use AuthLoom authentication dependencies.
- Environment and deployment-specific configuration.


## Install

From this directory:

```bash
python -m venv venv
source venv/bin/activate
pip install -e ../../ "fastapi[standard]" alembic asyncpg
```

When copied into a separate application, replace `pip install ../../` with a
normal AuthLoom package dependency.

## Start PostgreSQL

From this directory:

```bash
docker compose up -d postgres
```

The default database URL is:

```text
postgresql+asyncpg://authloom:authloom@localhost:5432/authloom
```

Override it with `DATABASE_URL` if needed. The app and Alembic both use the
async `postgresql+asyncpg://` URL by default.

If you prefer synchronous Alembic migrations, install `psycopg[binary]` and
adapt `alembic/env.py` and `alembic.ini` to use `postgresql+psycopg://`.

## Run Database Migrations

After PostgreSQL is running, from this directory:

```bash
alembic upgrade head
```

## Start The App

From this directory:

```bash
fastapi dev
```

The app will be available at:

```text
http://127.0.0.1:8000
```

## Authentication Flow With Curl

Use a cookie jar so curl preserves the session cookie between requests.

### Signup

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

The response sets the `authloom.auth` cookie.

### Built-In AuthLoom `/auth/me`

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/auth/me
```

### Application-Owned Protected `/me`

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/me
```

Without a valid cookie, this route returns `401`.

### Application-Owned Optional Auth

Without a cookie:

```bash
curl -i http://127.0.0.1:8000/optional-auth
```

With a cookie:

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/optional-auth
```

### Signout

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signout
```

After signout, authenticated routes should return `401`.

### Signin Again

```bash
curl -i -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signin \
  -H 'content-type: application/json' \
  -d '{
    "email": "user@example.com",
    "password": "abcdefghijklmno"
  }'
```

## Cookie Settings

The example configures cookies for local development:

```python
AuthLoomCookieSessionConfig(
    cookie_name="authloom.auth",
    http_only=True,
    samesite="lax",
    secure=False,
)
```

For HTTPS production deployments, set `secure=True`.

If you use `samesite="none"`, AuthLoom requires `secure=True`.
