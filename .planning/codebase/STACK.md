# Technology Stack

**Analysis Date:** 2026-04-14

## Languages

**Primary:**
- Python >= 3.12 - Used for all application code, data extraction, and Airflow orchestration.

**Secondary:**
- SQL (PostgreSQL 13) - Used for Airflow metadata storage.
- Markdown - Documentation.
- Dockerfile / YAML - Configuration for containerization.

## Runtime

**Environment:**
- Python 3.12 (Local and Containerized)
- Apache Airflow (running in Docker containers)

**Package Manager:**
- `uv` - Modern Python package manager/workspace tool detected in `pyproject.toml`.
- Lockfile: `uv.lock` present.
- Legacy fallback: `requirements.txt` present in `election_pipeline/`.

## Frameworks

**Core:**
- Apache Airflow 2.x - Orchestration for the data pipeline.
- Docker & Docker Compose - Container management.

**Testing:**
- No dedicated testing framework (e.g., pytest) detected in `pyproject.toml` or `requirements.txt`.
- Validation is performed inline within Jupyter Notebooks (`pipeline.ipynb`) and production scripts using logic in `src/`.

**Build/Dev:**
- `uv` - Project management and workspace orchestration.

## Key Dependencies

**Critical:**
- `typhoon-ocr` - Typhoon API client for document analysis and OCR.
- `apache-airflow` - Core orchestration logic.
- `pandas` - Data manipulation and aggregation.
- `thefuzz` - Fuzzy string matching (Levenshtein distance) for name validation.

**Infrastructure:**
- `PyMuPDF` (fitz) - PDF parsing and image extraction.
- `Pillow` (PIL) - Image processing and manipulation.
- `google-api-python-client` / `google-auth` - Interaction with Google Drive API.
- `python-dotenv` - Environment variable management.

## Configuration

**Environment:**
- `.env` files - Used to store sensitive keys (e.g., `TYPHOON_API_KEY`, `GDRIVE_ROOT_FOLDER_ID`).
- Environment variables - Airflow configuration is handled via `AIRFLOW__*` variables in `docker-compose.yml`.

**Build:**
- `pyproject.toml` - Root project configuration.
- `Dockerfile` - instructions for building the Airflow-based image.
- `docker-compose.yml` - Service orchestration and volume mapping.

## Platform Requirements

**Development:**
- Linux (tested on user system)
- Docker Desktop or Docker Engine with Compose.
- Python 3.12+.

**Production:**
- Dockerized environment running Postgres and Airflow services.
- Google Cloud Project credentials (OAuth2/Service Account) for Drive access.
- Typhoon API access.

---

*Stack analysis: 2026-04-14*
*Update after major dependency changes*
