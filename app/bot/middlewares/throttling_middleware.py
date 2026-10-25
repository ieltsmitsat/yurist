"""Rate limiting and throttling middleware for Telegram Bot events."""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Rate-limits incoming Telegram messages to protect AI inference quota and DB pools."""

    def __init__(self, rate_limit_seconds: float = 1.5) -> None:
        super().__init__()
        self.rate_limit_seconds = rate_limit_seconds
        # In-memory fallback if Redis is unavailable
        self._memory_cache: dict[int, float] = {}
        self._warned_users: dict[int, float] = {}

    def _is_exempt(self, user_id: int) -> bool:
        """Check if user is exempt from throttling (admins, lawyers)."""
        if settings.LAWYER_TELEGRAM_ID and user_id == settings.LAWYER_TELEGRAM_ID:
            return True
        if settings.ADMIN_TELEGRAM_IDS:
            admin_ids = [
                int(x.strip()) for x in settings.ADMIN_TELEGRAM_IDS.split(",") if x.strip().isdigit()
            ]
            if user_id in admin_ids:
                return True
        return False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        if not from_user:
            return await handler(event, data)

        # Only throttle private chats with users
        chat = getattr(event, "chat", None)
        chat_type = getattr(chat, "type", "private") if chat else "private"
        if chat_type != "private":
            return await handler(event, data)

        user_id = from_user.id
        if self._is_exempt(user_id):
            return await handler(event, data)

        now = time.monotonic()
        throttled = False

        # 1. Try Redis first
        try:
            redis = await get_redis_client()
            key = f"throttle:{user_id}"
            is_locked = await redis.get(key)
            if is_locked:
                throttled = True
            else:
                await redis.set(key, "1", ex=int(self.rate_limit_seconds) or 1)
        except Exception:  # noqa: BLE001
            # Fallback to local in-memory dict
            last_time = self._memory_cache.get(user_id, 0.0)
            if now - last_time < self.rate_limit_seconds:
                throttled = True
            self._memory_cache[user_id] = now

        if throttled:
            logger.info("Throttled rapid message from user %d", user_id)
            # Only send warning if not warned in last 5 seconds to prevent spamming
            last_warn = self._warned_users.get(user_id, 0.0)
            if now - last_warn > 5.0:
                self._warned_users[user_id] = now
                try:
                    answer_fn = getattr(event, "answer", None)
                    if callable(answer_fn):
                        await answer_fn(
                            "⏳ <b>Iltimos, shoshilmang!</b>\n"
                            "Oldingi savolingiz qayta ishlanmoqda. Bir oz kuting...",
                            parse_mode="HTML",
                        )
                except Exception as warn_err:  # noqa: BLE001
                    logger.debug("Failed to send throttle notice: %s", warn_err)
            return None

        return await handler(event, data)
