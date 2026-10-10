from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.db.models import Certificate
import uuid
import os
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/{certificate_id}")
def download_certificate(certificate_id: uuid.UUID, db: Session = Depends(get_db)):
    cert = db.query(Certificate).filter(Certificate.id == str(certificate_id)).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
        
    if not os.path.exists(cert.file_path):
        raise HTTPException(status_code=404, detail="Certificate file missing from storage")
        
    return FileResponse(
        cert.file_path,
        media_type="application/pdf",
        filename=f"{cert.certificate_number}.pdf",
        content_disposition_type="attachment"
    )
