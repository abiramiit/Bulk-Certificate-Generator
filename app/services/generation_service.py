import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import Job, CertificateItem, Certificate, JobStatus, ItemStatus
from app.certificates.generator import generate_certificate_pdf
from app.storage.local_storage import LocalStorage

logger = logging.getLogger(__name__)

async def process_job_background(job_id: str, db: Session):
    def _run_processing():
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status != JobStatus.queued:
            return
            
        job.status = JobStatus.processing
        job.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # We also want to include any invalid items in our status check eventually, but here we process pending ones.
        items = db.query(CertificateItem).filter(CertificateItem.job_id == job_id, CertificateItem.status == ItemStatus.pending).all()
        storage = LocalStorage()
        
        for item in items:
            try:
                # idempotency check
                if item.certificate:
                    item.status = ItemStatus.succeeded
                    db.commit()
                    continue
                    
                item.status = ItemStatus.processing
                db.commit()
                
                # generate unique number
                cert_number = f"CERT-{job.id[:8]}-{item.id[:8]}"
                
                # generate PDF
                pdf_bytes = generate_certificate_pdf(
                    recipient_name=item.name,
                    event_name=job.event_name,
                    issue_date=job.issue_date,
                    issued_by=job.issued_by,
                    certificate_number=cert_number
                )
                
                filename = f"{cert_number}.pdf"
                file_path = storage.save_file(pdf_bytes, filename)
                
                # create certificate record
                cert = Certificate(
                    item_id=item.id,
                    job_id=job.id,
                    certificate_number=cert_number,
                    file_path=file_path
                )
                db.add(cert)
                db.commit()
                db.refresh(cert)
                
                # update item
                item.status = ItemStatus.succeeded
                db.commit()
                
            except Exception as e:
                logger.error(f"Failed to process item {item.id}: {str(e)}")
                db.rollback()
                
                # Refetch item in case of rollback
                item_re = db.query(CertificateItem).filter(CertificateItem.id == item.id).first()
                if item_re:
                    item_re.status = ItemStatus.failed
                    item_re.error_message = str(e)
                    db.commit()
        
        # update job status
        failed_invalid_count = db.query(CertificateItem).filter(
            CertificateItem.job_id == job.id, 
            CertificateItem.status.in_([ItemStatus.failed, ItemStatus.invalid])
        ).count()
        
        if failed_invalid_count > 0:
            job.status = JobStatus.completed_with_errors
        else:
            job.status = JobStatus.completed
            
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_processing)
