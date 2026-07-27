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


class AuthLoomConfig(BaseSettings):
    cookie_session: AuthLoomCookieSessionConfig
    session_factory: async_sessionmaker[AsyncSession]
