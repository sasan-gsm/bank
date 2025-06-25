from functools import lru_cache
from typing import List, Optional
from decouple import config, Csv
from pydantic import BaseSettings, Field, field_validator
from pydantic_settings import BaseSettings as PydanticBaseSettings


class Settings(PydanticBaseSettings):
    # Environment
    ENVIRONMENT: str = config("ENVIRONMENT", default="development")
    DEBUG: bool = config("DEBUG", default=True, cast=bool)

    # Application
    APP_NAME: str = config("APP_NAME", default="Banking Auth Service")
    APP_VERSION: str = config("APP_VERSION", default="1.0.0")
    API_V1_PREFIX: str = config("API_V1_PREFIX", default="/api/v1")

    # Database
    DATABASE_URL: str = config("DATABASE_URL")
    DATABASE_ECHO: bool = config("DATABASE_ECHO", default=False, cast=bool)

    # Security - RS256 JWT
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="RS256")
    JWT_PRIVATE_KEY_PATH: str = config(
        "JWT_PRIVATE_KEY_PATH", default="keys/private_key.pem"
    )
    JWT_PUBLIC_KEY_PATH: str = config(
        "JWT_PUBLIC_KEY_PATH", default="keys/public_key.pem"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = config(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = config(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int
    )

    # Password Security
    PASSWORD_MIN_LENGTH: int = config("PASSWORD_MIN_LENGTH", default=5, cast=int)

    # Redis Configuration
    REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = config("REDIS_PASSWORD", default=None)
    CACHE_TTL_SECONDS: int = config("CACHE_TTL_SECONDS", default=3600, cast=int)

    # Celery Configuration
    CELERY_BROKER_URL: str = config(
        "CELERY_BROKER_URL", default="redis://localhost:6379/1"
    )
    CELERY_RESULT_BACKEND: str = config(
        "CELERY_RESULT_BACKEND", default="redis://localhost:6379/2"
    )

    # Email Configuration
    SMTP_SERVER: str = config("SMTP_SERVER")
    SMTP_PORT: int = config("SMTP_PORT", default=587, cast=int)
    SMTP_USERNAME: str = config("SMTP_USERNAME")
    SMTP_PASSWORD: str = config("SMTP_PASSWORD")
    SMTP_USE_TLS: bool = config("SMTP_USE_TLS", default=True, cast=bool)
    EMAIL_FROM: str = config("EMAIL_FROM")
    EMAIL_FROM_NAME: str = config("EMAIL_FROM_NAME", default="Banking Auth Service")

    # OTP Configuration
    OTP_EXPIRE_MINUTES: int = config("OTP_EXPIRE_MINUTES", default=5, cast=int)
    OTP_LENGTH: int = config("OTP_LENGTH", default=6, cast=int)
    OTP_MAX_ATTEMPTS: int = config("OTP_MAX_ATTEMPTS", default=3, cast=int)

    # Inter-Service Communication
    TRANSACTION_SERVICE_URL: str = config(
        "TRANSACTION_SERVICE_URL", default="http://localhost:8001"
    )
    ACCOUNT_SERVICE_URL: str = config(
        "ACCOUNT_SERVICE_URL", default="http://localhost:8002"
    )
    NOTIFICATION_SERVICE_URL: str = config(
        "NOTIFICATION_SERVICE_URL", default="http://localhost:8003"
    )

    # CORS
    ALLOWED_ORIGINS: List[str] = config("ALLOWED_ORIGINS", default="*", cast=Csv())

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is development or production."""
        if v not in ["development", "production", "testing"]:
            raise ValueError("Environment must be development, production, or testing")
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


settings = get_settings()
