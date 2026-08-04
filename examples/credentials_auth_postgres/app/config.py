from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://authloom:authloom@localhost:5432/authloom"
    csrf_secret_key: str

    model_config = SettingsConfigDict(env_file=".env")


# BaseSettings fills this required field from the environment or .env at runtime.
settings = Settings()  # pyright: ignore[reportCallIssue]
