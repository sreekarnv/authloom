import unicodedata
from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
    model_validator,
)


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
    password: str
    password_confirm: str

    @model_validator(mode="after")
    def passwords_match(self) -> Self:
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")

        return self

    @field_validator("password", "password_confirm")
    @classmethod
    def normalize_password(cls, v: str) -> str:
        return unicodedata.normalize("NFC", v)


class SigninHttpReqDto(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def normalize_password(cls, v: str) -> str:
        return unicodedata.normalize("NFC", v)


class AuthHttpResDto(BaseModel):
    message: str
    user: UserResDto


class SignupSrvInputDto(BaseModel):
    name: str
    email: EmailStr
    password: str


class SigninSrvInputDto(BaseModel):
    email: EmailStr
    password: str


class SessionResDto(BaseModel):
    id: str
    token_raw: str
    expires_at: datetime


class RequestPasswordResetHttpReqDto(BaseModel):
    email: EmailStr
