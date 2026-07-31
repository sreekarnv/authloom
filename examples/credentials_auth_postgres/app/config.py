from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://authloom:authloom@localhost:5432/authloom"


settings = Settings()
