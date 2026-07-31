import os

import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from authloom import AuthLoom, AuthLoomConfig, create_auth_router
from authloom.db.schema import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    database_url = os.environ.get("AUTHLOOM_TEST_DATABASE_URL") or TEST_DATABASE_URL
    engine_options = {"url": database_url, "echo": False}

    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}

    if database_url == TEST_DATABASE_URL:
        engine_options["poolclass"] = StaticPool

    engine = create_async_engine(**engine_options)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def app(async_engine: AsyncEngine) -> FastAPI:
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    _app = FastAPI()

    auth = AuthLoom(config=AuthLoomConfig(session_factory=session_maker))

    auth_router = create_auth_router(auth=auth)
    _app.include_router(auth_router)

    return _app
