"""Viral Referral Program service (Anti-fraud reward attribution and stats)."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User

logger = logging.getLogger(__name__)


class ReferralService:
    """Handles deep-linking referrals, reward delivery upon phone verification, and stats."""

    @classmethod
    def get_referral_link(cls, bot_username: str, user: User) -> str:
        """Generate deep-link referral URL for a user."""
        code = user.referral_code or f"ref_{user.telegram_id}"
        return f"https://t.me/{bot_username}?start={code}"

    @classmethod
    async def process_referral_reward(
        cls,
        session: AsyncSession,
        new_user: User,
    ) -> tuple[int, str] | None:
        """Grant reward (+1 question) to referrer when new_user verifies phone number.

        Returns (referrer_telegram_id, referrer_language) if reward was granted, else None.
        Anti-fraud: Requires verified phone_number and prevents double claiming.
        """
        if not new_user.referred_by_id or not new_user.phone_number:
            return None

        # Prevent double claiming
        if new_user.lead_status == "rewarded_referral":
            return None

        # Anti-fraud: Verify phone number was not previously registered by another user
        stmt_dup = (
            select(User.id)
            .where(User.phone_number == new_user.phone_number)
            .where(User.id != new_user.id)
        )
        res_dup = await session.execute(stmt_dup)
        if res_dup.scalar_one_or_none() is not None:
            logger.warning(
                "Phone %s already exists in database. Withholding referral bonus for lead %d",
                new_user.phone_number,
                new_user.id,
            )
            return None

        # Fetch referrer
        stmt = select(User).where(User.id == new_user.referred_by_id)
        res = await session.execute(stmt)
        referrer = res.scalar_one_or_none()

        if not referrer:
            return None

        bonus = settings.REFERRAL_BONUS_QUESTIONS
        referrer.free_questions_left += bonus
        new_user.lead_status = "rewarded_referral"

        await session.commit()
        await session.refresh(referrer)
        await session.refresh(new_user)

        logger.info(
            "Granted referral bonus (+%d questions) to user %d for verified lead %d",
            bonus,
            referrer.id,
            new_user.id,
        )
        return referrer.telegram_id, referrer.language

    @classmethod
    async def get_referral_stats(
        cls,
        session: AsyncSession,
        user: User,
    ) -> dict[str, int]:
        """Get total referred friends count and verified leads count."""
        # Total invited
        stmt_total = select(func.count(User.id)).where(User.referred_by_id == user.id)
        res_total = await session.execute(stmt_total)
        total_invited = res_total.scalar_one() or 0

        # Verified (shared phone number)
        stmt_verified = (
            select(func.count(User.id))
            .where(User.referred_by_id == user.id)
            .where(User.phone_number.is_not(None))
        )
        res_verified = await session.execute(stmt_verified)
        verified_count = res_verified.scalar_one() or 0

        return {
            "total_invited": total_invited,
            "verified_count": verified_count,
            "bonus_earned": verified_count * settings.REFERRAL_BONUS_QUESTIONS,
        }
