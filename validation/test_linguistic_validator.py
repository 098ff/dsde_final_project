"""
Tests for validation.linguistic_validator

Covers all 8 validation dimensions from 01-VALIDATION.md:
  1. Numeric Accuracy        - Extraction of digits (Arabic and Thai)
  2. Linguistic Accuracy     - Conversion of Thai words via PyThaiNLP
  3. Mismatch Detection      - Mismatch triggers flag + NaN
  4. Normalization Robustness - Handling OCR noise and whitespace
  5. Error Propagation       - Flags and NaN values set correctly
  6. Backward Compatibility  - Simple numeric inputs still parse
  7. Structural Consistency  - Flexible formats (with/without parens)
  8. Pipeline Integration    - flag_linguistic_mismatch appears in output
"""

import math
import sys

import numpy as np

from validation.linguistic_validator import (
    clean_score_to_int,
    normalize_numerals,
    thai_word_to_int,
    validate_score,
)

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, str, str]] = []  # (dim, name, status)


def check(dim: str, name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    _results.append((dim, name, status))
    marker = "[PASS]" if condition else "[FAIL]"
    suffix = f" -- {detail}" if detail and not condition else ""
    print(f"  {marker} {name}{suffix}")


# ---------------------------------------------------------------------------
# Dimension 1: Numeric Accuracy
# ---------------------------------------------------------------------------
print("\n=== Dimension 1: Numeric Accuracy ===")

check("1", "Arabic digits passthrough", clean_score_to_int("177") == 177)
check("1", "Thai digits ๑๗๗ -> 177", clean_score_to_int("๑๗๗") == 177)
check("1", "normalize_numerals Thai", normalize_numerals("๑๗๗") == "177")
check("1", "normalize_numerals Arabic unchanged", normalize_numerals("177") == "177")
check("1", "Mixed Thai/Arabic digits", clean_score_to_int("๑7๗") == 177)
check("1", "Digits with punctuation stripped", clean_score_to_int("1,7.7") == 177)


# ---------------------------------------------------------------------------
# Dimension 2: Linguistic Accuracy
# ---------------------------------------------------------------------------
print("\n=== Dimension 2: Linguistic Accuracy ===")

check("2", "แปด -> 8", thai_word_to_int("แปด") == 8)
check("2", "หนึ่งร้อยเจ็ดสิบเจ็ด -> 177", thai_word_to_int("หนึ่งร้อยเจ็ดสิบเจ็ด") == 177)
check("2", "หนึ่งร้อยหกสิบ -> 160", thai_word_to_int("หนึ่งร้อยหกสิบ") == 160)
check("2", "หนึ่งร้อย -> 100", thai_word_to_int("หนึ่งร้อย") == 100)


# ---------------------------------------------------------------------------
# Dimension 3: Mismatch Detection
# ---------------------------------------------------------------------------
print("\n=== Dimension 3: Mismatch Detection ===")

r3a = validate_score("177", "หนึ่งร้อยหกสิบ")
check("3", "Mismatch triggers flag_linguistic_mismatch=True", r3a["flag_linguistic_mismatch"] is True)
check("3", "Mismatch sets value to NaN", math.isnan(r3a["value"]))
check("3", "Mismatch sets needs_manual_check=True", r3a["needs_manual_check"] is True)

r3b = validate_score("177", "หนึ่งร้อยเจ็ดสิบเจ็ด")
check("3", "Match does NOT trigger flag_linguistic_mismatch", r3b["flag_linguistic_mismatch"] is False)
check("3", "Match value is correct integer", r3b["value"] == 177)
check("3", "Match needs_manual_check=False", r3b["needs_manual_check"] is False)

r3c = validate_score("193", "หนึ่งร้อยห้าสิบ")
check("3", "193 vs หนึ่งร้อยห้าสิบ => mismatch", r3c["flag_linguistic_mismatch"] is True)


# ---------------------------------------------------------------------------
# Dimension 4: Normalization Robustness
# ---------------------------------------------------------------------------
print("\n=== Dimension 4: Normalization Robustness ===")

# Spaced Thai word — spaces between syllables should still parse
check("4", "Spaced Thai word '  หนึ่ง  ร้อย  ' -> 100", thai_word_to_int("  หนึ่ง  ร้อย  ") == 100)

# OCR noise: parens and spaces around Thai word
check("4", "Thai word with spaces -> 8", thai_word_to_int(" แปด ") == 8)

# Mixed noise characters stripped (dimension from VALIDATION.md: '8 ( แ ป ด )')
# The digit part is tested via clean_score_to_int; the word part via thai_word_to_int
check("4", "Noisy paren word '( แ ป ด )' -> 8", thai_word_to_int("( แ ป ด )") == 8)

# Thai digits with surrounding whitespace
check("4", "Thai digits with space normalize ok", clean_score_to_int("  ๑๗๗  ") == 177)


# ---------------------------------------------------------------------------
# Dimension 5: Error Propagation
# ---------------------------------------------------------------------------
print("\n=== Dimension 5: Error Propagation ===")

# Missing word part (only numeric provided)
r5a = validate_score("45", None)
check("5", "Missing word -> needs_manual_check=True", r5a["needs_manual_check"] is True)
check("5", "Missing word -> flag_linguistic_mismatch=False", r5a["flag_linguistic_mismatch"] is False)
check("5", "Missing word -> value falls back to numeric int 45", r5a["value"] == 45)

# Missing numeric part
r5b = validate_score(None, "สี่สิบห้า")
check("5", "Missing numeric -> needs_manual_check=True", r5b["needs_manual_check"] is True)

# Both missing
r5c = validate_score(None, None)
check("5", "Both missing -> needs_manual_check=True", r5c["needs_manual_check"] is True)
check("5", "Both missing -> value is NaN", math.isnan(r5c["value"]))

# Mismatch => is_match=False => needs_manual_check=True propagated
r5d = validate_score("100", "แปด")
check("5", "is_match=False => needs_manual_check=True", r5d["needs_manual_check"] is True)


# ---------------------------------------------------------------------------
# Dimension 6: Backward Compatibility
# ---------------------------------------------------------------------------
print("\n=== Dimension 6: Backward Compatibility ===")

check("6", "Plain arabic '177' still parses", clean_score_to_int("177") == 177)
check("6", "Plain '0' parses to 0", clean_score_to_int("0") == 0)
check("6", "None input returns None", clean_score_to_int(None) is None)
check("6", "Empty string returns None", clean_score_to_int("") is None)


# ---------------------------------------------------------------------------
# Dimension 7: Structural Consistency
# ---------------------------------------------------------------------------
print("\n=== Dimension 7: Structural Consistency ===")

# '177 (แปด)' and '177 แปด' — numeric part parsed the same regardless of parens
check("7", "clean_score_to_int handles '177 (แปด)'", clean_score_to_int("177 (แปด)") == 177)
check("7", "clean_score_to_int handles '177 แปด'", clean_score_to_int("177 แปด") == 177)

# Thai word inside parens still converts
check("7", "thai_word_to_int handles '(แปด)'", thai_word_to_int("(แปด)") == 8)
check("7", "thai_word_to_int handles 'แปด' without parens", thai_word_to_int("แปด") == 8)

# Full validate_score with parens in word string
r7 = validate_score("8", "(แปด)")
check("7", "validate_score with parens around word: match", r7["flag_linguistic_mismatch"] is False and r7["value"] == 8)


# ---------------------------------------------------------------------------
# Dimension 8: Pipeline Integration
# ---------------------------------------------------------------------------
print("\n=== Dimension 8: Pipeline Integration ===")

output = validate_score("177", "หนึ่งร้อยเจ็ดสิบเจ็ด")
check("8", "Output dict contains 'value' key", "value" in output)
check("8", "Output dict contains 'flag_linguistic_mismatch' key", "flag_linguistic_mismatch" in output)
check("8", "Output dict contains 'needs_manual_check' key", "needs_manual_check" in output)
check("8", "flag_linguistic_mismatch is bool type", isinstance(output["flag_linguistic_mismatch"], bool))
check("8", "needs_manual_check is bool type", isinstance(output["needs_manual_check"], bool))

# Mismatch output: flag_linguistic_mismatch=True + np.nan
mismatch_out = validate_score("177", "หนึ่งร้อยหกสิบ")
check("8", "Mismatch output has flag_linguistic_mismatch=True", mismatch_out["flag_linguistic_mismatch"] is True)
check("8", "Mismatch output value is np.nan", math.isnan(mismatch_out["value"]))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for _, _, s in _results if s == PASS)
failed = sum(1 for _, _, s in _results if s == FAIL)
total = len(_results)
print(f"Results: {passed}/{total} passed, {failed} failed")

if failed:
    print("\nFailed tests:")
    for dim, name, status in _results:
        if status == FAIL:
            print(f"  [Dim {dim}] {name}")
    sys.exit(1)
else:
    print("All tests PASSED.")
    sys.exit(0)
