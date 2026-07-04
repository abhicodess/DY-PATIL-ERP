import sys
import os

# Ensure we can import pg_wrapper from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from pg_wrapper import get_db
except ImportError:
    print("❌ Could not locate pg_wrapper.py. Please run this script from the root directory.")
    sys.exit(1)

def factory_reset():
    sure = input("⚠️ WARNING: This will completely wipe ALL ERP DATA (Students, Faculty, Timetable, Attendance, etc.). Type 'YES' to permanently erase: ")
    if sure != 'YES':
        print("Aborted. Database was untouched.")
        return

    tables = [
        'subjects', 'students', 'timetable', 'faculty', 'attendance', 'marks', 
        'faculty_notices', 'faculty_notes', 'cumulative_attendance', 'results', 
        'result_summary', 'audit_logs', 'notifications', 
        'events', 'attendance_summary', 'messages', 'timetable_notifications', 
        'classrooms', 'qr_sessions'
    ]

    conn = get_db()
    try:
        cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor()
        
        # TRUNCATE CASCADE wipes all tables instantly and resets ALL ID sequences
        sql = f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;"
        
        cur.execute(sql)
        if hasattr(conn, 'conn'): 
            conn.conn.commit()
        else: 
            conn.commit()
            
        print("✅ FULL FACTORY RESET COMPLETE.")
        print("All data has been deleted and ID counters restarted at 1.")
    except Exception as e:
        if hasattr(conn, 'conn'): 
            conn.conn.rollback()
        else: 
            conn.rollback()
        print("❌ Error during factory reset:", e)
    finally:
        conn.close()

if __name__ == "__main__":
    factory_reset()
