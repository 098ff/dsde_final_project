# Roadmap: Thai Election OCR Validation

Phased execution plan for enhancing the election pipeline validation layer.

## Phase 1: Linguistic Validation (Thai Word Cross-Check) [COMPLETE]
Implement the core logic to verify consistency between numeric and text-based scores.
- [x] Install and integrate `PyThaiNLP`.
- [x] Upgrade `clean_score_to_int` to extract both parenthetical Thai words and Arabic numbers.
- [x] Add `flag_linguistic_mismatch` to the validation engine.
- [x] **Verification**: Unit test with `8 (แปด)` and `193 (หนึ่งร้อยห้าสิบ)` — 22 tests passing.
- **Summary**: [01-SUMMARY.md](.planning/phases/01-linguistic-validation-thai-word-cross-check/01-SUMMARY.md) | Plans: 1/1 complete | 44 tests passing | validation/ module created

## Phase 2: Structural Integrity (Missing Unit Detection) [COMPLETE]
Ensure every station has a complete set of election types.
- [x] Implement `identify_form_type(ocr_text)` using regex to classify OCR text as Party List, Constituency, or Unknown.
- [x] Implement `audit_units(records)` grouping by (Tambon, Unit) and flagging missing form types.
- [x] Implement `generate_missing_report(missing_items, output_path)` writing findings to `missing_units.csv`.
- [x] **Verification**: 30 tests passing across form identifier, audit logic, and CSV report generation.
- **Summary**: [02-SUMMARY.md](.planning/phases/02-structural-integrity-missing-unit-detection/02-SUMMARY.md) | Plans: 1/1 complete | 30 tests passing | form_identifier.py + structural_auditor.py created

## Phase 3: Robust Error Propagation (NANs & Logs) [COMPLETE]
Implement standalone Jigsaw validation engine with NaN propagation and MISSING/null formatters.
- [x] Refactor `clean_score_to_int` to return `np.nan` for missing-data sentinels (`None`, `""`, `"-"`, `"—"`, `"."`).
- [x] Implement `ElectionValidator` jigsaw engine with master-list alignment and math consistency flags.
- [x] Implement `prepare_df_for_csv` (na_rep="MISSING") and `prepare_data_for_json` (NaN->None) formatters.
- [x] **Verification**: 46 unit and integration tests — all passing. Zero modifications to `election_pipeline/`.
- **Summary**: [03-SUMMARY.md](.planning/phases/03-robust-error-propagation-nans-logs/03-SUMMARY.md) | Plans: 1/1 complete | 46 tests passing | engine.py + formatters.py created

## Phase 4: Pipeline Integration & Orchestration
Full end-to-end integration with Airflow.
- [ ] Integrate the structural check into the initial file collection task in `election_dag.py`.
- [ ] Update Airflow task logs to surface `missing_units.csv` summaries.
- [ ] Perform a full dry-run processing several units from Uthai Thani.
- [ ] **Verification**: Confirm `missing_units.csv` is generated and contains accurate data after a full DAG run.

---
*Created: 2026-04-14*
