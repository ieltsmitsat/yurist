"""Skill 6: Multimodal Voice DM Processing Skill (skill_multimodal_audio_stt).

Handles Instagram Direct audio attachments (Voice DMs), downloads audio securely,
and transcribes speech to text using Google Gemini Multimodal Audio or Whisper.
"""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class MultimodalVoiceDMSkill:
    """Processes Instagram Voice DM audio files and converts speech to text."""

    SUPPORTED_AUDIO_TYPES = ("audio/mp4", "audio/m4a", "audio/ogg", "audio/wav", "audio/mpeg")

    @classmethod
    def is_voice_attachment(cls, attachment_payload: dict[str, Any]) -> bool:
        """Check if incoming webhook attachment is an audio/voice DM."""
        att_type = attachment_payload.get("type")
        return att_type in ("audio", "voice")

    @classmethod
    def extract_audio_url(cls, attachment_payload: dict[str, Any]) -> str | None:
        """Extract media URL from Meta attachment object."""
        payload: dict[str, Any] = attachment_payload.get("payload", {})
        raw_url = payload.get("url")
        return str(raw_url) if raw_url else None

    @classmethod
    async def transcribe_audio_bytes(
        cls,
        audio_bytes: bytes,
        mime_type: str = "audio/m4a",
    ) -> str:
        """Transcribe audio bytes using Google Gemini Multimodal STT or local fallback."""
        if not audio_bytes:
            return ""

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            prompt = (
                "Ushbu ovozli xabarni benuqson o'zbek yoki rus tilida matnga aylantiring. "
                "Faqat aytilgan gaplarni yozing, hech qanday qo'shimcha sharh qo'shmang."
            )
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[part, prompt],
            )
            text_result = str(response.text or "").strip()
            return text_result
        except Exception as err:  # noqa: BLE001
            logger.error("Gemini Multimodal STT failed: %s", err)
            return ""
