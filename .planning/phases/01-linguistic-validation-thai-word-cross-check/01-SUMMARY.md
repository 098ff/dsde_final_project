---
phase: "01"
plan: "01"
subsystem: "election_pipeline/src"
tags: ["pythainlp", "ocr", "validation", "thai-nlp", "linguistic-cross-check"]
dependency_graph:
  requires: []
  provides: ["linguistic-cross-check", "normalize_numerals", "thai_word_to_int", "parse_score_cell"]
  affects: ["election_pipeline/src/ocr_parser.py"]
tech_stack:
  added: ["pythainlp>=5.3.1"]
  patterns: ["dual-extraction pipeline", "NaN sentinel for mismatch", "regex score-cell parsing"]
key_files:
  created:
    - ".planning/phases/01-linguistic-validation-thai-word-cross-check/test_linguistic_validation.py"
  modified:
    - "election_pipeline/requirements.txt"
    - "election_pipeline/src/ocr_parser.py"
decisions:
  - "Use pythainlp.util.thaiword_to_num as the sole Thai word-to-integer converter"
  - "Store _score_validation dict on data object during parse_markdown to pass to validate_data"
  - "Replace mismatched scores with np.nan rather than raising; flag for human audit"
  - "Math validation skips NaN scores to avoid false positives downstream"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-14"
  tasks_completed: 5
  tasks_total: 5
  files_changed: 3
---

# Phase 01 Plan 01: Linguistic Validation (Thai Word Cross-Check) Summary

**One-liner:** Thai word-to-number cross-check using pythainlp with np.nan mismatch flagging and OCR noise normalization.

## What Was Built

The `ElectionOCRParser` in `election_pipeline/src/ocr_parser.py` was upgraded with a full linguistic validation pipeline:

1. **`normalize_numerals(s)`** - Converts any mix of Arabic and Thai digit characters (`๐-๙`) to a clean digit string, enabling consistent integer parsing regardless of OCR output format.

2. **`thai_word_to_int(word_str)`** - Converts Thai number words (e.g., `หนึ่งร้อยเจ็ดสิบเจ็ด`) to integers using `pythainlp.util.thaiword_to_num`. Strips all non-Thai characters and internal whitespace first, handling OCR-induced spacing artifacts (e.g., `ห นึ ่ ง` -> `หนึ่ง`). Returns `None` for unparseable input.

3. **`parse_score_cell(score_cell)`** - Splits a score cell string (e.g., `177 (หนึ่งร้อยเจ็ดสิบเจ็ด)`) into a `(numeric_val, linguistic_val)` tuple. Handles both parenthesized and bare word formats.

4. **`parse_markdown` updated** - Now calls `parse_score_cell` for each candidate score row, storing both `numeric_val` and `linguistic_val` in a `_score_validation` sidecar dict on the `data` object.

5. **`validate_data` updated** - Added Linguistic Cross-Check as step 0, comparing `numeric_val` vs `linguistic_val` for every score. On mismatch: sets `flag_linguistic_mismatch = True`, `needs_manual_check = True`, and replaces the score with `np.nan`. Math validation gracefully skips NaN scores.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | Update Dependencies | a7e7c2a | election_pipeline/requirements.txt |
| 02 | Enhance Digits Normalization | a6ab7ec | election_pipeline/src/ocr_parser.py |
| 03 | Implement Linguistic Conversion | 2e6ecfe | election_pipeline/src/ocr_parser.py |
| 04 | Update Extraction and Cross-Check | a963398 | election_pipeline/src/ocr_parser.py |
| 05 | Validation Tests | 64331e4 | .planning/phases/.../test_linguistic_validation.py |

## Verification

The test suite at `.planning/phases/01-linguistic-validation-thai-word-cross-check/test_linguistic_validation.py` covers all 8 validation dimensions from `01-VALIDATION.md`:

- Dimension 1: Numeric accuracy (Arabic + Thai digit extraction)
- Dimension 2: Linguistic accuracy (Thai word conversion via pythainlp)
- Dimension 3: Mismatch detection (flag + NaN propagation)
- Dimension 4: Normalization robustness (OCR noise/whitespace)
- Dimension 5: Error propagation (flags cascade)
- Dimension 6: Backward compatibility (numeric-only inputs unchanged)
- Dimension 7: Structural consistency (parens vs no-parens formats)
- Dimension 8: Pipeline integration (`flag_linguistic_mismatch` in output)

**All 22 test cases pass. Exit status: 0.**

## Deviations from Plan

None - plan executed exactly as written.

The test stub for Dimension 5 required `valid_ballots=177` to prevent a math validation false positive from interfering with the linguistic flag test, but this was a test-data correctness adjustment, not a plan deviation.

## Known Stubs

None. All new methods are fully implemented and wired to the pipeline.

## Self-Check: PASSED

Files confirmed to exist:
- `election_pipeline/src/ocr_parser.py` - modified with all new methods
- `election_pipeline/requirements.txt` - pythainlp>=5.3.1 added
- `.planning/phases/01-linguistic-validation-thai-word-cross-check/test_linguistic_validation.py` - created

Commits confirmed:
- a7e7c2a - chore(01-01): add pythainlp>=5.3.1 to dependencies
- a6ab7ec - feat(01-01): enhance digits normalization with normalize_numerals helper
- 2e6ecfe - feat(01-01): implement thai_word_to_int for linguistic conversion
- a963398 - feat(01-01): integrate linguistic cross-check into parse_markdown and validate_data
- 64331e4 - test(01-01): add validation test suite covering all 8 dimensions
