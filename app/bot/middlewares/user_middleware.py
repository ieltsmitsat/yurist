"""User context middleware for Aiogram handlers."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService


class UserContextMiddleware(BaseMiddleware):
    """Fetches and injects current User object into data['user']."""

    @staticmethod
    def _extract_telegram_user(event: TelegramObject, data: dict[str, Any]) -> TelegramUser | None:
        """Extract Telegram User object from Aiogram event context or event hierarchy."""
        # 1. Check Aiogram context first (injected by built-in UserContextMiddleware)
        event_from_user = data.get("event_from_user")
        if isinstance(event_from_user, TelegramUser):
            return event_from_user

        # 2. Check direct event attributes
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            return event.from_user

        # 3. Check Update wrapper attributes
        if isinstance(event, Update):
            for attr in ("message", "callback_query", "business_message", "edited_message"):
                sub_event = getattr(event, attr, None)
                if sub_event:
                    u = getattr(sub_event, "from_user", None)
                    if isinstance(u, TelegramUser):
                        return u

        return None

    @staticmethod
    def _extract_start_payload(event: TelegramObject) -> str | None:
        """Extract /start payload (e.g. ref_123456) from Message or Update event."""
        text = None
        if isinstance(event, Message) and event.text:
            text = event.text
        elif isinstance(event, Update) and event.message and event.message.text:
            text = event.message.text

        if text and text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1:
                return parts[1].strip()
        return None

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_user = self._extract_telegram_user(event, data)
        session: AsyncSession | None = data.get("session")

        if telegram_user and session:
            payload = self._extract_start_payload(event)
            referred_by_code = None
            if payload and payload != f"ref_{telegram_user.id}":
                referred_by_code = payload

            user, _ = await UserService.get_or_create_user(
                session=session,
                telegram_id=telegram_user.id,
                full_name=telegram_user.full_name or telegram_user.username or "Mijoz",
                referred_by_code=referred_by_code,
            )
            data["user"] = user

        return await handler(event, data)
