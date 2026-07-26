from fastapi import APIRouter, HTTPException, status, Response

from authloom.dtos import (
    AuthHttpResDto,
    SigninSrvInputDto,
    SignupHttpReqDto,
    SignupSrvInputDto,
)
from authloom.exceptions import InvalidCredentialsException, UserAlreadyExistsException
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
                "authloom.auth",
                value=session.token_raw,
                httponly=True,
            )
            return AuthHttpResDto(message="account created successfully", user=user)
        except UserAlreadyExistsException as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="user with this email already exists",
            ) from exc

    @router.post(
        "/signin", status_code=status.HTTP_200_OK, response_model=AuthHttpResDto
    )
    async def signin(input: SigninSrvInputDto):
        try:
            user = await auth.signin(input=SigninSrvInputDto(**input.model_dump()))
        except InvalidCredentialsException as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            ) from exc
        return AuthHttpResDto(message="logged in successfully", user=user)

    return router
