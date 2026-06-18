import pytest
import os
import json
from unittest.mock import MagicMock, patch
from extensions import db
from services.notification_service import NotificationService

@pytest.fixture(autouse=True)
def setup_raw_tables(session):
    # Setup all required tables in in-memory SQLite for testing
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
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS whatsapp_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT UNIQUE NOT NULL,
            body TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS communications_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            recipient TEXT NOT NULL,
            template_name TEXT,
            message TEXT NOT NULL,
            status TEXT NOT NULL,
            provider TEXT,
            provider_ref TEXT,
            meta_data TEXT,
            error_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    # Clear tables to guarantee test isolation
    session.execute(db.text("DELETE FROM sms_templates"))
    session.execute(db.text("DELETE FROM sms_logs"))
    session.execute(db.text("DELETE FROM whatsapp_templates"))
    session.execute(db.text("DELETE FROM communications_log"))
    session.commit()

def test_send_whatsapp_success(session):
    # Insert template
    session.execute(db.text("INSERT INTO whatsapp_templates (template_name, body) VALUES ('welcome_tmpl', 'Welcome {{name}}!')"))
    session.commit()

    # Patch requests.post globally and inside notification_service
    with patch('services.notification_service.requests.post') as mock_post:
        # Mock successful Gupshup response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messageId": "GS_REF_123", "status": "submitted"}
        mock_post.return_value = mock_response

        res = NotificationService.send_whatsapp("919999999999", "welcome_tmpl", {"name": "User"})
        
        assert res["success"] is True
        assert res["channel"] == "whatsapp"
        assert res["provider_ref"] == "GS_REF_123"

        # Verify DB logs
        log = session.execute(db.text("SELECT * FROM communications_log")).fetchone()
        assert log is not None
        assert log[2] == "919999999999" # recipient
        assert log[3] == "welcome_tmpl" # template_name
        assert log[4] == "Welcome User!" # message
        assert log[5] == "sent" # status
        assert log[6] == "gupshup" # provider
        assert log[7] == "GS_REF_123" # provider_ref

def test_send_whatsapp_template_not_found(session):
    # Setup SMS template since fallback will fetch it
    session.execute(db.text("INSERT INTO sms_templates (slug, body) VALUES ('non_existent_tmpl', 'SMS: Welcome!')"))
    session.commit()

    with patch('services.sms.factory.SMSFactory.get_provider') as mock_sms_provider:
        mock_provider = MagicMock()
        mock_provider.send_sms.return_value = {"success": True, "id": "SMS_FALLBACK_123", "error": None, "raw": {}}
        mock_sms_provider.return_value = mock_provider

        res = NotificationService.send_whatsapp("919999999999", "non_existent_tmpl", {"name": "User"})
        
        assert res["success"] is True
        assert res["channel"] == "sms_fallback"
        assert "not found" in res["error"]

        # Verify communications_log entry shows failure and details
        log = session.execute(db.text("SELECT * FROM communications_log")).fetchone()
        assert log is not None
        assert log[5] == "failed"
        assert "not found" in log[9] # error_log

def test_send_whatsapp_gupshup_failure_fallback(session):
    # Insert template
    session.execute(db.text("INSERT INTO whatsapp_templates (template_name, body) VALUES ('welcome_tmpl', 'Welcome!')"))
    session.execute(db.text("INSERT INTO sms_templates (slug, body) VALUES ('welcome_tmpl', 'SMS: Welcome!')"))
    session.commit()

    with patch('services.notification_service.requests.post') as mock_post, \
         patch('services.sms.factory.SMSFactory.get_provider') as mock_sms_provider:
        
        # Mock Gupshup API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # Mock SMS fallback success
        mock_provider = MagicMock()
        mock_provider.send_sms.return_value = {"success": True, "id": "SMS_FALLBACK_123", "error": None, "raw": {}}
        mock_sms_provider.return_value = mock_provider

        res = NotificationService.send_whatsapp("919999999999", "welcome_tmpl", {})
        
        assert res["success"] is True
        assert res["channel"] == "sms_fallback"
        assert "Gupshup API returned status 500" in res["error"]

        # Verify DB logs show failure and error info
        log = session.execute(db.text("SELECT * FROM communications_log")).fetchone()
        assert log is not None
        assert log[5] == "failed"
        assert "Gupshup API returned status 500" in log[9]
