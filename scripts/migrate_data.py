import sqlite3
import psycopg2
import os

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

    # Disable foreign key checks during migration if needed, but in Postgres 
    # it's usually better to just insert in order or defer constraints:
    # Set session replication role to replica to bypass FK checks!
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
                continue

            columns = list(rows[0].keys())
            
            # Remove duplicate teacher_assessment
            if 'teaching_assessment' in columns and 'teacher_assessment' in columns:
                columns.remove('teacher_assessment')
                
            columns_mapped = columns
            
            col_names = ", ".join(columns_mapped)
            placeholders = ", ".join(["%s"] * len(columns))

            print(f"Migrating {len(rows)} rows for table: {table}...")
            
            # Create the insert statement
            insert_query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            
            for row in rows:
                values = tuple(row[col] for col in columns)
                try:
                    pg_cur.execute("SAVEPOINT pg_migration_sp")
                    pg_cur.execute(insert_query, values)
                    pg_cur.execute("RELEASE SAVEPOINT pg_migration_sp")
                except Exception as ex:
                    pg_cur.execute("ROLLBACK TO SAVEPOINT pg_migration_sp")
                    # If the entire table insert fails due to schema mismatch, it fails one row and logs, but continues
                    
                    # Alternatively, if we just want to bypass errors like "column missing":
                    print(f"Error migrating row in {table}: {ex}")
                    # And then we break out of this table if the schema is totally broken
                    break
            
            # Update the sequence so new inserts don't fail (for SERIAL columns)
            if 'id' in columns:
                pg_cur.execute(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id)+1 FROM {table}), 1), false);")
                
        except Exception as e:
            print(f"Error migrating table {table}: {e}")
    
    # Re-enable foreign key checks
    pg_cur.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()
    
    print("Migration completed successfully!")

    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate_data()
