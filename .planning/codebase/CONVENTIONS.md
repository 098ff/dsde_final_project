# Coding Conventions

**Analysis Date:** 2026-04-14

## Naming Patterns

**Files:**
- `snake_case.py` for all production Python modules and scripts.
- `kebab-case.ipynb` for experimental and prototyping notebooks.
- `snake_case.py` within `dags/` for Airflow pipeline definitions.

**Functions:**
- `snake_case` for all functions and methods (e.g., `process_pdf`, `clean_score_to_int`).
- `handle_event_name` pattern for event-driven logic if any.

**Variables:**
- `snake_case` for local and member variables.
- `UPPER_SNAKE_CASE` for global constants and configuration (e.g., `MASTER_CANDIDATES`, `GDRIVE_ROOT_FOLDER_ID`).

**Classes:**
- `PascalCase` for class definitions (e.g., `ElectionOCRParser`).

## Code Style

**Formatting:**
- Indentation: 4 spaces (standard PEP 8).
- Line Length: Generally kept within 88-100 characters.
- Quotes: Double quotes used for strings, especially those containing Thai text or internal single quotes.

**Thai Language Integration:**
- Use of Thai numerals (`๑-๙`) within regex patterns: `r'[\d,๑-๙]+'`.
- Thai-specific cleaning: `thai_digits = "๐๑๒๓๔๕๖๗๘๙"` used for translation to Arabic numerals.

## Import Organization

**Order:**
1. Standard library imports (`os`, `re`, `shutil`, `tempfile`).
2. Third-party packages (`pandas`, `fitz`, `PIL`, `typhoon_ocr`, `airflow`).
3. Local application modules (`src.config`, `src.processor`).

**Grouping:**
- Blank line between standard library, third-party, and local imports.

## Error Handling

**Patterns:**
- **Graceful Degradation**: Functions like `clean_score_to_int` return a default value (e.g., `0`) rather than raising an exception for malformed input.
- **Retry Logic**: API-dependent functions (Typhoon OCR) implement a 3-attempt retry loop with `time.sleep()` to handle transient network issues or 504 Gateway Timeouts.
- **Validation Flags**: Instead of throwing errors, validation failures are captured as Boolean flags (`flag_math_total_used`) in a results dictionary for downstream auditing.

## Logging

**Framework:**
- **Console Output**: Extensive use of `print()` for real-time progress logging in the Airflow task scheduler and worker logs.
- **Structured Logs**: The pipeline generates a `master_summary_log.csv` which acts as a structured audit trail for all processed units.

## Comments

**When to Comment:**
- **Translation Documentation**: Explain what specific Thai terms mean in the context of the code.
- **Regex Explanation**: Briefly describe what complex regex patterns are intended to extract.
- **Business logic**: Document math validation rules (e.g., `Valid + Invalid + No Vote == Total Used`).

## Function Design

**Size:**
- Production methods are generally kept under 50 lines.
- Complex logic (like the Airflow DAG) is split into decorated `@task` functions.

**Parameters:**
- Uses standard positional and keyword arguments.
- Context is passed via dictionary `unit_info` in Airflow tasks.

---

*Convention analysis: 2026-04-14*
*Update when patterns change*
