# Requirements: Thai Election OCR Validation

This document defines the functional and technical requirements for the validation module enhancement.

## Functional Requirements

### 1. Linguistic Cross-Check (Thai Word to Number)
- **ID:** `REQ-001`
- **Description:** Whenever an OCR result contains both an Arabic number and a Thai number word (e.g., `177 (หนึ่งร้อยเจ็ดสิบเจ็ด)`), the system MUST extract both and verify they represent the same value.
- **Dependency:** `PyThaiNLP`
- **Failure Action:** Set `flag_linguistic_mismatch` to `True` and trigger `needs_manual_check`.

### 2. Missing Unit Detection (Structural Completeness)
- **ID:** `REQ-002`
- **Description:** For every election station (หน่วยเลือกตั้ง), the system MUST verify the presence of both "Constituency" (แบ่งเขต/สส 5ทับxx) and "Party List" (บัญชีรายชื่อ/บช) results.
- **Scope:** Based on the folder-based unit structure in Google Drive.
- **Failure Action:** Log the missing station and missing type in `missing_units.csv`.

### 3. Missing Field Representation
- **ID:** `REQ-003`
- **Description:** Any field that is physically missing from the OCR output or unparseable MUST be represented as `numpy.nan` in the final dataset.
- **Rationale:** Standardizes missing data handling for downstream Pandas analysis.

### 4. Standalone Structural Logging
- **ID:** `REQ-004`
- **Description:** Structural errors (missing station/type) MUST be logged in a dedicated `missing_units.csv` file, separate from extraction-level flags.

## Technical Requirements

- **Language:** Python 3.12+ 
- **Libraries:**
  - `PyThaiNLP`: For `thaiword_to_num` conversion.
  - `NumPy`: For `np.nan` representation.
  - `Pandas`: For log generation and data manipulation.
- **Integration:** Must be backwards compatible with the existing `election_pipeline` and `ElectionOCRParser`.

## Success Criteria

1.  Given an OCR string `8 (แปด)`, the validator confirms the match.
2.  Given an OCR string `193 (หนึ่งร้อยห้าสิบ)`, the validator flags a mismatch (`needs_manual_check`).
3.  Given a unit folder `หน่วยเลือกตั้งที่ 1` containing only a constituency file, the system logs `หน่วยเลือกตั้งที่ 1, Party List, Missing` to `missing_units.csv`.
4.  Dataframes passed to the exporter show `NaN` for failed extractions.

---
*Created: 2026-04-14*
