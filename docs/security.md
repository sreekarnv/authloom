# Security

This document describes AuthLoom's current security model and the boundaries of the `v0.1` scope.

## What AuthLoom Provides

AuthLoom currently provides:

- Argon2 password hashing through `argon2-cffi`.
- Email normalization before signup and signin.
- Random session tokens generated with Python's `secrets` module.
- Raw session tokens sent to clients through cookies.
- SHA-256 hashes of session tokens stored in the database.
- Session expiry using the configured cookie/session lifetime.
- Session revocation during signout.
- `HttpOnly` cookie support.
- Generic invalid-credential responses for signin failures.

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
- CSRF protection beyond the configured cookie policy, if required by the application.
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
- Session cleanup jobs for expired or revoked sessions.

These features are outside the current `v0.1` scope.
