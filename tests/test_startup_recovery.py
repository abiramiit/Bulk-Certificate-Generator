import pytest
from datetime import date
from app.db.models import Job, JobStatus, ItemStatus, CertificateItem
from app.main import lifespan
from unittest.mock import patch

@pytest.mark.asyncio
async def test_startup_recovery(db_session, client):
    # Setup stale jobs
    job1 = Job(event_name="Test Event 1", issue_date=date(2026, 10, 1), issued_by="Issuer", status=JobStatus.queued)
    job2 = Job(event_name="Test Event 2", issue_date=date(2026, 10, 1), issued_by="Issuer", status=JobStatus.processing)
    db_session.add(job1)
    db_session.add(job2)
    db_session.commit()
    
    item1 = CertificateItem(job_id=job1.id, name="User1", email="user1@example.com", row_index=0, status=ItemStatus.pending)
    item2 = CertificateItem(job_id=job2.id, name="User2", email="user2@example.com", row_index=0, status=ItemStatus.processing)
    db_session.add(item1)
    db_session.add(item2)
    db_session.commit()

    from sqlalchemy.orm import sessionmaker
    TestSessionLocal = sessionmaker(bind=db_session.get_bind())
    
    with patch("app.main.SessionLocal", TestSessionLocal):
        async with lifespan(client.app):
            pass
        
    db_session.expire_all()
    
    assert job1.status == JobStatus.failed
    assert job2.status == JobStatus.failed
    assert item1.status == ItemStatus.failed
    assert item1.error_message == "Interrupted by server restart"
    assert item2.status == ItemStatus.failed
