from fastapi import APIRouter, HTTPException, Response, status, Request

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
                expires=session.expires_at,
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
    async def signin(input: SigninSrvInputDto, response: Response):
        try:
            user, session = await auth.signin(
                input=SigninSrvInputDto(**input.model_dump())
            )
            
        except InvalidCredentialsException as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
            ) from exc

        response.set_cookie(
            "authloom.auth",
            value=session.token_raw,
            httponly=True,
            expires=session.expires_at,
        )
        return AuthHttpResDto(message="logged in successfully", user=user)

    @router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
    async def signout(request: Request, response: Response):
        token_raw = request.cookies.get("authloom.auth")
        if not token_raw: return None

        await auth.signout(token_raw=token_raw)

        response.delete_cookie("authloom.auth")

    return router
