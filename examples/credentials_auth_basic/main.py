from contextlib import asynccontextmanager

from database import AsyncSessionLocal, engine
from fastapi import FastAPI

from authloom import AuthLoom, AuthLoomBase, create_auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(AuthLoomBase.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)
auth = AuthLoom(session_factory=AsyncSessionLocal)

app.include_router(create_auth_router(auth))
