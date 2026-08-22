from datetime import timedelta

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig
from authloom.db.schema import ResetPasswordToken, Session
from authloom.db.utils.time import utc_now
from authloom.exceptions import PasswordPolicyCode
from authloom.service import hash_password_reset_token, hash_session_token


def _session_maker(async_engine: AsyncEngine):
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def _signup(client: AsyncClient, email: str, password: str):
    return await client.post(
        "/auth/signup",
        json={
            "name": "Test User",
            "email": email,
            "password": password,
            "password_confirm": password,
        },
    )


@pytest.mark.asyncio
async def test_request_password_reset_persists_hashed_token(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_request_password_reset_persists_hashed_token@example.com"
    credential_value = "#SUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, credential_value)

    token_raw = await auth.request_password_reset(email=email)

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))
        reset_token = result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert token_raw is not None
    assert reset_token.token == hash_password_reset_token(token_raw)
    assert reset_token.token != token_raw
    assert reset_token.user_id is not None
    assert reset_token.expires_at > utc_now()
    assert reset_token.used_at is None


@pytest.mark.asyncio
async def test_request_password_reset_unknown_email_returns_none(
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))

    token_raw = await auth.request_password_reset(email="unknown@example.com")

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))

    assert token_raw is None
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_password_reset_with_valid_token_updates_password_and_revokes_sessions(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_password_reset_with_valid_token@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "#NEWSUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        current_token = signup_response.cookies["authloom.auth"]
        signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        other_token = signin_response.cookies["authloom.auth"]
        token_raw = await auth.request_password_reset(email=email)
        reset_response = await client.post(
            f"/auth/password-reset?token={token_raw}",
            json={"password": new_value, "password_confirm": new_value},
        )
        client.cookies.set("authloom.auth", current_token)
        current_session_response = await client.get("/auth/me")
        client.cookies.set("authloom.auth", other_token)
        other_session_response = await client.get("/auth/me")
        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        new_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": new_value}
        )

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))
        reset_token = result.scalar_one()
        result = await session.execute(
            select(Session).where(
                Session.token_hash.in_(
                    [hash_session_token(current_token), hash_session_token(other_token)]
                )
            )
        )
        sessions = result.scalars().all()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_200_OK
    assert reset_response.status_code == status.HTTP_200_OK
    assert current_session_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert other_session_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert old_signin_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_signin_response.status_code == status.HTTP_200_OK
    assert reset_token.used_at is not None
    assert len(sessions) == 2
    assert all(session.revoked_at is not None for session in sessions)


@pytest.mark.asyncio
async def test_password_reset_rejects_invalid_token(
    app: FastAPI,
):
    transport = ASGITransport(app=app)
    email = "test_password_reset_rejects_invalid_token@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "#NEWSUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        current_token = signup_response.cookies["authloom.auth"]
        reset_response = await client.post(
            "/auth/password-reset?token=invalid-token",
            json={"password": new_value, "password_confirm": new_value},
        )
        client.cookies.set("authloom.auth", current_token)
        current_session_response = await client.get("/auth/me")
        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        new_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": new_value}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert reset_response.status_code == status.HTTP_400_BAD_REQUEST
    assert current_session_response.status_code == status.HTTP_200_OK
    assert old_signin_response.status_code == status.HTTP_200_OK
    assert new_signin_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_password_reset_rejects_expired_token(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_password_reset_rejects_expired_token@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "#NEWSUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        current_token = signup_response.cookies["authloom.auth"]
        token_raw = await auth.request_password_reset(email=email)

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))
        reset_token = result.scalar_one()
        reset_token.expires_at = utc_now() - timedelta(microseconds=1)
        await session.commit()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.cookies.set("authloom.auth", current_token)
        reset_response = await client.post(
            f"/auth/password-reset?token={token_raw}",
            json={"password": new_value, "password_confirm": new_value},
        )
        current_session_response = await client.get("/auth/me")
        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert reset_response.status_code == status.HTTP_400_BAD_REQUEST
    assert current_session_response.status_code == status.HTTP_200_OK
    assert old_signin_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_password_reset_rejects_used_token(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_password_reset_rejects_used_token@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "#NEWSUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        current_token = signup_response.cookies["authloom.auth"]
        token_raw = await auth.request_password_reset(email=email)

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))
        reset_token = result.scalar_one()
        reset_token.used_at = utc_now()
        await session.commit()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.cookies.set("authloom.auth", current_token)
        reset_response = await client.post(
            f"/auth/password-reset?token={token_raw}",
            json={"password": new_value, "password_confirm": new_value},
        )
        current_session_response = await client.get("/auth/me")
        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert reset_response.status_code == status.HTTP_400_BAD_REQUEST
    assert current_session_response.status_code == status.HTTP_200_OK
    assert old_signin_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_password_reset_enforces_password_policy(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_password_reset_enforces_password_policy@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "too-short"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        token_raw = await auth.request_password_reset(email=email)
        reset_response = await client.post(
            f"/auth/password-reset?token={token_raw}",
            json={"password": new_value, "password_confirm": new_value},
        )

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))
        reset_token = result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert reset_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert reset_response.json()["detail"]["code"] == PasswordPolicyCode.TOO_SHORT
    assert reset_token.used_at is None
