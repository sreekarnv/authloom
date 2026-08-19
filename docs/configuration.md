# Configuration

AuthLoom configuration is passed through `AuthLoomConfig`.

## AuthLoomConfig

| Option | Description |
| --- | --- |
| `session_factory` | Required async SQLAlchemy session factory. |
| `cookie_session` | Cookie/session settings. |
| `password_config` | Password length policy. |
| `hooks` | Consumer callbacks for password-reset and email-verification tokens. |

## Cookie Settings

| Option | Default | Validation |
| --- | --- | --- |
| `cookie_name` | `"authloom.auth"` | Must not be empty. |
| `ttl` | `604800` | Must be greater than `0`. |
| `http_only` | `True` | Boolean. |
| `secure` | `False` | Boolean. Use `True` in production over HTTPS. |
| `samesite` | `"lax"` | One of `"lax"`, `"strict"`, or `"none"`. `"none"` requires `secure=True`. |
| `domain` | `None` | Optional cookie domain. |
| `path` | `"/"` | Must not be empty and must start with `/`. |

## Password Settings

| Option | Default | Validation |
| --- | --- | --- |
| `min_length` | `15` | Cannot be less than `15` and cannot exceed `max_length`. |
| `max_length` | `64` | Cannot be less than `64` or greater than `128`. |

## Security Flow Hooks

Hooks receive the destination email address and the raw, one-time token after
AuthLoom has persisted its hash. AuthLoom does not send email; consumers use
these hooks only to deliver password-reset and email-verification links.

```python
from authloom import AuthLoom
from authloom.settings import AuthLoomConfig, AuthLoomHooks

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

The callback type is synchronous:

```python
Callable[[str, str], None]
```

Consumers are responsible for constructing links, sending messages, and
preventing raw tokens from appearing in logs or persistent application data.
AuthLoom owns token consumption for its built-in password-reset and
email-verification completion routes.
