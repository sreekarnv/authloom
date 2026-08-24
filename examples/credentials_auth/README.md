# Credentials Auth Example

This example shows one FastAPI application using AuthLoom for email/password
authentication, session cookies, account-security flows, CSRF protection, and
local email delivery.

It is for learning and integration testing. It is not a production application
template.

## Prerequisites

- Python 3.12 or newer.
- Docker, if you use MailHog for local email delivery or PostgreSQL for the
  database.

SQLite is the default database and does not need Docker. The HTML signup and
email flows still expect a reachable SMTP server. This README uses MailHog for
that SMTP server.

## What It Demonstrates

- Plain Jinja2 HTML pages for signup, signin, signout, password reset, password
  change, and email verification.
- AuthLoom's built-in JSON routes under `/auth`.
- Application-owned routes using AuthLoom current-user dependencies.
- AuthLoom metadata combined with application-owned SQLAlchemy models.
- Consumer-owned Alembic migrations.
- SQLite or PostgreSQL through one `DATABASE_URL` setting.
- Consumer-owned CSRF protection.
- Local password-reset and email-verification delivery through MailHog.

## 1. Install

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../../
```

When copied into a separate application, replace `pip install -e ../../` with a
normal AuthLoom package dependency.

## 2. Create .env And Set A CSRF Secret

Create `.env` from the example file:

```bash
cp .env.example .env
```

Set a strong `CSRF_SECRET_KEY`. It must be at least 32 characters.

```env
CSRF_SECRET_KEY=replace-with-a-long-random-value-123456
```

Other default settings:

```env
APP_BASE_URL=http://127.0.0.1:8000
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
EMAIL_FROM=no-reply@authloom.local
```

## 3. Choose A Database

SQLite is the default:

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

Both options use async SQLAlchemy URLs. Do not use synchronous URLs such as
`sqlite:///...` or `postgresql://...`.

## 4. Start MailHog

Start MailHog before testing signup, password reset, or email verification:

```bash
docker compose up -d mailhog
```

MailHog's inbox is available at:

```text
http://127.0.0.1:8025
```

Email delivery is application-owned. In this example, failed email delivery can
occur after AuthLoom has already persisted an account or token.

## 5. Run Database Migrations

From this directory:

```bash
alembic upgrade head
```

The example owns its Alembic migration history. `alembic/env.py` includes
AuthLoom metadata and the example application's metadata.

## 6. Start The App

From this directory:

```bash
fastapi dev app/main.py
```

The app will be available at:

```text
http://127.0.0.1:8000
```

## 7. Test With Curl

The built-in `/auth` routes are protected by this example's CSRF dependency.
Fetch a CSRF token before each unsafe request. The commands below store it in
`$CSRF_TOKEN` and send that value with the request.

Use a cookie jar so curl preserves both the CSRF cookie and the AuthLoom session
cookie:

```bash
rm -f cookies.txt
CSRF_TOKEN=$(curl -s -c cookies.txt http://127.0.0.1:8000/csrf \
  | python -c 'import json, sys; print(json.load(sys.stdin)["csrf_token"])')
echo "$CSRF_TOKEN"
```

### Signup

```bash
curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signup \
  -H 'content-type: application/json' \
  -d "{
    \"csrf_token\": \"$CSRF_TOKEN\",
    \"name\": \"Example User\",
    \"email\": \"user@example.com\",
    \"password\": \"abcdefghijklmno\",
    \"password_confirm\": \"abcdefghijklmno\"
  }"
```

The password is 15 characters to satisfy the default minimum length.

### Current User

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/auth/me
```

### Signout

Fetch a fresh CSRF token, then sign out:

```bash
CSRF_TOKEN=$(curl -s -b cookies.txt -c cookies.txt http://127.0.0.1:8000/csrf \
  | python -c 'import json, sys; print(json.load(sys.stdin)["csrf_token"])')

curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signout \
  -H 'content-type: application/x-www-form-urlencoded' \
  -d "csrf_token=$CSRF_TOKEN"
```

After signout, `/auth/me` should return `401`.

### Signin

Fetch a fresh CSRF token, then sign in again:

```bash
CSRF_TOKEN=$(curl -s -b cookies.txt -c cookies.txt http://127.0.0.1:8000/csrf \
  | python -c 'import json, sys; print(json.load(sys.stdin)["csrf_token"])')

curl -i -b cookies.txt -c cookies.txt \
  -X POST http://127.0.0.1:8000/auth/signin \
  -H 'content-type: application/json' \
  -d "{
    \"csrf_token\": \"$CSRF_TOKEN\",
    \"email\": \"user@example.com\",
    \"password\": \"abcdefghijklmno\"
  }"
```

Confirm the new session:

```bash
curl -i -b cookies.txt http://127.0.0.1:8000/auth/me
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
- `GET /verify-email` is an optional HTML verification result page.
- `GET /account` displays the current user and verification state.

Generated verification emails currently use AuthLoom's built-in route:

```text
/auth/email-verification?token=...
```

## Built-In /auth Routes

The AuthLoom JSON router is mounted under `/auth`:

- `POST /auth/signup`
- `POST /auth/signin`
- `POST /auth/signout`
- `GET /auth/me`
- `POST /auth/request-password-reset`
- `POST /auth/password-reset?token=...`
- `POST /auth/password-change`
- `POST /auth/request-email-verification`
- `GET /auth/email-verification?token=...`

## CSRF Responsibility

This example uses `fastapi-csrf-protect` to protect AuthLoom's unsafe built-in
routes through `unsafe_route_dependencies`. It also protects application-owned
HTML form posts and the example `POST /example-mutation` route.

AuthLoom does not generate or validate CSRF tokens. The clickable
`GET /auth/email-verification?token=...` route uses the verification token as
bearer authorization and does not require a CSRF token. CORS is separate
application configuration.

## Troubleshooting

- If migrations fail with a driver error, check that `DATABASE_URL` uses
  `sqlite+aiosqlite://` or `postgresql+asyncpg://`.
- If PostgreSQL connection fails, run `docker compose up -d postgres` and confirm
  port `5432` is available.
- If email links do not appear, run `docker compose up -d mailhog` and open
  `http://127.0.0.1:8025`.
- If forms fail CSRF validation, fetch a fresh `/csrf` token or clear stale
  cookies.
- If cookies are not sent over local HTTP, ensure `secure=False` in local cookie
  settings.
- If a reset or verification link fails, it may be expired or already used.
