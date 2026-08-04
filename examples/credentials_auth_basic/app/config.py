from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./test.db"
    csrf_secret_key: str = Field(min_length=32)

    model_config = SettingsConfigDict(env_file=".env")


# BaseSettings fills this required field from the environment or .env at runtime.
settings = Settings()  # pyright: ignore[reportCallIssue]
