import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig
from authloom.db.schema import ResetPasswordToken
from authloom.exceptions import PasswordPolicyCode


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


async def _change_password(
    client: AsyncClient,
    current_password: str,
    new_password: str,
):
    return await client.post(
        "/auth/password-change",
        json={
            "current_password": current_password,
            "new_password": new_password,
            "new_password_confirm": new_password,
        },
    )


@pytest.mark.asyncio
async def test_password_change_with_valid_current_password_changes_password(
    app: FastAPI,
):
    transport = ASGITransport(app=app)
    email = "test_password_change_with_valid_current_password@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "#NEWSUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        current_token = signup_response.cookies["authloom.auth"]
        signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        other_token = signin_response.cookies["authloom.auth"]

        client.cookies.set("authloom.auth", current_token)
        change_response = await _change_password(client, old_value, new_value)
        current_session_response = await client.get("/auth/me")

        client.cookies.set("authloom.auth", other_token)
        other_session_response = await client.get("/auth/me")

        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        new_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": new_value}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_200_OK
    assert change_response.status_code == status.HTTP_200_OK
    assert current_session_response.status_code == status.HTTP_200_OK
    assert other_session_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert old_signin_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_signin_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_password_change_invalidates_unused_reset_tokens(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    transport = ASGITransport(app=app)
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_password_change_invalidates_unused_reset_tokens@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    changed_value = "#CHANGEDSUPERSECRETPASSWORD#"
    stale_value = "#STALESUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        stale_token_raw = await auth.request_password_reset(email=email)

        change_response = await _change_password(client, old_value, changed_value)
        stale_reset_response = await client.post(
            f"/auth/password-reset?token={stale_token_raw}",
            json={"password": stale_value, "password_confirm": stale_value},
        )
        changed_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": changed_value}
        )
        stale_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": stale_value}
        )

    async with session_maker() as session:
        result = await session.execute(select(ResetPasswordToken))
        reset_token = result.scalar_one()

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert change_response.status_code == status.HTTP_200_OK
    assert stale_reset_response.status_code == status.HTTP_400_BAD_REQUEST
    assert changed_signin_response.status_code == status.HTTP_200_OK
    assert stale_signin_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert reset_token.used_at is not None


@pytest.mark.asyncio
async def test_password_change_with_wrong_current_password_changes_nothing(
    app: FastAPI,
):
    transport = ASGITransport(app=app)
    email = "test_password_change_with_wrong_current_password@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "#NEWSUPERSECRETPASSWORD#"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        change_response = await _change_password(
            client, "#WRONGSUPERSECRETPASSWORD#", new_value
        )
        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        new_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": new_value}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert change_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert change_response.json()["detail"] == "invalid credentials"
    assert old_signin_response.status_code == status.HTTP_200_OK
    assert new_signin_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_password_change_password_policy_failure_changes_nothing(
    app: FastAPI,
):
    transport = ASGITransport(app=app)
    email = "test_password_change_password_policy_failure@example.com"
    old_value = "#SUPERSECRETPASSWORD#"
    new_value = "too-short"

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _signup(client, email, old_value)
        change_response = await _change_password(client, old_value, new_value)
        old_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": old_value}
        )
        new_signin_response = await client.post(
            "/auth/signin", json={"email": email, "password": new_value}
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert change_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert change_response.json()["detail"]["code"] == PasswordPolicyCode.TOO_SHORT
    assert old_signin_response.status_code == status.HTTP_200_OK
    assert new_signin_response.status_code == status.HTTP_401_UNAUTHORIZED
