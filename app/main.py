from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from app.core.config import settings
from app.api.v1 import jobs, certificates
from app.db.session import engine, SessionLocal
from app.db import models
from app.db.models import Job, JobStatus, ItemStatus
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    
    # Startup Recovery: fail stale jobs interrupted by previous server restart
    try:
        db = SessionLocal()
        stale_jobs = db.query(Job).filter(Job.status.in_([JobStatus.queued, JobStatus.processing])).all()
        for job in stale_jobs:
            job.status = JobStatus.failed
            logger.warning(f"Marked stale job {job.id} as failed due to server restart.")
            
            for item in job.items:
                if item.status in [ItemStatus.pending, ItemStatus.processing]:
                    item.status = ItemStatus.failed
                    item.error_message = "Interrupted by server restart"
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error during startup recovery: {str(e)}")
        
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        loc = ".".join([str(l) for l in error.get("loc", [])])
        errors.append({"field": loc, "message": error.get("msg")})
    return JSONResponse(
        status_code=422,
        content={"detail": errors}
    )

app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(certificates.router, prefix="/api/v1/certificates", tags=["Certificates"])
