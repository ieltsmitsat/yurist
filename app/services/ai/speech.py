"""Speech-to-Text (STT) service using Google Gemini."""

import logging
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechService:
    """Handles audio transcription using Google Gemini Multimodal API."""

    def __init__(self, client: Any | None = None) -> None:
        if client is not None:
            self.client = client
        else:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    @staticmethod
    def _detect_mime_type(file_path: Path) -> str:
        """Infer audio MIME type from file extension."""
        ext = file_path.suffix.lower()
        if ext in (".ogg", ".oga", ".opus"):
            return "audio/ogg"
        if ext in (".mp3", ".mpeg"):
            return "audio/mp3"
        if ext == ".wav":
            return "audio/wav"
        if ext in (".m4a", ".mp4", ".aac"):
            return "audio/mp4"
        return "audio/ogg"

    async def transcribe_audio(
        self,
        audio_path: str | Path,
        language: str = "uz",
    ) -> str:
        """Transcribe an audio file (e.g. voice memo .ogg) into text using Gemini."""
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        try:
            audio_bytes = path.read_bytes()
            mime_type = self._detect_mime_type(path)

            if language == "ru":
                prompt = (
                    "Расшифруйте эту аудиозапись в текст максимально точно. "
                    "Верните исключительно расшифрованный текст без лишних пояснений, "
                    "вступительных слов и кавычек."
                )
            else:
                prompt = (
                    "Ushbu audio yozuvni aniq matnga aylantiring (transkripsiya qiling). "
                    "Hech qanday ortiqcha izoh, kirish so'zi yoki qo'shimchasiz faqat eshitilgan matnni qaytaring."
                )

            # Check if Gemini client
            if hasattr(self.client, "aio") and hasattr(self.client.aio, "models"):
                audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

                for model_name in [
                    "gemini-3.5-transcribe",
                    settings.GEMINI_MODEL,
                    settings.GEMINI_FALLBACK_MODEL,
                ]:
                    try:
                        response = await self.client.aio.models.generate_content(
                            model=model_name,
                            contents=[audio_part, prompt],
                            config=types.GenerateContentConfig(
                                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                                    disable=True
                                ),
                            ),
                        )
                        text = (response.text or "").strip()
                        logger.info(
                            "Successfully transcribed audio file %s with %s (%d chars)",
                            path.name,
                            model_name,
                            len(text),
                        )
                        return text
                    except Exception as model_err:  # noqa: BLE001
                        logger.warning(
                            "Audio transcription failed on model %s (%s). Trying next...",
                            model_name,
                            model_err,
                        )
                        continue

                raise RuntimeError(f"All transcription models failed for audio file {path.name}")

            # Legacy OpenAI client fallback
            if hasattr(self.client, "audio") and hasattr(self.client.audio, "transcriptions"):
                file_payload = (path.name, audio_bytes)
                kwargs: dict[str, Any] = {
                    "model": settings.WHISPER_MODEL,
                    "file": file_payload,
                }
                if language in ("uz", "ru"):
                    kwargs["language"] = language
                transcript = await self.client.audio.transcriptions.create(**kwargs)
                return str(transcript.text).strip()

            raise RuntimeError("Unsupported client type for audio transcription")

        except Exception as e:
            logger.error("Failed to transcribe audio %s: %s", path.name, e)
            raise
