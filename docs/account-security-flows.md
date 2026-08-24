# Account Security Flows

AuthLoom provides the database state changes for account-security flows. Your
application owns email delivery, browser pages, CSRF protection, rate limiting,
and product-specific authorization rules.

## Built-In Routes vs Direct Service Calls

AuthLoom exposes both built-in FastAPI routes and direct service methods.

- Built-in request routes create tokens and invoke configured hooks.
- Direct service calls create tokens and return the raw token to your code. They
  do not invoke hooks.
- Hooks are synchronous. Your application constructs URLs and delivers messages.

Avoid logging or storing raw password-reset and email-verification tokens.

## Session Invalidation

Signout revokes the current session.

To revoke all active sessions for a user:

```python
revoked_count = await auth.revoke_all_sessions(user_id=user.id)
```

To revoke other active sessions while keeping one session active:

```python
revoked_count = await auth.revoke_all_sessions(
    user_id=user.id,
    except_session_id=current_session_id,
)
```

An active session is one with no `revoked_at` value and an `expires_at` value
later than the operation time. Revocation updates matching active session rows.
It does not rewrite sessions that are already expired or already revoked.

Expired and revoked sessions can be removed later with `delete_stale_sessions`.
AuthLoom does not schedule that cleanup.

## Password Reset

### Request A Reset

Direct service call:

```python
token_raw = await auth.request_password_reset(email=email)
```

The service returns `None` when the email is unknown.

The built-in route, `POST /auth/request-password-reset`, returns the same generic
response for known and unknown emails:

```text
password reset sent to your email
```

This avoids revealing whether an account exists.

### Deliver The Reset Link

Configure a hook if you want the built-in route to call your delivery function:

```python
from authloom import AuthLoomHooks

hooks = AuthLoomHooks(
    on_request_password_reset=send_password_reset_email,
)
```

The hook receives `(email, raw_token)` after AuthLoom has stored the token hash.
Your application builds the reset URL and sends it. If you configured a custom
router prefix with `create_auth_router(..., prefix="/accounts")`, use that same
prefix in the link.

### Complete A Reset

Built-in route:

```text
POST /auth/password-reset?token=<token_raw>
```

Direct service call:

```python
await auth.complete_password_reset(
    token_raw=token_raw,
    new_password=new_password,
)
```

Successful password reset atomically consumes the submitted token, invalidates
every other outstanding unused password-reset token for that user, updates the
password, and revokes all active sessions. If validation fails, password and
sessions are unchanged.

Validation can fail because the token is invalid, expired, or already used, or
because the new password does not satisfy the configured password policy.

## Password Change

Password change is for an already-authenticated user. It requires the current
password and applies the configured new-password policy.

Built-in route:

```text
POST /auth/password-change
```

Direct service call:

```python
updated_user = await auth.change_password(
    user_id=user.id,
    current_password=current_password,
    new_password=new_password,
    preserve_session_token_raw=current_session_token,
)
```

Successful authenticated password change verifies the current password, updates
the password, invalidates every outstanding unused reset token, and revokes the
user's other active sessions in the same transaction. The built-in route
preserves the authenticated session that performed the change.

If you call the service directly and do not pass `preserve_session_token_raw`, no
session is preserved.

Invalid current credentials raise `InvalidCredentialsException`. Password length
failures raise `PasswordPolicyException`.

## Email Verification

### Request Verification

Direct service call:

```python
token_raw = await auth.request_email_verification(email=user.email)
```

The built-in route, `POST /auth/request-email-verification`, creates a token and
invokes the configured hook when one is configured.

### Deliver The Verification Link

Configure a hook if you want the built-in route to call your delivery function:

```python
from authloom import AuthLoomHooks

hooks = AuthLoomHooks(
    on_request_email_verification=send_email_verification,
)
```

The built-in verification URL is:

```text
/auth/email-verification?token=<token_raw>
```

If you configured a custom router prefix, replace `/auth` with that prefix.

The credentials-auth example demonstrates local email delivery:

<https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth>

### Complete Verification

Built-in route:

```text
GET /auth/email-verification?token=<token_raw>
```

Direct service call:

```python
await auth.verify_email(token_raw=token_raw)
```

On success, AuthLoom consumes the submitted verification token and sets
`User.email_verified_at` in the same transaction. The submitted token is
single-use: invalid, expired, and previously used submitted tokens fail with a
generic error.

`User.email_verified_at` has these semantics:

- `None`: the email is not verified.
- A timestamp: the email was verified at that time.

## Browser Security Requirements

Protect every browser-facing state-changing route with consumer-owned CSRF
protection. This includes routes that set cookies, revoke sessions, create
tokens, consume password-reset tokens, update passwords, or mutate
application-owned data.

For AuthLoom's built-in unsafe routes, pass a dependency with
`unsafe_route_dependencies`:

```python
app.include_router(
    create_auth_router(
        auth,
        unsafe_route_dependencies=(csrf_dependency,),
    )
)
```

Attach equivalent protection separately to your application-owned HTML or JSON
mutation routes. Configure CORS and trusted origins separately.

Email verification completion is different:
`GET /auth/email-verification?token=...` is a clickable bearer-token link. Use
HTTPS, avoid logging full verification URLs, and do not require a browser CSRF
token for that route.
