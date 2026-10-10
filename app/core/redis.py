"""Redis client and business pause state management."""

import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class InMemoryRedisClient:
    """Lightweight in-memory Redis-compatible store for local development."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._expires: dict[str, float] = {}

    async def get(self, key: str) -> str | None:
        import time

        now = time.time()
        if key in self._expires and self._expires[key] < now:
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return None
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        import time

        self._data[key] = value
        if ex:
            self._expires[key] = time.time() + ex
        return True

    async def delete(self, key: str) -> int:
        existed = key in self._data
        self._data.pop(key, None)
        self._expires.pop(key, None)
        return 1 if existed else 0

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._data.clear()
        self._expires.clear()


# Global redis connection
_redis_client: Any = None


async def get_redis_client() -> Any:
    """Get or create async Redis client with automatic local in-memory fallback."""
    global _redis_client
    if _redis_client is None:
        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            # Test connectivity with ping
            await client.ping()
            _redis_client = client
            logger.info("Connected to Redis server at: %s", settings.REDIS_URL)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Redis server not accessible at %s (%s). Using local in-memory fallback.",
                settings.REDIS_URL,
                e,
            )
            _redis_client = InMemoryRedisClient()
    return _redis_client


async def close_redis_client() -> None:
    """Close async Redis client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class BusinessPauseManager:
    """Manages lawyer takeover 30-minute pause state per chat in Telegram Business."""

    PAUSE_KEY_PREFIX = "business_pause"

    @classmethod
    def _make_key(cls, chat_id: int) -> str:
        return f"{cls.PAUSE_KEY_PREFIX}:{chat_id}"

    @classmethod
    async def set_paused(
        cls,
        chat_id: int,
        redis_client: Any,
        duration_seconds: int = settings.BUSINESS_TAKEOVER_PAUSE_SECONDS,
    ) -> None:
        """Pause AI responses for a chat for specified duration (default 30 mins)."""
        key = cls._make_key(chat_id)
        await redis_client.set(key, "1", ex=duration_seconds)
        logger.info(
            "Paused AI response for chat %d for %d seconds due to lawyer manual takeover",
            chat_id,
            duration_seconds,
        )

    @classmethod
    async def is_paused(cls, chat_id: int, redis_client: Any) -> bool:
        """Check if AI response is currently paused for this chat."""
        key = cls._make_key(chat_id)
        val = await redis_client.get(key)
        return val is not None

    @classmethod
    async def resume(cls, chat_id: int, redis_client: Any) -> None:
        """Manually unpause AI responses for a chat."""
        key = cls._make_key(chat_id)
        await redis_client.delete(key)
        logger.info("Resumed AI response for chat %d", chat_id)
