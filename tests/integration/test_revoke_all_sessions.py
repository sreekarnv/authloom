from datetime import timedelta

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig
from authloom.db.schema import Session
from authloom.db.utils.time import utc_now
from authloom.service import hash_session_token


@pytest.mark.asyncio
async def test_revoke_all_sessions_revokes_all_active_sessions(
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
    signup_body = {
        "name": "Test User",
        "email": "test_revoke_all_sessions_revokes_all_active_sessions@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        first_token_raw = signup_resp.cookies["authloom.auth"]
        signin_resp = await client.post(
            "/auth/signin",
            json={"email": signup_body["email"], "password": signup_body["password"]},
        )
        second_token_raw = signin_resp.cookies["authloom.auth"]

        async with session_maker() as session:
            result = await session.execute(
                select(Session).where(
                    Session.token_hash.in_(
                        [
                            hash_session_token(first_token_raw),
                            hash_session_token(second_token_raw),
                        ]
                    )
                )
            )
            sessions = result.scalars().all()

        revoked_count = await auth.revoke_all_sessions(user_id=sessions[0].user_id)

        async with session_maker() as session:
            result = await session.execute(
                select(Session).where(Session.id.in_([s.id for s in sessions]))
            )
            revoked_sessions = result.scalars().all()

        client.cookies.set("authloom.auth", first_token_raw)
        current_user_resp = await client.get("/auth/me")

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert signin_resp.status_code == status.HTTP_200_OK
    assert revoked_count == 2
    assert len(revoked_sessions) == 2
    assert all(session.revoked_at is not None for session in revoked_sessions)
    assert current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_revoke_all_sessions_preserves_except_session(
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
    signup_body = {
        "name": "Test User",
        "email": "test_revoke_all_sessions_preserves_except_session@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        first_token_raw = signup_resp.cookies["authloom.auth"]
        signin_resp = await client.post(
            "/auth/signin",
            json={"email": signup_body["email"], "password": signup_body["password"]},
        )
        second_token_raw = signin_resp.cookies["authloom.auth"]

        async with session_maker() as session:
            result = await session.execute(
                select(Session).where(
                    Session.token_hash.in_(
                        [
                            hash_session_token(first_token_raw),
                            hash_session_token(second_token_raw),
                        ]
                    )
                )
            )
            sessions_by_hash = {s.token_hash: s for s in result.scalars()}
            first_session = sessions_by_hash[hash_session_token(first_token_raw)]
            second_session = sessions_by_hash[hash_session_token(second_token_raw)]

        revoked_count = await auth.revoke_all_sessions(
            user_id=second_session.user_id,
            except_session_id=second_session.id,
        )

        async with session_maker() as session:
            first_result = await session.execute(
                select(Session).where(Session.id == first_session.id)
            )
            second_result = await session.execute(
                select(Session).where(Session.id == second_session.id)
            )
            first_session = first_result.scalar_one()
            second_session = second_result.scalar_one()

        client.cookies.set("authloom.auth", first_token_raw)
        first_current_user_resp = await client.get("/auth/me")
        client.cookies.set("authloom.auth", second_token_raw)
        second_current_user_resp = await client.get("/auth/me")

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert signin_resp.status_code == status.HTTP_200_OK
    assert revoked_count == 1
    assert first_session.revoked_at is not None
    assert second_session.revoked_at is None
    assert first_current_user_resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert second_current_user_resp.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_revoke_all_sessions_ignores_non_active_sessions(
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
    now = utc_now()
    already_revoked_at = now - timedelta(minutes=5)
    signup_body = {
        "name": "Test User",
        "email": "test_revoke_all_sessions_ignores_non_active_sessions@example.com",
        "password": "#SUPERSECRETPASSWORD#",
        "password_confirm": "#SUPERSECRETPASSWORD#",
    }

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        signup_resp = await client.post("/auth/signup", json=signup_body)
        active_token_raw = signup_resp.cookies["authloom.auth"]

    async with session_maker() as session:
        result = await session.execute(
            select(Session).where(
                Session.token_hash == hash_session_token(active_token_raw)
            )
        )
        active_session = result.scalar_one()
        already_revoked_session = Session(
            token_hash="1" * 64,
            user_id=active_session.user_id,
            expires_at=now + timedelta(days=1),
            revoked_at=already_revoked_at,
        )
        expired_session = Session(
            token_hash="2" * 64,
            user_id=active_session.user_id,
            expires_at=now - timedelta(microseconds=1),
        )
        session.add_all([already_revoked_session, expired_session])
        await session.commit()

    revoked_count = await auth.revoke_all_sessions(user_id=active_session.user_id)
    second_revoked_count = await auth.revoke_all_sessions(
        user_id=active_session.user_id
    )

    async with session_maker() as session:
        result = await session.execute(
            select(Session).where(
                Session.id.in_(
                    [
                        active_session.id,
                        already_revoked_session.id,
                        expired_session.id,
                    ]
                )
            )
        )
        sessions_by_id = {s.id: s for s in result.scalars()}

    assert signup_resp.status_code == status.HTTP_201_CREATED
    assert revoked_count == 1
    assert sessions_by_id[active_session.id].revoked_at is not None
    assert sessions_by_id[already_revoked_session.id].revoked_at == already_revoked_at
    assert sessions_by_id[expired_session.id].revoked_at is None
    assert second_revoked_count == 0
