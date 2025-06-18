from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Bank Auth Service"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:4200",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/auth.db"
    DATABASE_ECHO: bool = False

    # JWT Security
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Password Hashing
    PASSWORD_HASH_ALGORITHM: str = "argon2"
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 1

    # RabbitMQ Configuration
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "auth_exchange"
    RABBITMQ_QUEUE: str = "auth_queue"
    RABBITMQ_ROUTING_KEY: str = "auth.events"

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    LOG_FILE: str = "logs/auth_service.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"

    # Persian Calendar
    USE_JALALI_CALENDAR: bool = True

    # Default Superuser
    FIRST_SUPERUSER_EMAIL: str = "sasan.gsm@gmail.com"
    FIRST_SUPERUSER_USERNAME: str = "sassan"
    FIRST_SUPERUSER_PASSWORD: str = "QAZ123"
    FIRST_SUPERUSER_FULL_NAME: str = "System Administrator"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    def _parse_cors_origins(self, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.BACKEND_CORS_ORIGINS = self._parse_cors_origins(self.BACKEND_CORS_ORIGINS)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create settings instance for backward compatibility
settings = get_settings()
