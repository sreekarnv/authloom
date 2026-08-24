# Configuration

Only `session_factory` is required.

AuthLoom configuration is passed through `AuthLoomConfig`.

## Required Configuration

```python
from authloom import AuthLoom, AuthLoomConfig, create_auth_router

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
    )
)

app.include_router(create_auth_router(auth))
```

`session_factory` must be an async SQLAlchemy
`async_sessionmaker[AsyncSession]`.

## Optional Customization

| Option | Purpose |
| --- | --- |
| `cookie_session` | Session cookie name, lifetime, and browser cookie attributes. |
| `password_config` | Password length policy. |
| `hooks` | Synchronous callbacks for password-reset and email-verification delivery. |

## Local Cookie Example

This example keeps `secure=False` so cookies work over local HTTP.

```python
from authloom import AuthLoom, AuthLoomConfig, AuthLoomCookieSessionConfig, create_auth_router
from authloom.settings import AuthLoomHooks, AuthLoomPasswordConfig

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
        cookie_session=AuthLoomCookieSessionConfig(
            cookie_name="authloom.auth",
            ttl=60 * 60 * 24 * 7,
            http_only=True,
            secure=False,
            samesite="lax",
            path="/",
        ),
        password_config=AuthLoomPasswordConfig(
            min_length=15,
            max_length=64,
        ),
    )
)
```

## Production Cookie Settings

Use HTTPS and `secure=True` in production.

```python
from authloom import AuthLoomCookieSessionConfig

cookie_session = AuthLoomCookieSessionConfig(
    cookie_name="authloom.auth",
    ttl=60 * 60 * 24 * 7,
    http_only=True,
    secure=True,
    samesite="lax",
    path="/",
)
```

Use `samesite="none"` only when the browser must send cookies in a cross-site
context. AuthLoom requires `secure=True` with `samesite="none"`.

## Cookie Settings Reference

| Option | Default | Notes |
| --- | --- | --- |
| `cookie_name` | `"authloom.auth"` | Must not be empty. |
| `ttl` | `604800` | Lifetime in seconds. Must be greater than `0`. |
| `http_only` | `True` | Keep enabled unless your app has a specific reason not to. |
| `secure` | `False` | Use `True` for HTTPS production. |
| `samesite` | `"lax"` | One of `"lax"`, `"strict"`, or `"none"`. |
| `domain` | `None` | Leave unset for most single-host apps. |
| `path` | `"/"` | Must start with `/`. |

## Password Settings

| Option | Default | Validation |
| --- | --- | --- |
| `min_length` | `15` | Cannot be less than `15` and cannot exceed `max_length`. |
| `max_length` | `64` | Cannot be less than `64` or greater than `128`. |

## Security Flow Hooks

AuthLoom does not send email. Your application owns URL construction, message
delivery, retries, logging policy, and provider configuration.

Configure hooks when you use the built-in request routes and want AuthLoom to
call your delivery functions:

```python
from authloom import AuthLoom, AuthLoomConfig
from authloom.settings import AuthLoomHooks

auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
        hooks=AuthLoomHooks(
            on_request_password_reset=send_password_reset_email,
            on_request_email_verification=send_email_verification_email,
        ),
    )
)
```

Hooks are synchronous functions with this shape:

```python
Callable[[str, str], None]
```

They receive `(email, raw_token)` after AuthLoom has persisted the token hash.
Avoid logging or storing raw tokens.

Built-in request routes invoke configured hooks:

- `POST /auth/request-password-reset`
- `POST /auth/request-email-verification`

Direct service calls return tokens and do not invoke hooks:

```python
token = await auth.request_password_reset(email=email)
token = await auth.request_email_verification(email=email)
```

When you call services directly, your application must deliver any returned token
itself.
