import psycopg2
import os

PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:2233@localhost:5432/antigravity_db")

def init_db():
    conn = psycopg2.connect(PG_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Drop existing tables if you want a clean start, but we won't drop them here.
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id        SERIAL PRIMARY KEY,
                name      TEXT    NOT NULL,
                roll      TEXT    NOT NULL UNIQUE,
                department TEXT   NOT NULL,
                year      TEXT    NOT NULL,
                email     TEXT,
                password  TEXT    DEFAULT 'student123',
                photo     TEXT    DEFAULT '',
                division  TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS faculty (
                id           SERIAL PRIMARY KEY,
                name         TEXT NOT NULL,
                department   TEXT NOT NULL,
                designation  TEXT,
                email        TEXT NOT NULL UNIQUE,
                phone        TEXT,
                qualification TEXT,
                joining_date  TEXT,
                password     TEXT DEFAULT 'faculty123',
                photo        TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id           SERIAL PRIMARY KEY,
                name         TEXT NOT NULL,
                department   TEXT NOT NULL,
                subject_code TEXT,
                teacher      TEXT,
                semester     TEXT
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id           SERIAL PRIMARY KEY,
                student_name TEXT NOT NULL,
                subject      TEXT NOT NULL,
                date         TEXT NOT NULL,
                status       TEXT NOT NULL CHECK(status IN ('Present','Absent','Leave','Late','Medical')),
                remark       TEXT DEFAULT '',
                time_slot    TEXT DEFAULT '',
                faculty      TEXT DEFAULT '',
                division     TEXT DEFAULT '',
                semester     TEXT DEFAULT '',
                student_id   INTEGER REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS timetable (
                id        SERIAL PRIMARY KEY,
                day       TEXT NOT NULL,
                time      TEXT NOT NULL,
                subject   TEXT NOT NULL,
                teacher   TEXT,
                room      TEXT,
                semester  TEXT DEFAULT '',
                division  TEXT DEFAULT '',
                slot_type TEXT DEFAULT 'Theory',
                color     TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS marks (
                id           SERIAL PRIMARY KEY,
                faculty_id   INTEGER REFERENCES faculty(id),
                student_name TEXT NOT NULL,
                roll         TEXT,
                subject      TEXT NOT NULL,
                department   TEXT,
                marks        REAL NOT NULL,
                total        REAL NOT NULL DEFAULT 60,
                exam_type    TEXT NOT NULL,
                date         TEXT NOT NULL,
                semester     TEXT DEFAULT '',
                published    INTEGER DEFAULT 0,
                year         TEXT DEFAULT '',
                division     TEXT DEFAULT '',
                assignment_marks    REAL DEFAULT 0,
                attendance_marks    REAL DEFAULT 0,
                teaching_assessment REAL DEFAULT 0,
                ut_marks            REAL DEFAULT 0,
                mse_marks           REAL DEFAULT 0,
                remarks             TEXT DEFAULT '',
                student_id   INTEGER REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS faculty_notices (
                id         SERIAL PRIMARY KEY,
                faculty_id INTEGER NOT NULL REFERENCES faculty(id),
                title      TEXT NOT NULL,
                message    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS faculty_notes (
                id         SERIAL PRIMARY KEY,
                faculty_id INTEGER NOT NULL REFERENCES faculty(id),
                subject    TEXT NOT NULL,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                note_type  TEXT DEFAULT 'Lecture Note',
                attachment_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cumulative_attendance (
                id           SERIAL PRIMARY KEY,
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
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(roll, subject_code, semester, acad_year)
            );

            CREATE TABLE IF NOT EXISTS results (
                id                  SERIAL PRIMARY KEY,
                student_name        TEXT NOT NULL,
                roll                TEXT,
                department          TEXT,
                year                TEXT,
                semester            TEXT,
                subject             TEXT NOT NULL,
                marks               REAL NOT NULL,
                total               REAL NOT NULL DEFAULT 60,
                exam_type           TEXT NOT NULL DEFAULT 'Semester Exam',
                grade               TEXT,
                result              TEXT DEFAULT 'Pass',
                faculty_id          INTEGER REFERENCES faculty(id),
                published           INTEGER DEFAULT 0,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assignment_marks    REAL DEFAULT 0,
                attendance_marks    REAL DEFAULT 0,
                teaching_assessment REAL DEFAULT 0,
                ut_marks            REAL DEFAULT 0,
                mse_marks           REAL DEFAULT 0,
                tw_marks            REAL DEFAULT 0,
                pr_or_marks         REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS result_summary (
                id            SERIAL PRIMARY KEY,
                student_name  TEXT NOT NULL,
                roll          TEXT,
                department    TEXT,
                year          TEXT,
                semester      TEXT NOT NULL,
                total_marks   REAL NOT NULL,
                total_max     REAL NOT NULL,
                percentage    REAL NOT NULL,
                grade         TEXT,
                result        TEXT DEFAULT 'Pass',
                rank_in_class INTEGER,
                published     INTEGER DEFAULT 0,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY, 
                action TEXT, 
                details TEXT, 
                role TEXT, 
                user_id INTEGER, 
                ip_addr TEXT, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY, 
                title TEXT, 
                message TEXT, 
                role_target TEXT, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                sender_id INTEGER,
                sender_role TEXT,
                receiver_role TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                title TEXT,
                description TEXT,
                event_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_student_name ON attendance(student_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_status ON attendance(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_marks_student_id ON marks(student_id)")
        print("Database schema initialized successfully.")

    conn.close()

if __name__ == "__main__":
    init_db()
