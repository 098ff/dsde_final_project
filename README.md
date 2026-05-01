# Thai Election Document OCR Pipeline (Uthai Thani - District 2)
### *Data Science & Data Engineering Project (2110446)*

End-to-end pipeline that digitizes and validates handwritten Thai election result forms (**ส.ส. 5/18**) from **Uthai Thani, Constituency District 2** using Vision-Language Models, orchestrated via Apache Airflow.

---

## Project Overview

Extracting data from election forms presents several challenges:
- **Handwritten Content** — scores recorded by local officials require robust OCR
- **Complex Structures** — tables, stamps, and signatures confuse standard OCR
- **Regional Accuracy** — names must match the official candidate list for Uthai Thani District 2

We tested two OCR approaches:
1. **Thai-TrOCR** — initial Transformer-based OCR for Thai script
2. **Typhoon Vision OCR (selected)** — Typhoon (SCB 10X) VLM for superior document understanding

---

## Architecture

```
Google Drive
    │
    ▼
discover_units          ← finds all (tambon/unit) folders
    │
    ▼
process_unit ×N         ← parallel OCR + ElectionValidator per unit
    │                      max 5 concurrent (or 1 in RATE_LIMIT mode)
    ▼
aggregate_summaries     ← flattens logs, runs structural audit,
(master_summary_log.csv)   stamps flag_missing_counterpart on every row
```

### Components

| Directory | Role |
|---|---|
| `election_pipeline/dags/` | Airflow DAG definition |
| `election_pipeline/src/` | OCR processor, Google Drive client, exporter, parser |
| `election_pipeline/validation/` | Standalone validation modules (engine, linguistic, structural, formatters) |

---

## Validation Flags

All flags appear as columns in `master_summary_log.csv`.

| Flag | Meaning | Action if `True` |
|---|---|---|
| `flag_math_total_used` | Valid + Invalid + No Vote ≠ Total Used | Check top section of form |
| `flag_math_valid_score` | Sum of candidate scores ≠ Total Valid Ballots | Check score table |
| `flag_name_mismatch` | Candidate name not found in master list | Manual name mapping required |
| `flag_missing_data` | Score or ballot field could not be parsed (`NaN`) | Verify OCR source image |
| `flag_linguistic_mismatch` | OCR score cell has conflicting digit and Thai word | Re-read score cell manually |
| `flag_ocr_timeout` | OCR API timed out after all retries for some pages/chunks | Review attached image / missing data |
| `flag_missing_counterpart` | Station is missing its paired form type | Locate and re-scan missing form |
| `needs_manual_check` | Any of the 6 per-unit flags above is `True` | Human-in-the-loop verification |

> **`flag_missing_data` vs `flag_missing_counterpart`** — these are not the same:
> - `flag_missing_data` — the form **exists** but a score or ballot field could not be read (OCR returned NaN). Action: verify the numbers on the physical form.
> - `flag_missing_counterpart` — an entire form type for a station is **absent** (e.g. station has บัญชีรายชื่อ but no แบ่งเขต). Action: locate and re-scan the missing form.
>
> `needs_manual_check` covers the first 6 per-unit flags. `flag_missing_counterpart` is set separately during aggregation and does **not** affect `needs_manual_check`.

---

## Running the Pipeline

### Prerequisites

- Docker Desktop installed and running
- Typhoon API key
- Google Drive credentials (OAuth)

### 1. Clone and navigate

```bash
git clone https://github.com/098ff/dsde_final_project.git
cd dsde_final_project/election_pipeline
```

### 2. Set up credentials

Create `.env` in `election_pipeline/`:
```env
TYPHOON_API_KEY=your_typhoon_api_key_here
GDRIVE_ROOT_FOLDER_ID=your_google_drive_folder_id
AIRFLOW_UID=1000
RATE_LIMIT=false
```

> Set `AIRFLOW_UID` to your host user ID (`id -u` on Linux/macOS). This prevents file permission conflicts between the container and your host filesystem.
>
> Set `RATE_LIMIT=true` to cap at 1 concurrent OCR request with a 3-second gap (20 req/min). Default `false` runs 5 concurrent tasks.

Authorize Google Drive access (first time only):
```bash
python auth_setup.py
```

This opens a browser — click **อนุญาต (Allow)**. A `credentials/token.json` file will be created.

### 3. Start Airflow

```bash
docker compose up -d
```

Wait ~30 seconds for the containers to initialize, then open **http://localhost:8080**

Login: `admin` / `admin`

### 4. Trigger `election_ocr_pipeline`

1. Find `election_ocr_pipeline` in the DAG list and toggle it **ON**
2. Click the **▶ Trigger DAG** button → **Trigger DAG w/ config**
3. Set the parameters:
   ```json
   {
     "amphoe": "อำเภอบ้านไร่",
     "tambons": []
   }
   ```
   Leave `tambons` empty to process all sub-districts, or specify names to filter:
   ```json
   { "amphoe": "อำเภอบ้านไร่", "tambons": ["ตำบลบ้านไร่", "ตำบลคอกควาย"] }
   ```
4. Click **Trigger**

### 5. What the DAG produces

| Output file | Location | Description |
|---|---|---|
| Per-unit CSVs | `output_data/{tambon}/{unit}/` | Parsed scores + validation flags per form |
| `master_summary_log.csv` | `output_data/` | One row per processed form — all flags included |
| `visualize_flags.ipynb` | `output_data/` | Notebook for flag visualisation and human review queue |

> `missing_units.csv` is no longer produced. Missing counterpart forms are flagged inline via `flag_missing_counterpart` in `master_summary_log.csv`.

### 6. Stop Airflow

```bash
docker compose down
```

---

## Visualising Results

Run streamlit to view the manual review queue:

```bash
streamlit run election_pipeline/validation/notebooks/streamlit_manual_review.py
```

The notebook provides:
- Flag prevalence bar chart across all records
- Flag load distribution (how many flags each record carries)
- Per-tambon heatmap
- Flag breakdown by form type
- Colour-coded table of all records needing human verification
- Drilldowns for each flag type
- Summary table per tambon

---

## Election Insights Dashboard

A second Streamlit app in `visualize/` presents three analytical insights derived from the OCR-validated election data.

```bash
streamlit run visualize/app.py
```

### Tab 1 — Vote Buying Detection (การซื้อเสียง)

**Hypothesis:** When vote buying occurs, voters mark the same party number on both the constituency (แบ่งเขต) and party-list (บัญชีรายชื่อ) ballots. This causes small/no-name parties to receive disproportionately high party-list votes at certain polling stations.

**Method:**
1. Parties are scored on 8 variables — MP ratio (district & party-list), branch count, representatives, members (log-scaled), Facebook followers (log-scaled), Google Trends (30-day sum), and historical seat wins (binary ≥ 10 seats).
2. All variables are Min-Max scaled to [0, 1], then reduced to a single **PCA Index** via PCA. Parties with PCA Index < 0.5 are classified as *small / no-name* (`small_party.csv`).
3. Any polling unit where a small party received **> 6.5%** of party-list votes is flagged as suspicious (`suspect.csv`).

**Displays:**
- Key metrics — total parties analysed, small-party count, suspicious station count
- Sortable table of small parties with PCA and scaled feature values
- Map of suspicious polling stations across Uthai Thani sub-districts

### Tab 2 — Outlier Detection

**Method:** Z-score analysis on the list/constituency vote ratio (`merged_parties_with_ratio.csv`). Parties with |z| > 2 are flagged as statistical outliers — their party-list vote share is anomalously high or low relative to the field.

**Displays:**
- Summary metrics — outlier count, mean and max z-score
- Scatter plot of z-scores across all parties, coloured by outlier status
- Filterable table of flagged parties with vote counts and ratio

### Tab 3 — Bhumjaithai Loyalty Map (แผนที่ความจงรักภักดี)

**Metric:** For each sub-district (ตำบล), the loyalty ratio is:

```
ratio = Bhumjaithai party-list votes / total valid party-list ballots
```

**Displays:**
- Summary metrics — tambon count, mean and peak loyalty ratio
- Scatter map coloured in shades of blue (light = low, dark = high Bhumjaithai support) across the 25 tambons in อ.บ้านไร่, อ.ลานสัก, อ.หนองฉาง, and อ.ห้วยคต
- Bar chart fallback with the same colour encoding when the map is unavailable

### Data files

All input files live in `visualize/data/` and are produced by the analysis notebooks in `visualization_prep_insight*/`.

| File | Source | Used by |
|---|---|---|
| `small_party.csv` | PCA party classification | Tab 1 |
| `suspect.csv` | Threshold detection (> 6.5%) | Tab 1 |
| `merged_parties_with_ratio.csv` | Z-score analysis | Tab 2 |
| `all_districts_bhumjaithai_ratio.csv` | District-level aggregation | Tab 3 |

### Dependencies

```bash
pip install visualize/requirements.txt
# streamlit, pandas, pydeck, geopandas, requests, altair
```

---

## Validation Module (standalone)

The `validation/` package can be used independently of Airflow:

```python
from validation.engine import ElectionValidator
from validation.structural_auditor import audit_units, generate_missing_report
from validation.linguistic_validator import clean_score_to_int, thai_word_to_int
from validation.formatters import prepare_df_for_csv

# Validate a single parsed record
validator = ElectionValidator(master_candidates=MASTER_CANDIDATES, master_parties=MASTER_PARTIES)
cleaned_data, flags = validator.validate(parsed_data)

# Audit a batch for missing forms
missing = audit_units(records)   # records = [{"Tambon": ..., "Unit": ..., "form_type": ...}]
generate_missing_report(missing, "output_data/missing_units.csv")
```

Run tests:
```bash
cd election_pipeline && uv run pytest validation/tests/
```

---

## Contributors

- **Chanatda Konchom** (6631305321)
- **Chatrin Yoonchalard** (6631304721) - Validation Pipeline, Visualization 
- **Rinlada Rojchanapakul** - OCR Quality Assurance
- Course: 2110446 Data Science and Data Engineering, Chulalongkorn University
