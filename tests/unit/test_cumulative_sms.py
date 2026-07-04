import pytest
from unittest.mock import patch, MagicMock
from extensions import db
from models.student import Student

@pytest.fixture(autouse=True)
def setup_tables(session):
    # Setup required tables in sqlite in-memory
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS cumulative_attendance (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            roll         TEXT NOT NULL,
            student_name TEXT NOT NULL,
            department   TEXT NOT NULL DEFAULT '',
            division     TEXT NOT NULL DEFAULT '',
            semester     TEXT NOT NULL DEFAULT '',
            acad_year    TEXT NOT NULL DEFAULT '',
            subject      TEXT NOT NULL,
            subject_code TEXT DEFAULT '',
            conducted    INTEGER NOT NULL DEFAULT 0,
            attended     INTEGER NOT NULL DEFAULT 0,
            percentage   REAL DEFAULT 0,
            updated_at   TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(roll, subject_code, semester, acad_year)
        );
    """))
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS parent_contacts (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone_primary VARCHAR(15) NOT NULL UNIQUE
        )
    """))
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS student_parent_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            parent_id TEXT,
            relationship_type VARCHAR(20),
            is_primary_contact BOOLEAN DEFAULT TRUE
        )
    """))
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            parent_id TEXT,
            category VARCHAR(30) NOT NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (parent_id, category)
        )
    """))
    session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS sms_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            body TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            category VARCHAR(30)
        )
    """))
    # Clear tables
    session.execute(db.text("DELETE FROM cumulative_attendance"))
    session.execute(db.text("DELETE FROM parent_contacts"))
    session.execute(db.text("DELETE FROM student_parent_mapping"))
    session.execute(db.text("DELETE FROM notification_preferences"))
    session.execute(db.text("DELETE FROM sms_templates"))
    session.execute(db.text("DELETE FROM students"))
    session.commit()

def test_notify_parents_unauthorized(client):
    # Default client session has no role set
    resp = client.post("/api/cumulative/notify-parents", json={"rolls": ["A01"]})
    assert resp.status_code == 403

def test_notify_parents_missing_parameters(client):
    with client.session_transaction() as sess:
        sess["role"] = "admin"
    resp = client.post("/api/cumulative/notify-parents", json={})
    assert resp.status_code == 400
    assert b"No student rolls provided" in resp.data

def test_notify_parents_success(client, session):
    # 1. Setup Student
    std = Student(id=101, name="Test Student", roll="A01", department="Computer", year="TY")
    session.add(std)
    session.commit()

    # 2. Setup Parent and Mapping
    session.execute(db.text("INSERT INTO parent_contacts (id, full_name, phone_primary) VALUES ('parent-uuid-1', 'Parent One', '9876543210')"))
    session.execute(db.text("INSERT INTO student_parent_mapping (student_id, parent_id) VALUES (101, 'parent-uuid-1')"))
    
    # 3. Setup Template
    session.execute(db.text("INSERT INTO sms_templates (slug, body, category) VALUES ('defaulter_alert', 'Urgent: {{student_name}} low attendance {{percentage}}.', 'attendance')"))
    
    # 4. Setup Cumulative Attendance
    session.execute(db.text("""
        INSERT INTO cumulative_attendance (roll, student_name, department, division, semester, acad_year, subject, conducted, attended, percentage)
        VALUES ('A01', 'Test Student', 'Computer', 'A', '1', '2025-26', 'Maths', 10, 5, 50.0)
    """))
    session.commit()

    # Call endpoint
    with client.session_transaction() as sess:
        sess["role"] = "admin"

    with patch("services.parent_notification_service.SMSService.queue_sms") as mock_queue:
        mock_queue.return_value = {"success": True, "id": "task_123_abc"}
        
        resp = client.post("/api/cumulative/notify-parents", json={"rolls": ["A01"]})
        assert resp.status_code == 200
        
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["notified"]) == 1
        assert data["notified"][0]["roll"] == "A01"
        assert data["notified"][0]["parent"] == "Parent One"
        
        # Verify queue_sms parameters
        mock_queue.assert_called_once()
        args, kwargs = mock_queue.call_args
        assert args[0] == "9876543210" # parent phone
        assert args[1] == "defaulter_alert"
        assert args[2]["student_name"] == "Test Student"
        assert args[2]["percentage"] == "50.0%"
