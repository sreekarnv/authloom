# Credentials Auth Basic Example

This example shows how a FastAPI application can consume AuthLoom for basic email/password authentication with session cookies.

It demonstrates:

- Signup, signin, signout, and AuthLoom's built-in `/auth/me` route.
- An application-owned protected `/me` route.
- An application-owned `/optional-auth` route that works with or without a session.
- AuthLoom configuration through public APIs.
- AuthLoom database metadata combined with application-owned SQLAlchemy models.
- Consumer-owned Alembic migrations.
- Consumer-owned CSRF protection for browser cookie flows.

This example is intentionally SQLite-focused for local development.

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
- CSRF token issuance, validation, and cookie/header configuration.


## Install

From this directory:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ../../
```

When copied into a separate application, replace `pip install -e ../../` with a
normal AuthLoom package dependency.

## Run Database Migrations

From this directory:

```bash
alembic upgrade head
```

## Start The App

From this directory:

```bash
fastapi dev
```

Set a strong `CSRF_SECRET_KEY` before starting the application:

```bash
CSRF_SECRET_KEY='replace-with-a-long-random-value' fastapi dev
```

The app will be available at:

```text
http://127.0.0.1:8000
```

## Authentication Flow With Curl

Use a cookie jar so curl preserves the session cookie between requests.

Fetch a CSRF token before unsafe requests:

```bash
curl -i -c cookies.txt http://127.0.0.1:8000/csrf
```

Send the returned token in the `X-CSRF-Token` request header. Follow the
`fastapi-csrf-protect` documentation for client-side token handling.

In `/docs`, execute `GET /csrf` first, copy the `csrf_token` value, then use
`Try it out` on an unsafe route and enter that value in the `X-CSRF-Token`
header field.

### Signup

```bash
curl -i -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signup \
  -H 'content-type: application/json' \
  -H 'X-CSRF-Token: <csrf-token>' \
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
  -X POST http://127.0.0.1:8000/auth/signout \
  -H 'X-CSRF-Token: <csrf-token>'
```

After signout, authenticated routes should return `401`.

### Application-Owned Mutation

```bash
curl -i -b cookies.txt \
  -X POST http://127.0.0.1:8000/example-mutation \
  -H 'X-CSRF-Token: <csrf-token>'
```

### Signin Again

```bash
curl -i -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signin \
  -H 'content-type: application/json' \
  -H 'X-CSRF-Token: <csrf-token>' \
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

## CSRF Responsibility

This example uses `fastapi-csrf-protect` to protect AuthLoom's signup, signin,
and signout routes through `unsafe_route_dependencies`. It also protects the
application-owned `POST /example-mutation` route. AuthLoom does not generate or
validate these tokens, and the example does not claim that they are bound to
AuthLoom sessions. CORS remains a separate application configuration concern.
