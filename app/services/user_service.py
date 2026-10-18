"""User management service (Onboarding, Language, Lead Status, Freemium Questions)."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.user import User
from app.services.access_service import AccessService

logger = logging.getLogger(__name__)


class UserService:
    """Handles user registration, phone capture, and questions balance."""

    @classmethod
    async def get_by_telegram_id(cls, session: AsyncSession, telegram_id: int) -> User | None:
        """Fetch user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_or_create_user(
        cls,
        session: AsyncSession,
        telegram_id: int,
        full_name: str | None = None,
        language: str = "uz",
        referred_by_code: str | None = None,
    ) -> tuple[User, bool]:
        """Get existing user or create a new lead."""
        user = await cls.get_by_telegram_id(session, telegram_id)
        if user:
            # Dynamically synchronize lawyer status if user is added/activated as lawyer
            is_lawyer_account = await AccessService.is_lawyer(session, telegram_id)
            if is_lawyer_account and (
                user.lead_status != "lawyer"
                or not user.is_subscribed
                or user.free_questions_left < 999999
            ):
                user.lead_status = "lawyer"
                user.is_subscribed = True
                user.free_questions_left = 999999
                await session.commit()
                await session.refresh(user)

            # Attribute referral if user has no referrer and valid code supplied
            if (
                referred_by_code
                and not user.referred_by_id
                and referred_by_code != f"ref_{telegram_id}"
            ):
                stmt = select(User.id).where(User.referral_code == referred_by_code)
                res = await session.execute(stmt)
                referrer_id = res.scalar_one_or_none()
                if referrer_id and referrer_id != user.id:
                    user.referred_by_id = referrer_id
                    await session.commit()
                    await session.refresh(user)
                    logger.info(
                        "Attributed referral to existing user %d -> referrer %d",
                        user.id,
                        referrer_id,
                    )
            return user, False

        # Handle referral attribution (anti-fraud: prevent self-referral)
        referred_by_id = None
        if referred_by_code and referred_by_code != f"ref_{telegram_id}":
            stmt = select(User.id).where(User.referral_code == referred_by_code)
            res = await session.execute(stmt)
            referred_by_id = res.scalar_one_or_none()

        is_lawyer_account = await AccessService.is_lawyer(session, telegram_id)
        referral_code = f"ref_{telegram_id}"

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            language=language,
            lead_status="lawyer" if is_lawyer_account else "new",
            referred_by_id=referred_by_id,
            referral_code=referral_code,
            free_questions_left=999999 if is_lawyer_account else settings.FREE_QUESTIONS_LIMIT,
            is_subscribed=is_lawyer_account,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("Created new user: id=%d, telegram_id=%d", user.id, user.telegram_id)
        return user, True

    @classmethod
    async def update_language(
        cls, session: AsyncSession, telegram_id: int, language: str
    ) -> User | None:
        """Update user interface and communication language."""
        user = await cls.get_by_telegram_id(session, telegram_id)
        if user:
            user.language = language
            await session.commit()
            await session.refresh(user)
        return user

    @classmethod
    def normalize_phone_number(cls, raw: str) -> str | None:
        """Clean, format, and validate phone number into E.164 format.

        Supports Uzbek (+998...) and international formats.
        Returns normalized string like '+998901234567' or None if invalid.
        """
        import re

        digits = re.sub(r"[^\d+]", "", raw.strip())
        if not digits:
            return None

        if digits.startswith("+"):
            clean = "+" + re.sub(r"\D", "", digits[1:])
        else:
            clean = re.sub(r"\D", "", digits)
            if len(clean) == 9:  # e.g. 901234567 -> +998901234567
                clean = "+998" + clean
            elif len(clean) == 12 and clean.startswith("998"):
                clean = "+" + clean
            elif len(clean) == 11 and clean.startswith("8"):  # e.g. 8926... -> +7926...
                clean = "+7" + clean[1:]
            else:
                clean = "+" + clean

        # Validate E.164: + followed by 8 to 15 digits
        if re.match(r"^\+[1-9]\d{7,14}$", clean):
            return clean
        return None

    @classmethod
    async def update_phone(
        cls, session: AsyncSession, telegram_id: int, phone_number: str
    ) -> User | None:
        """Capture phone number (hard gate verification) and mark lead as verified."""
        user = await cls.get_by_telegram_id(session, telegram_id)
        if user:
            normalized = cls.normalize_phone_number(phone_number) or phone_number
            user.phone_number = normalized
            if user.lead_status == "new":
                user.lead_status = "verified_lead"
            await session.commit()
            await session.refresh(user)
            logger.info("Verified phone for user %d: %s", user.id, normalized)
        return user

    @classmethod
    def is_lawyer(cls, user: User) -> bool:
        """Check if user is a designated lawyer / administrator."""
        free_q = getattr(user, "free_questions_left", 0)
        has_infinite = isinstance(free_q, int) and free_q >= 999999
        is_sub = getattr(user, "is_subscribed", False) is True
        return bool(
            user.lead_status == "lawyer"
            or (is_sub and has_infinite)
            or (settings.LAWYER_TELEGRAM_ID and user.telegram_id == settings.LAWYER_TELEGRAM_ID)
        )

    @classmethod
    async def has_questions_available(
        cls, user: User, session: AsyncSession | None = None
    ) -> bool:
        """Check if user has remaining free inquiries or an active subscription."""
        if cls.is_lawyer(user) or user.is_subscribed:
            return True
        if session and await AccessService.is_lawyer(session, user.telegram_id):
            await cls.sync_lawyer_status(session, user.telegram_id, is_active_lawyer=True)
            return True
        return user.free_questions_left > 0

    @classmethod
    async def decrement_question(cls, session: AsyncSession, user: User) -> int:
        """Deduct one question from balance if not subscribed and not lawyer."""
        if (
            cls.is_lawyer(user)
            or user.is_subscribed
            or await AccessService.is_lawyer(session, user.telegram_id)
        ):
            return user.free_questions_left
        if user.free_questions_left > 0:
            user.free_questions_left -= 1
            await session.commit()
            await session.refresh(user)
        return user.free_questions_left

    @classmethod
    async def sync_lawyer_status(
        cls, session: AsyncSession, telegram_id: int, is_active_lawyer: bool
    ) -> User | None:
        """Synchronize lawyer status and unlimited questions across User records."""
        user = await cls.get_by_telegram_id(session, telegram_id)
        if not user:
            return None

        if is_active_lawyer:
            user.lead_status = "lawyer"
            user.is_subscribed = True
            user.free_questions_left = 999999
            logger.info("Promoted user %d (TG %d) to lawyer with unlimited questions", user.id, user.telegram_id)
        elif user.lead_status == "lawyer":
            user.lead_status = "verified_lead" if user.phone_number else "new"
            user.is_subscribed = False
            if user.free_questions_left >= 999999:
                user.free_questions_left = settings.FREE_QUESTIONS_LIMIT
            logger.info("Demoted user %d (TG %d) from lawyer status", user.id, user.telegram_id)

        await session.commit()
        await session.refresh(user)
        return user

    @classmethod
    async def add_questions(cls, session: AsyncSession, user_id: int, count: int) -> User | None:
        """Add free question credits (e.g. from referral rewards)."""
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            user.free_questions_left += count
            await session.commit()
            await session.refresh(user)
            logger.info(
                "Added %d questions to user %d (new balance: %d)",
                count,
                user.id,
                user.free_questions_left,
            )
        return user
