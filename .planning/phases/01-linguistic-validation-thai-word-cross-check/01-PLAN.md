# Phase 01: Linguistic Validation - Plan

Implement the cross-check between numeric digits and Thai number words in the election OCR results.

## Phase Objective
Create a robust, standalone validation module that uses `PyThaiNLP` to verify score consistency and flags discrepancies for human audit. The module lives at `validation/linguistic_validator.py` (project root, outside `election_pipeline/`).

## Requirements Addressed
- **REQ-001**: Linguistic Cross-Check (Thai Word to Number)
- **REQ-003**: Missing Field Representation (np.nan for mismatches)

## Verification Logic
- **Success**: Numeric value matches converted Thai word value.
- **Failure**: Mismatch between numeric and linguistic values.
- **Action on Failure**: Set score to `np.nan`, set `flag_linguistic_mismatch = True`, set `needs_manual_check = True`.

---

## Wave 1: Foundation & Setup
Logical first step to ensure environment and utilities are ready.

### Task 01: Update Dependencies
Add `pythainlp` to the root `pyproject.toml`.
- **Files Modified**: [pyproject.toml](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/pyproject.toml)
- **Read First**: [pyproject.toml](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/pyproject.toml)
- **Action**: Add `pythainlp>=5.3.1` to the `dependencies` list in `pyproject.toml`.
- **Acceptance Criteria**: `pyproject.toml` contains `pythainlp>=5.3.1` in its dependencies list.

---

## Wave 2: Core Parsing Logic
Implementation of standalone utilities.

### Task 02: Implement Digits Normalization
Create the `validation/` package with a helper to normalize Thai and Arabic digits.
- **Files Modified**: [NEW] `validation/__init__.py`, [NEW] `validation/linguistic_validator.py`
- **Read First**: [01-RESEARCH.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-RESEARCH.md)
- **Action**:
    - Create `validation/__init__.py` (empty).
    - Create `validation/linguistic_validator.py` with:
        - `normalize_numerals(s)` — converts any combination of Arabic/Thai digits (`๐-๙`) to a clean integer string.
        - `clean_score_to_int(s)` — strips punctuation and calls `normalize_numerals`, returns `int` or `None`.
- **Acceptance Criteria**: `clean_score_to_int("๑๗๗")` returns `177`.

### Task 03: Implement Linguistic Conversion
Add Thai word-to-integer conversion to `validation/linguistic_validator.py`.
- **Files Modified**: `validation/linguistic_validator.py`
- **Read First**: [01-RESEARCH.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-RESEARCH.md)
- **Action**:
    - Implement `thai_word_to_int(word_str)`:
        - Normalize: Remove non-Thai characters and all whitespace.
        - Convert: Use `pythainlp.util.thaiword_to_num`.
        - Handle errors: Return `None` if unparseable.
- **Acceptance Criteria**: `thai_word_to_int("แปด")` returns `8`; `thai_word_to_int(" หนึ่ง ร้อย ")` returns `100`.

---

## Wave 3: Integration & Validation
Cross-check logic as a self-contained function.

### Task 04: Implement Cross-Check Function
Add the comparison logic to `validation/linguistic_validator.py`.
- **Files Modified**: `validation/linguistic_validator.py`
- **Read First**: [01-CONTEXT.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-CONTEXT.md)
- **Action**:
    - Implement `validate_score(numeric_str, word_str)` that:
        - Converts both inputs using `clean_score_to_int` and `thai_word_to_int`.
        - Returns a dict: `{"value": int_or_nan, "flag_linguistic_mismatch": bool, "needs_manual_check": bool}`.
        - If mismatch: sets `flag_linguistic_mismatch = True`, `needs_manual_check = True`, `value = np.nan`.
        - If either input is unparseable: also sets `needs_manual_check = True`.
- **Acceptance Criteria**: `validate_score("177", "หนึ่งร้อยหกสิบ")` returns `flag_linguistic_mismatch: True` and `value` is `NaN`.

---

## Wave 4: Verification
Atomic check of the entire implementation.

### Task 05: Validation Tests
Run unit tests to verify all 8 dimensions of the validation strategy.
- **Files Modified**: [NEW] `validation/test_linguistic_validator.py`
- **Read First**: [01-VALIDATION.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-VALIDATION.md)
- **Action**: Create a test script that imports from `validation.linguistic_validator` and runs test cases from `VALIDATION.md`.
- **Acceptance Criteria**: Script exits with status 0 and all test cases pass.

---
*Created: 2026-04-14*
*Updated: 2026-04-14 — redirected to standalone validation/ module, not election_pipeline/*
