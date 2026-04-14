---
phase: "03"
plan: "03"
subsystem: validation
tags: [nan-propagation, jigsaw-design, formatters, error-handling]
dependency_graph:
  requires: [validation/linguistic_validator.py, validation/form_identifier.py, validation/structural_auditor.py]
  provides: [validation/engine.py, validation/formatters.py, validation/tests/test_jigsaw.py, demo_jigsaw.py]
  affects: []
tech_stack:
  added: [pytest]
  patterns: [jigsaw-interface, nan-sentinel-propagation, master-list-alignment]
key_files:
  created:
    - validation/engine.py
    - validation/formatters.py
    - validation/tests/__init__.py
    - validation/tests/test_jigsaw.py
    - demo_jigsaw.py
  modified:
    - validation/linguistic_validator.py
key_decisions:
  - "ElectionValidator exposes a single validate(raw_data) -> (cleaned_data, flags) interface (Jigsaw contract)"
  - "clean_score_to_int returns np.nan (not None) for all missing-data sentinels to enable downstream math propagation"
  - "Math flags use '(Missing Data)' detail string when any NaN operand is present"
  - "CSV export uses na_rep='MISSING' so auditors see explicit string not empty cells"
  - "JSON export converts np.nan to None so output is valid standard JSON"
metrics:
  duration: "~4 min"
  completed_date: "2026-04-14"
  tasks_completed: 4
  tasks_total: 4
  files_changed: 6
---

# Phase 3 Plan 03: Robust Error Propagation (Jigsaw Design) Summary

**One-liner:** Jigsaw ElectionValidator engine with np.nan propagation, master-list alignment, math consistency flags, and MISSING/null formatters — zero election_pipeline/ modifications.

## What Was Built

### Task 1 — Refactor Core Numerics (`validation/linguistic_validator.py`)

Commit: `9b7200f`

- `clean_score_to_int` now returns `np.nan` (not `None`) for `None`, `""`, `"-"`, `"—"`, `"."` inputs
- Added `try/except` around `int()` parse to return `np.nan` on any parse failure
- Added `validate_thai_word(arabic_num, thai_word)` skeleton delegating to `validate_score` for Phase 1 cross-check integration

### Task 2 — Jigsaw Engine (`validation/engine.py`)

Commit: `22b207b`

`ElectionValidator` class with stable `validate(raw_data) -> (cleaned_data, flags)` interface:

- **Score cleaning**: all raw score values run through `clean_score_to_int`; Thai digits converted
- **Master-list alignment**: absent candidates/parties filled with `np.nan`; extra raw candidates kept
- **Math consistency**:
  - `flag_math_total_used`: checks `valid + invalid + no_vote == ballots_used`; NaN operand -> `"(Missing Data)"`
  - `flag_math_valid_score`: checks `sum(candidate scores) == valid_ballots`; NaN -> `"(Missing Data)"`
- **Flags**: `flag_math_total_used`, `flag_math_valid_score`, `flag_name_mismatch`, `flag_missing_data`

### Task 3 — Formatting Utilities (`validation/formatters.py`)

Commit: `35c8d02`

- `prepare_df_for_csv(df, path=None, **kwargs)`: wraps `DataFrame.to_csv` with `na_rep="MISSING"` default; returns CSV string or writes file
- `prepare_data_for_json(data)`: recursively replaces `np.nan`/`float("nan")` with `None`; unwraps numpy scalar types to plain Python

### Task 4 — Tests and Demo

Commit: `c92711d`

- `validation/tests/test_jigsaw.py`: 46 tests covering all modules — **46/46 passing**
  - `TestCleanScoreToInt` (13 tests): NaN sentinels, Arabic/Thai digits, parse failure
  - `TestElectionValidatorNaNPropagation` (4 tests): missing candidates, sentinels, absent ballot fields
  - `TestElectionValidatorMathFlags` (6 tests): OK path, mismatch, NaN missing-data path
  - `TestElectionValidatorNameMismatch` (2 tests): known/unknown candidates
  - `TestElectionValidatorMissingDataFlag` (3 tests): complete data, NaN score, absent candidate
  - `TestPreparedfForCsv` (4 tests): NaN->MISSING, None->MISSING, no-index, file write
  - `TestPrepareDataForJson` (8 tests): scalars, dicts, lists, nested, numpy types
  - `TestJigsawIntegration` (6 tests): full mock pipeline call, Thai digits, flags, JSON safety
- `demo_jigsaw.py`: runnable demonstration of the complete flow

## Success Criteria Verification

- [x] `ElectionValidator` accepts raw pipeline dicts and returns NaN-compatible results
- [x] Math validation correctly flags NaN inputs with `"(Missing Data)"` detail
- [x] CSV export explicitly shows `"MISSING"` for failed extractions
- [x] Zero modifications to `election_pipeline/` directory (verified via git diff)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assumption about party_scores in flag_missing_data test**

- **Found during:** Task 4 test execution
- **Issue:** `test_no_missing_when_all_present` did not include `party_scores`, so master parties (Party A, Party B) were filled with NaN by the engine, causing `flag_missing_data=True` despite test intent
- **Fix:** Updated test to supply complete `party_scores` matching master parties
- **Files modified:** `validation/tests/test_jigsaw.py`
- **Commit:** `c92711d`

## Known Stubs

None — all implemented functionality is wired end-to-end.

## Self-Check: PASSED
