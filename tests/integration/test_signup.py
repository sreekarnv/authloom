import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from authloom.exceptions import PasswordPolicyCode


@pytest.mark.asyncio
async def test_signup_rejects_with_same_email(app: FastAPI):
    transport = ASGITransport(app=app)
    body = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "#Test122345678842Test#",
        "password_confirm": "#Test122345678842Test#"
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_response = await client.post("/auth/signup", json=body)
        second_response = await client.post("/auth/signup", json=body)

    assert first_response.status_code == status.HTTP_201_CREATED
    assert "user" in first_response.json()
    assert second_response.status_code == status.HTTP_409_CONFLICT
    assert second_response.json()["detail"] == "user with this email already exists"

@pytest.mark.asyncio
async def test_signup_rejects_with_invalid_passwords(app: FastAPI):
    transport = ASGITransport(app=app)
    body = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "#Test12234567",
        "password_confirm": "#Test12234567"
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/auth/signup", json=body)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    data = response.json()
    assert "detail" in data and "message" in data["detail"]
    assert data["detail"]["code"] == PasswordPolicyCode.TOO_SHORT

@pytest.mark.asyncio
async def test_signup_accepts_creates_user_and_cookie(app: FastAPI):
    transport = ASGITransport(app=app)
    body = {
        "name": "Test User",
        "email": "test_signup_accepts_creates_user_and_cookie@example.com",
        "password": "#Test12234567890#",
        "password_confirm": "#Test12234567890#"
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/auth/signup", json=body)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.cookies.get("authloom.auth")

    data = response.json()
    assert "user" in data and "message" in data
