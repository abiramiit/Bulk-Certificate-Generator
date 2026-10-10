from app.db.models import JobStatus, ItemStatus, Job, CertificateItem
import time
import pytest
from unittest.mock import patch
from app.services.generation_service import process_job_background
import asyncio

def test_create_job_validation(client, temp_storage):
    # Test oversized payload
    response = client.post("/api/v1/jobs", json={
        "event_name": "Test Event",
        "issue_date": "2026-10-01",
        "issued_by": "Issuer",
        "recipients": [{"name": "User", "email": f"user{i}@example.com"} for i in range(5001)]
    })
    assert response.status_code == 413, response.json()
    
    # Test valid but with missing fields
    response = client.post("/api/v1/jobs", json={
        "issue_date": "2026-10-01",
        "recipients": [{"name": "A", "email": "a@ex.com"}]
    })
    assert response.status_code == 422
    
def test_create_job_success_and_status(client, temp_storage, db_session):
    response = client.post("/api/v1/jobs", json={
        "event_name": "Python Bootcamp",
        "issue_date": "2026-10-01",
        "issued_by": "Tech Club",
        "recipients": [
            {"name": "Valid User", "email": "user@example.com"},
            {"name": "Duplicate User", "email": "user@example.com"} # Duplicate email within request
        ]
    })
    assert response.status_code == 202
    data = response.json()
    assert data["total_count"] == 2
    assert data["status"] == "queued"
    
    job_id = data["id"]
    status_resp = client.get(f"/api/v1/jobs/{job_id}")
    s_data = status_resp.json()
    print("JOB STATUS RESPONSE:", s_data)
    
    items_resp = client.get(f"/api/v1/jobs/{job_id}/items")
    items_data = items_resp.json()
    print("JOB ITEMS RESPONSE:", items_data)
    
    assert s_data["status"] == "completed_with_errors"
    assert s_data["succeeded_count"] == 1
    assert s_data["invalid_count"] == 1
    
    items_resp = client.get(f"/api/v1/jobs/{job_id}/items")
    items_data = items_resp.json()
    assert len(items_data["items"]) == 2
    assert items_data["items"][0]["status"] == "succeeded"
    assert items_data["items"][1]["status"] == "invalid"
