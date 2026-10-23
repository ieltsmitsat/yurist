"""Middleware enforcing mandatory channel and group subscription."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class MandatorySubscriptionMiddleware(BaseMiddleware):
    """Intercepts messages and callback queries to verify mandatory subscriptions."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # 1. Bypass non-message / non-callback events
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        # 2. Bypass Telegram Business interactions (client-to-lawyer private chat)
        if getattr(event, "business_connection_id", None) or data.get("is_business"):
            return await handler(event, data)

        # 3. Allow check_mandatory_sub callback to proceed directly to its handler
        if isinstance(event, CallbackQuery) and event.data == "check_mandatory_sub":
            return await handler(event, data)

        telegram_user: TelegramUser | None = data.get("event_from_user")
        if not telegram_user and isinstance(event, (Message, CallbackQuery)):
            telegram_user = event.from_user

        if not telegram_user:
            return await handler(event, data)

        # 4. Bypass lawyers and admins
        user: User | None = data.get("user")
        if user:
            from app.services.user_service import UserService

            if UserService.is_lawyer(user) or user.lead_status == "lawyer":
                return await handler(event, data)

        session: AsyncSession | None = data.get("session")
        bot: Bot | None = data.get("bot")

        if not session or not bot:
            return await handler(event, data)

        # 5. Check subscriptions
        is_subscribed, unsubscribed = await SubscriptionService.check_user_subscribed_all(
            bot=bot,
            user_id=telegram_user.id,
            session=session,
            bypass_cache=False,
        )

        if is_subscribed:
            return await handler(event, data)

        # 6. User is NOT subscribed - prompt user and stop execution
        lang = user.language if user else (telegram_user.language_code or "uz")
        if lang not in ("uz", "ru"):
            lang = "uz"

        msg_text = SubscriptionService.build_subscription_message(unsubscribed, lang)
        kb = SubscriptionService.build_subscription_keyboard(unsubscribed, lang)

        if isinstance(event, Message):
            await event.answer(msg_text, reply_markup=kb, disable_web_page_preview=True)
        elif isinstance(event, CallbackQuery):
            await event.answer()
            if event.message and isinstance(event.message, Message):
                await event.message.answer(
                    msg_text, reply_markup=kb, disable_web_page_preview=True
                )

        return None
