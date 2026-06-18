import psycopg2
import os
import re

PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:2233@localhost:5432/antigravity_db")

def parse_time(t_str):
    if not t_str: return None, None
    m = re.match(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", t_str)
    if not m: return None, None
    h1, m1, h2, m2 = map(int, m.groups())
    if h1 < 7: h1 += 12
    if h2 < 7: h2 += 12
    return f"{h1:02d}:{m1:02d}:00", f"{h2:02d}:{m2:02d}:00"

def upgrade():
    conn = psycopg2.connect(PG_URL)
    cur = conn.cursor()
    
    # Clean up invalid data before applying NOT NULL constraints
    cur.execute("DELETE FROM timetable WHERE branch IS NULL OR year IS NULL OR division IS NULL OR branch='' OR year='' OR division=''")
    cur.execute("DELETE FROM timetable WHERE faculty_id IS NULL")
    
    # 1. Add columns
    for col, dtype in [("subject_id", "INTEGER"), ("start_time", "TIME"), ("end_time", "TIME")]:
        try:
            cur.execute(f"ALTER TABLE timetable ADD COLUMN {col} {dtype}")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
        except psycopg2.errors.InFailedSqlTransaction:
            conn.rollback()
        else:
            conn.commit()

    # 2. Populate start_time, end_time, subject_id
    cur.execute("SELECT id, time, subject FROM timetable")
    rows = cur.fetchall()
    for rid, time_str, subject_name in rows:
        st, et = parse_time(time_str)
        # find subject_id
        cur.execute("SELECT id FROM subjects WHERE name=%s LIMIT 1", (subject_name,))
        s_row = cur.fetchone()
        sid = s_row[0] if s_row else None
        
        cur.execute("UPDATE timetable SET start_time=%s, end_time=%s, subject_id=%s WHERE id=%s", (st, et, sid, rid))
    
    conn.commit()
    
    # 3. Add Constraints
    for col in ["faculty_id", "branch", "year", "division"]:
        try:
            cur.execute(f"ALTER TABLE timetable ALTER COLUMN {col} SET NOT NULL")
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Warn: Constraint {col} NOT NULL failed: {e}")

    # 4. Add Indexes
    indexes = [
        ("idx_tt_faculty", "faculty_id"),
        ("idx_tt_class", "branch, year, division"),
        ("idx_tt_time", "day, start_time")
    ]
    for idx_name, cols in indexes:
        try:
            cur.execute(f"CREATE INDEX {idx_name} ON timetable ({cols})")
            conn.commit()
        except psycopg2.errors.DuplicateTable:
            conn.rollback()
        except Exception as e:
            conn.rollback()
            print(f"Warn: Index {idx_name} creation failed: {e}")

    print("Timetable V2 database migration successful!")

if __name__ == "__main__":
    upgrade()
