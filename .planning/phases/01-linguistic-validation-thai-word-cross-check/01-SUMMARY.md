---
phase: "01"
plan: "01"
subsystem: "validation"
tags: ["linguistic-validation", "pythainlp", "thai-ocr", "cross-check", "numpy"]
dependency_graph:
  requires: []
  provides: ["validation.linguistic_validator"]
  affects: []
tech_stack:
  added: ["pythainlp>=5.3.1", "numpy>=2.0.0"]
  patterns: ["standalone validation module", "pure-function utilities", "defensive None-returning parsers"]
key_files:
  created:
    - validation/__init__.py
    - validation/linguistic_validator.py
    - validation/test_linguistic_validator.py
  modified:
    - pyproject.toml
decisions:
  - "Standalone validation/ module at project root — no changes to election_pipeline/"
  - "thai_word_to_int uses regex to strip non-Thai-word chars before thaiword_to_num"
  - "validate_score returns np.nan on mismatch; falls back to available value on parse failure"
  - "Tests use PYTHONPATH=. to resolve validation package from project root"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-14"
  tasks_completed: 5
  tasks_total: 5
  files_changed: 4
---

# Phase 01 Plan 01: Linguistic Validation Summary

**One-liner:** Standalone `validation/` package using `pythainlp.util.thaiword_to_num` to cross-check Arabic/Thai digit scores against Thai word scores, returning `np.nan` and audit flags on mismatch.

## What Was Built

A new `validation/` Python package at the project root (no changes to `election_pipeline/`) containing:

- **`normalize_numerals(s)`** — maps Thai digit chars (๐-๙) to ASCII digits and strips non-digit characters.
- **`clean_score_to_int(s)`** — parses a raw OCR score string (Arabic or Thai digits, with optional punctuation) to an integer or `None`.
- **`thai_word_to_int(word_str)`** — strips non-Thai-consonant/vowel characters and whitespace, then calls `pythainlp.util.thaiword_to_num`, returning an integer or `None` on failure.
- **`validate_score(numeric_str, word_str)`** — cross-checks the two parsed values. Returns a dict `{value, flag_linguistic_mismatch, needs_manual_check}`. On mismatch: `value=np.nan`, both flags `True`. On parse failure: `needs_manual_check=True`, `value` falls back to whichever side is available.

A 44-case test suite in `validation/test_linguistic_validator.py` covers all 8 validation dimensions defined in `01-VALIDATION.md`. All 44 tests pass.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 01 | Update Dependencies | 7a6bd0f | pyproject.toml |
| 02 | Implement Digits Normalization | 47cf58b | validation/__init__.py, validation/linguistic_validator.py |
| 03 | Implement Linguistic Conversion | 3e496cb | validation/linguistic_validator.py |
| 04 | Implement Cross-Check Function | 3f8f290 | validation/linguistic_validator.py |
| 05 | Validation Tests | 3820e5e | validation/test_linguistic_validator.py |

## Verification Results

```
Results: 44/44 passed, 0 failed
All tests PASSED.
```

Dimensions covered:
1. Numeric Accuracy — Arabic and Thai digit extraction
2. Linguistic Accuracy — PyThaiNLP word-to-number conversion
3. Mismatch Detection — flag + NaN on value disagreement
4. Normalization Robustness — OCR noise, whitespace, parentheses
5. Error Propagation — correct NaN and flag propagation on parse failure
6. Backward Compatibility — plain numeric inputs still parse correctly
7. Structural Consistency — formats with and without parentheses
8. Pipeline Integration — output dict has all required keys and correct types

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Module lives in `validation/` at project root | Strict constraint: no changes to `election_pipeline/` |
| Thai word chars regex `[\u0E01-\u0E3A\u0E40-\u0E4E]` | Excludes Thai digits (๐-๙) and punctuation; targets only consonants/vowels/tones |
| `validate_score` returns dict (not raising exceptions) | Callers get structured audit data; None-safe throughout |
| Tests run with `PYTHONPATH=.` | `validation/` is not an installed package; project root must be on sys.path |

## Deviations from Plan

None — plan executed exactly as written. All tasks completed in order with all acceptance criteria met.

## Known Stubs

None — all functions are fully implemented and wired to real data.

## Self-Check: PASSED

Files verified present:
- validation/__init__.py: FOUND
- validation/linguistic_validator.py: FOUND
- validation/test_linguistic_validator.py: FOUND

Commits verified:
- 7a6bd0f: FOUND (chore: add pythainlp/numpy deps)
- 47cf58b: FOUND (feat: digit normalization)
- 3e496cb: FOUND (feat: thai_word_to_int)
- 3f8f290: FOUND (feat: validate_score)
- 3820e5e: FOUND (test: 44 test cases)
