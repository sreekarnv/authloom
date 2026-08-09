# Credentials Auth PostgreSQL Example

This example shows how a FastAPI application can consume AuthLoom for basic email/password authentication with session cookies, PostgreSQL, and consumer-owned CSRF protection.

It demonstrates:

- Plain Jinja2 template pages for signup, signin, signout, password reset,
  password change, and email verification.
- Signup, signin, signout, and AuthLoom's built-in `/auth/me` route.
- An application-owned protected `/me` route.
- An application-owned `/optional-auth` route that works with or without a session.
- AuthLoom configuration through public APIs.
- AuthLoom database metadata combined with application-owned SQLAlchemy models.
- Consumer-owned Alembic migrations against PostgreSQL.
- Local PostgreSQL setup through Docker Compose.
- Consumer-owned CSRF protection for browser cookie flows.
- Local email delivery through MailHog.

The CSRF package is an example-only dependency and is not part of core AuthLoom.

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
- CSRF token issuance, validation, and cookie/body configuration.


## Install

From this directory:

```bash
python -m venv venv
source venv/bin/activate
pip install -e ../../ "fastapi[standard]" Jinja2 python-multipart alembic asyncpg fastapi-csrf-protect==1.0.7
```

When copied into a separate application, replace `pip install ../../` with a
normal AuthLoom package dependency.

## Start PostgreSQL

From this directory:

```bash
docker compose up -d postgres mailhog
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

Set a strong `CSRF_SECRET_KEY` before starting the application:

```bash
CSRF_SECRET_KEY='replace-with-a-long-random-value' fastapi dev
```

Password-reset and email-verification emails are delivered to MailHog. Open
the MailHog inbox at `http://127.0.0.1:8025`. Set `APP_BASE_URL` when running
the application at a different address.

The application sends SMTP traffic to MailHog at `127.0.0.1:1025` by default.
Override `SMTP_HOST`, `SMTP_PORT`, or `EMAIL_FROM` in `.env` when needed.

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

Include the returned token as the `csrf_token` field in each unsafe request.
The HTML forms already include this hidden field.

In `/docs`, execute `GET /csrf` first, copy the `csrf_token` value, then include
it in the JSON body of an unsafe route.

### Signup

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signup \
  -H 'content-type: application/json' \
  -d '{
    "csrf_token": "<csrf-token>",
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
  -H 'content-type: application/x-www-form-urlencoded' \
  -d 'csrf_token=<csrf-token>'
```

After signout, authenticated routes should return `401`.

### Application-Owned Mutation

```bash
curl -i -b cookies.txt \
  -X POST http://127.0.0.1:8000/example-mutation \
  -H 'content-type: application/x-www-form-urlencoded' \
  -d 'csrf_token=<csrf-token>'
```

### Signin Again

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signin \
  -H 'content-type: application/json' \
  -d '{
    "csrf_token": "<csrf-token>",
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

## HTML Routes

The example renders plain Jinja2 templates without CSS or JavaScript:

- `GET /` redirects to the account page or signin page.
- `GET/POST /signup` creates an account and signs the user in.
- `GET/POST /signin` signs the user in.
- `POST /signout` signs the user out.
- `GET/POST /forgot-password` requests a password-reset link.
- `GET/POST /reset-password` completes a password reset.
- `GET/POST /account/password` changes the current password.
- `POST /account/email-verification` requests a verification link.
- `GET /verify-email` consumes a verification link in the example application.
- `GET /account` displays the current user and verification state.

The JSON AuthLoom router remains available under `/auth`.

## CSRF Responsibility

This example uses `fastapi-csrf-protect` to protect AuthLoom's signup, signin,
and signout routes through `unsafe_route_dependencies`. It also protects the
application-owned `POST /example-mutation` route. AuthLoom does not generate or
validate these tokens, and the example does not claim that they are bound to
AuthLoom sessions. CORS remains a separate application configuration concern.
