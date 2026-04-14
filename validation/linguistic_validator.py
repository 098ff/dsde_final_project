"""
Linguistic Validator for Thai Election OCR Results.

Provides cross-check utilities between numeric digits (Arabic/Thai) and
Thai number words to detect OCR extraction inconsistencies.
"""

import re

import numpy as np
from pythainlp.util import thaiword_to_num


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


# ---------------------------------------------------------------------------
# Thai Word Conversion
# ---------------------------------------------------------------------------

# Match only Thai consonants and vowel/tone marks (excludes Thai digits ๐-๙)
_THAI_WORD_CHARS_RE = re.compile(r"[^\u0E01-\u0E3A\u0E40-\u0E4E]")


def thai_word_to_int(word_str: str) -> int | None:
    """Convert a Thai number word string to an integer using PyThaiNLP.

    Steps applied before conversion:
      1. Remove all non-Thai-word characters (keeps only consonants/vowels/tones).
      2. Remove internal whitespace.
      3. Pass the cleaned string to ``pythainlp.util.thaiword_to_num``.

    Args:
        word_str: A string containing a Thai number word, potentially with
            surrounding whitespace or punctuation (e.g. ``" หนึ่ง ร้อย "``).

    Returns:
        Integer value or None if the string cannot be parsed.
    """
    if word_str is None:
        return None
    cleaned = _THAI_WORD_CHARS_RE.sub("", str(word_str))
    cleaned = re.sub(r"\s+", "", cleaned)
    if not cleaned:
        return None
    try:
        result = thaiword_to_num(cleaned)
        return int(result)
    except Exception:
        return None
