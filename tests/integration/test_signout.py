import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_signout_accepted_and_cookie_is_deleted(app: FastAPI):
    transport = ASGITransport(app=app)
    signup_body = {
        "name": "Test User",
        "email": "test_signout_accepted_and_cookie_is_deleted@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        signout_resp = await client.post("/auth/signout")
        current_user_resp = await client.get("/auth/me")

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert signout_resp.status_code == status.HTTP_204_NO_CONTENT
    assert "authloom.auth=\"\"" in signout_resp.headers["set-cookie"]
    assert "Path=/" in signout_resp.headers["set-cookie"]
    assert current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_signout_skipped_when_cookie_doesnt_exists(app: FastAPI):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signout_resp = await client.post("/auth/signout")

    assert signout_resp.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_signout_skipped_when_token_is_invalid(app: FastAPI):
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.cookies.set("authloom.auth", "invalid-token")
        signout_resp = await client.post("/auth/signout")
        current_user_resp = await client.get("/auth/me")

    assert signout_resp.status_code == status.HTTP_204_NO_CONTENT
    assert current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED
