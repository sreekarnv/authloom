from database import AsyncSessionLocal
from fastapi import FastAPI

from authloom import AuthLoom, create_auth_router
from authloom.settings import (
    AuthLoomConfig,
    AuthLoomCookieSessionConfig,
)

app = FastAPI()
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
