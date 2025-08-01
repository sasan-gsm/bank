# notification-service/app/core/config.py
from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from decouple import config


class Settings(BaseSettings):
    # Environment Configuration
    environment: str = config("ENVIRONMENT", default="development")
    debug: bool = config("DEBUG", default=True, cast=bool)
    project_name: str = config("PROJECT_NAME", default="Notification Service")
    project_version: str = config("PROJECT_VERSION", default="1.0.0")
    api_v1_prefix: str = config("API_V1_PREFIX", default="/api/v1")

    # Database Configuration (SQLite as per original)
    database_url: str = config(
        "DATABASE_URL", default="sqlite+aiosqlite:///./data/notifications.db"
    )

    # Security Configuration
    secret_key: str = config("SECRET_KEY")
    jwt_public_key_path: str = config(
        "JWT_PUBLIC_KEY_PATH", default="./keys/public_key.pem"
    )
    jwt_algorithm: str = config("JWT_ALGORITHM", default="RS256")

    # Redis Configuration
    redis_host: str = config("REDIS_HOST", default="localhost")
    redis_port: int = config("REDIS_PORT", default=6379, cast=int)
    redis_db: int = config("REDIS_DB", default=0, cast=int)
    redis_password: Optional[str] = config("REDIS_PASSWORD", default=None)

    # Cache Configuration
    cache_ttl: int = config("CACHE_TTL", default=300, cast=int)
    cache_prefix: str = config("CACHE_PREFIX", default="notification-service")

    # Inter-service Communication
    auth_service_url: str = config("AUTH_SERVICE_URL", default="http://localhost:8000")
    transaction_service_url: str = config(
        "TRANSACTION_SERVICE_URL", default="http://localhost:8001"
    )
    account_service_url: str = config(
        "ACCOUNT_SERVICE_URL", default="http://localhost:8002"
    )
    analytics_service_url: str = config(
        "ANALYTICS_SERVICE_URL", default="http://localhost:8004"
    )
    document_service_url: str = config(
        "DOCUMENT_SERVICE_URL", default="http://localhost:8005"
    )

    # Redis Streams Configuration
    redis_stream_notifications: str = config(
        "REDIS_STREAM_NOTIFICATIONS", default="notification-events"
    )
    redis_stream_transactions: str = config(
        "REDIS_STREAM_TRANSACTIONS", default="transaction-events"
    )
    redis_stream_accounts: str = config(
        "REDIS_STREAM_ACCOUNTS", default="account-events"
    )
    redis_stream_consumer_group: str = config(
        "REDIS_STREAM_CONSUMER_GROUP", default="notification-service-group"
    )

    # Email Configuration
    smtp_host: str = config("SMTP_HOST", default="localhost")
    smtp_port: int = config("SMTP_PORT", default=587, cast=int)
    smtp_user: str = config("SMTP_USER", default="")
    smtp_password: str = config("SMTP_PASSWORD", default="")
    smtp_tls: bool = config("SMTP_TLS", default=True, cast=bool)
    smtp_ssl: bool = config("SMTP_SSL", default=False, cast=bool)
    notify_from: str = config("NOTIFY_FROM", default="noreply@bankapp.com")
    notify_from_name: str = config(
        "NOTIFY_FROM_NAME", default="Bank Notification Service"
    )

    # Notification Settings
    max_notifications_per_user: int = config(
        "MAX_NOTIFICATIONS_PER_USER", default=1000, cast=int
    )
    notification_retention_days: int = config(
        "NOTIFICATION_RETENTION_DAYS", default=90, cast=int
    )
    email_retry_attempts: int = config("EMAIL_RETRY_ATTEMPTS", default=3, cast=int)
    email_retry_delay: int = config("EMAIL_RETRY_DELAY", default=300, cast=int)

    # CORS Configuration
    allowed_origins: List[str] = config(
        "ALLOWED_ORIGINS",
        default="http://localhost:3000,http://localhost:8080",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )

    # Logging Configuration
    log_level: str = config("LOG_LEVEL", default="INFO")
    log_format: str = config("LOG_FORMAT", default="json")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def jwt_public_key(self) -> str:
        """Load JWT public key from file."""
        try:
            with open(self.jwt_public_key_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="forbid",
    )


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of the Settings."""
    return Settings()


settings = get_settings()
