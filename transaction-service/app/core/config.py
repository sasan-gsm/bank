# app/core/config.py
from pydantic import BaseSettings, Field
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    environment: str = Field("development")
    debug: bool = Field(True)
    database_url: str = Field("sqlite+aiosqlite:///./transactions.db")

    jwt_public_key: str
    jwt_algorithm: str = Field("RS256")

    redis_host: str = Field("localhost")
    redis_port: int = Field(6379)
    redis_db: int = Field(0)
    redis_password: Optional[str]

    cache_ttl: int = Field(300)
    cache_prefix: str = Field("transaction-service")

    celery_broker_url: str = Field("redis://localhost:6379/1")
    celery_result_backend: str = Field("redis://localhost:6379/2")

    auth_service_url: str = Field("http://localhost:8000")
    notification_service_url: str = Field("http://localhost:8003")

    default_currency: str = Field("USD")
    max_transaction_amount: float = Field(1_000_000.00)
    future_transaction_max_days: int = Field(365)

    allowed_origins: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS",
        env_parser=lambda v: v.split(","),
    )

    LOG_FILE: str = Field("logs/transaction_service.log")
    LOG_LEVEL: str = Field("INFO")
    LOG_FORMAT: str = Field("{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    LOG_ROTATION: str = Field("10 MB")
    LOG_RETENTION: str = Field("30 days")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def redis_url(self) -> str:
        pwd = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{pwd}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create settings instance for backward compatibility
settings = get_settings()
