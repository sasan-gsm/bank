import json
import asyncio
from typing import Any, Optional, Dict
from functools import wraps

import redis.asyncio as redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from .config import settings


class RedisConfig:
    """Redis configuration embedded in cache module."""

    @staticmethod
    def get_redis_settings() -> Dict[str, Any]:
        """Get Redis connection settings."""
        return {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "password": settings.redis_password,
            "decode_responses": True,
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "health_check_interval": 30,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        }


class CacheManager:
    """Cache management with Redis backend and invalidation capabilities."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def init_cache(self) -> redis.Redis:
        """Initialize Redis backend for FastAPI cache."""
        if not self._initialized:
            async with self._lock:
                if not self._initialized:  # double check inside the lock
                    try:
                        self.redis_client = redis.Redis(
                            **RedisConfig.get_redis_settings()
                        )
                        FastAPICache.init(
                            RedisBackend(self.redis_client),
                            prefix=settings.cache_prefix,
                        )
                        self._initialized = True
                    except Exception as e:
                        print(f"[Cache Init Error]: {e}")
                        raise
        return self.redis_client

    async def _delete_by_pattern(self, pattern: str):
        """Efficiently deletes keys matching pattern using SCAN."""
        try:
            async for key in self.redis_client.scan_iter(match=pattern):
                await self.redis_client.delete(key)
        except Exception as e:
            print(f"[Cache Delete Pattern Error]: {e}")

    async def invalidate_user_cache(self, user_id: int) -> None:
        """Invalidate all user-related cache."""
        if not self.redis_client:
            return

        base = settings.cache_prefix
        patterns = [
            f"{base}:*user:{user_id}*",
            f"{base}:*permissions:{user_id}*",
            f"{base}:*roles:{user_id}*",
        ]

        for pattern in patterns:
            await self._delete_by_pattern(pattern)

    async def invalidate_permission_cache(self, user_id: int) -> None:
        """Invalidate permission cache for a specific user."""
        if self.redis_client:
            await self._delete_by_pattern(
                f"{settings.cache_prefix}:*permissions:{user_id}*"
            )

    async def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a cache value with optional TTL."""
        if not self.redis_client:
            return

        try:
            ttl = ttl or settings.cache_ttl
            await self.redis_client.setex(
                f"{settings.cache_prefix}:{key}", ttl, json.dumps(value, default=str)
            )
        except Exception as e:
            print(f"[Cache Set Error]: {e}")

    async def get_cache(self, key: str) -> Optional[Any]:
        """Retrieve a cached value."""
        if not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(f"{settings.cache_prefix}:{key}")
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"[Cache Get Error]: {e}")
        return None

    async def delete_cache(self, key: str) -> None:
        """Delete a cached key."""
        if self.redis_client:
            try:
                await self.redis_client.delete(f"{settings.cache_prefix}:{key}")
            except Exception as e:
                print(f"[Cache Delete Error]: {e}")


# Singleton instance of CacheManager
cache_manager = CacheManager()


def cached(key_prefix: str, ttl: Optional[int] = None):
    """
    Generic cache decorator with a key prefix and optional TTL.

    Example:
        @cached("user", ttl=300)
        async def get_user(user_id: int): ...
    """

    def decorator(func):
        @wraps(func)
        @cache(
            expire=ttl or settings.cache_ttl,
            key_builder=lambda *args,
            **kwargs: f"{key_prefix}:{kwargs.get('user_id', args[0])}",
        )
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator
