import psycopg2
from pg_wrapper import get_db

def create_table():
    conn = get_db()
    try:
        cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS timetable_notifications(
                id SERIAL PRIMARY KEY,
                sender_id INT,
                sender_role TEXT,
                student_id INT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        if hasattr(conn, 'conn'): conn.conn.commit()
        else: conn.commit()
        print("Table timetable_notifications created successfully.")
    except Exception as e:
        if hasattr(conn, 'conn'): conn.conn.rollback()
        else: conn.rollback()
        print(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
