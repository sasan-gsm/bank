from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, EmailStr
from functools import lru_cache
from decouple import config
from typing import Optional


class Settings(BaseSettings):
    # Environment Configuration
    environment: str = config("ENVIRONMENT", default="development")
    debug: bool = config("DEBUG", default=True, cast=bool)
    service_name: str = config("SERVICE_NAME", default="auth-service")
    service_version: str = config("SERVICE_VERSION", default="1.0.0")

    # Security Configuration
    secret_key: str = config("SECRET_KEY")

    # Database Configuration (SQLite as per original)
    database_url: str = config("DATABASE_URL", default="sqlite+aiosqlite:///./auth.db")

    # JWT Configuration (RS256 Enterprise Standard)
    jwt_private_key: str = config("JWT_PRIVATE_KEY")
    jwt_public_key: str = config("JWT_PUBLIC_KEY")
    jwt_algorithm: str = config("JWT_ALGORITHM", default="RS256")
    access_token_expire_minutes: int = config(
        "ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int
    )
    refresh_token_expire_days: int = config(
        "REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int
    )

    # Redis Configuration
    redis_host: str = config("REDIS_HOST", default="localhost")
    redis_port: int = config("REDIS_PORT", default=6379, cast=int)
    redis_db: int = config("REDIS_DB", default=0, cast=int)
    redis_password: Optional[str] = config("REDIS_PASSWORD", default=None)

    # Cache Configuration
    cache_ttl: int = config("CACHE_TTL", default=300, cast=int)
    cache_prefix: str = config("CACHE_PREFIX", default="auth-service")

    # Email Configuration
    smtp_host: str = config("SMTP_HOST", default="localhost")
    smtp_port: int = config("SMTP_PORT", default=587, cast=int)
    smtp_username: Optional[str] = config("SMTP_USERNAME", default=None)
    smtp_password: Optional[str] = config("SMTP_PASSWORD", default=None)
    smtp_use_tls: bool = config("SMTP_USE_TLS", default=True, cast=bool)

    # OTP Configuration
    otp_length: int = config("OTP_LENGTH", default=6, cast=int)
    otp_expire_minutes: int = config("OTP_EXPIRE_MINUTES", default=10, cast=int)

    # First Superuser Configuration
    first_superuser_username: str = config("FIRST_SUPERUSER_USERNAME", default="admin")
    first_superuser_email: EmailStr = config(
        "FIRST_SUPERUSER_EMAIL", default="admin@example.com"
    )
    first_superuser_password: str = config(
        "FIRST_SUPERUSER_PASSWORD", default="admin123"
    )
    first_superuser_full_name: str = config(
        "FIRST_SUPERUSER_FULL_NAME", default="System Administrator"
    )

    # Inter-service Communication URLs
    transaction_service_url: str = config(
        "TRANSACTION_SERVICE_URL", default="http://localhost:8001"
    )
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

    # Celery Configuration
    celery_broker_url: str = config(
        "CELERY_BROKER_URL", default="redis://localhost:6379/1"
    )
    celery_result_backend: str = config(
        "CELERY_RESULT_BACKEND", default="redis://localhost:6379/2"
    )

    # CORS Configuration
    allowed_origins: List[str] = config(
        "ALLOWED_ORIGINS",
        default="http://localhost:3000,http://localhost:8080",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )

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
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_assignment=True,
        extra="forbid",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = Settings()
