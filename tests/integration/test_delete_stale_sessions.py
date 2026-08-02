from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig
from authloom.db.schema import Session, User


@pytest.mark.asyncio
async def test_delete_stale_sessions_deletes_stale_sessions_and_returns_count(
    async_engine: AsyncEngine,
):
    cutoff = datetime(2026, 1, 1, 12, tzinfo=UTC)
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))

    async with session_maker() as session:
        user = User(
            name="Test User",
            email="test_delete_stale_sessions@example.com",
            **{"password": "test-password-hash"},
        )
        session.add(user)
        await session.flush()

        expired_session = Session(
            token_hash="0" * 64,
            user_id=user.id,
            expires_at=cutoff - timedelta(microseconds=1),
        )
        boundary_session = Session(
            token_hash="1" * 64,
            user_id=user.id,
            expires_at=cutoff,
        )
        revoked_session = Session(
            token_hash="2" * 64,
            user_id=user.id,
            expires_at=cutoff + timedelta(days=1),
            revoked_at=cutoff - timedelta(seconds=1),
        )
        active_session = Session(
            token_hash="3" * 64,
            user_id=user.id,
            expires_at=cutoff + timedelta(microseconds=1),
        )
        session.add_all(
            [expired_session, boundary_session, revoked_session, active_session]
        )
        await session.commit()

    deleted_count = await auth.delete_stale_sessions(before=cutoff)

    async with session_maker() as session:
        result = await session.execute(select(Session.token_hash))

    assert deleted_count == 3
    assert set(result.scalars()) == {active_session.token_hash}


@pytest.mark.asyncio
async def test_delete_stale_sessions_rejects_naive_cutoff(
    async_engine: AsyncEngine,
):
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))

    with pytest.raises(ValueError, match="before must be timezone-aware"):
        await auth.delete_stale_sessions(before=datetime(2026, 1, 1, 12))
