import psycopg2
from pg_wrapper import exe, get_db

def migrate():
    # Create classrooms table
    exe("""
    CREATE TABLE IF NOT EXISTS classrooms (
        id SERIAL PRIMARY KEY,
        name TEXT,
        latitude FLOAT,
        longitude FLOAT,
        radius INTEGER
    )
    """)
    
    # Create qr_sessions table
    exe("""
    CREATE TABLE IF NOT EXISTS qr_sessions (
        id SERIAL PRIMARY KEY,
        faculty_id INTEGER,
        token TEXT,
        subject TEXT,
        division TEXT,
        classroom_id INTEGER,
        expiry TIMESTAMP,
        is_active BOOLEAN
    )
    """)
    
    # Add columns to attendance table
    def add_col(col_name, col_type):
        conn = get_db()
        try:
            conn.execute(f"ALTER TABLE attendance ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"Added column {col_name}")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print(f"Column {col_name} already exists")
        except Exception as e:
            conn.rollback()
            print(f"Error adding {col_name}: {e}")
        finally:
            conn.close()
            
    add_col("latitude", "FLOAT")
    add_col("longitude", "FLOAT")
    add_col("method", "TEXT DEFAULT 'QR'")
    add_col("location_verified", "BOOLEAN DEFAULT FALSE")
    
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
