"""Skill 2: 24-Hour Window & Contact Capture Skill (skill_24h_contact_capture).

Monitors Meta's 24-hour standard messaging window, tracks last inbound message timestamp,
prompts for client name and phone number during initial inquiries, and validates Uzbekistan
phone numbers for CRM storage.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class ContactCapture24hSkill:
    """Manages the 24-hour standard messaging window and lead contact extraction."""

    # Uzbekistan phone regex: supports +998901234567, 998901234567, 901234567 with optional spaces/dashes
    UZ_PHONE_REGEX = re.compile(
        r"(?:\+?998)?[\s\-]?(9[012345789]|33|88|77)[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})\b"
    )

    CONTACT_REQUEST_PROMPT = (
        "Hurmatli mijoz, vaziyatingiz bo'yicha aniqroq yordam berishimiz uchun "
        "ismingiz va bog'lanish uchun telefon raqamingizni qoldiring."
    )

    WINDOW_EXPIRING_WARNING = (
        "Hurmatli mijoz! Instagram Direct'dagi 24 soatlik bepul muloqot oynasi "
        "yaqin 2 soat ichida yakunlanadi. Qo'shimcha savollaringiz yoki advokat "
        "konsultatsiyasi bo'yicha masalangiz bo'lsa, xabaringizni yozib qoldiring."
    )

    WINDOW_SECONDS = 86400  # 24 hours
    WARNING_THRESHOLD_HOURS = 22.0

    @classmethod
    def get_current_utc_timestamp(cls) -> float:
        """Return current UTC epoch timestamp."""
        return datetime.now(UTC).timestamp()

    @classmethod
    def is_window_active(cls, last_inbound_timestamp: float) -> bool:
        """Check if 24-hour messaging window is currently open."""
        if not last_inbound_timestamp or last_inbound_timestamp <= 0:
            return False
        elapsed = cls.get_current_utc_timestamp() - last_inbound_timestamp
        return 0 <= elapsed <= cls.WINDOW_SECONDS

    @classmethod
    def should_send_closing_warning(
        cls,
        last_inbound_timestamp: float,
        warning_already_sent: bool = False,
    ) -> bool:
        """Determine if 2-hour closing warning should be dispatched."""
        if warning_already_sent or not cls.is_window_active(last_inbound_timestamp):
            return False
        elapsed_hours = (cls.get_current_utc_timestamp() - last_inbound_timestamp) / 3600.0
        return cls.WARNING_THRESHOLD_HOURS <= elapsed_hours < 24.0

    @classmethod
    def should_request_contact(
        cls,
        interaction_count: int,
        has_phone: bool,
    ) -> bool:
        """Prompt for contact during the first 3 interactions if phone is missing."""
        return not has_phone and interaction_count <= 3

    @classmethod
    def extract_uz_phone(cls, text: str) -> str | None:
        """Extract and normalize Uzbekistan phone number to +998XXXXXXXXX format."""
        if not text or not isinstance(text, str):
            return None

        match = cls.UZ_PHONE_REGEX.search(text)
        if match:
            operator_code, part1, part2, part3 = match.groups()
            return f"+998{operator_code}{part1}{part2}{part3}"
        return None

    @classmethod
    async def update_inbound_activity(
        cls,
        ig_user_id: str,
        redis_client: Any | None = None,
    ) -> float:
        """Update last inbound timestamp in cache and return current epoch."""
        now = cls.get_current_utc_timestamp()
        if redis_client is not None:
            key = f"ig_user_last_inbound:{ig_user_id}"
            await redis_client.set(key, str(now), ex=cls.WINDOW_SECONDS * 7)
        return now

    @classmethod
    async def get_last_inbound_timestamp(
        cls,
        ig_user_id: str,
        redis_client: Any | None = None,
    ) -> float:
        """Retrieve last inbound message timestamp from cache."""
        if redis_client is not None:
            key = f"ig_user_last_inbound:{ig_user_id}"
            val = await redis_client.get(key)
            if val:
                try:
                    return float(val)
                except ValueError:
                    return 0.0
        return 0.0
