import json
import os
from datetime import datetime

from utils.pg_wrapper import get_db, qone, qry


ATT_BACKUP_DIR = os.path.join("backups", "attendance_engine")


def ensure_attendance_engine_schema():
    conn = get_db()
    is_sqlite = False
    try:
        from extensions import db
        if db.engine.dialect.name != 'postgresql':
            is_sqlite = True
    except Exception:
        pass
    try:
        for sql in (
            """
            CREATE TABLE IF NOT EXISTS attendance_sessions (
                id SERIAL PRIMARY KEY,
                timetable_id INTEGER NULL,
                subject_id INTEGER NULL,
                subject TEXT NOT NULL DEFAULT '',
                division TEXT NOT NULL DEFAULT '',
                branch TEXT NOT NULL DEFAULT '',
                lecture_date DATE NOT NULL,
                time_slot TEXT NOT NULL DEFAULT '',
                start_time TEXT NOT NULL DEFAULT '',
                end_time TEXT NOT NULL DEFAULT '',
                faculty_id INTEGER NULL,
                created_by INTEGER NULL,
                created_role TEXT NOT NULL DEFAULT '',
                method TEXT NOT NULL DEFAULT 'Manual',
                status TEXT NOT NULL DEFAULT 'Draft',
                is_locked BOOLEAN NOT NULL DEFAULT FALSE,
                locked_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                lecture_type TEXT DEFAULT 'Lecture',
                academic_year TEXT DEFAULT '',
                semester TEXT DEFAULT '',
                UNIQUE(subject, division, branch, lecture_date, time_slot, faculty_id)
            )
            """,
            """
            ALTER TABLE attendance_sessions
            ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP NULL
            """,
            """
            ALTER TABLE attendance_sessions
            ADD COLUMN IF NOT EXISTS lecture_type TEXT DEFAULT 'Lecture'
            """,
            """
            ALTER TABLE attendance_sessions
            ADD COLUMN IF NOT EXISTS academic_year TEXT DEFAULT ''
            """,
            """
            ALTER TABLE attendance_sessions
            ADD COLUMN IF NOT EXISTS semester TEXT DEFAULT ''
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS subject_id INTEGER NULL
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS faculty_id INTEGER NULL
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS lecture_id INTEGER NULL
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT 'Manual'
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS branch TEXT DEFAULT ''
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS division TEXT DEFAULT ''
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            """,
            """
            ALTER TABLE attendance
            ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE
            """,
            """
            ALTER TABLE attendance_summary
            ADD COLUMN IF NOT EXISTS subject_id INTEGER NULL
            """,
            """
            ALTER TABLE attendance_summary
            ADD COLUMN IF NOT EXISTS faculty_id INTEGER NULL
            """,
            """
            ALTER TABLE attendance_summary
            ADD COLUMN IF NOT EXISTS branch TEXT DEFAULT ''
            """,
            """
            ALTER TABLE attendance_summary
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            """,
            """
            CREATE TABLE IF NOT EXISTS attendance_audit_log (
                id SERIAL PRIMARY KEY,
                actor_role TEXT NOT NULL DEFAULT '',
                actor_id INTEGER NULL,
                action TEXT NOT NULL DEFAULT '',
                details_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS faculty_subjects (
                id SERIAL PRIMARY KEY,
                faculty_id INTEGER NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
                subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                division TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(faculty_id, subject_id, division)
            )
            """,
            """
            ALTER TABLE subjects ADD COLUMN IF NOT EXISTS division TEXT DEFAULT ''
            """,
            """
            ALTER TABLE subjects ADD COLUMN IF NOT EXISTS faculty_id INTEGER NULL
            """,
            """
            ALTER TABLE subjects ADD COLUMN IF NOT EXISTS year TEXT DEFAULT ''
            """,
            """
            ALTER TABLE attendance_sessions ADD COLUMN IF NOT EXISTS timetable_id INTEGER NULL
            """,
            """
            ALTER TABLE attendance DROP CONSTRAINT IF EXISTS unique_student_lecture
            """,
            """
            ALTER TABLE faculty_notes ADD COLUMN IF NOT EXISTS target_year TEXT DEFAULT 'All'
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS subject TEXT DEFAULT ''
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS body TEXT DEFAULT ''
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS from_id INTEGER NULL
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS from_name TEXT DEFAULT ''
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS to_id INTEGER NULL
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS to_name TEXT DEFAULT ''
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS from_role TEXT DEFAULT ''
            """,
            """
            ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE
            """,
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            """,
            """
            DROP TRIGGER IF EXISTS trg_attendance_updated_at ON attendance;
            """,
            """
            CREATE TRIGGER trg_attendance_updated_at
            BEFORE UPDATE ON attendance
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            """,
            """
            ALTER TABLE attendance ADD CONSTRAINT uq_attendance_student_lecture 
            UNIQUE (student_id, lecture_id)
            """,
            """
            ALTER TABLE attendance ALTER COLUMN date TYPE DATE USING (
                CASE 
                    WHEN date::TEXT IS NULL OR date::TEXT = '' THEN NULL 
                    ELSE date::DATE 
                END
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                short_code TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS student_alerts (
                id SERIAL PRIMARY KEY,
                student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                threshold FLOAT,
                message TEXT,
                is_resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ):
            try:
                if is_sqlite:
                    sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                conn.execute(sql)
            except Exception as exc:
                message = str(exc).lower()
                conn.rollback()
                if "already exists" in message or "duplicate key value violates unique constraint" in message or "does not exist" in message:
                    continue
                print(f"Schema warning: {message}")
                # Don't raise, just continue so it doesn't crash on boot
        for sql in (
            "CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_subject_id ON attendance(subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_lecture_id ON attendance(lecture_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_summary_student_id ON attendance_summary(student_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_summary_subject_id ON attendance_summary(subject_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_sessions_faculty_id ON attendance_sessions(faculty_id)",
            "CREATE INDEX IF NOT EXISTS idx_attendance_sessions_date ON attendance_sessions(lecture_date)",
        ):
            try:
                conn.execute(sql)
            except Exception:
                conn.rollback()
                continue
        conn.commit()
    finally:
        conn.close()


def log_attendance_action(actor_role, actor_id, action, details):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO attendance_audit_log(actor_role, actor_id, action, details_json) VALUES(%s,%s,%s,%s)",
            (actor_role, actor_id, action, json.dumps(details, ensure_ascii=True)),
        )
        conn.commit()
    finally:
        conn.close()


def create_attendance_backup(payload, extension="json"):
    os.makedirs(ATT_BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(ATT_BACKUP_DIR, f"attendance_backup_{stamp}.{extension}")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=True, default=str)
    return path


def load_attendance_backup(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def latest_attendance_backup():
    if not os.path.isdir(ATT_BACKUP_DIR):
        return None
    files = [os.path.join(ATT_BACKUP_DIR, f) for f in os.listdir(ATT_BACKUP_DIR) if f.endswith(".json")]
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def export_attendance_snapshot():
    return {
        "sessions": [dict(r) for r in qry("SELECT * FROM attendance_sessions ORDER BY id DESC LIMIT 10000")],
        "attendance": [dict(r) for r in qry("SELECT * FROM attendance ORDER BY id DESC LIMIT 50000")],
        "summary": [dict(r) for r in qry("SELECT * FROM attendance_summary ORDER BY id DESC LIMIT 50000")],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def attendance_backup_row():
    path = latest_attendance_backup()
    if not path:
        return None
    return {"path": path}
