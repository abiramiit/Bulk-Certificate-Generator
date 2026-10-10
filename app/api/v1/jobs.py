from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.dependencies import get_db
from app.schemas.job import JobCreateRequest, JobResponse, PaginatedItemsResponse, ItemResponse
from app.services.job_service import create_job
from app.services.generation_service import process_job_background
from app.db.models import Job, CertificateItem, ItemStatus, JobStatus
from app.core.config import settings
import uuid
import zipfile
import os
import tempfile
from fastapi.responses import FileResponse

router = APIRouter()

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=JobResponse)
async def submit_job(job_in: JobCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if len(job_in.recipients) > settings.MAX_RECIPIENTS_PER_REQUEST:
        raise HTTPException(status_code=413, detail=f"Too many recipients. Maximum is {settings.MAX_RECIPIENTS_PER_REQUEST}.")
        
    job, items = create_job(db, job_in)
    
    background_tasks.add_task(process_job_background, job.id, db)
    
    return get_job_info(job.id, db)

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    return get_job_info(str(job_id), db)

def get_job_info(job_id: str, db: Session):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    counts = db.query(CertificateItem.status, func.count(CertificateItem.id)).filter(CertificateItem.job_id == job.id).group_by(CertificateItem.status).all()
    status_counts = {s: c for s, c in counts}
    
    pending = status_counts.get(ItemStatus.pending, 0)
    processing = status_counts.get(ItemStatus.processing, 0)
    succeeded = status_counts.get(ItemStatus.succeeded, 0)
    failed = status_counts.get(ItemStatus.failed, 0)
    invalid = status_counts.get(ItemStatus.invalid, 0)
    
    processed_count = succeeded + failed + invalid
    percent = (processed_count / job.total_count * 100) if job.total_count > 0 else 0
    
    return {
        "id": job.id,
        "event_name": job.event_name,
        "issue_date": job.issue_date,
        "issued_by": job.issued_by,
        "status": job.status,
        "total_count": job.total_count,
        "pending_count": pending,
        "processing_count": processing,
        "succeeded_count": succeeded,
        "failed_count": failed,
        "invalid_count": invalid,
        "percent_complete": percent,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at
    }

@router.get("/{job_id}/items", response_model=PaginatedItemsResponse)
def get_job_items(
    job_id: uuid.UUID, 
    status: ItemStatus = Query(None), 
    limit: int = Query(50, ge=1, le=1000), 
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == str(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    query = db.query(CertificateItem).filter(CertificateItem.job_id == str(job_id))
    if status is not None:
        query = query.filter(CertificateItem.status == status)
        
    total = query.count()
    items = query.order_by(CertificateItem.row_index).offset(offset).limit(limit).all()
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/{job_id}/certificates")
def download_certificates_zip(job_id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == str(job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status not in [JobStatus.completed, JobStatus.completed_with_errors]:
        raise HTTPException(status_code=409, detail="Job is not yet completed")
        
    items = db.query(CertificateItem).filter(CertificateItem.job_id == str(job_id), CertificateItem.status == ItemStatus.succeeded).all()
    if not items:
        raise HTTPException(status_code=404, detail="No successful certificates found for this job")
        
    fd, temp_path = tempfile.mkstemp(suffix=".zip", prefix=f"job_{job_id}_")
    os.close(fd)
    
    def remove_file(path: str):
        try:
            os.unlink(path)
        except Exception:
            pass
            
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for item in items:
                if item.certificate and item.certificate.file_path:
                    file_path = item.certificate.file_path
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=os.path.basename(file_path))
    except Exception as e:
        remove_file(temp_path)
        raise HTTPException(status_code=500, detail="Failed to create zip file")
        
    background_tasks.add_task(remove_file, temp_path)
    return FileResponse(temp_path, media_type="application/zip", filename=f"certificates_{job_id}.zip")
