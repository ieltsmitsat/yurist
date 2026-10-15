"""Uzbek text normalization utilities for post-processing LLM output.

Corrects common LLM morphological errors and normalizes Unicode apostrophes
to the standard Uzbek Latin character (ʻ / ʼ → ').
"""

import re
from typing import Final

# Stem-based substitutions: map a root (incorrect → correct) and let a single
# regex match all inflected suffix forms automatically, instead of enumerating
# every suffix combination by hand.
_STEM_CORRECTIONS: Final[list[tuple[str, str]]] = [
    # h → x corrections (Uzbek Latin uses "x" for /χ/)
    ("hizmat", "xizmat"),
    ("hato", "xato"),
    # Common LLM hallucinated word-forms
    ("notarior", "notarius"),
    ("muizma", "muammo"),
]

# Whole-word morphological fixes that can't be expressed as stem swaps.
_WORD_CORRECTIONS: Final[list[tuple[str, str]]] = [
    (r"\bqoldirishiz\b", "qoldirishingiz"),
    (r"\byozishiz\b", "yozishingiz"),
    (r"\bko'rishiz\b", "ko'rishingiz"),
    (r"\bolishiz\b", "olishingiz"),
    (r"\bberishiz\b", "berishingiz"),
    (r"\bolishingiz haqingiz bor\b", "olishga haqingiz bor"),
]

# Pre-compiled stem patterns: match the stem at a word boundary, followed by
# optional Uzbek suffixes (letters + apostrophe characters).
_COMPILED_STEMS: Final[list[tuple[re.Pattern[str], str]]] = [
    (re.compile(rf"\b{wrong}([a-z'ʻʼ]*)\b", re.IGNORECASE), correct)
    for wrong, correct in _STEM_CORRECTIONS
]

_COMPILED_WORDS: Final[list[tuple[re.Pattern[str], str]]] = [
    (re.compile(pattern, re.IGNORECASE), replacement)
    for pattern, replacement in _WORD_CORRECTIONS
]

# Unicode apostrophe variants that LLMs sometimes inject instead of the
# standard ASCII apostrophe (') used in Uzbek Latin text.
_APOSTROPHE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\u2018\u2019\u02bc`´]")

# Official Uzbek modifier letter (ʻ, U+02BB) is also normalized to simple
# apostrophe for consistency, since both ʻ and ' are used interchangeably
# in everyday Uzbek Latin digital text.
_OFFICIAL_APOSTROPHE_PATTERN: Final[re.Pattern[str]] = re.compile(r"[\u02bb]")


def _case_preserving_replace(match: re.Match[str], replacement: str) -> str:
    """Return *replacement* with the same casing as the matched text."""
    matched = match.group(0)
    if matched.isupper():
        return replacement.upper()
    if matched[0].isupper():
        return replacement.capitalize()
    return replacement


def normalize_uzbek_text(text: str) -> str:
    """Normalize common LLM errors in Uzbek Latin text.

    Performs three passes:
    1. Unicode apostrophe normalization (ʻ, ʼ, `, ´, ' → ').
    2. Stem-based corrections with automatic suffix carry-over.
    3. Whole-word morphological corrections.

    Args:
        text: Raw Uzbek text from LLM output.

    Returns:
        Cleaned text with typos corrected and apostrophes normalized.
    """
    # 1. Normalize all apostrophe variants to ASCII '
    text = _APOSTROPHE_PATTERN.sub("'", text)
    text = _OFFICIAL_APOSTROPHE_PATTERN.sub("'", text)

    # 2. Stem corrections — carry over any suffix the LLM appended
    for pattern, correct_stem in _COMPILED_STEMS:
        def _stem_repl(m: re.Match[str], stem: str = correct_stem) -> str:
            suffix = m.group(1)
            base = stem + suffix
            original = m.group(0)
            if original.isupper():
                return base.upper()
            if original[0].isupper():
                return base.capitalize()
            return base

        text = pattern.sub(_stem_repl, text)

    # 3. Whole-word fixes
    for pattern, replacement in _COMPILED_WORDS:
        def _word_repl(m: re.Match[str], rep: str = replacement) -> str:
            return _case_preserving_replace(m, rep)

        text = pattern.sub(_word_repl, text)

    return text
