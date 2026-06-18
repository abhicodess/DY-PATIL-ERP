import psycopg2
import os

PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:2233@localhost:5432/antigravity_db")

def upgrade():
    try:
        conn = psycopg2.connect(PG_URL)
        cur = conn.cursor()
        
        cur.execute("ALTER TABLE attendance ADD COLUMN timetable_id INTEGER")
        print("Added timetable_id to attendance")
        conn.commit()
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        print("timetable_id already exists")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")

if __name__ == "__main__":
    upgrade()
    print("Attendance schema upgraded.")
