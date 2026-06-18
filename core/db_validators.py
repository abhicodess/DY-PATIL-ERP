import logging
from utils.pg_wrapper import get_db

def validate_schema():
    """
    Validates and synchronizes the database schema with the required enterprise architecture.
    """
    conn = get_db()
    cur = conn.cursor()
    
    # List of critical migrations that must be applied
    migrations = [
        # Table: leave_applications
        ("leave_applications", "faculty_id", "INTEGER"),
        ("leave_applications", "leave_type", "TEXT"),
        ("leave_applications", "from_date", "DATE"),
        ("leave_applications", "to_date", "DATE"),
        ("leave_applications", "remarks", "TEXT"),
        
        # Table: attendance_sessions
        ("attendance_sessions", "lecture_date", "DATE"),
        ("attendance_sessions", "academic_year", "TEXT"),
        ("attendance_sessions", "lecture_type", "TEXT DEFAULT 'Lecture'"),
        
        # Table: attendance
        ("attendance", "lecture_id", "INTEGER"),
        ("attendance", "faculty_id", "INTEGER"),
    ]
    
    try:
        for table, column, dtype in migrations:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            """, (table, column))
            
            if not cur.fetchone():
                logging.info(f"Synchronizing database: Adding {column} to {table}")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")
        
        conn.commit()
        logging.info("Database schema synchronization complete.")
    except Exception as e:
        conn.rollback()
        logging.error(f"Database synchronization failed: {e}")
        raise e
    finally:
        cur.close()
