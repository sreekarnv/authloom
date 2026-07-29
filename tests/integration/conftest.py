import pytest_asyncio

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker

from authloom import AuthLoom, AuthLoomConfig, create_auth_router
from authloom.db.schema import Session, User, Base


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine():
    engine = create_async_engine(
        url="sqlite+aiosqlite:///./test.db",
        echo=False,
        connect_args={
            "check_same_thread": False
        }
    )

    async with engine.begin() as conn:
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
        expire_on_commit=False
    )

    _app = FastAPI()

    auth = AuthLoom(
        config=AuthLoomConfig(
            session_factory=session_maker
        )
    )

    auth_router = create_auth_router(auth=auth)
    _app.include_router(auth_router)

    return _app
