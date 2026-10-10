from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo
from typing import List, Optional
from datetime import datetime, date
import uuid
from app.db.models import JobStatus, ItemStatus

class RecipientSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Za-z\s.'-]+$")
    email: EmailStr

    @field_validator("name")
    def name_must_be_stripped(cls, v: str) -> str:
        return v.strip()

class JobCreateRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=150)
    issue_date: date
    issued_by: str = Field(..., min_length=1, max_length=150)
    recipients: List[RecipientSchema] = Field(..., min_length=1)

class ItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    status: ItemStatus
    error_message: Optional[str] = None
    certificate_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}

class JobResponse(BaseModel):
    id: uuid.UUID
    event_name: str
    issue_date: date
    issued_by: str
    status: JobStatus
    total_count: int
    pending_count: int = 0
    processing_count: int = 0
    succeeded_count: int = 0
    failed_count: int = 0
    invalid_count: int = 0
    percent_complete: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class PaginatedItemsResponse(BaseModel):
    items: List[ItemResponse]
    total: int
    limit: int
    offset: int
