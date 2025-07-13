from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    environment: str
    debug: bool
    project_name: str
    project_version: str
    api_v1_prefix: str

    # Database Configuration
    database_url: str
    secret_key: str
    jwt_public_key_path: str
    jwt_algorithm: str

    # Redis Configuration
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: Optional[str] = None

    # Cache Configuration
    cache_ttl: int
    cache_prefix: str

    # Inter-service Communication
    auth_service_url: str
    transaction_service_url: str
    notification_service_url: str
    analytics_service_url: str
    document_service_url: str

    # Redis Streams Configuration
    redis_stream_account_events: str
    redis_stream_consumer_group: str
    redis_stream_transaction_events: str
    # CORS Configuration
    allowed_origins: List[str] = []

    # Logging Configuration
    log_level: str
    log_format: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="ignore",
    )

    @lru_cache
    def get_settings() -> Settings:
        return Settings()

    settings = get_settings()
