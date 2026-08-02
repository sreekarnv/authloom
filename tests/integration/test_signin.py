import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_signin_rejects_with_wrong_email(app: FastAPI):
    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_signin_rejects_with_wrong_email@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }
    signin_body = {
        "email": "wrong_email@example.com",
        "password": signup_body["password"],
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await client.post("/auth/signup", json=signup_body)
        signin_response = await client.post("/auth/signin", json=signin_body)

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_401_UNAUTHORIZED

    data = signin_response.json()
    assert "detail" in data and data["detail"] == "invalid credentials"


@pytest.mark.asyncio
async def test_signin_rejects_with_wrong_password(app: FastAPI):
    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_signin_rejects_with_wrong_password@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }
    signin_body = {"email": signup_body["email"], "password": "#WRONGPASSWORD#"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await client.post("/auth/signup", json=signup_body)
        signin_response = await client.post("/auth/signin", json=signin_body)

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_401_UNAUTHORIZED

    data = signin_response.json()
    assert "detail" in data and data["detail"] == "invalid credentials"


@pytest.mark.asyncio
async def test_signin_verifies_password_for_unknown_email(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    verify_calls = []

    def verify_spy(self, hash: str, password: str):
        verify_calls.append((hash, password))
        raise VerifyMismatchError("password does not match")

    monkeypatch.setattr(PasswordHasher, "verify", verify_spy)

    transport = ASGITransport(app=app)
    signin_body = {
        "email": "test_signin_verifies_unknown_email@example.com",
        "password": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signin_response = await client.post("/auth/signin", json=signin_body)

    assert signin_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert len(verify_calls) == 1
    assert verify_calls[0][1] == signin_body["password"]
    assert verify_calls[0][0].startswith("$argon2")


@pytest.mark.asyncio
async def test_signin_verifies_password_for_known_email(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
):
    verify_calls = []

    def verify_spy(self, hash: str, password: str):
        verify_calls.append((hash, password))
        raise VerifyMismatchError("password does not match")

    monkeypatch.setattr(PasswordHasher, "verify", verify_spy)

    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_signin_verifies_known_email@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }
    signin_body = {"email": signup_body["email"], "password": "#WRONGPASSWORD#"}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await client.post("/auth/signup", json=signup_body)
        signin_response = await client.post("/auth/signin", json=signin_body)

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert len(verify_calls) == 1
    assert verify_calls[0][1] == signin_body["password"]
    assert verify_calls[0][0].startswith("$argon2")


@pytest.mark.asyncio
async def test_signin_accepts_and_sets_cookie(app: FastAPI):
    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_signin_accepts_and_sets_cookie@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }
    signin_body = {"email": signup_body["email"], "password": signup_body["password"]}

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_response = await client.post("/auth/signup", json=signup_body)
        signin_response = await client.post("/auth/signin", json=signin_body)

    assert signup_response.status_code == status.HTTP_201_CREATED
    assert signin_response.status_code == status.HTTP_200_OK
    assert signin_response.cookies.get("authloom.auth")

    data = signin_response.json()

    assert "user" in data and "message" in data
