from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TG_", env_file=None, case_sensitive=False)

    # App
    ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Services
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/trade_guardian"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


