# 🗳️ Thai Election Document OCR Pipeline (Uthai Thani - District 2)
### *Data Science & Data Engineering Project (2110446)*

This repository implements an end-to-end data engineering pipeline designed to digitize and validate handwritten Thai election result forms (**ส.ส. 5/18**) from **Uthai Thani, Constituency District 2**. 

The project focuses on transforming complex, handwritten physical records into structured, high-quality digital data using state-of-the-art Vision-Language Models (VLMs), orchestrated via **Apache Airflow**.

---

## 📌 Project Overview & Challenges
Extracting data from election forms in Uthai Thani District 2 presents several data engineering challenges:
* **Handwritten Content:** Scores and counts are manually recorded by local officials, requiring robust OCR.
* **Complex Structures:** Official forms contain intricate tables, stamps, and signatures that can confuse standard OCR.
* **Regional Accuracy:** Extracted data must be strictly aligned with the specific candidate list of **Uthai Thani District 2**.

### 🧪 Methodology & Experiments
We experimented with two primary approaches to find the most resilient solution:
1.  **Thai-TrOCR:** Initial testing with Transformer-based OCR specialized for Thai script.
2.  **Typhoon Vision OCR (Selected):** A high-level pipeline using the **Typhoon (SCB 10X)** VLM for superior document understanding and structured extraction.

---

## ⚙️ Data Engineering Pipeline
Our pipeline is built on the principles of **Resilience** and **Data Quality**:

1.  **Image Pre-processing & Optimization:**
    * **Grayscale Conversion:** Reduces payload size to improve API response time.
    * **Smart Chunking:** For high-density "แบบแบ่งเขต" forms, the system splits images into segments to prevent **504 Gateway Timeouts** and enhance focus.
2.  **Adaptive Routing:**
    * *Constituency (แบ่งเขต):* Optimized for single-page extraction with image splitting.
    * *Party List (บัญชีรายชื่อ):* Processes multi-page documents with high-ratio compression.
3.  **Data Sanitization:** Automated mapping of Thai numerals (๑-๙) to Arabic (1-9) and removal of OCR noise.
4.  **Parallel Processing:** Uses Airflow's Dynamic Task Mapping to process multiple election units simultaneously.

---

## 🧪 Data Science & Validation
To ensure data integrity (Data Quality Assurance), the pipeline implements several validation flags:

| Flag | Description | Action if `True` |
| :--- | :--- | :--- |
| `flag_math_total_used` | Sum of (Valid + Invalid + No Vote) $\neq$ Total Used | Check top section of the form |
| `flag_math_valid_score` | Sum of candidate scores $\neq$ Total Valid Ballots | Check score table values |
| `flag_name_mismatch` | Extracted name similarity < 80% vs. Master Data | Manual mapping required |
| `needs_manual_check` | Triggered if any of the above are True | **Human-in-the-loop** verification |

**Fuzzy Matching:** We utilize Levenshtein distance (via `thefuzz`) to automatically correct minor OCR misspellings in candidate and party names against the official master list.

---

## 🚀 The Final Pipeline (`/election_pipeline`)
The `/election_pipeline` directory contains the production-ready version of this project. It connects directly to Google Drive to fetch election forms, processes them using Typhoon API, and aggregates the results—all orchestrated automatically by **Docker** and **Apache Airflow**.

### 🛠️ Getting Started (Airflow Version)

**1. Clone the repository & Navigate:**
   ```bash
   git clone https://github.com/098ff/dsde_final_project.git
   cd dsde_final_project/election_pipeline
   ```

**2. Setup Credentials:**
   * Create a `.env` file in the root of the `election_pipeline` folder:
     ```env
     TYPHOON_API_KEY=your_typhoon_api_key_here
     ```
   * Place your Google Drive OAuth credential file (`client_secret.json` or `token.json`) inside the designated folder (e.g., `src/`).

**3. Configure Target Google Drive Folder:**
   * Open `src/config.py`.
   * Update the `GDRIVE_ROOT_FOLDER_ID` to match the exact ID of your target folder on Google Drive (e.g., the folder for "อุทัยธานี_เขต2").
     ```python
     GDRIVE_ROOT_FOLDER_ID = 'your_google_drive_folder_id'
     ```

**4. Start the Airflow Environment:**
   Make sure you have Docker Desktop running, then start the containers:
   ```bash
   docker compose up -d
   ```

**5. Trigger the Pipeline:**
   * Open your browser and go to **`http://localhost:8080`**.
   * Login to Airflow (Default credentials: `admin` / `admin`).
   * Turn the toggle **ON** for the `election_ocr_pipeline` DAG.
   * Click the **Play** button (▶️) and select **"Trigger DAG w/ config"**.
   * Verify the parameters (e.g., `"amphoe": "อำเภอบ้านไร่"`) and click **Trigger**.

*(Note: If you only want to run standard tests without the Airflow orchestrator, you can still open and run the cells in `pipeline.ipynb`.)*

---

## 👨‍💻 Contributors
* **Chanatda Konchom** (6631305321)
* Course: 2110446 Data Science and Data Engineering, Chulalongkorn University.