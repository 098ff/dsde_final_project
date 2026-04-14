---
phase: "02"
plan: "02"
subsystem: "validation"
tags: ["structural-integrity", "missing-unit-detection", "regex", "ocr", "thai-election", "pandas"]
dependency_graph:
  requires: ["validation/__init__.py"]
  provides: ["identify_form_type", "audit_units", "generate_missing_report"]
  affects: []
tech_stack:
  added: []
  patterns: ["first-match-wins regex classification", "groupby audit pattern", "header-only CSV guarantee"]
key_files:
  created:
    - "validation/form_identifier.py"
    - "validation/structural_auditor.py"
    - "validation/test_structural.py"
  modified: []
decisions:
  - "Party List regex checked before Constituency regex so merged-text pages classify as Party List (first-match-wins)"
  - "generate_missing_report always writes CSV even when empty so downstream consumers can rely on file existence"
  - "audit_units uses sorted(_REQUIRED_FORMS) for deterministic missing-item order in output"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-14"
  tasks_completed: 4
  tasks_total: 4
  files_changed: 3
---

# Phase 02 Plan 02: Structural Integrity (Missing Unit Detection) Summary

**One-liner:** Regex-based form type classifier plus station-level audit producing missing_units.csv, with 30 passing unit tests.

## What Was Built

Three new files in the `validation/` package implement standalone structural integrity checks:

1. **`validation/form_identifier.py`** — `identify_form_type(ocr_text: str) -> str`
   - Detects `"Party List"` when OCR text contains `ส.ส. 5/18 (บช)` or `ส.ส. 5/11 (บช)`.
   - Detects `"Constituency"` when text contains `ส.ส. 5/18` or `ส.ส. 5/11` without `(บช)`.
   - Returns `"Unknown"` for empty, whitespace-only, or unrecognised text.
   - Party List pattern checked first so merged-page text (containing both keywords) is classified as Party List.

2. **`validation/structural_auditor.py`** — Two functions:
   - `audit_units(records: List[Dict]) -> List[Dict]`: Groups records by `(Tambon, Unit)`, checks whether both `"Constituency"` and `"Party List"` appear. Returns a list of `{"Tambon", "Unit", "missing_form"}` dicts for any absent form type.
   - `generate_missing_report(missing_items, output_path)`: Writes findings to a CSV via Pandas. Always writes the file (even when `missing_items` is empty) so downstream consumers can rely on its existence.

3. **`validation/test_structural.py`** — 30 test cases across three sections:
   - 10 tests for `identify_form_type` (Party List, Constituency, Unknown, merged-text priority, whitespace tolerance, compact form without spaces).
   - 10 tests for `audit_units` (complete stations, single-form stations, unknown-only, multi-station mixed, empty input).
   - 10 tests for `generate_missing_report` (CSV file creation, correct columns, row values, empty-list header-only CSV).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | Implement Form Identifier | 6afcf08 | validation/form_identifier.py |
| 02 | Implement Structural Auditor | 427ee85 | validation/structural_auditor.py |
| 03 | Validation Script | 53dce26 | validation/test_structural.py |
| 04 | Update STATE.md | (final commit) | .planning/STATE.md, .planning/ROADMAP.md |

## Verification

Run with:
```
uv run python -m validation.test_structural
```

All 30 tests pass. Exit status: 0.

Test coverage:
- Form identifier: Party List / Constituency / Unknown paths, edge cases (empty, whitespace, compact format, merged text)
- Audit: complete stations emit no missing items; single-form stations emit correct missing-form entry; unknown-only emits both missing; multi-station correctly isolates incomplete ones; empty input returns empty
- Report: CSV written with correct schema; empty list writes header-only; UTF-8 BOM encoding

## Deviations from Plan

None - plan executed exactly as written.

The plan specified "passing unit tests with sample OCR strings" as acceptance criteria. Tests were implemented inline (matching the style of `test_linguistic_validator.py`) rather than using pytest, consistent with the existing project pattern.

## Known Stubs

None. Both `form_identifier.py` and `structural_auditor.py` are fully implemented and independently testable. Integration with the pipeline (wiring `form_type` field into records) is deferred to Phase 4.

## Self-Check: PASSED

Files confirmed to exist:
- `validation/form_identifier.py` - created with identify_form_type
- `validation/structural_auditor.py` - created with audit_units and generate_missing_report
- `validation/test_structural.py` - created, 30/30 tests passing

Commits confirmed:
- 6afcf08 - feat(02-02): implement form_identifier for election form type classification
- 427ee85 - feat(02-02): implement structural_auditor for missing election unit detection
- 53dce26 - test(02-02): add structural validation test suite - all 30 cases pass
