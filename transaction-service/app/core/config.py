# transaction-service/app/core/config.py

from typing import List, Optional, Union
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from decouple import config


class Settings(BaseSettings):
    # Environment Configuration
    environment: str = config("ENVIRONMENT", default="development")
    debug: bool = config("DEBUG", default=True, cast=bool)
    secret_key: str = config("SECRET_KEY")

    # Database Configuration (SQLite as per original)
    database_url: str = config(
        "DATABASE_URL", default="sqlite+aiosqlite:///./data/transaction.db"
    )
    db_pool_size: int = config("DB_POOL_SIZE", default=20, cast=int)
    db_max_overflow: int = config("DB_MAX_OVERFLOW", default=30, cast=int)
    db_echo: bool = config("DB_ECHO", default=False, cast=bool)
    test_database_url: str = config(
        "TEST_DATABASE_URL", default="sqlite+aiosqlite:///./data/transaction_test.db"
    )

    # JWT Configuration (RS256 - Verification Only, following reference pattern)
    jwt_public_key_path: str = config(
        "JWT_PUBLIC_KEY_PATH", default="keys/public_key.pem"
    )
    jwt_algorithm: str = config("JWT_ALGORITHM", default="RS256")
    jwt_secret_key: str = config("JWT_SECRET_KEY")

    # Redis Configuration
    redis_host: str = config("REDIS_HOST", default="localhost")
    redis_port: int = config("REDIS_PORT", default=6379, cast=int)
    redis_db: int = config("REDIS_DB", default=0, cast=int)
    redis_password: Optional[str] = config("REDIS_PASSWORD", default=None)
    redis_ssl: bool = config("REDIS_SSL", default=False, cast=bool)
    redis_socket_timeout: int = config("REDIS_SOCKET_TIMEOUT", default=5, cast=int)
    redis_connection_timeout: int = config(
        "REDIS_CONNECTION_TIMEOUT", default=10, cast=int
    )

    # Cache Configuration
    cache_ttl: int = config("CACHE_TTL", default=300, cast=int)
    cache_prefix: str = config("CACHE_PREFIX", default="transaction-service")
    cache_max_connections: int = config("CACHE_MAX_CONNECTIONS", default=50, cast=int)

    # Celery Configuration
    celery_broker_url: str = config(
        "CELERY_BROKER_URL", default="redis://localhost:6379/1"
    )
    celery_result_backend: str = config(
        "CELERY_RESULT_BACKEND", default="redis://localhost:6379/2"
    )
    celery_task_serializer: str = config("CELERY_TASK_SERIALIZER", default="json")
    celery_result_serializer: str = config("CELERY_RESULT_SERIALIZER", default="json")
    celery_accept_content: str = config("CELERY_ACCEPT_CONTENT", default="json")
    celery_timezone: str = config("CELERY_TIMEZONE", default="Asia/Tehran")
    celery_enable_utc: bool = config("CELERY_ENABLE_UTC", default=True, cast=bool)
    celery_task_soft_time_limit: int = config(
        "CELERY_TASK_SOFT_TIME_LIMIT", default=60, cast=int
    )
    celery_task_time_limit: int = config(
        "CELERY_TASK_TIME_LIMIT", default=1800, cast=int
    )
    celery_worker_prefetch_multiplier: int = config(
        "CELERY_WORKER_PREFETCH_MULTIPLIER", default=1, cast=int
    )
    celery_worker_max_tasks_per_child: int = config(
        "CELERY_WORKER_MAX_TASKS_PER_CHILD", default=1000, cast=int
    )

    # Service URLs
    auth_service_url: str = config("AUTH_SERVICE_URL", default="http://localhost:8000")
    account_service_url: str = config(
        "ACCOUNT_SERVICE_URL", default="http://localhost:8002"
    )
    notification_service_url: str = config(
        "NOTIFICATION_SERVICE_URL", default="http://localhost:8003"
    )
    analytics_service_url: str = config(
        "ANALYTICS_SERVICE_URL", default="http://localhost:8004"
    )
    document_service_url: str = config(
        "DOCUMENT_SERVICE_URL", default="http://localhost:8005"
    )

    # Iranian Banking Configuration
    default_currency: str = config("DEFAULT_CURRENCY", default="IRR")
    max_transaction_amount: float = config(
        "MAX_TRANSACTION_AMOUNT", default=10_000_000_000.00, cast=float
    )
    min_transaction_amount: float = config(
        "MIN_TRANSACTION_AMOUNT", default=1000.00, cast=float
    )
    future_transaction_max_days: int = config(
        "FUTURE_TRANSACTION_MAX_DAYS", default=365, cast=int
    )
    persian_calendar_enabled: bool = config(
        "PERSIAN_CALENDAR_ENABLED", default=True, cast=bool
    )
    timezone: str = config("TIMEZONE", default="Asia/Tehran")
    locale: str = config("LOCALE", default="fa_IR")

    # Security Configuration
    allowed_hosts: List[str] = ["localhost", "127.0.0.1", "*.yourdomain.com"]
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:3001",
    ]
    cors_allow_credentials: bool = config(
        "CORS_ALLOW_CREDENTIALS", default=True, cast=bool
    )
    cors_max_age: int = config("CORS_MAX_AGE", default=86400, cast=int)

    # Feature Flags
    feature_future_transactions: bool = config(
        "FEATURE_FUTURE_TRANSACTIONS", default=True, cast=bool
    )
    feature_bulk_operations: bool = config(
        "FEATURE_BULK_OPERATIONS", default=True, cast=bool
    )
    feature_advanced_reporting: bool = config(
        "FEATURE_ADVANCED_REPORTING", default=False, cast=bool
    )
    feature_audit_logging: bool = config(
        "FEATURE_AUDIT_LOGGING", default=True, cast=bool
    )
    feature_real_time_notifications: bool = config(
        "FEATURE_REAL_TIME_NOTIFICATIONS", default=True, cast=bool
    )

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        elif isinstance(v, list):
            return v
        return ["localhost", "127.0.0.1", "*.yourdomain.com"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:3001",
        ]

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "testing", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components"""
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
        extra="forbid",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
