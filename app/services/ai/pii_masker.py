"""Local PII (Personally Identifiable Information) Redaction Service."""

import re


class PIIMasker:
    """Sanitizes sensitive personal data prior to LLM submission (OWASP & Security Rules)."""

    # Credit cards (16 digits with optional spaces or dashes)
    CARD_REGEX = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")

    # PINFL / JShShIR (14 digits starting with 1-6)
    PINFL_REGEX = re.compile(r"\b[1-6]\d{13}\b")

    # Uzbek Passport (Series 2 letters + 7 digits)
    PASSPORT_REGEX = re.compile(r"\b[A-Za-z]{2}\s?\d{7}\b")

    # Phone numbers (Uzbekistan formats)
    PHONE_REGEX = re.compile(
        r"(\+?998[\s.-]?)?\(?\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}\b"
    )

    @classmethod
    def redact(cls, text: str) -> str:
        """Mask passport, phone, PINFL, and card numbers with redaction placeholders."""
        if not text:
            return ""

        # 1. Cards
        sanitized = cls.CARD_REGEX.sub("[CARD_REDACTED]", text)
        # 2. PINFL
        sanitized = cls.PINFL_REGEX.sub("[PINFL_REDACTED]", sanitized)
        # 3. Passport
        sanitized = cls.PASSPORT_REGEX.sub("[PASSPORT_REDACTED]", sanitized)
        # 4. Phone numbers
        sanitized = cls.PHONE_REGEX.sub("[PHONE_REDACTED]", sanitized)

        return sanitized

    @classmethod
    def redact_financial(cls, text: str) -> str:
        """Redact only financial data (credit card numbers). Preserves legal PII."""
        if not text:
            return ""
        return cls.CARD_REGEX.sub("[CARD_REDACTED]", text)
