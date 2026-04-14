# Project: Thai Election OCR Validation

**Goal:** Implement a sophisticated validation layer for the Thai Election Document OCR Pipeline to ensure data integrity through multi-modal cross-checks and robust error tracking.

## Context
This is a brownfield project built upon the existing `election_pipeline`. The pipeline currently uses Typhoon VLM for OCR extraction from PDF forms. This project adds a critical validation module to verify OCR accuracy and completeness.

## Core Value
Ensure the extracted election results are mathematically consistent and structurally complete, providing a "Human-in-the-loop" audit trail for any discrepancies.

## Requirements

### Validated
- ✓ [Existing] Airflow-based orchestration for unit processing.
- ✓ [Existing] Image preprocessing (Smart Chunking, Grayscale).
- ✓ [Existing] Mathematical total validation (`Valid + Invalid + No Vote == Total`).

### Active
- [ ] **Cross-Check Validation**: Verify that Arabic numbers match the accompanying Thai number words (e.g., `177` vs `หนึ่งร้อยเจ็ดสิบเจ็ด`) using `PyThaiNLP`.
- [ ] **Missing Unit Detection**: For every station (หน่วยเลือกตั้ง), ensure both the "Constituency" (แบ่งเขต) and "Party List" (บัญชีรายชื่อ) results are present.
- [ ] **Robust NAN Handling**: Represent missing or unparseable fields as `numpy.nan` to facilitate downstream data analysis.
- [ ] **Advanced Logging**: Generate a standalone `missing_units.csv` log identifying any station with incomplete results.

### Out of Scope
- Modifying the core OCR model (Typhoon VLM) itself.
- Building a full web UI for manual verification (remains notebook-based for now).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use `PyThaiNLP` | Industry standard for Thai NLP; robust support for number translation. | — Pending |
| Standalone Log File | Decouples structural errors (missing files) from extraction errors (OCR issues). | — Pending |
| `numpy.nan` | Standardizes missing data for Pandas-based analysis. | — Pending |

## Evolution
This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions

---
*Last updated: 2026-04-14 after initialization*
