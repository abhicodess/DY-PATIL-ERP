import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash
from utils.pg_wrapper import get_db, qone
from extensions import db

class Attendance(db.Model):
    __tablename__ = 'attendance'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'lecture_id', name='uq_attendance_student_lecture'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    remark = db.Column(db.String(255), default='')
    time_slot = db.Column(db.String(50), default='')
    faculty = db.Column(db.String(100), default='')
    division = db.Column(db.String(50), default='')
    semester = db.Column(db.String(50), default='')
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
    lecture_id = db.Column(db.Integer, nullable=True)
    subject_id = db.Column(db.Integer, nullable=True)
    faculty_id = db.Column(db.Integer, nullable=True)
    method = db.Column(db.String(50), default='Manual')
    branch = db.Column(db.String(50), default='')
    is_locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

BACKUP_DIR = "backups"
ATTENDANCE_BACKUP_DIR = os.path.join(BACKUP_DIR, "attendance_uploads")


def _get_default_student_password():
    password = os.environ.get("DEFAULT_STUDENT_PASSWORD")
    if not password:
        raise RuntimeError("DEFAULT_STUDENT_PASSWORD must be set in environment variables")
    return password


# FIX: Ensure attendance_summary table exists and handle SQLite ALTER TABLE and SERIAL compatibility
def ensure_attendance_upload_tables():
    conn = get_db()
    
    # Detect SQLite testing mode
    is_sqlite = False
    from flask import current_app
    try:
        if current_app and current_app.config.get("TESTING"):
            is_sqlite = True
    except Exception:
        pass

    batches_sql = """
        CREATE TABLE IF NOT EXISTS attendance_upload_batches (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            uploader_role TEXT NOT NULL,
            uploader_id INTEGER,
            department TEXT DEFAULT '',
            division TEXT DEFAULT '',
            semester TEXT DEFAULT '',
            report_start_date DATE NULL,
            report_end_date DATE NULL,
            total_students INTEGER NOT NULL DEFAULT 0,
            total_subject_rows INTEGER NOT NULL DEFAULT 0,
            avg_attendance NUMERIC(6,2) NOT NULL DEFAULT 0,
            defaulters INTEGER NOT NULL DEFAULT 0,
            backup_path TEXT DEFAULT '',
            restore_source_batch_id INTEGER NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    rows_sql = """
        CREATE TABLE IF NOT EXISTS attendance_upload_rows (
            id SERIAL PRIMARY KEY,
            batch_id INTEGER NOT NULL,
            student_id INTEGER,
            roll_no TEXT NOT NULL,
            student_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            subject_code TEXT DEFAULT '',
            lecture_type TEXT DEFAULT '',
            attended_classes INTEGER NOT NULL DEFAULT 0,
            total_classes INTEGER NOT NULL DEFAULT 0,
            percentage NUMERIC(6,2) NOT NULL DEFAULT 0,
            department TEXT DEFAULT '',
            division TEXT DEFAULT '',
            semester TEXT DEFAULT '',
            report_start_date DATE NULL,
            report_end_date DATE NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (roll_no, subject, report_start_date, report_end_date)
        )
    """

    summary_sql = """
        CREATE TABLE IF NOT EXISTS attendance_summary (
            id SERIAL PRIMARY KEY,
            student_id INTEGER,
            student_name TEXT,
            subject TEXT NOT NULL,
            attended INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            division TEXT DEFAULT '',
            semester TEXT DEFAULT '',
            department TEXT DEFAULT '',
            report_start_date DATE NULL,
            report_end_date DATE NULL,
            upload_batch_id INTEGER NULL,
            UNIQUE(student_id, subject)
        )
    """

    if is_sqlite:
        batches_sql = batches_sql.replace("id SERIAL PRIMARY KEY", "id INTEGER PRIMARY KEY AUTOINCREMENT")
        rows_sql = rows_sql.replace("id SERIAL PRIMARY KEY", "id INTEGER PRIMARY KEY AUTOINCREMENT")
        summary_sql = summary_sql.replace("id SERIAL PRIMARY KEY", "id INTEGER PRIMARY KEY AUTOINCREMENT")

    try:
        # Create tables
        conn.execute(summary_sql)
        conn.execute(batches_sql)
        conn.execute(rows_sql)
        
        for sql in (
            "ALTER TABLE attendance_summary ADD COLUMN IF NOT EXISTS department TEXT DEFAULT ''",
            "ALTER TABLE attendance_summary ADD COLUMN IF NOT EXISTS report_start_date DATE NULL",
            "ALTER TABLE attendance_summary ADD COLUMN IF NOT EXISTS report_end_date DATE NULL",
            "ALTER TABLE attendance_summary ADD COLUMN IF NOT EXISTS upload_batch_id INTEGER NULL",
        ):
            try:
                conn.execute(sql)
            except Exception:
                # SQLite raises operational/syntax errors since it doesn't support IF NOT EXISTS in ALTER TABLE
                pass
        conn.commit()
    finally:
        conn.close()


def create_upload_backup(payload):
    os.makedirs(ATTENDANCE_BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(ATTENDANCE_BACKUP_DIR, f"attendance_upload_{stamp}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=True)
    return path


def load_backup_payload(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def persist_attendance_upload(parse_result, uploader_role, uploader_id):
    ensure_attendance_upload_tables()
    backup_payload = {
        "metadata": parse_result.metadata,
        "analytics": parse_result.analytics,
        "students": parse_result.students,
        "normalized_rows": parse_result.normalized_rows,
    }
    backup_path = create_upload_backup(backup_payload)
    conn = get_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO attendance_upload_batches
                (filename, uploader_role, uploader_id, department, division, semester,
                 report_start_date, report_end_date, total_students, total_subject_rows,
                 avg_attendance, defaulters, backup_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                parse_result.metadata.get("source_filename", ""),
                uploader_role,
                uploader_id,
                parse_result.metadata.get("department", ""),
                parse_result.metadata.get("division", ""),
                parse_result.metadata.get("semester", ""),
                parse_result.metadata.get("date_range", {}).get("start"),
                parse_result.metadata.get("date_range", {}).get("end"),
                parse_result.analytics.get("total_students", 0),
                len(parse_result.normalized_rows),
                parse_result.analytics.get("avg_attendance", 0),
                parse_result.analytics.get("defaulters", 0),
                backup_path,
            ),
        )
        batch_row = cur.fetchone()
        batch_id = batch_row["id"]

        student_ids = {}
        for student in parse_result.students:
            roll_no = student["roll_no"]
            existing = conn.execute("SELECT id FROM students WHERE roll=%s", (roll_no,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO students(name,roll,department,year,division,password) VALUES(%s,%s,%s,%s,%s,%s)",
                    (
                        student["student_name"],
                        roll_no,
                        student.get("department", "") or "CS",
                        infer_year_from_semester(student.get("semester", "")),
                        student.get("division", ""),
                        generate_password_hash(_get_default_student_password()),
                    ),
                )
                existing = conn.execute("SELECT id FROM students WHERE roll=%s", (roll_no,)).fetchone()
            student_ids[roll_no] = existing["id"] if existing else None

        for row in parse_result.normalized_rows:
            student_id = student_ids.get(row["roll_no"])
            conn.execute(
                """
                INSERT INTO attendance_upload_rows
                    (batch_id, student_id, roll_no, student_name, subject, subject_code, lecture_type,
                     attended_classes, total_classes, percentage, department, division, semester,
                     report_start_date, report_end_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (roll_no, subject, report_start_date, report_end_date) DO UPDATE SET
                    batch_id = excluded.batch_id,
                    student_id = excluded.student_id,
                    student_name = excluded.student_name,
                    subject_code = excluded.subject_code,
                    lecture_type = excluded.lecture_type,
                    attended_classes = excluded.attended_classes,
                    total_classes = excluded.total_classes,
                    percentage = excluded.percentage,
                    department = excluded.department,
                    division = excluded.division,
                    semester = excluded.semester,
                    report_start_date = excluded.report_start_date,
                    report_end_date = excluded.report_end_date
                """,
                (
                    batch_id,
                    student_id,
                    row["roll_no"],
                    row["student_name"],
                    row["subject"],
                    row.get("subject_code", ""),
                    row.get("lecture_type", ""),
                    row["attended_classes"],
                    row["total_classes"],
                    row["percentage"],
                    row.get("department", ""),
                    row.get("division", ""),
                    row.get("semester", ""),
                    row.get("report_start_date"),
                    row.get("report_end_date"),
                ),
            )
            conn.execute(
                """
                INSERT INTO attendance_summary
                    (student_id, student_name, subject, attended, total, division, semester,
                     department, report_start_date, report_end_date, upload_batch_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(student_id, subject) DO UPDATE SET
                    student_name = excluded.student_name,
                    attended = excluded.attended,
                    total = excluded.total,
                    division = excluded.division,
                    semester = excluded.semester,
                    department = excluded.department,
                    report_start_date = excluded.report_start_date,
                    report_end_date = excluded.report_end_date,
                    upload_batch_id = excluded.upload_batch_id
                """,
                (
                    student_id,
                    row["student_name"],
                    row["subject"],
                    row["attended_classes"],
                    row["total_classes"],
                    row.get("division", ""),
                    row.get("semester", ""),
                    row.get("department", ""),
                    row.get("report_start_date"),
                    row.get("report_end_date"),
                    batch_id,
                ),
            )

        conn.commit()
        return {
            "batch_id": batch_id,
            "backup_path": backup_path,
            "saved": len(parse_result.normalized_rows),
            "students": parse_result.analytics.get("total_students", 0),
            "skipped": 0,
            "analytics": parse_result.analytics,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def infer_year_from_semester(semester):
    return {
        "I": "I",
        "II": "I",
        "III": "II",
        "IV": "II",
        "V": "III",
        "VI": "III",
        "VII": "IV",
        "VIII": "IV",
    }.get((semester or "").upper(), "II")


def fetch_batch_backup(batch_id):
    row = qone("SELECT id, backup_path FROM attendance_upload_batches WHERE id=%s", (batch_id,))
    return row


def restore_attendance_upload(batch_id):
    ensure_attendance_upload_tables()
    batch = qone("SELECT * FROM attendance_upload_batches WHERE id=%s", (batch_id,))
    if not batch:
        raise ValueError("Backup batch not found.")
    payload = load_backup_payload(batch["backup_path"])
    conn = get_db()
    try:
        restore_cur = conn.execute(
            """
            INSERT INTO attendance_upload_batches
                (filename, uploader_role, uploader_id, department, division, semester,
                 report_start_date, report_end_date, total_students, total_subject_rows,
                 avg_attendance, defaulters, backup_path, restore_source_batch_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                batch["filename"],
                batch["uploader_role"],
                batch["uploader_id"],
                batch["department"],
                batch["division"],
                batch["semester"],
                batch["report_start_date"],
                batch["report_end_date"],
                batch["total_students"],
                batch["total_subject_rows"],
                batch["avg_attendance"],
                batch["defaulters"],
                batch["backup_path"],
                batch["id"],
            ),
        )
        new_batch_id = restore_cur.fetchone()["id"]
        for row in payload.get("normalized_rows", []):
            student = conn.execute("SELECT id FROM students WHERE roll=%s", (row["roll_no"],)).fetchone()
            student_id = student["id"] if student else None
            conn.execute(
                """
                INSERT INTO attendance_summary
                    (student_id, student_name, subject, attended, total, division, semester,
                     department, report_start_date, report_end_date, upload_batch_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(student_id, subject) DO UPDATE SET
                    student_name = excluded.student_name,
                    attended = excluded.attended,
                    total = excluded.total,
                    division = excluded.division,
                    semester = excluded.semester,
                    department = excluded.department,
                    report_start_date = excluded.report_start_date,
                    report_end_date = excluded.report_end_date,
                    upload_batch_id = excluded.upload_batch_id
                """,
                (
                    student_id,
                    row["student_name"],
                    row["subject"],
                    row["attended_classes"],
                    row["total_classes"],
                    row.get("division", ""),
                    row.get("semester", ""),
                    row.get("department", ""),
                    row.get("report_start_date"),
                    row.get("report_end_date"),
                    new_batch_id,
                ),
            )
        conn.commit()
        return new_batch_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
