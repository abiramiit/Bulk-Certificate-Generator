# Deployment Guide

## Running Locally via Docker

1. **Build the image**:
   ```bash
   docker build -t bulk-cert .
   ```
2. **Run the container**:
   ```bash
   MSYS_NO_PATHCONV=1 docker run --rm -p 8000:8000 -v "$(pwd)/data:/data" -e DATABASE_URL=sqlite:////data/app.db -e STORAGE_DIR=/data/storage bulk-cert
   ```
   *(Note: The `MSYS_NO_PATHCONV=1` is useful on Windows Git Bash so paths aren't translated incorrectly).*

## Deploying to Render
1. Push this code to GitHub.
2. In the Render Dashboard, go to **New > Blueprint** or **New > Web Service**.
3. Select this repository.
4. If using Blueprint (`render.yaml`), Render will automatically provision the web service, set the environment to Docker, attach a 1GB Persistent Disk mounted at `/data`, and inject the ENV variables natively.
5. Watch the deployment logs and verify it passes the `/health` check.

## Smoke Testing the API

```bash
# Health Check
curl http://<YOUR_RENDER_URL>/health

# Create a job
curl -X 'POST' \
  'http://<YOUR_RENDER_URL>/api/v1/jobs' \
  -H 'Content-Type: application/json' \
  -d '{
  "event_name": "Testing event",
  "issue_date": "2026-10-01",
  "issued_by": "Tester",
  "recipients": [{"name": "Smoke Test User", "email": "smoke@example.com"}]
}'

# Check Job Status
curl http://<YOUR_RENDER_URL>/api/v1/jobs/<JOB_ID>

# Download Certificate
curl http://<YOUR_RENDER_URL>/api/v1/certificates/<CERTIFICATE_ID> --output test_cert.pdf
```

## Architectural Limitations & Scaling
- **Free Tier Sleeps**: Render spins down free-tier services after 15 minutes of inactivity. First requests might take up to a minute to awaken the DB and service.
- **SQLite Single Instance**: Render limits scaling because SQLite cannot survive horizontal instances concurrently modifying the `.db` file on Disk properly without complex WAL sharing. Scaling past one instance requires a centralized PostgreSQL instance.
- **Background Tasks Volatility**: In-memory `FastAPI BackgroundTasks` are wiped on server restart. Startup recovery catches these and forcibly marks them as `failed` rather than letting them pause in `processing`. Move to Celery or RQ for durable queues.
- **Unbacked up Storage**: The 1GB persistent disk holds the sqlite DB and PDFs. Free tier persistent disks might not have standard backups enabled! File system artifacts aren't pruned automatically, requiring custom cron scripts eventually.
- **Upgrade to Postgres**:
  1. Add a managed PostgreSQL instance in Render.
  2. Change `DATABASE_URL` environment variable to point to the new Postgres endpoint.
  3. No application logic changes necessary! (Alembic handles the schema).
