from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.params import Depends as DependsParam

from authloom.db.schema import User
from authloom.dtos import (
    AuthHttpResDto,
    ChangePasswordReqDto,
    PasswordResetHttpReqDto,
    RequestEmailVerificationHttpReqDto,
    RequestPasswordResetHttpReqDto,
    SigninHttpReqDto,
    SigninSrvInputDto,
    SignupHttpReqDto,
    SignupSrvInputDto,
    UserResDto,
)
from authloom.exceptions import (
    InvalidCredentialsException,
    InvalidEmailVerificationTokenException,
    InvalidPasswordResetTokenException,
    PasswordPolicyException,
    SessionCreationException,
    UserAlreadyExistsException,
)
from authloom.service import AuthLoom


def create_auth_router(
    auth: AuthLoom,
    *,
    prefix: str = "/auth",
    unsafe_route_dependencies: Sequence[DependsParam] | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=["AuthLoom"])

    @router.post(
        "/signup",
        status_code=status.HTTP_201_CREATED,
        response_model=AuthHttpResDto,
        dependencies=unsafe_route_dependencies,
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
        "/signin",
        status_code=status.HTTP_200_OK,
        response_model=AuthHttpResDto,
        dependencies=unsafe_route_dependencies,
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

    @router.post(
        "/signout",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=unsafe_route_dependencies,
    )
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

    @router.post(
        "/request-password-reset",
        status_code=status.HTTP_200_OK,
        dependencies=unsafe_route_dependencies,
    )
    async def request_password_reset(input: RequestPasswordResetHttpReqDto):
        token = await auth.request_password_reset(email=input.email)

        if token is not None and auth.config.hooks.on_request_password_reset:
            auth.config.hooks.on_request_password_reset(input.email, token)

        return {"message": "password reset sent to your email"}

    @router.post(
        "/request-email-verification",
        status_code=status.HTTP_200_OK,
        dependencies=unsafe_route_dependencies,
    )
    async def request_email_verification(input: RequestEmailVerificationHttpReqDto):
        token = await auth.request_email_verification(email=input.email)

        if token is not None and auth.config.hooks.on_request_email_verification:
            auth.config.hooks.on_request_email_verification(input.email, token)

        return {"message": "email verification sent to your email"}

    @router.get(
        "/email-verification",
        status_code=status.HTTP_200_OK,
    )
    async def verify_email(token: str):
        try:
            await auth.verify_email(token_raw=token)
        except InvalidEmailVerificationTokenException as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="could not verify your email",
            ) from exc

        return {"message": "verified email successfully"}

    @router.post(
        "/password-reset",
        status_code=status.HTTP_200_OK,
        dependencies=unsafe_route_dependencies,
    )
    async def verify_token_password_reset(token: str, input: PasswordResetHttpReqDto):
        try:
            await auth.complete_password_reset(
                token_raw=token, new_password=input.password
            )
        except InvalidPasswordResetTokenException as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid or expired password reset token",
            ) from exc
        except PasswordPolicyException as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": exc.code,
                    "message": exc.message,
                },
            ) from exc

        return {"message": "password reset successful"}

    @router.post(
        "/password-change",
        status_code=status.HTTP_200_OK,
        dependencies=unsafe_route_dependencies,
    )
    async def password_change(
        request: Request,
        user: Annotated[User, Depends(auth.require_current_user)],
        input: ChangePasswordReqDto,
    ):
        try:
            updated = await auth.change_password(
                user_id=user.id,
                current_password=input.current_password,
                new_password=input.new_password,
                preserve_session_token_raw=request.cookies.get(
                    auth.config.cookie_session.cookie_name
                ),
            )
        except InvalidCredentialsException as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            ) from exc
        except PasswordPolicyException as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": exc.code,
                    "message": exc.message,
                },
            ) from exc

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not update your password",
            )

        return {"message": "Password updated successfully"}

    return router
