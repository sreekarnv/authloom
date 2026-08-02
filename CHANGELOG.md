# Changelog

All notable changes to AuthLoom will be documented in this file.

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
