from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom.db.schema import Session
from authloom.service import hash_session_token


@pytest.mark.asyncio
async def test_current_user_rejects_when_session_missing(app: FastAPI):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        current_user_resp = await client.get("/auth/me")

    assert current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED

    data = current_user_resp.json()
    assert "detail" in data and data["detail"] == "you are not logged in"


@pytest.mark.asyncio
async def test_current_user_accepts_when_session_is_valid(app: FastAPI):
    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_current_user_rejects_when_session_missing@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        current_user_resp = await client.get("/auth/me")

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert current_user_resp.status_code == status.HTTP_200_OK

    data = current_user_resp.json()
    assert data["email"] == signup_body["email"]


@pytest.mark.asyncio
async def test_current_user_rejects_when_session_token_is_invalid(app: FastAPI):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.cookies.set("authloom.auth", "invalid-session-token")
        current_user_resp = await client.get("/auth/me")

    assert current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED

    data = current_user_resp.json()
    assert data["detail"] == "you are not logged in"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("expires_delta", "expected_status"),
    [
        (timedelta(microseconds=-1), status.HTTP_401_UNAUTHORIZED),
        (timedelta(0), status.HTTP_401_UNAUTHORIZED),
        (timedelta(microseconds=1), status.HTTP_200_OK),
    ],
)
async def test_current_user_checks_session_expiry_boundary(
    app: FastAPI,
    async_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
    expires_delta: timedelta,
    expected_status: int,
):
    import authloom.service

    fixed_now = datetime(2026, 1, 1, tzinfo=UTC)
    transport = ASGITransport(app=app)
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    signup_body = {
        "name": "Test User",
        "email": (
            "test_current_user_checks_session_expiry_boundary_"
            f"{expected_status}_{expires_delta.total_seconds()}@example.com"
        ),
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        token_raw = signup_resp.cookies["authloom.auth"]

        async with session_maker() as session:
            result = await session.execute(
                select(Session).where(
                    Session.token_hash == hash_session_token(token_raw)
                )
            )
            auth_session = result.scalar_one()
            auth_session.expires_at = fixed_now + expires_delta
            await session.commit()

        monkeypatch.setattr(authloom.service, "utc_now", lambda: fixed_now)
        current_user_resp = await client.get("/auth/me")

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert current_user_resp.status_code == expected_status


@pytest.mark.asyncio
async def test_current_user_rejects_revoked_session_token_replay(
    app: FastAPI,
):
    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_current_user_rejects_revoked_session_token_replay@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        token_raw = signup_resp.cookies["authloom.auth"]

        signout_resp = await client.post("/auth/signout")
        client.cookies.set("authloom.auth", token_raw)
        current_user_resp = await client.get("/auth/me")

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert signout_resp.status_code == status.HTTP_204_NO_CONTENT
    assert current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED
