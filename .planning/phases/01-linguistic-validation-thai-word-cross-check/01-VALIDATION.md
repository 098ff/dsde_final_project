# Phase 01: Linguistic Validation - Validation Strategy

## Overview
This strategy ensures Phase 01 meets the requirement for cross-checking Arabic/Thai digits against Thai number words accurately and robustly.

## Validation Dimensions

| Dimension | Description | Success Criteria |
|-----------|-------------|------------------|
| **1. Numeric Accuracy** | Extraction of digits (Arabic and Thai). | `๑๗๗` -> `177`, `177` -> `177`. |
| **2. Linguistic Accuracy** | Conversion of Thai words using PyThaiNLP. | `หนึ่งร้อยเจ็ดสิบเจ็ด` -> `177`. |
| **3. Mismatch Detection** | Logic identifying differences between 1 & 2. | `177 (หนึ่งร้อยหกสิบ)` triggers flag + NaN. |
| **4. Normalization Robustness** | Handling OCR noise and whitespace. | `ห นึ ่ ง ร้อย` -> `100`. |
| **5. Error Propagation** | Setting flags and NaN values correctly. | `is_match=False` -> `needs_manual_check=True`. |
| **6. Backward Compatibility** | Parser still works for simple numeric inputs. | Inputs without words still parse correctly. |
| **7. Structural Consistency** | Parser handles flexible formats (with/without parens). | `177 (แปด)` and `177 แปด` match same rule. |
| **8. Pipeline Integration** | `validate_data` reflects the new linguistic flag. | `flag_linguistic_mismatch` appears in output. |

## Verification Plan

### Automated Verification
- **Unit Tests**: Pass/Fail on a suite of strings including:
    - Match: `177 (หนึ่งร้อยเจ็ดสิบเจ็ด)`
    - Thai Digit Match: `๑๗๗ (หนึ่งร้อยเจ็ดสิบเจ็ด)`
    - Mismatch: `193 (หนึ่งร้อยห้าสิบ)`
    - Noise: `8 ( แ ป ด )`
    - Missing Word: `45`
- **Output Audit**: Verify that `data` dict contains `np.nan` for mismatch cases.

### Manual Verification
- Process a sample notebook using documented "noisy" examples from the project context.

---
*Created: 2026-04-14*
