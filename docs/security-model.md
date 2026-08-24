# Security Model

This document describes AuthLoom's current security model and application
responsibility boundaries.

## What AuthLoom Provides

AuthLoom currently provides:

- Argon2 password hashing through `argon2-cffi`.
- Dummy Argon2 verification for unknown signin emails, so missing accounts still
  perform password verification work before returning invalid credentials.
- Email normalization before signup and signin.
- Random session tokens generated with Python's `secrets` module.
- Raw session tokens sent to clients through cookies.
- SHA-256 hashes of session tokens stored in the database.
- Session expiry using the configured cookie/session lifetime.
- Session revocation during signout.
- Explicit invalidation of active sessions, optionally preserving one current
  session.
- Password-reset token creation and single-use password reset.
- Authenticated password change with current-password verification.
- Email-verification token creation and submitted-token single-use completion
  that sets `User.email_verified_at`.
- `HttpOnly` cookie support.
- Generic invalid-credential responses for signin failures.

## Password Reset, Password Change, And Email Verification

Password-reset and email-verification tokens are generated from
cryptographically secure random values. AuthLoom exposes the raw value only to
the caller or configured consumer hook and stores only a hash in the database.

Successful password reset atomically consumes the submitted token, invalidates
every other outstanding unused password-reset token for that user, updates the
password, and revokes all active sessions. If validation fails, password and
sessions are unchanged.

Successful authenticated password change verifies the current password, updates
the password, invalidates every outstanding unused reset token, and revokes the
user's other active sessions in the same transaction. The built-in route
preserves the authenticated session that performed the change.

Successful email verification consumes the submitted verification token and sets
`User.email_verified_at` in the same transaction. Invalid, expired, and
previously used submitted tokens fail with a generic response.

Password-reset requests for unknown emails return the same generic response as
known emails. This avoids disclosing whether an account exists through the
request endpoint.

For route behavior, hooks, and operational details, see
[Account Security Flows](account-security-flows.md).

## CSRF Responsibility Boundary

AuthLoom authenticates browser requests with automatically submitted cookies.
Applications using browser-facing state-changing routes must configure their own
CSRF protection. `SameSite` is useful defense in depth, but it is not a complete
CSRF strategy for every browser flow.

AuthLoom does not define a CSRF token format, generate CSRF tokens, create a CSRF
cookie, or provide a CSRF issuance endpoint. The consuming application selects
and configures its CSRF solution.

Attach the consumer CSRF dependency to AuthLoom's built-in unsafe routes with
`create_auth_router(..., unsafe_route_dependencies=...)`, and protect
application-owned mutation routes separately. Do not require a browser CSRF token
for the clickable `GET /auth/email-verification?token=...` bearer-token link.

For setup guidance, see [Consumer Integration](consumer-integration.md#mandatory-csrf-for-browser-or-deployment-use).

## Sign-In Failures

Unknown email and wrong password attempts return the same invalid-credentials
response. AuthLoom performs Argon2 verification in both cases, using a dummy hash
for unknown users, to reduce account-enumeration timing differences.

This mitigation does not replace rate limiting or brute-force protection.

## Cookie Security

AuthLoom's default cookie settings are suitable for local development, not for
production.

For production deployments:

- Use HTTPS.
- Set `secure=True` so browsers only send the session cookie over HTTPS.
- Keep `http_only=True` unless there is a specific reason to disable it.
- Choose `samesite` based on the application's browser flow.
- Use `samesite="none"` only when cross-site cookies are required; AuthLoom
  requires `secure=True` for this setting.

See [Configuration](configuration.md#production-cookie-settings) for examples.

## Application Responsibilities

The consuming application remains responsible for deployment and product-specific
security controls, including:

- HTTPS and reverse proxy configuration.
- Rate limiting and brute-force protection.
- CSRF token issuance and validation.
- Email delivery, including provider configuration, retries, and bounce handling.
- Database migrations and operational database security.
- Logging, monitoring, and incident response.
- Authorization rules for application resources.

## Current Non-Goals

AuthLoom does not currently provide:

- Rate limiting.
- Multi-factor authentication.
- OAuth or social login.
- JWT access or refresh tokens.
- Roles or permissions.
- Organizations or multi-tenancy.
- Automatic scheduling of stale-session cleanup.
