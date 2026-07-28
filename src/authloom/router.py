from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from authloom.db.schema import User
from authloom.dtos import (
    AuthHttpResDto,
    SigninHttpReqDto,
    SigninSrvInputDto,
    SignupHttpReqDto,
    SignupSrvInputDto,
    UserResDto,
)
from authloom.exceptions import (
    InvalidCredentialsException,
    PasswordPolicyException,
    SessionCreationException,
    UserAlreadyExistsException,
)
from authloom.service import AuthLoom


def create_auth_router(auth: AuthLoom) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["AuthLoom"])

    @router.post(
        "/signup", status_code=status.HTTP_201_CREATED, response_model=AuthHttpResDto
    )
    async def signup(input: SignupHttpReqDto, response: Response):
        try:
            user, session = await auth.signup(
                input=SignupSrvInputDto(**input.model_dump())
            )
            response.set_cookie(
                key=auth.config.cookie_session.cookie_name,
                value=session.token_raw,
                httponly=auth.config.cookie_session.http_only,
                expires=session.expires_at,
                domain=auth.config.cookie_session.domain,
                path=auth.config.cookie_session.path,
                samesite=auth.config.cookie_session.samesite,
                secure=auth.config.cookie_session.secure,
            )
            return AuthHttpResDto(message="account created successfully", user=user)
        except PasswordPolicyException as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": exc.code,
                    "message": exc.message,
                },
            ) from exc
        except UserAlreadyExistsException as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="user with this email already exists",
            ) from exc
        except SessionCreationException as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="could not create session",
            ) from exc

    @router.post(
        "/signin", status_code=status.HTTP_200_OK, response_model=AuthHttpResDto
    )
    async def signin(input: SigninHttpReqDto, response: Response):
        try:
            user, session = await auth.signin(
                input=SigninSrvInputDto(**input.model_dump())
            )
        except InvalidCredentialsException as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            ) from exc
        except SessionCreationException as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="could not create session",
            ) from exc

        response.set_cookie(
            key=auth.config.cookie_session.cookie_name,
            value=session.token_raw,
            httponly=auth.config.cookie_session.http_only,
            expires=session.expires_at,
            domain=auth.config.cookie_session.domain,
            path=auth.config.cookie_session.path,
            samesite=auth.config.cookie_session.samesite,
            secure=auth.config.cookie_session.secure,
        )
        return AuthHttpResDto(message="logged in successfully", user=user)

    @router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
    async def signout(request: Request, response: Response):
        token_raw = request.cookies.get(auth.config.cookie_session.cookie_name)
        if not token_raw:
            return None

        await auth.signout(token_raw=token_raw)

        response.delete_cookie(
            key=auth.config.cookie_session.cookie_name,
            httponly=auth.config.cookie_session.http_only,
            domain=auth.config.cookie_session.domain,
            path=auth.config.cookie_session.path,
            samesite=auth.config.cookie_session.samesite,
            secure=auth.config.cookie_session.secure,
        )

    @router.get("/me", status_code=status.HTTP_200_OK)
    async def get_current_user(
        user: Annotated[User, Depends(auth.require_current_user)],
    ):
        return UserResDto.model_validate(user)

    return router
