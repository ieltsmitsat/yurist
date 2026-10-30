"""Skill 4: Legal Intake, Triage & Risk Level Scoring Skill (skill_legal_intake_triage).

Classifies client inquiries into legal domains, computes risk score (0-100),
assigns risk level (LOW, MEDIUM, HIGH, CRITICAL), and dictates next tactical action.
"""

import logging
import re
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class LegalCategory(str, Enum):
    CIVIL = "fuqarolik"
    FAMILY = "oila"
    CRIMINAL = "jinoyat"
    LABOR = "mehnat"
    HOUSING = "uy_joy"
    BUSINESS = "biznes"
    GENERAL = "umumiy"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LegalIntakeTriageSkill:
    """Performs legal category triage and quantitative risk scoring."""

    # Keyword patterns for category detection
    CATEGORY_PATTERNS: ClassVar[dict[LegalCategory, re.Pattern[str]]] = {
        LegalCategory.FAMILY: re.compile(
            r"(ajrash|aliment|nikoh|farzand|vasiy|erim|xotinim|ota-ona)", re.IGNORECASE
        ),
        LegalCategory.CRIMINAL: re.compile(
            r"(jinoyat|qamoq|hibs|tintuv|tergov|iib|prokuratur|firibgar|pora|sudlan|statya)",
            re.IGNORECASE,
        ),
        LegalCategory.LABOR: re.compile(
            r"(ishdan\s+bo'sh|ishxona|oylik|maosh|mehnat|ish\s+haqi|ta'til|boshliq)",
            re.IGNORECASE,
        ),
        LegalCategory.HOUSING: re.compile(
            r"(kvartira|uy-joy|propiska|ijara|kadastr|snos|yer\s+uchastka|ko'chirish)",
            re.IGNORECASE,
        ),
        LegalCategory.BUSINESS: re.compile(
            r"(mchj|firma|shartnoma|soliq|biznes|kontrakt|partner|bankrot|litsenziya)",
            re.IGNORECASE,
        ),
        LegalCategory.CIVIL: re.compile(
            r"(meros|qarz|vasiyat|shartnoma|zarar|tovon|sudga\s+ber|da'vo)",
            re.IGNORECASE,
        ),
    }

    # High and critical severity keywords
    CRITICAL_PATTERNS = re.compile(
        r"\b(ushlab\s+turishibdi|hibsga\s+olishdi|tintuv\s+qilishyapti|qo'lga\s+olishdi|tergovchi\s+qamamoqchi|advokat\s+kerak\s+tezda|qo'rqitishyapti)\b",
        re.IGNORECASE,
    )

    HIGH_PATTERNS = re.compile(
        r"\b(sudga\s+berishdi|sud\s+chaqiruv|sud\s+bo'ladi|jinoyat\s+ishi|katta\s+miqdorda\s+zarar|tortib\s+olishmoqda|sudlanuvchi)\b",
        re.IGNORECASE,
    )

    MEDIUM_PATTERNS = re.compile(
        r"\b(shartnoma\s+tuzmoqchiman|audit|aliment\s+to'lamayapti|ishdan\s+noqonuniy|shartnomani\s+buzishdi|snos)\b",
        re.IGNORECASE,
    )

    SOS_INSTRUCTIONS = (
        "🚨 FAVQULODDA HUQUQIY YO'RIQNOMA (30 soniyalik qoida):\n"
        "1. O'zbekiston Respublikasi Konstitutsiyasining 28-moddasiga ko'ra, "
        "siz o'zingiz va yaqinlaringizga qarshi ko'rsatma bermaslik huquqiga egasiz (sukut saqlash huquqi).\n"
        "2. Advokatingiz kelmaguncha hech qanday hujjatga qo'l qo'ymang va ko'rsatma bermang.\n"
        "3. Zudlik bilan advokat chaqirishni talab qiling.\n"
        "📞 Shoshilinch advokat bilan bog'lanish: +998901234567"
    )

    @classmethod
    def detect_category(cls, text: str) -> LegalCategory:
        """Classify inquiry text into a primary legal domain."""
        if not text:
            return LegalCategory.GENERAL

        for category, pattern in cls.CATEGORY_PATTERNS.items():
            if pattern.search(text):
                return category
        return LegalCategory.GENERAL

    @classmethod
    def calculate_risk_score(cls, text: str) -> tuple[int, RiskLevel]:
        """Compute 0-100 risk score and mapped risk level."""
        if not text:
            return 10, RiskLevel.LOW

        if cls.CRITICAL_PATTERNS.search(text):
            return 95, RiskLevel.CRITICAL
        if cls.HIGH_PATTERNS.search(text):
            return 75, RiskLevel.HIGH
        if cls.MEDIUM_PATTERNS.search(text):
            return 50, RiskLevel.MEDIUM

        return 20, RiskLevel.LOW

    @classmethod
    def determine_action_strategy(cls, risk_level: RiskLevel) -> dict[str, Any]:
        """Return recommended action strategy based on risk level."""
        if risk_level == RiskLevel.CRITICAL:
            return {
                "action": "SOS_DISPATCH",
                "include_sos_instructions": True,
                "upsell_type": "URGENT_ATTORNEY_CALL",
                "offer_free_info": False,
            }
        if risk_level == RiskLevel.HIGH:
            return {
                "action": "COURT_REPRESENTATION_UPSELL",
                "include_sos_instructions": False,
                "upsell_type": "COURT_REPRESENTATION",
                "offer_free_info": True,
            }
        if risk_level == RiskLevel.MEDIUM:
            return {
                "action": "DOCUMENT_AUDIT_UPSELL",
                "include_sos_instructions": False,
                "upsell_type": "CONTRACT_AUDIT",
                "offer_free_info": True,
            }
        return {
            "action": "FREE_LEGAL_INFO",
            "include_sos_instructions": False,
            "upsell_type": None,
            "offer_free_info": True,
        }
