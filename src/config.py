from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "PRS Backend"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prs"
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
