# Architecture

**Analysis Date:** 2026-04-14

## System Overview

The Thai Election Document OCR Pipeline is an end-to-end data engineering system designed to digitize handwritten election forms using Vision-Language Models (VLM). It is architected for **resilience**, **scalability** (via parallel processing), and **data quality** (via multi-stage validation).

## Core Patterns

- **Orchestrator-Worker Architecture**:
  - **Orchestrator**: Apache Airflow managing DAG execution, dynamic task mapping, and retries.
  - **Workers**: Distributed Airflow tasks (using `LocalExecutor`) performing data-heavy operations (Image processing, API calls).
- **Dynamic Task Mapping**: The pipeline dynamically scales the number of processing tasks based on the number of election units discovered in Google Drive.
- **Fail-Safe Processing**: Implementation of image chunking and retry logic to mitigate API timeouts and 504 Gateway errors common with large vision tasks.

## Key Components

- **`election_dag.py` (The Orchestrator)**:
  - Discovers Amphoe/Tambon/Unit folder structures in Google Drive.
  - Triggers parallel worker tasks for each election unit.
  - Aggregates final logs and reports.
- **`processor.py` (The Engine)**:
  - Handles PDF to Image conversion using `PyMuPDF`.
  - Implements **Smart Chunking** for high-density forms (splitting images into segments).
  - Manages grayscale conversion and compression to optimize payload size.
  - Interface for the `typhoon-ocr` API.
- **`ocr_parser.py` (The Brain)**:
  - Parses Markdown text returned by the VLM into structured candidate/party scores.
  - Implements fuzzy matching logic using `thefuzz` against official candidate lists.
- **`exporter.py` (The Sink)**:
  - Handles local file persistence (CSV/JSON).
  - Generates summary reports and audit logs.

## Data Flow

1.  **Discovery**: Scan Google Drive for new election unit folders.
2.  **Extraction**: Download PDFs to local temporary storage.
3.  **Transformation (Image)**:
    - PDF $\rightarrow$ Grayscale PNG.
    - Smart Chunking: Split into half-page blocks for "Constituency" forms.
    - Export to compressed JPEG for API transmission.
4.  **Inference**: Call Typhoon OCR API to get document transcription (Markdown).
5.  **Transformation (Structured)**:
    - Markdown $\rightarrow$ JSON/Dictionary format.
    - Fuzzy matching of candidate/party names.
6.  **Validation**: Apply math checks (Total Ballots vs. Sum of Scores).
7.  **Export**: Write individual results and aggregate summary logs.

## Quality & Validation Strategy

The architecture emphasizes "Human-in-the-Loop" for high-uncertainty data. A `needs_manual_check` flag is triggered by:
- **Math Total Used**: Sum of (Valid + Invalid + No Vote) $\neq$ Total Ballots Used.
- **Math Valid Score**: Sum of individual candidate scores $\neq$ Total Valid Ballots reported.
- **Name Mismatch**: Fuzzy matching similarity falls below a threshold (80%) against master data.

## Deployment Architecture

The system is deployed as a stack of Docker containers:
- `airflow-webserver`: UI for monitoring and manual triggering.
- `airflow-scheduler`: Manages task timing and dependencies.
- `postgres`: Persistent metadata database.
- `airflow-init`: One-time setup and migration service.
- **Shared Volumes**: Persistent storage for input credentials, output data, and shared source code.

---

*Architectural analysis: 2026-04-14*
*Update after major system redesigns*
