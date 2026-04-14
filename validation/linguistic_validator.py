"""
Linguistic Validator for Thai Election OCR Results.

Provides cross-check utilities between numeric digits (Arabic/Thai) and
Thai number words to detect OCR extraction inconsistencies.
"""

import re

import numpy as np


# ---------------------------------------------------------------------------
# Digit Normalization
# ---------------------------------------------------------------------------

_THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"
_THAI_DIGIT_MAP = {ch: str(i) for i, ch in enumerate(_THAI_DIGITS)}


def normalize_numerals(s: str) -> str:
    """Convert Thai digit characters (๐-๙) and Arabic digits to a plain digit string.

    Returns the digits-only portion of the string, stripping all non-digit
    characters after Thai-to-Arabic conversion.

    Args:
        s: Input string that may contain Arabic digits, Thai digits, or both.

    Returns:
        A string containing only ASCII digit characters.
    """
    if not s:
        return ""
    for thai_ch, arabic_ch in _THAI_DIGIT_MAP.items():
        s = s.replace(thai_ch, arabic_ch)
    return re.sub(r"[^\d]", "", s)


def clean_score_to_int(s: str) -> int | None:
    """Strip punctuation from *s*, normalize numerals, and return an integer.

    Args:
        s: Raw score string extracted from OCR output.

    Returns:
        Integer value or None if the string contains no recognisable digits.
    """
    if s is None:
        return None
    digits = normalize_numerals(str(s))
    if not digits:
        return None
    return int(digits)
