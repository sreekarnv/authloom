from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserResDto(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class SignupHttpReqDto(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=1)
    password_confirm: str = Field(min_length=1)

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")

        return self


class AuthHttpResDto(BaseModel):
    message: str
    user: UserResDto


class SignupSrvInputDto(BaseModel):
    name: str
    email: EmailStr
    password: str


class SigninSrvInputDto(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
