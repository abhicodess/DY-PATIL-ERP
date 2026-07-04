import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB = "college.db"
PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:2233@localhost:5432/antigravity_db")

def migrate_data():
    if not os.path.exists(SQLITE_DB):
        print(f"SQLite database '{SQLITE_DB}' not found.")
        return

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(PG_URL)
    pg_cur = pg_conn.cursor()

    # Disable foreign key checks during migration
    pg_cur.execute("SET session_replication_role = 'replica';")

    tables = [
        "students", "faculty", "subjects", "attendance", "timetable", "marks",
        "faculty_notices", "faculty_notes", "cumulative_attendance", "results",
        "result_summary"
    ]

    for table in tables:
        try:
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            if not rows:
                print(f"Table {table} has 0 rows in SQLite. Skipping.")
                continue

            columns = list(rows[0].keys())
            # Remove duplicate teacher_assessment if exists
            if 'teaching_assessment' in columns and 'teacher_assessment' in columns:
                columns.remove('teacher_assessment')
                
            col_names = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))

            print(f"Migrating {len(rows)} rows for table: {table}...")
            
            # Create the insert statement
            insert_query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            
            # Chunk insertions to keep memory footprint low and optimize DB network traffic
            chunk_size = 2000
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i + chunk_size]
                values_list = []
                for row in chunk:
                    values = tuple(row[col] for col in columns)
                    values_list.append(values)
                
                pg_cur.executemany(insert_query, values_list)
            
            # Update the sequence so new inserts don't fail (for SERIAL columns)
            if 'id' in columns:
                pg_cur.execute(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id)+1 FROM {table}), 1), false);")
                
            print(f" [OK] Migrated {table} successfully.")
        except Exception as e:
            print(f"Error migrating table {table}: {e}")
            pg_conn.rollback()
            pg_cur.execute("SET session_replication_role = 'replica';")
            continue
    
    # Re-enable foreign key checks
    pg_cur.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()
    
    print("Migration completed successfully!")

    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate_data()
