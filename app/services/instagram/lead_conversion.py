"""Skill 9: Lead Qualification & High-Ticket Conversion Skill (skill_lead_conversion).

Tracks freemium limit (3 free questions), evaluates Qualified Leads,
and triggers high-ticket consultation upsells and payment checkout links.
"""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class LeadConversionSkill:
    """Manages free question limits and high-ticket service conversion funnels."""

    UPSELL_EXHAUSTED_LIMIT_UZ = (
        "Hurmatli mijoz! Sizga taqdim etilgan 3 ta bepul dastlabki yuridik tahlil "
        "yakunlandi. Masalangizni to'liq hal qilish va sizga xos individual strategiya "
        "ishlab chiqish uchun quyidagi xizmatlardan birini tanlashingiz mumkin:\n"
        "1. 🏢 Advokat bilan shaxsiy qabulda ko'rishish (Ofisda konsultatsiya)\n"
        "2. 📄 Shartnoma yoki hujjatlarning to'liq yuridik ekspertizasi\n"
        "3. ⚖️ Sudda professional vakillik va da'vo arizasi tayyorlash\n\n"
        "To'lovni amalga oshirish va qabulga yozilish uchun 'To'lov' deb yozing."
    )

    UPSELL_EXHAUSTED_LIMIT_RU = (
        "Уважаемый клиент! Ваш лимит из 3 бесплатных вводных консультаций исчерпан. "
        "Для детального ведения вашего дела и подготовки правовой позиции вы можете "
        "воспользоваться следующими услугами:\n"
        "1. 🏢 Очная консультация в офисе адвоката\n"
        "2. 📄 Правовая экспертиза договоров и документов\n"
        "3. ⚖️ Представительство в суде и составление искового заявления\n\n"
        "Чтобы записаться и произвести оплату, напишите 'Оплата'."
    )

    @classmethod
    async def get_remaining_free_questions(
        cls,
        ig_user_id: str,
        redis_client: Any | None = None,
        default_limit: int = settings.FREE_QUESTIONS_LIMIT,
    ) -> int:
        """Get number of free questions left for this Instagram user."""
        if redis_client is None:
            return default_limit

        key = f"ig_free_questions:{ig_user_id}"
        val = await redis_client.get(key)
        if val is None:
            # Initialize with default limit
            await redis_client.set(key, str(default_limit), ex=86400 * 30)
            return default_limit

        try:
            return max(0, int(val))
        except ValueError:
            return 0

    @classmethod
    async def decrement_free_question(
        cls,
        ig_user_id: str,
        redis_client: Any | None = None,
    ) -> int:
        """Decrement free question balance and return updated count."""
        current = await cls.get_remaining_free_questions(ig_user_id, redis_client)
        new_count = max(0, current - 1)
        if redis_client is not None:
            key = f"ig_free_questions:{ig_user_id}"
            await redis_client.set(key, str(new_count), ex=86400 * 30)
        return new_count

    @classmethod
    def is_lead_qualified(
        cls,
        has_phone: bool,
        risk_score: int,
        interactions_count: int,
    ) -> bool:
        """Determine if client qualifies as a warm/hot lead for direct lawyer outreach."""
        # A lead is qualified if they provided their phone and have medium/high/critical risk
        if has_phone and risk_score >= 35:
            return True
        # Or engaged actively with high risk
        return bool(interactions_count >= 2 and risk_score >= 60)

    @classmethod
    def get_exhausted_limit_message(cls, is_russian: bool = False) -> str:
        """Return upsell message when free questions are exhausted."""
        if is_russian:
            return cls.UPSELL_EXHAUSTED_LIMIT_RU
        return cls.UPSELL_EXHAUSTED_LIMIT_UZ
