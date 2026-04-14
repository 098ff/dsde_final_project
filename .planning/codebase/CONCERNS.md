# Codebase Concerns

**Analysis Date:** 2026-04-14

## Tech Debt

**Lack of Formal Automated Tests:**
- Issue: Critical business logic for parsing and math validation exists without unit tests.
- Why: Research-oriented project focused on rapid experimentation and manual verification via notebooks.
- Impact: Refactoring `election_pipeline/src/ocr_parser.py` is risky; regressions in Thai numeral parsing or fuzzy matching could go unnoticed.
- Fix approach: Introduce `pytest` and create test cases for `clean_score_to_int` and `validate_data`.

**Manual Retry Loops in Core Logic:**
- Issue: 3-attempt retry loops are hardcoded directly into `election_pipeline/src/processor.py`.
- Why: To handle transient 504 Gateway errors from the Typhoon VLM API.
- Impact: Makes the processor logic more complex and harder to test in isolation.
- Fix approach: Abstract API communication into a separate client class with configurable retry/backoff policies.

## Known Bugs

**504 Gateway Timeouts (API Level):**
- Symptoms: The Typhoon OCR API occasionally fails with 504 errors on large image payloads.
- Trigger: Processing full-page constituency forms without splitting, or high-density forms.
- Workaround: "Smart Chunking" (splitting images in half) is implemented in `election_pipeline/src/processor.py` to mitigate this.

## Security Considerations

**Hardcoded Secret Keys:**
- Risk: `AIRFLOW__WEBSERVER__SECRET_KEY` is hardcoded in `election_pipeline/docker-compose.yml`.
- Current mitigation: None (present in source code).
- Recommendations: Move the secret key to the `.env` file and reference it as a variable in Compose.

**OAuth Credential Management:**
- Risk: `google-auth` tokens/secrets are stored in `election_pipeline/credentials/`.
- Current mitigation: Directory is typically ignored by Git (need to verify `.gitignore`).
- Recommendations: Ensure strict `.gitignore` patterns and consider a secrets manager if moving to cloud production.

## Performance Bottlenecks

**VLM Inference Latency:**
- Problem: Calling an external VLM for OCR is significantly slower than traditional OCR (Tesserac/EasyOCR).
- Measurement: 10-30 seconds per image chunk depending on API load.
- Cause: Complexity of the Vision-Language Model serving.
- Improvement path: Parallelize at the Airflow task level (already implemented via `.expand()`) or use a faster local model for simple text regions.

## Fragile Areas

**Single-Page Assumption for Constituency Forms:**
- File: `election_pipeline/src/processor.py` (line ~28)
- Why fragile: Explicitly selects only page 0 (`[0]`) for "แบ่งเขต" forms.
- Common failures: If a constituency form ever spans two pages, the second half will be ignored.
- Safe modification: Check the total page count or use a keyword search in OCR to detect continuation pages.

**Regular Expression Parsing:**
- File: `election_pipeline/src/ocr_parser.py`
- Why fragile: Depends on highly specific Thai phrasing returned by the VLM (which may vary slightly).
- Common failures: If the Typhoon VLM changes its Markdown output format (e.g., using different headings), parsing will fail.
- Safe modification: Use a more flexible parser or prompt the VLM to return structured JSON directly (if supported).

## Scaling Limits

**Typhoon API Rate Limits:**
- Current capacity: Not explicitly documented, but current DAG limits concurrency to 5 units (`max_active_tis_per_dag=5`).
- Limit: Likely governed by SCB 10X API quotas.
- Symptoms at limit: 429 Too Many Requests errors.

## Missing Critical Features

**Optimized Image Pre-processing:**
- Problem: Currently uses global grayscale and fixed 75% quality compression.
- Blocks: Potential for accuracy loss on low-contrast forms.
- Implementation complexity: Medium (conditional sharpening or contrast adjustment).

---

*Concerns audit: 2026-04-14*
*Update as issues are fixed or new ones discovered*
