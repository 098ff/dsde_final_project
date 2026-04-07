# 🗳️ Thai Election Document OCR Pipeline (Uthai Thani - District 2)
### *Data Science & Data Engineering Project (2110446)*

This repository implements an end-to-end data engineering pipeline designed to digitize and validate handwritten Thai election result forms (**ส.ส. 5/18**) from **Uthai Thani, Constituency District 2**. 

The project focuses on transforming complex, handwritten physical records into structured, high-quality digital data using state-of-the-art Vision-Language Models (VLMs).

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

## 🛠️ Getting Started

1. **Clone the repo:**
   ```bash
   git clone https://github.com/098ff/dsde_final_project.git
   ```
2. **Setup Environment:**
   Create a `.env` file and add your Typhoon API Key:
   ```env
   TYPHOON_API_KEY=your_key_here
   ```
3. **Run the Pipeline:**
   Open `pipeline.ipynb` and run all cells.

---

## 👨‍💻 Contributors
* **Chanatda Konchom** (6631305321)
* Course: 2110446 Data Science and Data Engineering, Chulalongkorn University.
