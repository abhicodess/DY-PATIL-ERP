import logging
from utils.pg_wrapper import get_db

logger = logging.getLogger("db_schema_setup")

def setup_db_schemas():
    """
    Verifies that all required tables and columns exist in PostgreSQL.
    Creates or alters them if missing.
    """
    logger.info("Initializing enterprise PostgreSQL schemas...")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 1. Students contact and control columns
            for col, col_type in [
                ("contact_number", "TEXT"),
                ("parent_contact", "TEXT"),
                ("dob", "DATE"),
                ("gender", "TEXT"),
                ("address", "TEXT"),
                ("admission_year", "INTEGER"),
                ("must_change_password", "BOOLEAN DEFAULT FALSE")
            ]:
                try:
                    cur.execute(f"ALTER TABLE students ADD COLUMN IF NOT EXISTS {col} {col_type}")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.warning(f"Could not add column students.{col}: {e}")

            # 2. Faculty control columns
            for col, col_type in [
                ("must_change_password", "BOOLEAN DEFAULT FALSE")
            ]:
                try:
                    cur.execute(f"ALTER TABLE faculty ADD COLUMN IF NOT EXISTS {col} {col_type}")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.warning(f"Could not add column faculty.{col}: {e}")

            # 3. Timetable columns and tables
            try:
                cur.execute("ALTER TABLE timetable ADD COLUMN IF NOT EXISTS published BOOLEAN DEFAULT TRUE")
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not add column timetable.published: {e}")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS timetable_substitutions (
                    id SERIAL PRIMARY KEY,
                    timetable_id INTEGER REFERENCES timetable(id) ON DELETE CASCADE,
                    substitute_faculty_id INTEGER REFERENCES faculty(id) ON DELETE CASCADE,
                    session_date DATE NOT NULL,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance_disputes (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
                    attendance_id INTEGER REFERENCES attendance(id) ON DELETE CASCADE,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    resolved_by TEXT,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Faculty Assignments and Leaves
            cur.execute("""
                CREATE TABLE IF NOT EXISTS faculty_subject_assignments (
                    id SERIAL PRIMARY KEY,
                    faculty_id INTEGER REFERENCES faculty(id) ON DELETE CASCADE,
                    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
                    subject_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    semester TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    division TEXT NOT NULL,
                    academic_year TEXT DEFAULT '2025-26',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(faculty_id, subject_id, division)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS leave_applications (
                    id SERIAL PRIMARY KEY,
                    faculty_id INTEGER REFERENCES faculty(id) ON DELETE CASCADE,
                    leave_type TEXT,
                    from_date DATE,
                    to_date DATE,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    event_type TEXT DEFAULT 'Event',
                    description TEXT DEFAULT '',
                    created_by TEXT DEFAULT 'admin'
                )
            """)

            # Alter assignments columns if needed
            try:
                cur.execute("ALTER TABLE faculty_subject_assignments ADD COLUMN IF NOT EXISTS semester TEXT NOT NULL DEFAULT 'I'")
                conn.commit()
            except Exception:
                conn.rollback()
            try:
                cur.execute("ALTER TABLE faculty_subject_assignments ADD COLUMN IF NOT EXISTS class_name TEXT NOT NULL DEFAULT '-'")
                conn.commit()
            except Exception:
                conn.rollback()
            try:
                cur.execute("ALTER TABLE faculty_subject_assignments ADD COLUMN IF NOT EXISTS academic_year TEXT DEFAULT '2025-26'")
                conn.commit()
            except Exception:
                conn.rollback()

            # Alter unique constraints on faculty_subject_assignments
            try:
                cur.execute("ALTER TABLE faculty_subject_assignments DROP CONSTRAINT IF EXISTS faculty_subject_assignments_faculty_id_subject_name_class__key")
                conn.commit()
            except Exception:
                conn.rollback()
            try:
                cur.execute("ALTER TABLE faculty_subject_assignments ADD CONSTRAINT unique_fac_sub_class UNIQUE (faculty_id, subject_name, class_name)")
                conn.commit()
            except Exception:
                conn.rollback()

            # 4. SMS templates and logs tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_templates (
                    id SERIAL PRIMARY KEY,
                    slug TEXT UNIQUE NOT NULL,
                    body TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            cur.execute("""
                INSERT INTO sms_templates (slug, body)
                VALUES ('student_absent', 'Dear {{parent_name}}, your child {{student_name}} was marked Absent for the subject {{subject}} on {{date}}.')
                ON CONFLICT (slug) DO NOTHING
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sms_logs (
                    id SERIAL PRIMARY KEY,
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
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance_audit (
                    id SERIAL PRIMARY KEY,
                    faculty_id INTEGER,
                    session_id INTEGER,
                    student_id INTEGER,
                    action TEXT,
                    prev_status TEXT,
                    new_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_templates (
                    id SERIAL PRIMARY KEY,
                    template_name TEXT UNIQUE NOT NULL,
                    body TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                INSERT INTO whatsapp_templates (template_name, body)
                VALUES ('attendance_alert', 'Dear {{parent_name}}, your child {{student_name}} was marked Absent for the subject {{subject}} on {{date}}.')
                ON CONFLICT (template_name) DO NOTHING
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS communications_log (
                    id SERIAL PRIMARY KEY,
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
            """)

            # 5. Messages table updates (adding missing columns for sharing feature)
            for col, col_type in [
                ("from_role", "TEXT NOT NULL DEFAULT ''"),
                ("from_id", "INTEGER NOT NULL DEFAULT 0"),
                ("from_name", "TEXT NOT NULL DEFAULT ''"),
                ("to_role", "TEXT NOT NULL DEFAULT ''"),
                ("to_id", "INTEGER NOT NULL DEFAULT 0"),
                ("to_name", "TEXT NOT NULL DEFAULT ''"),
                ("subject", "TEXT NOT NULL DEFAULT ''"),
                ("body", "TEXT NOT NULL DEFAULT ''"),
                ("is_read", "INTEGER NOT NULL DEFAULT 0"),
                ("sent_at", "TEXT")
            ]:
                try:
                    cur.execute(f"ALTER TABLE messages ADD COLUMN IF NOT EXISTS {col} {col_type}")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.warning(f"Could not add column messages.{col}: {e}")

        conn.commit()
        logger.info("Database schemas validated successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during schema validation: {e}", exc_info=True)
    finally:
        conn.close()
