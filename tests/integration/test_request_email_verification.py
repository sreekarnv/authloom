from datetime import timedelta

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig, AuthLoomHooks, create_auth_router
from authloom.db.schema import EmailVerificationToken
from authloom.db.utils.time import utc_now
from authloom.service import hash_email_verification_token


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
async def test_request_email_verification_persists_hashed_token(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_request_email_verification@example.com"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email)

    token_raw = await auth.request_email_verification(email=email)

    async with session_maker() as session:
        result = await session.execute(select(EmailVerificationToken))
        verification_token = result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert token_raw is not None
    assert verification_token.token_hash == hash_email_verification_token(token_raw)
    assert verification_token.token_hash != token_raw
    assert verification_token.user_id is not None
    assert verification_token.created_at is not None
    assert verification_token.expires_at > utc_now()
    assert verification_token.expires_at < utc_now() + timedelta(minutes=16)
    assert verification_token.used_at is None


@pytest.mark.asyncio
async def test_request_email_verification_unknown_email_returns_none(
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))

    token_raw = await auth.request_email_verification(email="unknown@example.com")

    async with session_maker() as session:
        result = await session.execute(select(EmailVerificationToken))

    assert token_raw is None
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_request_email_verification_exposes_raw_token_to_hook(
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    delivered: list[tuple[str, str]] = []

    def on_request_email_verification(email: str, token: str) -> None:
        delivered.append((email, token))

    auth = AuthLoom(
        config=AuthLoomConfig(
            session_factory=session_maker,
            hooks=AuthLoomHooks(
                on_request_email_verification=on_request_email_verification
            ),
        )
    )
    app = FastAPI()
    app.include_router(create_auth_router(auth))
    email = "test_email_verification_hook@example.com"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        signup_response = await _signup(client, email)
        request_response = await client.post(
            "/auth/request-email-verification", json={"email": email}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert request_response.status_code == status.HTTP_200_OK
    assert request_response.json() == {
        "message": "email verification sent to your email"
    }
    assert len(delivered) == 1
    assert delivered[0][0] == email

    async with session_maker() as session:
        result = await session.execute(select(EmailVerificationToken))
        verification_token = result.scalar_one()

    assert verification_token.token_hash == hash_email_verification_token(
        delivered[0][1]
    )
