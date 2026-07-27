from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class AuthLoomCookieSessionConfig(BaseModel):
    cookie_name: str = Field(
        default="authloom.auth", description="Name of the auth session cookie"
    )
    ttl: int = Field(default=604800, description="TTL in seconds")
    http_only: bool = True
    secure: bool = False
    samesite: Literal["lax", "strict", "none"] = "lax"
    domain: str | None = None
    path: str = "/"

    @model_validator(mode="after")
    def validate_samesite_secure_options(self) -> Self:
        if self.samesite == "none" and not self.secure:
            raise ValueError("samesite `none` required secure to be `true`")

        return self


class AuthLoomPasswordConfig(BaseModel):
    min_length: int = Field(default=15)
    max_length: int = Field(default=64)

    @model_validator(mode="after")
    def validate_lengths(self) -> Self:
        if self.min_length < 15:
            raise ValueError("min_length cannot be less than 15 characters")

        if self.max_length < 64:
            raise ValueError("max_length cannot be less than 64 characters")

        if self.max_length > 128:
            raise ValueError("max_length cannot be more than 128 characters")

        if self.min_length > self.max_length:
            raise ValueError("min_length cannot be greater than max_length")

        return self


class AuthLoomConfig(BaseSettings):
    cookie_session: AuthLoomCookieSessionConfig
    session_factory: async_sessionmaker[AsyncSession]
    password_config: AuthLoomPasswordConfig = Field(
        default_factory=AuthLoomPasswordConfig
    )
