from contextlib import asynccontextmanager
from fastapi import FastAPI
from authloom.schema import Base as AuthLoomBase
from authloom.router import create_auth_router
from authloom.service import AuthLoom
from database import AsyncSessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(AuthLoomBase.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)
auth = AuthLoom(session_factory=AsyncSessionLocal)

app.include_router(create_auth_router(auth))
