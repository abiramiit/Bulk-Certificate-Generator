import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    completed_with_errors = "completed_with_errors"
    failed = "failed"

class ItemStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    invalid = "invalid"

class Job(Base):
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_name: Mapped[str] = mapped_column(String(150), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    issued_by: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    items: Mapped[list["CertificateItem"]] = relationship("CertificateItem", back_populates="job", cascade="all, delete-orphan")
    certificates: Mapped[list["Certificate"]] = relationship("Certificate", back_populates="job", cascade="all, delete-orphan")

class CertificateItem(Base):
    __tablename__ = "certificate_items"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    row_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.pending, index=True)
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    job: Mapped["Job"] = relationship("Job", back_populates="items")
    certificate: Mapped["Certificate"] = relationship("Certificate", back_populates="item", uselist=False, cascade="all, delete-orphan")

    @property
    def certificate_id(self):
        return self.certificate.id if self.certificate else None

class Certificate(Base):
    __tablename__ = "certificates"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id: Mapped[str] = mapped_column(String, ForeignKey("certificate_items.id"), unique=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), index=True)
    
    certificate_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    item: Mapped["CertificateItem"] = relationship("CertificateItem", back_populates="certificate")
    job: Mapped["Job"] = relationship("Job", back_populates="certificates")
