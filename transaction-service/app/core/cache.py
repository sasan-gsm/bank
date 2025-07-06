# app/core/cache.py
import json
from typing import Any, Optional
import redis.asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from app.core.config import settings


class CacheManager:
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def init_cache(self) -> aioredis.Redis:
        if not self._redis:
            self._redis = aioredis.Redis.from_url(
                settings.redis_url, decode_responses=True
            )
            FastAPICache.init(RedisBackend(self._redis), prefix=settings.cache_prefix)
        return self._redis

    async def invalidate_pattern(self, pattern: str):
        if not self._redis:
            return
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)

    async def invalidate_account(self, account_id: int):
        await self.invalidate_pattern(f"{settings.cache_prefix}:*account:{account_id}*")

    async def invalidate_balance(self, account_id: int):
        await self.invalidate_pattern(f"{settings.cache_prefix}:*balance:{account_id}*")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if not self._redis:
            return
        ttl = ttl or settings.cache_ttl
        await self._redis.setex(
            f"{settings.cache_prefix}:{key}", ttl, json.dumps(value, default=str)
        )

    async def get(self, key: str) -> Optional[Any]:
        if not self._redis:
            return None
        val = await self._redis.get(f"{settings.cache_prefix}:{key}")
        return json.loads(val) if val else None

    @property
    def redis_client(self) -> Optional[aioredis.Redis]:
        return self._redis


cache_manager = CacheManager()


def _mk_cache_decorator(prefix: str, ttl: int):
    def decorator(func):
        return cache(expire=ttl, prefix=prefix)(func)

    return decorator


cached_account_balance = _mk_cache_decorator("balance", 60)
cached_account_data = _mk_cache_decorator("account", 300)
cached_transactions = _mk_cache_decorator("transactions", 180)
