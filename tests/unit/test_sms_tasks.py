import pytest
import os
import json
from unittest.mock import MagicMock, patch
from extensions import db
from tasks.sms_tasks import send_async_sms
from services.sms.twilio_gw import DummyProvider

@pytest.fixture(autouse=True)
def setup_raw_tables(session):
    # Setup tables in in-memory SQLite for testing
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS sms_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            body TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
        )
    """))
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS sms_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            provider TEXT NOT NULL,
            status TEXT NOT NULL,
            provider_ref TEXT,
            meta_data TEXT,
            error_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    # Clear tables to ensure test isolation
    session.execute(db.text("DELETE FROM sms_templates"))
    session.execute(db.text("DELETE FROM sms_logs"))
    session.commit()

def test_send_async_sms_success(session):
    # Insert template
    session.execute(db.text("INSERT INTO sms_templates (slug, body) VALUES ('test_slug', 'Hello {{name}}!')"))
    session.commit()

    # Mock task state using celery request stack
    mock_req = MagicMock()
    mock_req.retries = 0
    send_async_sms.request_stack.push(mock_req)
    
    try:
        with patch('services.sms.factory.SMSFactory.get_provider') as mock_get_provider:
            mock_provider = DummyProvider()
            mock_get_provider.return_value = mock_provider
            
            res = send_async_sms.run("919999999999", "test_slug", {"name": "World"})
            
            assert res["success"] is True
            assert res["id"] == "DUMMY_REF_123"
            
            # Verify database record
            log = session.execute(db.text("SELECT * FROM sms_logs")).fetchone()
            assert log is not None
            assert log[1] == "919999999999" # recipient
            assert log[2] == "Hello World!" # message
            assert log[4] == "delivered" # status
    finally:
        send_async_sms.request_stack.pop()

def test_send_async_sms_template_not_found(session):
    # Mock task state
    mock_req = MagicMock()
    mock_req.retries = 0
    send_async_sms.request_stack.push(mock_req)
    
    try:
        res = send_async_sms.run("919999999999", "missing_slug", {"name": "World"})
        assert res["success"] is False
        assert "not found" in res["error"]
        
        # Verify database failure log
        log = session.execute(db.text("SELECT * FROM sms_logs")).fetchone()
        assert log is not None
        assert log[4] == "failed"
        assert "not found" in log[7] # error_log
    finally:
        send_async_sms.request_stack.pop()

def test_send_async_sms_provider_failure_retry(session):
    # Insert template
    session.execute(db.text("INSERT INTO sms_templates (slug, body) VALUES ('test_slug', 'Hello!')"))
    session.commit()

    # Mock task state and retry method
    mock_req = MagicMock()
    mock_req.retries = 0
    send_async_sms.request_stack.push(mock_req)
    
    try:
        with patch('services.sms.factory.SMSFactory.get_provider') as mock_get_provider, \
             patch.object(send_async_sms, 'retry', side_effect=RuntimeError("Retry called")) as mock_retry:
            
            mock_prov = MagicMock()
            mock_prov.send_sms.return_value = {"success": False, "id": None, "error": "Network timeout", "raw": {}}
            mock_get_provider.return_value = mock_prov
            
            with pytest.raises(RuntimeError, match="Retry called"):
                send_async_sms.run("919999999999", "test_slug", {})
                
            log = session.execute(db.text("SELECT * FROM sms_logs")).fetchone()
            assert log is not None
            assert log[4] == "failed"
            assert "Network timeout" in log[7]
    finally:
        send_async_sms.request_stack.pop()
