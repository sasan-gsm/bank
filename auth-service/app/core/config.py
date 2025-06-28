import os
from typing import Optional, List
from pydantic import BaseSettings, Field, EmailStr
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment-specific configuration."""

    # Environment Configuration
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # Database Configuration
    database_url: str = Field(default="sqlite+aiosqlite:///./auth.db")

    # JWT Configuration
    jwt_private_key: str
    jwt_public_key: str
    jwt_algorithm: str = Field(default="RS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)

    # Redis Configuration
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = None

    # Cache Configuration
    cache_ttl: int = Field(default=300)  # 5 minutes
    cache_prefix: str = Field(default="auth-service")

    # Email Configuration
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=587)
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = Field(default=True)

    # OTP Configuration
    otp_length: int = Field(default=6)
    otp_expire_minutes: int = Field(default=10)

    # First Superuser Configuration
    first_superuser_username: str = Field(default="admin")
    first_superuser_email: EmailStr = Field(default="admin@example.com")
    first_superuser_password: str = Field(default="admin123")
    first_superuser_full_name: str = Field(default="System Administrator")

    # Inter-service Communication
    transaction_service_url: str = Field(default="http://localhost:8001")
    account_service_url: str = Field(default="http://localhost:8002")
    notification_service_url: str = Field(default="http://localhost:8003")

    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # CORS Configuration
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )

    class Config:
        # Automatically switch between .env and .env.production
        env_file = ".env.production" if os.getenv("ENV") == "production" else ".env"
        case_sensitive = False

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of the Settings."""
    return Settings()


# Usage: import `settings` wherever you need config access
settings = get_settings()
