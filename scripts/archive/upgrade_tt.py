import psycopg2
import os

PG_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:2233@localhost:5432/antigravity_db")

def upgrade():
    try:
        conn = psycopg2.connect(PG_URL)
        cur = conn.cursor()
        
        # Add columns to timetable table
        cols_to_add = {
            "faculty_id": "INTEGER",
            "branch": "VARCHAR(255)",
            "year": "VARCHAR(50)"
        }
        
        for col, dtype in cols_to_add.items():
            try:
                cur.execute(f"ALTER TABLE timetable ADD COLUMN {col} {dtype}")
                print(f"Added column {col} to timetable")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                print(f"Column {col} already exists in timetable")
            except Exception as e:
                conn.rollback()
                print(f"Error adding {col}: {e}")
            else:
                conn.commit()

        print("Upgrade done.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    print("Upgrading database schema for timetable...")
    upgrade()
