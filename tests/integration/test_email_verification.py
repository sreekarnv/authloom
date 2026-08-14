from datetime import timedelta

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig
from authloom.db.schema import EmailVerificationToken, User
from authloom.db.utils.time import utc_now


def _session_maker(async_engine: AsyncEngine):
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def _signup(client: AsyncClient, email: str):
    credential = "#SUPERSECRETPASSWORD#"
    return await client.post(
        "/auth/signup",
        json={
            "name": "Test User",
            "email": email,
            "password": credential,
            "password_confirm": credential,
        },
    )


@pytest.mark.asyncio
async def test_email_verification_with_valid_token_marks_user_verified_and_token_used(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_email_verification_with_valid_token@example.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email)
        token_raw = await auth.request_email_verification(email=email)
        verification_response = await client.get(
            f"/auth/email-verification?token={token_raw}"
        )

    async with session_maker() as session:
        token_result = await session.execute(select(EmailVerificationToken))
        verification_token = token_result.scalar_one()
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert token_raw is not None
    assert verification_response.status_code == status.HTTP_200_OK
    assert verification_token.used_at is not None
    assert user.email_verified_at is not None


@pytest.mark.asyncio
async def test_email_verification_rejects_used_token(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_email_verification_rejects_used_token@example.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email)
        token_raw = await auth.request_email_verification(email=email)
        first_response = await client.get(f"/auth/email-verification?token={token_raw}")
        second_response = await client.get(
            f"/auth/email-verification?token={token_raw}"
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_email_verification_rejects_unknown_token_without_modifying_user(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    email = "test_email_verification_rejects_unknown_token@example.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email)
        verification_response = await client.get(
            "/auth/email-verification?token=unknown-token"
        )

    async with session_maker() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert verification_response.status_code == status.HTTP_400_BAD_REQUEST
    assert user.email_verified_at is None


@pytest.mark.asyncio
async def test_email_verification_rejects_expired_token_without_modifying_user(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_email_verification_rejects_expired_token@example.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email)
        token_raw = await auth.request_email_verification(email=email)

    async with session_maker() as session:
        token_result = await session.execute(select(EmailVerificationToken))
        verification_token = token_result.scalar_one()
        verification_token.expires_at = utc_now() - timedelta(microseconds=1)
        await session.commit()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        verification_response = await client.get(
            f"/auth/email-verification?token={token_raw}"
        )

    async with session_maker() as session:
        token_result = await session.execute(select(EmailVerificationToken))
        verification_token = token_result.scalar_one()
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert verification_response.status_code == status.HTTP_400_BAD_REQUEST
    assert verification_token.used_at is None
    assert user.email_verified_at is None
