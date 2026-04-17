"""
Form Identifier for Thai Election OCR Results.

Classifies OCR text into election form types by detecting specific Thai
administrative codes: Constituency (แบ่งเขต) vs Party List (บัญชีรายชื่อ).

Form type indicators used in Thai election documents:
- Party List:     ส.ส. 5/18 (บช)  or  ส.ส. 5/11 (บช)
- Constituency:   ส.ส. 5/18        or  ส.ส. 5/11  (without บช suffix)
"""

import re

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

# Party List pattern must be checked FIRST (more specific — includes บช).
# Matches: ส.ส. 5/18 (บช) or ส.ส. 5/11 (บช), with optional whitespace.
_PARTY_LIST_RE = re.compile(
    r"ส\.ส\.\s*5\s*/\s*(11|18)\s*\(บช\)",
    re.UNICODE,
)

# Constituency pattern: ส.ส. 5/18 or ส.ส. 5/11, NOT followed by (บช).
# The negative lookahead ensures we do not accidentally match Party List text.
_CONSTITUENCY_RE = re.compile(
    r"ส\.ส\.\s*5\s*/\s*(11|18)(?!\s*\(บช\))",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

FORM_PARTY_LIST = "Party List"
FORM_CONSTITUENCY = "Constituency"
FORM_UNKNOWN = "Unknown"


def identify_form_type(ocr_text: str) -> str:
    """Classify OCR text into an election form type.

    The classification applies the most-specific pattern first:

    1. If ``ส.ส. 5/18 (บช)`` or ``ส.ส. 5/11 (บช)`` is found -> ``"Party List"``.
    2. If ``ส.ส. 5/18`` or ``ส.ส. 5/11`` is found (without ``(บช)``) -> ``"Constituency"``.
    3. Otherwise -> ``"Unknown"``.

    Args:
        ocr_text: Raw text extracted from a single OCR page/document.

    Returns:
        One of ``"Party List"``, ``"Constituency"``, or ``"Unknown"``.
    """
    if not ocr_text:
        return FORM_UNKNOWN

    if _PARTY_LIST_RE.search(ocr_text):
        return FORM_PARTY_LIST

    if _CONSTITUENCY_RE.search(ocr_text):
        return FORM_CONSTITUENCY

    return FORM_UNKNOWN
