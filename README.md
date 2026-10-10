# Bulk Certificate Generator API

## Overview
A production-ready FastAPI backend that accepts bulk requests for generating PDF certificates. Built with Python 3.11+, FastAPI, SQLAlchemy, Alembic, and ReportLab. It features robust request validation, background processing preventing a single broken certificate from failing the rest of the job, idempotent retries, and zip archive bundling.

## Setup & Execution

### 1. Requirements
Ensure Python 3.11+ is installed. Then setup the Virtual Environment:
```bash
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/Mac

pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env`.
```
DATABASE_URL=sqlite:///./bulk_certs.db
STORAGE_DIR=./storage
MAX_RECIPIENTS_PER_REQUEST=5000
```

### 3. Database Migrations
Create the sqlite database schema using Alembic:
```bash
alembic upgrade head
```

### 4. Run the Server
```bash
uvicorn app.main:app --reload
```
Interactive docs will be available at `http://127.0.0.1:8000/docs`.

### 5. Running Tests
You can execute the automated pytest suite using:
```bash
pytest -v
```

## How to Check Status and Retrieve Certificates

### 1. Submit a Job
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/jobs' \
  -H 'Content-Type: application/json' \
  -d '{
  "event_name": "Python Bootcamp 2026",
  "issue_date": "2026-10-01",
  "issued_by": "Tech Club",
  "recipients": [
    {"name": "Asha Kumar", "email": "asha@example.com"},
    {"name": "Ravi Shankar", "email": "ravi@example.com"}
  ]
}'
```

### 2. Check Job Status
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/jobs/<job-uuid>'
```

### 3. Paginated Items in Job
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/jobs/<job-uuid>/items?limit=10&offset=0'
```

### 4. Download a specific PDF
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/certificates/<cert-uuid>' --output cert.pdf
```

### 5. Download ZIP archive
```bash
curl -X 'GET' 'http://127.0.0.1:8000/api/v1/jobs/<job-uuid>/certificates' --output certificates.zip
```

## Design Decisions and Tradeoffs

1. **Why FastAPI over Flask/Django?**: FastAPI provides out-of-the-box Pydantic validation which fits perfectly with validating large bulk submissions, automatically building swagger docs, and offering asynchronous concurrency (useful for I/O operations).
2. **Background Processing over Celery**: We used FastAPI's `BackgroundTasks` executing in a ThreadPoolExecutor. This keeps dependencies minimal without needing a running Redis/RabbitMQ instance. If PDF generation speed/scale increases vastly, the `generate_certificate_pdf` logic can be trivially swapped into a Celery task since core logic was intentionally isolated inside `generation_service.py`.
3. **Partial Failure Handling**: Invalid recipients (e.g. duplicate emails) are recorded into the DB immediately as `invalid`. Once in background processing, each generation runs via a loop in a `try...except` boundary. An exception marks exactly one record as `failed`, leaving remaining tasks alive.
4. **Idempotency**: Processing checks if the item already has an attached `certificate_id`. Thus, if the daemon unexpectedly restarts, it can safely skip processing duplicate PDFs.
5. **Storage Abstraction**: File writing uses `LocalStorage` derived from an abstract base class `StorageInterface`. This allows dependency-injecting an S3 storage bucket later.
6. **Rate of PDF Generation Limits**: With thread pooling, large loads may strain CPU on a single node. Deployers should constrain worker limits inside gunicorn / uvicorn to throttle thread-level CPU allocations.
7. **Cleanup of old files**: Unzipping or re-requesting large ZIP blobs produces temporary files inside `/tmp` or `./storage`. Currently Python's `BackgroundTasks` or the system tmpdir takes care of unlinking, but for Prod, a CRON job sweeping `{STORAGE_DIR}/*` older than 30 days is recommended.

## Known Limitations
- Background Tasks die if the Application restarts unexpectedly. Migration to an external queue (Celery/ARQ) is mandatory for HA setups.
- SQLite does not support high concurrency out-of-the-box well, production deployments should change `DATABASE_URL` to point to a PostgreSQL DB. Table migrations are already fully setup for this natively via Alembic configurations.

## Deployment
- **Live URL**: `https://bulk-certificate-generator-ti7o.onrender.com`
- **Platform**: Render free tier, Docker runtime
- **Storage limitation**: The free tier provides no persistent disk. The SQLite database and generated PDFs are stored in `/tmp` and are lost on restart, redeploy, or inactivity. This is acceptable for a demo, but a production version must configure managed PostgreSQL and S3-compatible object storage.
- **Cold start**: The first request after the application has been idle can take 30 to 60 seconds.
