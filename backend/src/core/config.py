from typing import Any

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: PostgresDsn
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Redis
    redis_url: RedisDsn

    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        return []

    # External APIs
    discogs_api_url: str = "https://api.discogs.com"
    ebay_api_url: str = "https://api.ebay.com/buy/browse/v1"
    ebay_oauth_url: str = "https://api.ebay.com/identity/v1/oauth2/token"

    # Background Tasks
    celery_broker_url: RedisDsn
    celery_result_backend: RedisDsn

    # Logging
    log_level: str = "INFO"

    # Application
    app_name: str = "VinylDigger"
    debug: bool = False


settings = Settings()  # type: ignore[call-arg]
