import unicodedata

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig
from authloom.dtos import SigninSrvInputDto, SignupSrvInputDto
from authloom.exceptions import PasswordPolicyCode, PasswordPolicyException


def _session_maker(async_engine: AsyncEngine):
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def _nfc(password: str) -> str:
    return unicodedata.normalize("NFC", password)


async def _http_signup(client: AsyncClient, email: str, password: str):
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
async def test_direct_signup_normalizes_password_for_http_signin(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_direct_signup_normalizes_password_for_http_signin@example.com"
    decomposed_credential = "Cafe\u0301Password123"
    composed_credential = _nfc(decomposed_credential)

    await auth.signup(
        SignupSrvInputDto(
            name="Test User",
            email=email,
            password=decomposed_credential,
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signin_response = await client.post(
            "/auth/signin",
            json={"email": email, "password": composed_credential},
        )

    assert signin_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_direct_signin_normalizes_password_to_match_http_signup(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_direct_signin_normalizes_password_to_match_http_signup@example.com"
    decomposed_credential = "Cafe\u0301Password123"
    composed_credential = _nfc(decomposed_credential)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _http_signup(client, email, composed_credential)

    user, session = await auth.signin(
        SigninSrvInputDto(email=email, password=decomposed_credential)
    )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert user.email == email
    assert session.token_raw


@pytest.mark.asyncio
async def test_direct_password_reset_normalizes_new_password_for_http_signin(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_direct_password_reset_normalizes_new_password@example.com"
    old_credential = "#OLDSUPERSECRETPASSWORD#"
    decomposed_new_credential = "ResetCafe\u0301Password123"
    composed_new_credential = _nfc(decomposed_new_credential)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _http_signup(client, email, old_credential)

    reset_token = await auth.request_password_reset(email=email)
    assert reset_token is not None

    await auth.complete_password_reset(reset_token, decomposed_new_credential)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signin_response = await client.post(
            "/auth/signin",
            json={"email": email, "password": composed_new_credential},
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_direct_password_change_normalizes_passwords_for_http_signin(
    app: FastAPI,
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    email = "test_direct_password_change_normalizes_passwords@example.com"
    decomposed_current_credential = "Cafe\u0301Password123"
    composed_current_credential = _nfc(decomposed_current_credential)
    decomposed_new_credential = "ChangedCafe\u0301Password123"
    composed_new_credential = _nfc(decomposed_new_credential)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await _http_signup(client, email, composed_current_credential)
        user_id = signup_response.json()["user"]["id"]

    await auth.change_password(
        user_id=user_id,
        current_password=decomposed_current_credential,
        new_password=decomposed_new_credential,
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signin_response = await client.post(
            "/auth/signin",
            json={"email": email, "password": composed_new_credential},
        )

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_direct_signup_enforces_max_length_after_normalization(
    async_engine: AsyncEngine,
):
    session_maker = _session_maker(async_engine)
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))
    normalized_over_max_credential = ("1" * 63) + "\u0344"

    assert len(normalized_over_max_credential) == 64
    assert len(_nfc(normalized_over_max_credential)) == 65

    with pytest.raises(PasswordPolicyException) as exc_info:
        await auth.signup(
            SignupSrvInputDto(
                name="Test User",
                email="test_direct_signup_enforces_max_length@example.com",
                password=normalized_over_max_credential,
            )
        )

    assert exc_info.value.code == PasswordPolicyCode.TOO_LONG
