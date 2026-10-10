from sqlalchemy.orm import Session
from app.db.models import Job, CertificateItem, ItemStatus
from app.schemas.job import JobCreateRequest
from typing import Tuple

def create_job(db: Session, job_data: JobCreateRequest) -> Tuple[Job, list[CertificateItem]]:
    job = Job(
        event_name=job_data.event_name,
        issue_date=job_data.issue_date,
        issued_by=job_data.issued_by,
        total_count=len(job_data.recipients)
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    items = []
    seen_emails = set()
    for index, recipient in enumerate(job_data.recipients):
        status = ItemStatus.pending
        error_msg = None
        
        if recipient.email in seen_emails:
            status = ItemStatus.invalid
            error_msg = "Duplicate email in request"
        else:
            seen_emails.add(recipient.email)
            
        item = CertificateItem(
            job_id=job.id,
            name=recipient.name,
            email=recipient.email,
            row_index=index,
            status=status,
            error_message=error_msg
        )
        db.add(item)
        items.append(item)
        
    db.commit()
    return job, items
