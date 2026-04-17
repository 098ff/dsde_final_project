"""
Tests for validation.form_identifier and validation.structural_auditor.

Coverage:
  1. identify_form_type - Party List detection (บช suffix)
  2. identify_form_type - Constituency detection (no บช suffix)
  3. identify_form_type - Unknown for unrelated text / empty input
  4. identify_form_type - Merged text containing both keywords (Party List wins first pass)
  5. audit_units - Both forms present -> no missing items
  6. audit_units - Only one form exists -> one missing item reported
  7. audit_units - No forms present -> two missing items
  8. audit_units - Multiple stations, mixed completeness
  9. generate_missing_report - Correct CSV written for non-empty missing list
 10. generate_missing_report - Empty list writes header-only CSV
"""

import math
import os
import sys
import tempfile

import pandas as pd

from validation.form_identifier import (
    FORM_CONSTITUENCY,
    FORM_PARTY_LIST,
    FORM_UNKNOWN,
    identify_form_type,
)
from validation.structural_auditor import audit_units, generate_missing_report

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, str]] = []  # (name, status)


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    _results.append((name, status))
    marker = "[PASS]" if condition else "[FAIL]"
    suffix = f" -- {detail}" if detail and not condition else ""
    print(f"  {marker} {name}{suffix}")


# ---------------------------------------------------------------------------
# Section 1: identify_form_type
# ---------------------------------------------------------------------------
print("\n=== identify_form_type ===")

# 1a. Party List via ส.ส. 5/18 (บช)
check(
    "Party List detected: ส.ส. 5/18 (บช)",
    identify_form_type("แบบ ส.ส. 5/18 (บช) การเลือกตั้ง") == FORM_PARTY_LIST,
)

# 1b. Party List via ส.ส. 5/11 (บช)
check(
    "Party List detected: ส.ส. 5/11 (บช)",
    identify_form_type("ส.ส. 5/11 (บช) บัญชีรายชื่อ") == FORM_PARTY_LIST,
)

# 1c. Constituency via ส.ส. 5/18 (no บช)
check(
    "Constituency detected: ส.ส. 5/18 without (บช)",
    identify_form_type("แบบ ส.ส. 5/18 แบ่งเขตเลือกตั้ง") == FORM_CONSTITUENCY,
)

# 1d. Constituency via ส.ส. 5/11 (no บช)
check(
    "Constituency detected: ส.ส. 5/11 without (บช)",
    identify_form_type("ส.ส. 5/11 การนับคะแนน") == FORM_CONSTITUENCY,
)

# 1e. Unknown for unrelated text
check(
    "Unknown for unrelated text",
    identify_form_type("ผลการเลือกตั้ง ปี 2566") == FORM_UNKNOWN,
)

# 1f. Empty string -> Unknown
check(
    "Unknown for empty string",
    identify_form_type("") == FORM_UNKNOWN,
)

# 1g. None-like: empty returns Unknown (not TypeError)
check(
    "Unknown for whitespace-only string",
    identify_form_type("   ") == FORM_UNKNOWN,
)

# 1h. Merged text containing both keywords: Party List takes priority (checked first)
merged_text = "ส.ส. 5/18 (บช) และ ส.ส. 5/18 แบ่งเขต"
check(
    "Merged text with both keywords -> Party List (first match wins)",
    identify_form_type(merged_text) == FORM_PARTY_LIST,
)

# 1i. Optional whitespace in pattern: ส.ส. 5 / 18 (บช)
check(
    "Party List with spaces around slash: ส.ส. 5 / 18 (บช)",
    identify_form_type("ส.ส. 5 / 18 (บช)") == FORM_PARTY_LIST,
)

# 1j. Constituency with dot shorthand — ส.ส.5/18 (no spaces)
check(
    "Constituency compact: ส.ส.5/18",
    identify_form_type("ส.ส.5/18 คะแนน") == FORM_CONSTITUENCY,
)


# ---------------------------------------------------------------------------
# Section 2: audit_units
# ---------------------------------------------------------------------------
print("\n=== audit_units ===")

# 2a. Both forms present -> no missing items
records_complete = [
    {"Tambon": "Baan Rai", "Unit": "1", "form_type": FORM_CONSTITUENCY},
    {"Tambon": "Baan Rai", "Unit": "1", "form_type": FORM_PARTY_LIST},
]
result_complete = audit_units(records_complete)
check(
    "Both forms present -> empty missing list",
    len(result_complete) == 0,
)

# 2b. Only Constituency -> Party List missing
records_missing_pl = [
    {"Tambon": "Baan Rai", "Unit": "2", "form_type": FORM_CONSTITUENCY},
]
result_missing_pl = audit_units(records_missing_pl)
check(
    "Only Constituency -> 1 missing item (Party List)",
    len(result_missing_pl) == 1,
)
check(
    "Missing item identifies correct form (Party List)",
    len(result_missing_pl) == 1 and result_missing_pl[0]["missing_form"] == FORM_PARTY_LIST,
)
check(
    "Missing item has correct Tambon",
    len(result_missing_pl) == 1 and result_missing_pl[0]["Tambon"] == "Baan Rai",
)

# 2c. Only Party List -> Constituency missing
records_missing_c = [
    {"Tambon": "Baan Rai", "Unit": "3", "form_type": FORM_PARTY_LIST},
]
result_missing_c = audit_units(records_missing_c)
check(
    "Only Party List -> 1 missing item (Constituency)",
    len(result_missing_c) == 1,
)
check(
    "Missing item identifies correct form (Constituency)",
    len(result_missing_c) == 1 and result_missing_c[0]["missing_form"] == FORM_CONSTITUENCY,
)

# 2d. No forms (Unknown only) -> both forms missing
records_unknown = [
    {"Tambon": "Baan Rai", "Unit": "4", "form_type": FORM_UNKNOWN},
]
result_unknown = audit_units(records_unknown)
check(
    "Unknown-only record -> 2 missing items",
    len(result_unknown) == 2,
)

# 2e. Multiple stations: one complete, one incomplete
records_multi = [
    {"Tambon": "Baan Rai", "Unit": "1", "form_type": FORM_CONSTITUENCY},
    {"Tambon": "Baan Rai", "Unit": "1", "form_type": FORM_PARTY_LIST},
    {"Tambon": "Baan Rai", "Unit": "2", "form_type": FORM_CONSTITUENCY},
]
result_multi = audit_units(records_multi)
check(
    "Multi-station: 1 complete + 1 incomplete -> 1 missing item total",
    len(result_multi) == 1,
)
check(
    "Incomplete station (Unit 2) flagged correctly",
    len(result_multi) == 1 and result_multi[0]["Unit"] == "2",
)

# 2f. Empty records -> empty missing list
check(
    "Empty records list -> empty missing list",
    audit_units([]) == [],
)


# ---------------------------------------------------------------------------
# Section 3: generate_missing_report
# ---------------------------------------------------------------------------
print("\n=== generate_missing_report ===")

with tempfile.TemporaryDirectory() as tmpdir:
    # 3a. Non-empty missing list
    items = [
        {"Tambon": "Baan Rai", "Unit": "2", "missing_form": FORM_PARTY_LIST},
        {"Tambon": "Baan Rai", "Unit": "3", "missing_form": FORM_CONSTITUENCY},
    ]
    out_path = os.path.join(tmpdir, "missing_units.csv")
    generate_missing_report(items, out_path)

    check("CSV file created", os.path.isfile(out_path))

    df = pd.read_csv(out_path, encoding="utf-8-sig")
    check("CSV has correct number of rows", len(df) == 2)
    check("CSV has Tambon column", "Tambon" in df.columns)
    check("CSV has Unit column", "Unit" in df.columns)
    check("CSV has missing_form column", "missing_form" in df.columns)
    check(
        "CSV row 1 Tambon matches",
        df.iloc[0]["Tambon"] == "Baan Rai",
    )
    check(
        "CSV row 1 missing_form matches Party List",
        df.iloc[0]["missing_form"] == FORM_PARTY_LIST,
    )

    # 3b. Empty list -> header-only CSV
    empty_path = os.path.join(tmpdir, "empty_missing.csv")
    generate_missing_report([], empty_path)
    check("Empty CSV file created", os.path.isfile(empty_path))
    df_empty = pd.read_csv(empty_path, encoding="utf-8-sig")
    check("Empty CSV has 0 rows", len(df_empty) == 0)
    check("Empty CSV still has correct columns", list(df_empty.columns) == ["Tambon", "Unit", "missing_form"])


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for _, s in _results if s == PASS)
failed = sum(1 for _, s in _results if s == FAIL)
total = len(_results)
print(f"Results: {passed}/{total} passed, {failed} failed")

if failed:
    print("\nFailed tests:")
    for name, status in _results:
        if status == FAIL:
            print(f"  [FAIL] {name}")
    sys.exit(1)
else:
    print("All tests PASSED.")
    sys.exit(0)
