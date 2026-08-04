from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic_settings import BaseSettings

from app.config import settings
from app.database import AsyncSessionLocal
from authloom import AuthLoom, create_auth_router
from authloom.db import User
from authloom.settings import (
    AuthLoomConfig,
    AuthLoomCookieSessionConfig,
)


class CsrfSettings(BaseSettings):
    secret_key: str
    cookie_samesite: str = "lax"


@CsrfProtect.load_config
def get_csrf_config() -> CsrfSettings:
    return CsrfSettings(secret_key=settings.csrf_secret_key)


csrf_protect_dependency = Depends()


async def verify_csrf(
    request: Request,
    csrf_header: Annotated[str, Header(alias="X-CSRF-Token")],
    csrf_protect: CsrfProtect = csrf_protect_dependency,
) -> None:
    await csrf_protect.validate_csrf(request)


csrf_dependency = Depends(verify_csrf)
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

app.include_router(
    create_auth_router(
        auth,
        unsafe_route_dependencies=(csrf_dependency,),
    )
)


@app.exception_handler(CsrfProtectError)
async def csrf_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.get("/csrf")
def get_csrf_token(csrf_protect: CsrfProtect = csrf_protect_dependency):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse({"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


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


@app.post("/example-mutation", dependencies=[csrf_dependency])
async def example_mutation():
    return {"status": "changed"}
