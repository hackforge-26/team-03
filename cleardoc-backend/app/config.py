from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "ClearDoc"
    app_env: str = "development"
    secret_key: str
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str
    sync_database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: str

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str

    # Celery
    celery_broker_url: str
    celery_result_backend: str

    # Rate Limiting
    rate_limit_per_minute: int = 10
    rate_limit_per_day: int = 50

    # Sentry
    sentry_dsn: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
