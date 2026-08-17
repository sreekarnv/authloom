# Credentials Auth Example

This example shows how a FastAPI application can consume AuthLoom for email/password authentication with session cookies, account-security flows, consumer-owned CSRF protection, and consumer-owned email delivery.

It can run with SQLite for quick local development or PostgreSQL for a more production-like local setup.

This is a reference implementation for learning and integration testing. It is not a production application template; review security, deployment, email, CSRF, rate limiting, observability, and operational requirements before adapting it.

## What It Demonstrates

- Plain Jinja2 template pages for signup, signin, signout, password reset, password change, and email verification.
- AuthLoom's JSON router under `/auth`.
- Application-owned routes that use AuthLoom authentication dependencies.
- AuthLoom metadata combined with application-owned SQLAlchemy models.
- Consumer-owned Alembic migrations.
- SQLite or PostgreSQL through one `DATABASE_URL` setting.
- Consumer-owned CSRF protection for browser cookie flows.
- Local password-reset and email-verification delivery through MailHog.

## Responsibilities

AuthLoom owns:

- Authentication routes mounted with `create_auth_router(auth)`.
- User and session models exposed through `authloom.db`.
- Session cookie creation, validation, revocation, and deletion.
- Password hashing and credential verification.
- Password reset, password change, and email-verification token consumption.

The consuming application owns:

- Database engine and session factory setup.
- Alembic migration history.
- Application models, such as `Post`.
- Application routes that use AuthLoom authentication dependencies.
- Environment and deployment-specific configuration.
- CSRF token issuance, validation, and cookie/body configuration.
- Email delivery. This example sends password-reset and email-verification links through MailHog.

## Install

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../../
```

When copied into a separate application, replace `pip install -e ../../` with a normal AuthLoom package dependency.

## Choose A Database

SQLite is the default and does not require Docker:

```env
DATABASE_URL=sqlite+aiosqlite:///./authloom_example.db
```

For PostgreSQL, start the database and set `DATABASE_URL`:

```bash
docker compose up -d postgres
```

```env
DATABASE_URL=postgresql+asyncpg://authloom:authloom@localhost:5432/authloom
```

Both options use async SQLAlchemy URLs. Do not use synchronous URLs such as `sqlite:///...` or `postgresql://...`.

## Configure Environment

Create `.env` from the example file:

```bash
cp .env.example .env
```

Set a strong `CSRF_SECRET_KEY` before starting the app:

```env
CSRF_SECRET_KEY=replace-with-a-long-random-value
```

Other useful settings:

```env
APP_BASE_URL=http://127.0.0.1:8000
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
EMAIL_FROM=no-reply@authloom.local
```

## Run Database Migrations

From this directory:

```bash
alembic upgrade head
```

The example owns its Alembic migration history and includes AuthLoom metadata in `alembic/env.py` so migrations include AuthLoom tables and the example `posts` table.

## Start MailHog

Password-reset and email-verification links are sent through SMTP. For local delivery, start MailHog:

```bash
docker compose up -d mailhog
```

MailHog's inbox is available at `http://127.0.0.1:8025`.

If MailHog is not running, routes that request password-reset or email-verification emails can fail when the delivery hook tries to send mail.

## Start The App

From this directory:

```bash
fastapi dev
```

The app will be available at:

```text
http://127.0.0.1:8000
```

## HTML Routes

The example renders plain Jinja2 templates:

- `GET /` redirects to the account page or signin page.
- `GET/POST /signup` creates an account and signs the user in.
- `GET/POST /signin` signs the user in.
- `POST /signout` signs the user out.
- `GET/POST /forgot-password` requests a password-reset link.
- `GET/POST /reset-password` completes a password reset.
- `GET/POST /account/password` changes the current password.
- `POST /account/email-verification` requests a verification link.
- `GET /auth/email-verification?token=...` consumes a verification link through AuthLoom core.
- `GET /verify-email` is an optional HTML wrapper that delegates to AuthLoom core when used directly.
- `GET /account` displays the current user and verification state.

The JSON AuthLoom router remains available under `/auth`.

## Authentication Flow With Curl

Use a cookie jar so curl preserves the session cookie between requests.

Fetch a CSRF token before unsafe requests:

```bash
curl -i -c cookies.txt http://127.0.0.1:8000/csrf
```

Include the returned token as the `csrf_token` field in each unsafe request. The HTML forms already include this hidden field.

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

### Current User

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/auth/me
```

### Signout

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signout \
  -H 'content-type: application/x-www-form-urlencoded' \
  -d 'csrf_token=<csrf-token>'
```

After signout, authenticated routes should return `401`.

## CSRF Responsibility

This example uses `fastapi-csrf-protect` to protect AuthLoom's signup, signin, signout, password-reset request, password-reset completion, password-change, and email-verification request routes through `unsafe_route_dependencies`. It also protects the application-owned `POST /example-mutation` route.

AuthLoom does not generate or validate CSRF tokens, and the example does not claim that they are bound to AuthLoom sessions. The clickable `GET /auth/email-verification?token=...` route uses the verification token as bearer authorization and does not require a CSRF token. CORS remains a separate application configuration concern.

## Troubleshooting

- If migrations fail with a driver error, check that `DATABASE_URL` uses `sqlite+aiosqlite://` or `postgresql+asyncpg://`.
- If PostgreSQL connection fails, run `docker compose up -d postgres` and confirm port `5432` is available.
- If email links do not appear, run `docker compose up -d mailhog` and open `http://127.0.0.1:8025`.
- If forms fail CSRF validation, fetch a fresh `/csrf` token or clear stale cookies.
- If cookies are not sent over local HTTP, ensure `secure=False` in local cookie settings.
- If a reset or verification link fails, it may be expired or already used.
