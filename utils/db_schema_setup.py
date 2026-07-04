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
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cur.execute("ALTER TABLE attendance_audit ADD COLUMN IF NOT EXISTS details TEXT")
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not add column attendance_audit.details: {e}")

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

            # 6. Faculty Timetable self-service & Admin Notifications
            cur.execute("""
                CREATE TABLE IF NOT EXISTS faculty_timetable (
                    id            SERIAL PRIMARY KEY,
                    faculty_id    INTEGER NOT NULL,
                    faculty_name  TEXT NOT NULL,
                    day           TEXT NOT NULL
                                  CHECK (day IN ('Monday','Tuesday','Wednesday',
                                                 'Thursday','Friday','Saturday')),
                    time_slot     TEXT NOT NULL,
                    subject       TEXT NOT NULL,
                    division      TEXT NOT NULL,
                    room          TEXT DEFAULT '',
                    slot_type     TEXT DEFAULT 'Theory'
                                  CHECK (slot_type IN ('Theory','Lab','Elective','Minor')),
                    semester      TEXT DEFAULT '',
                    academic_year TEXT DEFAULT '',
                    status        TEXT DEFAULT 'draft'
                                  CHECK (status IN ('draft','pending','approved','rejected')),
                    admin_note    TEXT DEFAULT '',
                    resubmission_count INTEGER DEFAULT 0,
                    last_rejected_note TEXT DEFAULT '',
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Recreate constraint and update default status to draft
            try:
                cur.execute("ALTER TABLE faculty_timetable DROP CONSTRAINT IF EXISTS faculty_timetable_status_check")
                cur.execute("ALTER TABLE faculty_timetable ADD CONSTRAINT faculty_timetable_status_check CHECK (status IN ('draft', 'pending', 'approved', 'rejected'))")
                cur.execute("ALTER TABLE faculty_timetable ALTER COLUMN status SET DEFAULT 'draft'")
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not update status constraint on faculty_timetable: {e}")

            # Add resubmission columns to faculty_timetable
            for col, col_type in [
                ("resubmission_count", "INTEGER DEFAULT 0"),
                ("last_rejected_note", "TEXT DEFAULT ''")
            ]:
                try:
                    cur.execute(f"ALTER TABLE faculty_timetable ADD COLUMN IF NOT EXISTS {col} {col_type}")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.warning(f"Could not add column faculty_timetable.{col}: {e}")

            try:
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS
                    uq_fac_tt_active
                    ON faculty_timetable (faculty_id, day, time_slot)
                    WHERE status NOT IN ('rejected','approved')
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not create uq_fac_tt_active index: {e}")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_notifications (
                    id            SERIAL PRIMARY KEY,
                    event_type    TEXT NOT NULL,
                    faculty_id    INTEGER,
                    faculty_name  TEXT,
                    message       TEXT NOT NULL,
                    payload       TEXT DEFAULT '{}',
                    is_read       BOOLEAN DEFAULT FALSE,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS student_timetable (
                    id SERIAL PRIMARY KEY,
                    division VARCHAR(10) NOT NULL,
                    semester VARCHAR(10) NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    day VARCHAR(20) NOT NULL,
                    time_slot VARCHAR(50) NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    faculty_name VARCHAR(100) NOT NULL,
                    room VARCHAR(50) NOT NULL,
                    created_by_faculty_id INTEGER NOT NULL,
                    approved_by_admin BOOLEAN DEFAULT FALSE,
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            for col, col_type in [
                ("status", "TEXT DEFAULT 'pending'"),
                ("admin_note", "TEXT DEFAULT ''"),
                ("requested_at", "TEXT"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]:
                try:
                    cur.execute(f"ALTER TABLE faculty_subject_assignments ADD COLUMN IF NOT EXISTS {col} {col_type}")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.warning(f"Could not add column faculty_subject_assignments.{col}: {e}")

            # 7. Initialize attendance engine schemas
            try:
                from services.attendance_service import init_attendance_engine
                init_attendance_engine()
            except Exception as e:
                logger.warning(f"Could not initialize attendance engine: {e}")

            # 8. Assessments Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS assessments (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
                    subject VARCHAR(100) NOT NULL,
                    faculty_id INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
                    assignment_1 VARCHAR(255) DEFAULT '',
                    assignment_2 VARCHAR(255) DEFAULT '',
                    assignment_3 VARCHAR(255) DEFAULT '',
                    assignment_4 VARCHAR(255) DEFAULT '',
                    assignment_5 VARCHAR(255) DEFAULT '',
                    paper_q1 VARCHAR(255) DEFAULT '',
                    paper_q2 VARCHAR(255) DEFAULT '',
                    paper_q3 VARCHAR(255) DEFAULT '',
                    paper_q4 VARCHAR(255) DEFAULT '',
                    patent_publication VARCHAR(255) DEFAULT '',
                    copyright VARCHAR(255) DEFAULT '',
                    project_review_1 VARCHAR(255) DEFAULT '',
                    project_review_2 VARCHAR(255) DEFAULT '',
                    implementation_documentation TEXT DEFAULT '',
                    remark TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 9. Faculty notes attachment column
            try:
                cur.execute("ALTER TABLE faculty_notes ADD COLUMN IF NOT EXISTS attachment_path TEXT")
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not add column faculty_notes.attachment_path: {e}")

            # 10. Marks remarks column
            try:
                cur.execute("ALTER TABLE marks ADD COLUMN IF NOT EXISTS remarks TEXT DEFAULT ''")
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not add column marks.remarks: {e}")

            # 11. Marks system upgrades (subjects_master, marks columns, seed data)
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS subjects_master (
                      id             SERIAL PRIMARY KEY,
                      subject_code   TEXT UNIQUE NOT NULL,
                      subject_name   TEXT NOT NULL,
                      department     TEXT,
                      semester       TEXT,
                      max_assignment INTEGER DEFAULT 5,
                      max_attendance INTEGER DEFAULT 5,
                      max_teaching   INTEGER DEFAULT 10,
                      max_ut         INTEGER DEFAULT 20,
                      max_mse        INTEGER DEFAULT 20,
                      max_total      INTEGER DEFAULT 60
                    )
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not create subjects_master: {e}")

            try:
                cur.execute("""
                    ALTER TABLE marks
                      ADD COLUMN IF NOT EXISTS subject_code TEXT DEFAULT '',
                      ADD COLUMN IF NOT EXISTS prn_number   TEXT DEFAULT '',
                      ADD COLUMN IF NOT EXISTS ut_published  BOOLEAN DEFAULT FALSE,
                      ADD COLUMN IF NOT EXISTS mse_published BOOLEAN DEFAULT FALSE,
                      ADD COLUMN IF NOT EXISTS result_published BOOLEAN DEFAULT FALSE,
                      ADD COLUMN IF NOT EXISTS grade TEXT DEFAULT '',
                      ADD COLUMN IF NOT EXISTS result TEXT DEFAULT ''
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not add marks subject_code/prn/published/grade/result columns: {e}")

            try:
                cur.execute("""
                    UPDATE marks SET
                      assignment_marks   = CAST(assignment_marks AS REAL),
                      attendance_marks   = CAST(attendance_marks AS REAL),
                      ut_marks           = CAST(ut_marks AS REAL),
                      mse_marks          = CAST(mse_marks AS REAL)
                    WHERE true
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not cast text mark columns to REAL: {e}")

            try:
                cur.execute("""
                    INSERT INTO subjects_master
                      (subject_code, subject_name, department, semester)
                    VALUES
                      ('U24AIMLPC401','Statistics & Probability','AIML','SEM IV'),
                      ('U24AIMLPC402','Introduction to AI','AIML','SEM IV'),
                      ('U24AIMLPC403','Database Management Systems','AIML','SEM IV')
                    ON CONFLICT (subject_code) DO NOTHING
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.warning(f"Could not seed subjects_master: {e}")


        conn.commit()
        logger.info("Database schemas validated successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during schema validation: {e}", exc_info=True)
    finally:
        conn.close()
