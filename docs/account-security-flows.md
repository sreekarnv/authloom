# Account Security Flows

AuthLoom provides the persistence and service operations for account-security
flows. The consuming application owns email delivery, browser presentation,
CSRF protection, rate limiting, and any product-specific authorization rules.

## Session Invalidation

Signout revokes the current session. To invalidate all active sessions for a
user, call `revoke_all_sessions`:

```python
revoked_count = await auth.revoke_all_sessions(user_id=user.id)
```

When a current session should remain active, pass its session ID:

```python
revoked_count = await auth.revoke_all_sessions(
    user_id=user.id,
    except_session_id=current_session_id,
)
```

Expired and revoked sessions can be removed separately with
`delete_stale_sessions`. AuthLoom does not schedule that cleanup.

## Password Reset

### Request A Reset

Call `request_password_reset` with the submitted email address:

```python
token_raw = await auth.request_password_reset(email=email)
```

The method returns `None` when the email is unknown. The built-in route still
returns the same generic success message, so consumers should not reveal
whether an account exists.

### Consumer Hook

AuthLoom does not send email. Configure a consumer-owned hook to receive the
email address and raw token exactly once:

```python
from authloom.settings import AuthLoomHooks

hooks = AuthLoomHooks(
    on_request_password_reset=send_password_reset_email,
)
```

The consumer should construct the reset URL, deliver the message through its
email provider, and avoid logging or storing the raw token.

### Complete A Reset

The built-in reset route consumes a token and updates the password. Consumers
calling the service directly can use:

```python
await auth.verify_token_reset_password(
    token_raw=token_raw,
    new_password=new_password,
)
```

The operation validates the password policy, rejects invalid, expired, and
already-used tokens, marks a valid token with `used_at`, and updates the
password in the same transaction.

Password reset does not currently revoke existing sessions automatically. A
consumer that requires that policy should call `revoke_all_sessions` after a
successful reset.

## Password Change

Password change requires the current password and applies the configured new
password policy:

```python
updated_user = await auth.change_password(
    user_id=user.id,
    current_password=current_password,
    new_password=new_password,
    preserve_session_token_raw=current_session_token,
)
```

On success, AuthLoom verifies the current password, hashes the new password,
preserves the supplied current session, and revokes the user's other active
sessions. If no current session token is supplied, all active sessions are
revoked.

Invalid current credentials raise `InvalidCredentialsException`. Password
length failures raise `PasswordPolicyException`.

## Email Verification

### Request Verification

Request a verification token with:

```python
token_raw = await auth.request_email_verification(email=user.email)
```

AuthLoom stores the token hash and returns the raw token to the caller. It does
not send email.

### Consumer Hook

Configure the consumer-owned delivery hook:

```python
hooks = AuthLoomHooks(
    on_request_email_verification=send_email_verification,
)
```

The hook receives `(email, raw_token)`. The consumer constructs the verification
URL and sends it through its email provider. The built-in verification URL is:

```text
/auth/email-verification?token=<token_raw>
```

The credentials auth example uses MailHog for local delivery.

### Complete Verification

The built-in route consumes a token and marks the email verified. Consumers
calling the service directly can use:

```python
await auth.verify_email(token_raw=token_raw)
```

On success, AuthLoom:

1. Hashes the submitted raw token.
2. Atomically claims an unused, unexpired token.
3. Sets `used_at` and `User.email_verified_at` in one transaction.
4. Rejects invalid, expired, and previously used tokens with a generic failure.

`User.email_verified_at` has these semantics:

- `None`: the email is not verified.
- A timestamp: the email was verified at that time.

## Example Application

The credentials auth example demonstrates these flows with plain Jinja2
templates, consumer-owned CSRF protection, and MailHog:

[Credentials auth example](https://github.com/sreekarnv/authloom/tree/main/examples/credentials_auth)

Start MailHog for local email delivery with:

```bash
docker compose up -d mailhog
```

If you are running the example with PostgreSQL, start both dependencies with:

```bash
docker compose up -d postgres mailhog
```

MailHog's inbox is available at `http://127.0.0.1:8025`. Email delivery is
consumer-owned; MailHog is only a local development SMTP service used by the
example.

## Browser Security Requirements

All cookie-authenticated browser mutations require CSRF protection, including
signup, signin, signout, password reset, password change, and verification
request routes. AuthLoom does not provide CSRF token generation or validation.

Email verification completion is different: `/auth/email-verification?token=...`
is a clickable bearer-token link. It should be HTTPS-only and should not require
a browser CSRF token. Avoid logging full verification URLs because query tokens
can appear in access logs, browser history, referrers, or analytics tools.

Attach the consumer's CSRF dependency to AuthLoom's unsafe built-in routes with
`unsafe_route_dependencies`, and attach it separately to application-owned HTML
mutation routes. Configure CORS and trusted origins separately.
