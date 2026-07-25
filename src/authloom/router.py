from fastapi import APIRouter, HTTPException, status

from authloom.dtos import SignupHttpReqDto, SignupHttpResDto, SignupSrvInputDto
from authloom.exceptions import UserAlreadyExistsException
from authloom.service import AuthLoom


def create_auth_router(auth: AuthLoom) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["AuthLoom"])

    @router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=SignupHttpResDto)
    async def signup(input: SignupHttpReqDto):
        try:
            user = await auth.signup(input=SignupSrvInputDto(**input.model_dump()))
            return SignupHttpResDto(message="account created successfully", user=user)
        except UserAlreadyExistsException as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="user with this email already exists",
            ) from exc

    return router