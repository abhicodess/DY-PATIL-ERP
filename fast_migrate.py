import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB = "college.db"
PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/erp_db")


def fast_migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"SQLite database '{SQLITE_DB}' not found.")
        return

    print("Connecting to databases...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(PG_URL)
    pg_cur = pg_conn.cursor()

    # Truncate tables to ensure a clean slate
    tables = [
        "students", "faculty", "subjects", "attendance", "timetable", "marks",
        "faculty_notices", "faculty_notes", "cumulative_attendance", "results",
        "result_summary"
    ]
    
    print("Truncating existing tables for a clean migration...")
    pg_cur.execute("SET session_replication_role = 'replica';")
    for table in tables:
        try:
            pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
        except Exception as e:
            print(f"Failed to truncate {table}: {e}")
            pg_conn.rollback()
            pg_cur.execute("SET session_replication_role = 'replica';")

    for table in tables:
        try:
            sqlite_cur.execute(f"SELECT * FROM {table}")
            rows = sqlite_cur.fetchall()
            if not rows:
                print(f"Table {table} is empty in SQLite.")
                continue

            columns = list(rows[0].keys())
            
            # Remove duplicate teacher_assessment if present
            if 'teaching_assessment' in columns and 'teacher_assessment' in columns:
                columns.remove('teacher_assessment')

            # Ensure all columns exist in PostgreSQL table
            pg_cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")
            pg_cols = {r[0] for r in pg_cur.fetchall()}
            
            # Filter columns that actually exist in PostgreSQL
            columns = [c for c in columns if c in pg_cols]
            
            col_names = ", ".join(columns)
            
            print(f"Migrating {len(rows)} rows for table: {table} in bulk...")
            
            # Read all values
            values = []
            for row in rows:
                values.append(tuple(row[col] for col in columns))

            # Build and run execute_values with ON CONFLICT DO NOTHING (no target specified to catch all unique constraints)
            query = f"INSERT INTO {table} ({col_names}) VALUES %s ON CONFLICT DO NOTHING"
            execute_values(pg_cur, query, values, page_size=2000)
            
            # Update sequence if serial ID column exists
            if 'id' in columns:
                pg_cur.execute(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id)+1 FROM {table}), 1), false);")
                
            print(f"Table {table} migration finished successfully.")

        except Exception as e:
            print(f"Error migrating table {table}: {e}")

    pg_cur.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()
    
    sqlite_conn.close()
    pg_conn.close()
    print("Fast bulk migration completed successfully!")

if __name__ == "__main__":
    fast_migrate()
