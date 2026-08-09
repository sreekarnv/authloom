# Changelog

All notable changes to AuthLoom will be documented in this file.

## 0.1.0a4 — 2026-08-09

### Added

- Session invalidation with optional current-session preservation.
- Password-reset flow.
- Authenticated password changes.
- Email-verification token creation.
- Consumer hooks for password-reset and email-verification delivery.
- Updated examples/credentials_auth_postgres example with Jinja2 templates and MailHog.

### Security

- Single-use hashed password-reset and email-verification tokens.
- Atomic password-reset token consumption.
- Session invalidation support after password changes.

## 0.1.0a3 — 2026-08-04

### Added

- Added the generic `unsafe_route_dependencies` hook to
  `create_auth_router()` for consumer-owned dependencies on signup, signin, and
  signout.
- Added SQLite and PostgreSQL examples integrating
  `fastapi-csrf-protect` as an example-only dependency.
- Added documentation for consumer-owned CSRF protection and application-owned
  mutation routes.

### Security

- AuthLoom does not provide CSRF token cryptography, cookies, or an issuance
  endpoint. Consumers select and configure their own CSRF solution.
- `fastapi-csrf-protect` is used only by the examples and is not a core
  AuthLoom dependency.

## 0.1.0a2

### Added

- Added explicit cleanup for expired and revoked database sessions.
- Added regression tests for session expiry boundaries and revoked-token replay.

### Security

- Reduced sign-in account-enumeration risk by performing Argon2 verification
  for both unknown-email and wrong-password failures.

## 0.1.0a1 — 2026-07-30

Initial alpha release of AuthLoom.

### Included

- Email/password signup and signin for FastAPI applications
- Cookie-backed database sessions with expiry and signout revocation
- Required and optional current-user dependencies
- Argon2 password hashing, email normalization, and hashed session-token storage
- Async SQLAlchemy integration with Alembic migration guidance
- Basic credentials-authentication example and test coverage

### Release status

AuthLoom is pre-release software. APIs, configuration, and database integration details may change before the first stable release.
