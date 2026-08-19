from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./authloom_example.db"
    csrf_secret_key: str = Field(min_length=32)
    app_base_url: str = "http://127.0.0.1:8000"
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    email_from: str = "no-reply@authloom.local"

    model_config = SettingsConfigDict(env_file=".env")


# BaseSettings fills this required field from the environment or .env at runtime.
settings = Settings()  # pyright: ignore[reportCallIssue]
