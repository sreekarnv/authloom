from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./test.db"
    csrf_secret_key: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
