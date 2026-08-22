# Security

This document describes AuthLoom's current security model and the boundaries of the `v0.1` scope.

## What AuthLoom Provides

AuthLoom currently provides:

- Argon2 password hashing through `argon2-cffi`.
- Dummy Argon2 verification for unknown signin emails, so missing accounts
  still perform password verification work before returning invalid credentials.
- Email normalization before signup and signin.
- Random session tokens generated with Python's `secrets` module.
- Raw session tokens sent to clients through cookies.
- SHA-256 hashes of session tokens stored in the database.
- Session expiry using the configured cookie/session lifetime.
- Session revocation during signout.
- Explicit invalidation of all active sessions, optionally preserving one
  current session.
- Password-reset token creation, single-use password reset, and automatic
  revocation of every active session for the affected user after a successful
  reset.
- Password-change current-password verification and session invalidation.
- Email-verification token creation and single-use completion that sets
  `User.email_verified_at`.
- `HttpOnly` cookie support.
- Generic invalid-credential responses for signin failures.

## Password Reset And Email Verification Tokens

Password-reset and email-verification tokens are generated from cryptographically
secure random values. AuthLoom exposes the raw value only to the caller or
configured consumer hook and stores only a SHA-256 hash in the database.

Both token types include creation and expiry timestamps and a nullable
`used_at`. A token must be unused and unexpired to be accepted. A successful
password reset atomically claims the token, updates the password, and revokes
every active session for the affected user in the same transaction. Failed
password reset attempts do not revoke sessions. A successful email verification
marks its token used in the same transaction as the `User.email_verified_at`
update.

Verification links use the raw token as bearer authorization, for example
`/auth/email-verification?token=<token_raw>`. Keep these links HTTPS-only and
avoid logging them. AuthLoom stores only token hashes, uses short expirations,
and rejects invalid, expired, or already-used tokens with a generic failure.

Password-reset requests for unknown emails return the same generic response as
known emails. This avoids disclosing whether an account exists through the
request endpoint.

## CSRF Responsibility Boundary

AuthLoom authenticates browser requests with automatically submitted cookies.
Applications using cookie authentication must therefore configure CSRF protection
for unsafe requests. `SameSite` is useful defense in depth, but it may not be a
complete CSRF defence for every browser flow.

AuthLoom does not provide or globally enforce a CSRF mechanism. It does not define
a token format, generate CSRF tokens, create a CSRF cookie, or provide a CSRF
issuance endpoint. The consuming application selects and configures its CSRF
solution, including token issuance, validation, cookie and header settings, and
frontend handling. `fastapi-csrf-protect` is one possible integration, not a
required dependency or an AuthLoom security guarantee.

Consumers can attach their CSRF dependency to AuthLoom's built-in unsafe routes
through `create_auth_router(..., unsafe_route_dependencies=...)`. This includes
signup, signin, signout, password reset, password change, and token-request
routes. The email-verification completion route is a clickable bearer-token link
and should not require a browser CSRF token. Application-owned mutation routes
must attach the same consumer-owned protection separately. CORS and
trusted-origin configuration are separate from CSRF protection.

The `fastapi-csrf-protect` integration in the example application is optional
example code and is not a dependency of the AuthLoom package.

## Sign-In Failures

Unknown email and wrong password attempts return the same invalid-credentials
response. AuthLoom performs Argon2 verification in both cases, using a dummy
hash for unknown users, to reduce account-enumeration timing differences.

This mitigation does not replace rate limiting or brute-force protection.

## Cookie Security

AuthLoom's default cookie settings are suitable for local development, not for production.

For production deployments:

- Use HTTPS.
- Set `secure=True` so browsers only send the session cookie over HTTPS.
- Keep `http_only=True` unless there is a specific reason to disable it.
- Choose `samesite` based on the application's browser flow.
- Use `samesite="strict"` when the application can tolerate stricter same-site behavior.
- Use `samesite="lax"` for the default browser-friendly same-site behavior.
- Use `samesite="none"` only when cross-site cookies are required; AuthLoom requires `secure=True` for this setting.

## Application Responsibilities

The consuming application remains responsible for deployment and product-specific security controls, including:

- HTTPS and reverse proxy configuration.
- Rate limiting and brute-force protection.
- CSRF token issuance and validation.
- CSRF protection beyond the configured cookie policy.
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
- AuthLoom provides stale-session cleanup but does not schedule it automatically.

These features are outside the current `v0.1` scope.
