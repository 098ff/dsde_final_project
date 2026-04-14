# Phase 01: Linguistic Validation - Plan

Implement the cross-check between numeric digits and Thai number words in the election OCR results.

## Phase Objective
Create a robust validation layer that uses `PyThaiNLP` to verify score consistency and flags discrepancies for human audit.

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
Add `pythainlp` to the project requirements.
- **Files Modified**: [requirements.txt](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/requirements.txt)
- **Read First**: [requirements.txt](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/requirements.txt)
- **Action**: Add `pythainlp>=5.3.1` to the list.
- **Acceptance Criteria**: `pip install -r requirements.txt` succeeds and `import pythainlp` works in a python shell.

---

## Wave 2: Core Parsing Logic
Implementation of the extraction and conversion logic.

### Task 02: Enhance Digits Normalization
Update the parser to handle both Arabic and Thai digits consistently.
- **Files Modified**: [ocr_parser.py](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/election_pipeline/src/ocr_parser.py)
- **Read First**: [ocr_parser.py](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/election_pipeline/src/ocr_parser.py) (Lines 5-20)
- **Action**: 
    - Improve `clean_score_to_int` to handle Thai digits `๐-๙` and strip punctuation more effectively.
    - Create a helper `normalize_numerals(s)` to convert any combination of Arabic/Thai digits to a clean integer string.
- **Acceptance Criteria**: `clean_score_to_int("๑๗๗")` returns `177`.

### Task 03: Implement Linguistic Conversion
Add the ability to convert Thai number words to integers with normalization.
- **Files Modified**: [ocr_parser.py](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/election_pipeline/src/ocr_parser.py)
- **Read First**: [01-RESEARCH.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-RESEARCH.md)
- **Action**: 
    - Implement `thai_word_to_int(word_str)`:
        - Normalize: Remove non-Thai characters and all whitespace.
        - Convert: Use `pythainlp.util.thaiword_to_num`.
        - Handle errors: Return `None` if unparseable.
- **Acceptance Criteria**: `thai_word_to_int("แปด")` returns `8`; `thai_word_to_int(" หนึ่ง ร้อย ")` returns `100`.

---

## Wave 3: Integration & Validation
Hooking the logic into the extraction pipeline.

### Task 04: Update Extraction and Cross-Check
Revise `parse_markdown` and `validate_data` to perform the cross-check.
- **Files Modified**: [ocr_parser.py](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/election_pipeline/src/ocr_parser.py)
- **Read First**: [ocr_parser.py](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/election_pipeline/src/ocr_parser.py) (Line 46), [01-CONTEXT.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-CONTEXT.md)
- **Action**:
    - Update `parse_markdown`:
        - Use a flexible regex to capture both the number and the (word) part: `([\d๐-๙]+)\s*(?:\(?([\u0E01-\u0E7F\s]+)\)?)?`.
        - Store both `numeric_val` and `linguistic_val` temporarily (or in a validation object).
    - Update `validate_data`:
        - Compare `numeric_val` and `linguistic_val`.
        - If mismatch: set `flag_linguistic_mismatch = True`, `needs_manual_check = True`, and replace the numeric value with `np.nan` in the data dictionary.
- **Acceptance Criteria**: `validate_data` with inputs `177` and `หนึ่งร้อยหกสิบ` returns `flag_linguistic_mismatch: True` and data contains `NaN`.

---

## Wave 4: Verification
Atomic check of the entire implementation.

### Task 05: Validation Tests
Run unit tests to verify all 8 dimensions of the validation strategy.
- **Files Modified**: [NEW] [test_linguistic_validation.py](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/test_linguistic_validation.py)
- **Read First**: [01-VALIDATION.md](file:///home/chatrin/Documents/Chat/CU/Year-3/2110446_DSDE_2025s2/dsde_final_project/.planning/phases/01-linguistic-validation-thai-word-cross-check/01-VALIDATION.md)
- **Action**: Create a script that instantiates `ElectionOCRParser` and passes test strings defined in `VALIDATION.md`.
- **Acceptance Criteria**: Script should exit with status 0 and all test cases pass.

---
*Created: 2026-04-14*
