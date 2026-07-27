from contextlib import asynccontextmanager

from database import AsyncSessionLocal, engine
from fastapi import FastAPI

from authloom import AuthLoom, AuthLoomBase, create_auth_router
from authloom.settings import AuthLoomConfig, AuthLoomCookieSessionConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(AuthLoomBase.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)
auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
        cookie_session=AuthLoomCookieSessionConfig(
            cookie_name="authloom.auth",
            http_only=True,
            samesite="lax",
            secure=False,
        ),
    )
)

app.include_router(create_auth_router(auth))
