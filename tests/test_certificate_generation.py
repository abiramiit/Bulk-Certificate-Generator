from app.db.models import JobStatus, ItemStatus, Certificate
import os
import zipfile
from unittest.mock import patch

def test_pdf_generation(client, temp_storage, db_session):
    response = client.post("/api/v1/jobs", json={
        "event_name": "Testing event",
        "issue_date": "2026-10-01",
        "issued_by": "Tester",
        "recipients": [{"name": "Gen User", "email": "gen@example.com"}]
    })
    
    assert response.status_code == 202
    job_id = response.json()["id"]
    
    cert_item = client.get(f"/api/v1/jobs/{job_id}/items").json()["items"][0]
    cert_id = cert_item["certificate_id"]
    
    cert_db = db_session.query(Certificate).filter_by(id=cert_id).first()
    assert cert_db is not None
    assert os.path.exists(cert_db.file_path)
    
    with open(cert_db.file_path, "rb") as f:
        header = f.read(5)
        assert header.startswith(b"%PDF-")
        
    download_resp = client.get(f"/api/v1/certificates/{cert_id}")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    
def test_job_failure_isolation(client, temp_storage, db_session):
    with patch("app.services.generation_service.generate_certificate_pdf") as mock_gen:
        def side_effect(recipient_name, **kwargs):
            if recipient_name == "FailName":
                raise Exception("Forced failure")
            return b"%PDF-mock bytes"
            
        mock_gen.side_effect = side_effect
        
        response = client.post("/api/v1/jobs", json={
            "event_name": "Failure isolation",
            "issue_date": "2026-10-01",
            "issued_by": "Tester",
            "recipients": [
                {"name": "ValidName", "email": "valid@example.com"},
                {"name": "FailName", "email": "fail@example.com"}
            ]
        })
        
        assert response.status_code == 202
        job_id = response.json()["id"]
        
        s_data = client.get(f"/api/v1/jobs/{job_id}").json()
        assert s_data["status"] == "completed_with_errors"
        assert s_data["succeeded_count"] == 1
        assert s_data["failed_count"] == 1
        
        items_data = client.get(f"/api/v1/jobs/{job_id}/items").json()["items"]
        fail_item = next(i for i in items_data if i["email"] == "fail@example.com")
        valid_item = next(i for i in items_data if i["email"] == "valid@example.com")
        
        assert fail_item["status"] == "failed"
        assert fail_item["error_message"] == "Forced failure"
        assert valid_item["status"] == "succeeded"

def test_certificate_zip_download(client, temp_storage, db_session):
    response = client.post("/api/v1/jobs", json={
        "event_name": "ZIP Test",
        "issue_date": "2026-10-01",
        "issued_by": "ZIP Tester",
        "recipients": [{"name": "A", "email": "a@ex.com"}, {"name": "B", "email": "b@ex.com"}]
    })
    job_id = response.json()["id"]
    
    zip_resp = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"
