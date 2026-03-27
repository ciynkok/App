"""
Redis connection module.
Provides async Redis client for the application.
"""
import redis.asyncio as aioredis
from src.config.settings import settings


class RedisClient:
    """Redis client wrapper."""

    def __init__(self):
        self._client: aioredis.Redis | None = None

    @property
    def client(self) -> aioredis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get_client(self) -> aioredis.Redis:
        """Get Redis client (async)."""
        return self.client

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Global Redis client instance
redis_client = RedisClient()
