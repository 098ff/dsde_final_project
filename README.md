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
process_unit ×N         ← parallel OCR + ElectionValidator per unit (max 5 concurrent)
    │           │
    ▼           ▼
aggregate_summaries   run_structural_audit
(master_summary_log.csv)  (missing_units.csv)
```

### Components

| Directory | Role |
|---|---|
| `election_pipeline/` | Airflow DAG, OCR processor, Google Drive client, exporter |
| `validation/` | Standalone validation modules (linguistic, structural, engine, formatters) |

---

## Validation Flags

| Flag | Meaning | Action if `True` |
|---|---|---|
| `flag_math_total_used` | Valid + Invalid + No Vote ≠ Total Used | Check top section of form |
| `flag_math_valid_score` | Sum of candidate scores ≠ Total Valid Ballots | Check score table |
| `flag_name_mismatch` | Extracted name similarity < 80% vs master list | Manual mapping required |
| `flag_missing_data` | Score field could not be parsed (returns `NaN`) | Verify OCR source |
| `needs_manual_check` | Any flag above is `True` | Human-in-the-loop verification |

Missing forms per station are written to `output_data/missing_units.csv` by `run_structural_audit`.

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
```

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
| `master_summary_log.csv` | `output_data/` | One row per processed form across all units |
| `missing_units.csv` | `output_data/` | Stations missing Party List or Constituency form |

The `run_structural_audit` task runs automatically in parallel with `aggregate_summaries` — no manual step needed.

### 6. Stop Airflow

```bash
docker compose down
```

---

## Validation Module (standalone)

The `validation/` package can also be used independently of Airflow:

```python
from validation.engine import ElectionValidator
from validation.structural_auditor import audit_units, generate_missing_report
from validation.linguistic_validator import clean_score_to_int, thai_word_to_int
from validation.formatters import prepare_df_for_csv

# Validate a single parsed record
validator = ElectionValidator(master_candidates=MASTER_CANDIDATES, master_parties=MASTER_PARTIES)
cleaned_data, flags = validator.validate(parsed_data)

# Audit a batch for missing forms
missing = audit_units(records)          # records = [{"Tambon": ..., "Unit": ..., "form_type": ...}]
generate_missing_report(missing, "output_data/missing_units.csv")
```

Run tests:
```bash
uv run pytest validation/
```

---

## Contributors

- **Chanatda Konchom** (6631305321)
- Course: 2110446 Data Science and Data Engineering, Chulalongkorn University
