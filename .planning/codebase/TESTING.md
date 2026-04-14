# Testing Patterns

**Analysis Date:** 2026-04-14

## Testing Approach

The project utilizes a **Validation-Led Testing** approach rather than traditional automated unit tests. Quality is ensured through rigorous mathematical and structural validation applied directly to the pipeline's output.

## Validation Engine

The core validation logic is encapsulated in `ElectionOCRParser.validate_data()`.

**Assertion Areas:**
- **Mathematical Integrity**: 
  - `Total Ballots Used == Valid + Invalid + No Vote`.
  - `Total Valid Ballots == Sum of individual candidate/party scores`.
- **Structural Integrity**:
  - Verification of Markdown table parsing.
  - Presence of required metadata (Amphoe, Tambon, Unit).
- **Label Accuracy**:
  - Fuzzy matching similarity threshold ($ \ge 80\% $) against master candidate/party lists.

## Manual Verification

For cases where automated validation fails, the system triggers a **Human-in-the-Loop** workflow.

**Manual Check Triggers:**
- Any mathematical mismatch flag set to `True`.
- `flag_name_mismatch` set to `True` (indicating OCR uncertainty in matching names).

## Run Commands (Manual Verification)

Interactive testing and verification are performed using Jupyter Notebooks:

```bash
# To run interactive tests with live data:
jupyter notebook typhoon/pipeline.ipynb
# Or run specific experiments:
jupyter notebook thai-trocr/pipeline.ipynb
```

**Verification Flow:**
1.  Run the production Airflow DAG.
2.  Inspect `election_pipeline/output_data/master_summary_log.csv`.
3.  Filter rows where `needs_manual_check` is `True`.
4.  Compare extracted data in individual CSV/JSON files against the original PDF sourced from Google Drive.

## Test Data Organization

**Location:**
- **Master Data**: Official candidate and party names are stored in `election_pipeline/src/config.py`.
- **Input Data**: Raw PDFs are fetched dynamically from Google Drive.
- **Experimental Data**: Sample result files are kept in `wikipedia-scraped/data/`.

## Quality Assurance Strategy

- **Retry Patterns**: The extraction process implements a 3-attempt retry loop for API calls to ensure successful data retrieval despite transient network issues.
- **Pre-processing Checks**: Grayscale conversion and smart chunking are validated by their ability to reduce 504 API timeouts.
- **Sanitization**: Automatic conversion of Thai numerals and removal of OCR artifacts (like `<p>` tags) is built into the parsing logic.

## Coverage

- **Logic Coverage**: Focused on the `ElectionOCRParser` and `processor.py` logic.
- **Data Coverage**: Tested across multiple election units (Amphoe/Tambon) to ensure generalizability across different form formats (Constituency vs. Party List).

---

*Testing analysis: 2026-04-14*
*Update when formal testing frameworks (e.g., pytest) are introduced*
