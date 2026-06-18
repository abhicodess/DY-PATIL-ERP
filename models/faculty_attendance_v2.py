
import json
from datetime import datetime
from utils.pg_wrapper import get_db

def ensure_faculty_attendance_v2_schema():
    conn = get_db()
    try:
        # 1. Faculty Subject Assignment Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS faculty_subject_assignments (
                id SERIAL PRIMARY KEY,
                faculty_id INTEGER NOT NULL,
                subject_id INTEGER,
                subject_name TEXT NOT NULL,
                class_name TEXT NOT NULL, -- e.g. SE-A
                department TEXT NOT NULL,
                semester TEXT NOT NULL,
                division TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(faculty_id, subject_name, class_name)
            )
        """)

        # 2. Update Attendance Sessions Table (Expanding existing one if it exists or creating it)
        # Note: attendance_model.py already has a basic one, we expand it.
        # Check and add status, lecture_type, etc.
        for column in [
            ("status", "TEXT NOT NULL DEFAULT 'draft'"),
            ("lecture_type", "TEXT NOT NULL DEFAULT 'Theory'"),
            ("academic_year", "TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(f"ALTER TABLE attendance_sessions ADD COLUMN IF NOT EXISTS {column[0]} {column[1]}")
            except Exception:
                pass

        # 3. Attendance Audit Log Table
        # (This was already in attendance_model.py, but we ensure it matches user needs)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance_audit (
                id SERIAL PRIMARY KEY,
                faculty_id INTEGER NOT NULL,
                session_id INTEGER,
                student_id INTEGER,
                action TEXT NOT NULL, -- 'CREATED', 'SUBMITTED', 'STATUS_CHANGE', 'DELETED'
                prev_status TEXT,
                new_status TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Students attendance percentage cache/summary update if needed
        # (Existing attendance_summary is likely okay)

        conn.commit()
    finally:
        conn.close()

def log_attendance_audit(faculty_id, action, session_id=None, student_id=None, prev_status=None, new_status=None, details=None):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO attendance_audit (faculty_id, session_id, student_id, action, prev_status, new_status, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (faculty_id, session_id, student_id, action, prev_status, new_status, details))
        conn.commit()
    finally:
        conn.close()
