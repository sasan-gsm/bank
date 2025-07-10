# transaction-service/app/core/config.py

from typing import List, Optional
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environment Configuration
    environment: str = Field(...)
    debug: bool = Field(default=True)

    # Database Configuration
    database_url: str = Field(...)
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=30)
    db_echo: bool = Field(default=False)

    # JWT Configuration
    jwt_public_key_path: str = Field(...)
    jwt_algorithm: str = Field(default="RS256")
    jwt_secret_key: str = Field(...)

    # Redis Configuration
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = None
    redis_ssl: bool = Field(default=False)
    redis_socket_timeout: int = Field(default=5)
    redis_connection_timeout: int = Field(default=10)

    # Cache Configuration
    cache_ttl: int = Field(default=300)
    cache_prefix: str = Field(default="transaction-service")
    cache_max_connections: int = Field(default=50)

    # Celery Configuration
    celery_broker_url: str = Field(...)
    celery_result_backend: str = Field(...)
    celery_task_serializer: str = Field(default="json")
    celery_result_serializer: str = Field(default="json")
    celery_accept_content: str = Field(default="json")
    celery_timezone: str = Field(default="Asia/Tehran")
    celery_enable_utc: bool = Field(default=True)
    celery_task_soft_time_limit: int = Field(default=60)
    celery_task_time_limit: int = Field(default=1800)
    celery_worker_prefetch_multiplier: int = Field(default=1)
    celery_worker_max_tasks_per_child: int = Field(default=1000)

    # Service URLs
    auth_service_url: str = Field(...)
    account_service_url: str = Field(...)
    notification_service_url: str = Field(...)
    analytics_service_url: str = Field(...)
    document_service_url: str = Field(...)

    # Iranian Banking Configuration
    default_currency: str = Field(default="IRR")
    max_transaction_amount: float = Field(default=10_000_000_000.00)
    min_transaction_amount: float = Field(default=1000.00)
    future_transaction_max_days: int = Field(default=365)
    persian_calendar_enabled: bool = Field(default=True)
    timezone: str = Field(default="Asia/Tehran")
    locale: str = Field(default="fa_IR")

    # Security Configuration
    allowed_hosts: List[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:3001",
        ]
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_max_age: int = Field(default=86400)

    # Feature Flags
    feature_future_transactions: bool = Field(default=True)
    feature_bulk_operations: bool = Field(default=True)
    feature_advanced_reporting: bool = Field(default=False)
    feature_audit_logging: bool = Field(default=True)
    feature_real_time_notifications: bool = Field(default=True)

    @property
    def redis_url(self) -> str:
        pwd = f":{self.redis_password}@" if self.redis_password else ""
        protocol = "rediss" if self.redis_ssl else "redis"
        return f"{protocol}://{pwd}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic"""
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
