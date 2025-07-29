from typing import List
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # Environment
    env: str
    debug: bool = False
    service_name: str
    service_version: str

    # Database
    database_url: str

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool
    minio_bucket: str
    minio_region: str

    # Redis/Celery
    redis_url: str

    # JWT
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # External Services
    auth_service_url: str
    account_service_url: str
    notification_service_url: str
    analytics_service_url: str
    transaction_service_url: str

    # File Upload
    max_file_size: int
    allowed_mime_types: List[str] = []
    allowed_origins: List[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="forbid",
    )

    @field_validator("allowed_mime_types", mode="before")
    def parse_mime_types(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
