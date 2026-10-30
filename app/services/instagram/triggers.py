"""Skill 10: Advanced Triggers Skill (Story Mentions, Story Replies, Click-to-Direct Ads).

Detects and handles Instagram Stories interactions and Meta Click-to-Direct Ad referrals.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StoryAndAdsTriggerSkill:
    """Processes Instagram Story Mentions, Story Replies, and Click-to-Direct Ad Referrals."""

    STORY_MENTION_GREETING = (
        "Assalomu alaykum! Sahifamizni Stories'da belgilaganingiz uchun tashakkur! "
        "Professional huquqiy yordam yoki advokat konsultatsiyasi kerak bo'lsa, "
        "qanday masalada yordam bera olamiz?"
    )

    AD_REFERRAL_GREETING_TEMPLATE = (
        "Assalomu alaykum! Reklamamiz orqali murojaat qilganingiz uchun tashakkur! "
        "Sizga tezkor va aniq huquqiy yordam berishimiz uchun qanday yuridik muammo "
        "yoki savol yuzasidan murojaat qilayotganingizni yozib qoldiring."
    )

    @classmethod
    def is_story_mention(cls, message_data: dict[str, Any]) -> bool:
        """Check if incoming message is an Instagram Story Mention."""
        # Meta sends story mentions inside message attachments or story_mention field
        attachments = message_data.get("attachments") or []
        for att in attachments:
            if att.get("type") in ("story_mention", "story_share"):
                return True
        return bool(message_data.get("story_mention"))

    @classmethod
    def is_story_reply(cls, message_data: dict[str, Any]) -> bool:
        """Check if incoming message is a reply to an Instagram Story."""
        reply_to = message_data.get("reply_to") or {}
        return bool(reply_to.get("story") or message_data.get("story_reply"))

    @classmethod
    def extract_ad_referral(
        cls,
        message_data: dict[str, Any],
        event_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Extract Click-to-Direct Ad referral details if user originated from an Ad."""
        # Meta sends referral either under message.referral or event.referral
        referral = message_data.get("referral")
        if not referral and event_data:
            referral = event_data.get("referral")

        if isinstance(referral, dict) and referral.get("source") in ("ADS", "ad", "ads"):
            return {
                "ad_id": str(referral.get("ad_id") or ""),
                "source": "ADS",
                "ref": str(referral.get("ref") or ""),
                "ad_title": str(referral.get("ad_title") or ""),
            }
        return None

    @classmethod
    def get_story_mention_response(cls) -> str:
        """Return standardized warm greeting for Story mentions."""
        return cls.STORY_MENTION_GREETING

    @classmethod
    def get_ad_referral_greeting(cls, ad_title: str | None = None) -> str:
        """Return personalized greeting for users arriving via Click-to-Direct Ads."""
        if ad_title:
            return (
                f"Assalomu alaykum! '{ad_title}' reklamamiz orqali murojaat qilganingiz uchun tashakkur! "
                "Sizga aniq huquqiy yechim berishimiz uchun vaziyatingizni qisqacha yozib qoldiring."
            )
        return cls.AD_REFERRAL_GREETING_TEMPLATE
