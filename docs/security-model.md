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
- `HttpOnly` cookie support.
- Generic invalid-credential responses for signin failures.

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
through `create_auth_router(..., unsafe_route_dependencies=...)`. Application-owned
mutation routes must attach the same consumer-owned protection separately. CORS
and trusted-origin configuration are separate from CSRF protection.

The `fastapi-csrf-protect` integration in the example applications is optional
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
- Database migrations and operational database security.
- Logging, monitoring, and incident response.
- Authorization rules for application resources.

## Current Non-Goals

AuthLoom does not currently provide:

- Rate limiting.
- Email verification.
- Password reset or password change flows.
- Multi-factor authentication.
- OAuth or social login.
- JWT access or refresh tokens.
- Roles or permissions.
- Organizations or multi-tenancy.
- AuthLoom provides stale-session cleanup but does not schedule it automatically.

These features are outside the current `v0.1` scope.
