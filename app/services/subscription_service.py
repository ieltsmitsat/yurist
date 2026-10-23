"""Mandatory channel and group subscription verification service."""

import logging
from collections.abc import Sequence

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.models.mandatory_channel import MandatoryChannel

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 300  # 5 minutes cache for verified subscriptions


class SubscriptionService:
    """Manages channel subscription checks and prompt UI."""

    @staticmethod
    async def get_active_channels(session: AsyncSession) -> Sequence[MandatoryChannel]:
        """Fetch all active mandatory subscription channels and groups."""
        stmt = (
            select(MandatoryChannel)
            .where(MandatoryChannel.is_active.is_(True))
            .order_by(MandatoryChannel.order.asc(), MandatoryChannel.id.asc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def check_user_subscribed_all(
        bot: Bot,
        user_id: int,
        session: AsyncSession,
        bypass_cache: bool = False,
    ) -> tuple[bool, list[MandatoryChannel]]:
        """Verify whether a Telegram user is a member of all active mandatory channels.

        Returns (is_all_subscribed, list_of_unsubscribed_channels).
        """
        active_channels = await SubscriptionService.get_active_channels(session)
        if not active_channels:
            return True, []

        redis = await get_redis_client()
        cache_key = f"user_sub_ok:{user_id}"

        if not bypass_cache and redis:
            try:
                cached = await redis.get(cache_key)
                if cached == "1":
                    return True, []
            except Exception as e:  # noqa: BLE001
                logger.debug("Redis cache check error: %s", e)

        unsubscribed: list[MandatoryChannel] = []

        for ch in active_channels:
            chat_identifier = ch.chat_id.strip()
            # If chat_id is stored as numeric string e.g. -100123..., cast to int
            chat_target: int | str = chat_identifier
            if (
                chat_identifier.startswith("-") or chat_identifier.isdigit()
            ) and chat_identifier.lstrip("-").isdigit():
                chat_target = int(chat_identifier)

            try:
                member = await bot.get_chat_member(chat_id=chat_target, user_id=user_id)
                # Valid member statuses
                if member.status in (
                    ChatMemberStatus.CREATOR,
                    ChatMemberStatus.ADMINISTRATOR,
                    ChatMemberStatus.MEMBER,
                    ChatMemberStatus.RESTRICTED,
                ):
                    continue

                # Status is 'left', 'kicked', etc.
                unsubscribed.append(ch)

            except TelegramAPIError as e:
                # If bot is not in the channel or lacks rights, log warning and do NOT lock out user
                logger.warning(
                    "Cannot verify membership for chat %s (user %d): %s",
                    ch.chat_id,
                    user_id,
                    e,
                )
                continue
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Unexpected error checking chat %s (user %d): %s",
                    ch.chat_id,
                    user_id,
                    e,
                )
                continue

        if not unsubscribed:
            if redis:
                try:
                    await redis.set(cache_key, "1", ex=CACHE_TTL_SECONDS)
                except Exception as e:  # noqa: BLE001
                    logger.debug("Redis cache set error: %s", e)
            return True, []

        if redis:
            try:
                await redis.delete(cache_key)
            except Exception as e:  # noqa: BLE001
                logger.debug("Redis cache delete error: %s", e)

        return False, unsubscribed

    @staticmethod
    def build_subscription_keyboard(
        unsubscribed: list[MandatoryChannel],
        lang: str = "uz",
    ) -> InlineKeyboardMarkup:
        """Build inline keyboard linking to unsubscribed channels and check button."""
        buttons: list[list[InlineKeyboardButton]] = []

        for ch in unsubscribed:
            btn_text = f"📢 {ch.title}"
            buttons.append([InlineKeyboardButton(text=btn_text, url=ch.url)])

        check_btn_text = (
            "✅ Obunani tekshirish" if lang == "uz" else "✅ Проверить подписку"
        )
        buttons.append(
            [InlineKeyboardButton(text=check_btn_text, callback_data="check_mandatory_sub")]
        )

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def build_subscription_message(
        unsubscribed: list[MandatoryChannel],
        lang: str = "uz",
    ) -> str:
        """Build instructional message requiring users to subscribe to channels."""
        if lang == "ru":
            lines = [
                "📢 <b>Уважаемый пользователь!</b>\n",
                "Для полноценного использования бота и получения юридической помощи, пожалуйста, подпишитесь на наши официальные каналы и группы:\n",
            ]
            for idx, ch in enumerate(unsubscribed, start=1):
                lines.append(f"{idx}. <a href=\"{ch.url}\">{ch.title}</a>")
            lines.append(
                "\nПосле подписки нажмите кнопку <b>«✅ Проверить подписку»</b> ниже!"
            )
            return "\n".join(lines)

        lines = [
            "📢 <b>Hurmatli foydalanuvchi!</b>\n",
            "Botdan to'liq foydalanish va professional huquqiy yordam olish uchun quyidagi rasmiy kanal va guruhlarimizga a'zo bo'lishingiz lozim:\n",
        ]
        for idx, ch in enumerate(unsubscribed, start=1):
            lines.append(f"{idx}. <a href=\"{ch.url}\">{ch.title}</a>")
        lines.append(
            "\nObuna bo'lgach, pastdagi <b>«✅ Obunani tekshirish»</b> tugmasini bosing!"
        )
        return "\n".join(lines)
