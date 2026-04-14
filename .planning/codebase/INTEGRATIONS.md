# External Integrations

**Analysis Date:** 2026-04-14

## APIs & External Services

**Document OCR & Analysis:**
- **Typhoon OCR (SCB 10X)** - Used for extracting structured data from handwritten Thai election forms.
  - SDK/Client: `typhoon-ocr` Python package.
  - Auth: API key stored in `TYPHOON_API_KEY` environment variable.
  - Usage: Vision-Language Model inference on document images.

**Cloud Storage:**
- **Google Drive API** - Used as the source for raw election document images and potentially as an output destination.
  - SDK/Client: `google-api-python-client`, `google-auth-oauthlib`.
  - Auth: OAuth2 credentials (typically `client_secret.json` or `token.json`) stored in the `credentials/` directory.
  - Configuration: `GDRIVE_ROOT_FOLDER_ID` env var specifies the target folder.

**Data Scraping:**
- **Wikipedia** - Used in experiments for scraping master lists of election candidates and results.
  - Integration method: Web scraping using `requests` and `beautifulsoup4`.
  - Rate limits: Not explicitly handled, but typically governed by standard crawler courtesy.

## Data Storage

**Databases:**
- **PostgreSQL 13** - Backend database for Apache Airflow metadata.
  - Connection: Configured via `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`.
  - Client: `psycopg2` (standard Airflow postgres provider).
  - Persistence: Docker volume `postgres-db-volume` mapping to `/var/lib/postgresql/data`.

**File Storage:**
- **Local / Docker Volumes** - Used for intermediate data processing and structured output.
  - Volumes:
    - `output_data/` mapped to `/opt/airflow/output_data` - Stores processed CSVs and JSONs.
    - `dags/` mapped to `/opt/airflow/dags` - Stores Airflow DAG definitions.
    - `src/` mapped to `/opt/airflow/src` - Stores shared utility code.

## Authentication & Identity

**API Authentication:**
- **Environment Variables**: Sensitive keys (`TYPHOON_API_KEY`, `GDRIVE_ROOT_FOLDER_ID`) are managed via `.env` files and loaded via `python-dotenv`.
- **Secret Keys**: Airflow webserver uses `AIRFLOW__WEBSERVER__SECRET_KEY` for session security.

**Service Authentication:**
- **Google OAuth2**: Implementation uses file-based token storage in the `credentials/` directory relative to the repository root.

## CI/CD & Deployment

**Hosting:**
- **Dockerized Environment** - The entire pipeline is designed to run within Docker containers orchestrated by Docker Compose.
- **Local Dev**: Standard `docker compose up` workflow.

## Environment Configuration

**Development:**
- Required env vars: `TYPHOON_API_KEY`, `GDRIVE_ROOT_FOLDER_ID`.
- Secrets location: `.env` file (gitignored).
- Mock/stub services: None explicitly mentioned, but `pipeline.ipynb` allows for local execution without Airflow.

---

*Integration audit: 2026-04-14*
*Update when adding/removing external services*
