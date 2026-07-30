# Configuration

AuthLoom configuration is passed through `AuthLoomConfig`.

## AuthLoomConfig

| Option | Description |
| --- | --- |
| `session_factory` | Required async SQLAlchemy session factory. |
| `cookie_session` | Cookie/session settings. |
| `password_config` | Password length policy. |

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
