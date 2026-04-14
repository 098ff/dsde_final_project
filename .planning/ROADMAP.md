# Roadmap: Thai Election OCR Validation

Phased execution plan for enhancing the election pipeline validation layer.

## Phase 1: Linguistic Validation (Thai Word Cross-Check) [COMPLETE]
Implement the core logic to verify consistency between numeric and text-based scores.
- [x] Install and integrate `PyThaiNLP`.
- [x] Upgrade `clean_score_to_int` to extract both parenthetical Thai words and Arabic numbers.
- [x] Add `flag_linguistic_mismatch` to the validation engine.
- [x] **Verification**: Unit test with `8 (แปด)` and `193 (หนึ่งร้อยห้าสิบ)` — 22 tests passing.
- **Summary**: [01-SUMMARY.md](.planning/phases/01-linguistic-validation-thai-word-cross-check/01-SUMMARY.md) | Plans: 1/1 complete

## Phase 2: Structural Integrity (Missing Unit Detection)
Ensure every station has a complete set of election types.
- [ ] Develop a file-scanning utility to group PDF files by `Station + Type` (Constituency vs Party List).
- [ ] Implement detection logic for missing "Party List" vs "Constituency" per unit.
- [ ] Create a standalone logging utility for `missing_units.csv`.
- [ ] **Verification**: Run against the provided directory tree sample to confirm correct detection of missing pairs.

## Phase 3: Robust Error Propagation (NANs & Logs)
Modernize how missing and invalid data are handled in the pipeline.
- [ ] Update `ElectionOCRParser.parse_markdown` to return `np.nan` for missing fields instead of `0`.
- [ ] Update `validate_data` to handle `NaN` inputs without crashing.
- [ ] Refactor the exporter to ensure `NaN` values are correctly persisted in final CSVs/JSONs.
- [ ] **Verification**: Mock a failed OCR response and confirm `NaN` appears in the output dataframe.

## Phase 4: Pipeline Integration & Orchestration
Full end-to-end integration with Airflow.
- [ ] Integrate the structural check into the initial file collection task in `election_dag.py`.
- [ ] Update Airflow task logs to surface `missing_units.csv` summaries.
- [ ] Perform a full dry-run processing several units from Uthai Thani.
- [ ] **Verification**: Confirm `missing_units.csv` is generated and contains accurate data after a full DAG run.

---
*Created: 2026-04-14*
