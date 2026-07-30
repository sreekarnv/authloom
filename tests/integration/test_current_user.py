import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient


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
