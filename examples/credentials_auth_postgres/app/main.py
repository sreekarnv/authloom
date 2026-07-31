from typing import Annotated

from fastapi import Depends, FastAPI

from app.database import AsyncSessionLocal
from authloom import AuthLoom, create_auth_router
from authloom.db import User
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


@app.get("/me")
async def get_me(user: Annotated[User, Depends(auth.require_current_user)]):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@app.get("/optional-auth")
async def optional_auth(
    user: Annotated[User | None, Depends(auth.optional_current_user)],
):
    if user is None:
        return {"authenticated": False, "user": None}

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
    }
