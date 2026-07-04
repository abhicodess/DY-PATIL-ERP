import json
import datetime
import os
import psycopg2
import psycopg2.extras
from utils.pg_wrapper import get_db

TABLES = [
    'subjects', 'students', 'timetable', 'faculty', 'attendance', 'marks', 
    'faculty_notices', 'faculty_notes', 'cumulative_attendance', 'results', 
    'result_summary', 'audit_logs', 'notifications', 
    'events', 'attendance_summary', 'messages', 'timetable_notifications', 
    'classrooms', 'qr_sessions'
]

def backup_db():
    print("\n📦 Starting Database Backup...")
    conn = get_db()
    backup_data = {}
    try:
        cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        for t in TABLES:
            if t not in TABLES:
                raise ValueError(f"Unauthorized table: {t}")
            cur.execute(f"SELECT * FROM {t}")  # nosec B608
            rows = cur.fetchall()
            
            # Serialize dates for JSON mapping
            for row in rows:
                for k, v in row.items():
                    if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
                        row[k] = str(v)
                        
            backup_data[t] = rows
            print(f"  ✓ Exported {len(rows)} records from '{t}'")
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("backups", exist_ok=True)
        bcname = f"backups/erp_backup_{timestamp}.json"
        with open(bcname, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
        print(f"\n✅ Backup Complete! Saved to: {bcname}\n")
    except Exception as e:
        print("❌ Backup Failed:", e)
    finally:
        conn.close()

def reset_db():
    print("\n⚠️ WARNING: You are about to DESTROY ALL DATA in the database!")
    sure = input("To proceed, type exactly 'ERASE ALL': ")
    if sure != 'ERASE ALL':
        print("❌ Operation aborted. No data was deleted.")
        return

    conn = get_db()
    try:
        cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor()
        for t in TABLES:
            if t not in TABLES:
                raise ValueError(f"Unauthorized table: {t}")
        sql = f"TRUNCATE TABLE {', '.join(TABLES)} RESTART IDENTITY CASCADE;"
        cur.execute(sql)  # nosec B608
        if hasattr(conn, 'conn'): conn.conn.commit()
        else: conn.commit()
        print("\n✅ FACTORY RESET COMPLETE!")
        print("All records have been securely dropped. Primary keys reset to 1.\n")
    except Exception as e:
        if hasattr(conn, 'conn'): conn.conn.rollback()
        else: conn.rollback()
        print("\n❌ Reset Failed:", e)
    finally:
        conn.close()

def menu():
    while True:
        print("========================================")
        print("  DY PATIL ERP - DATABASE MANAGER TOOL")
        print("========================================")
        print(" 1. Backup all data (Export to JSON)")
        print(" 2. Factory Reset (Erase all data)")
        print(" 3. Exit")
        print("========================================")
        choice = input("Select an option (1, 2, or 3): ")
        
        if choice == '1':
            backup_db()
        elif choice == '2':
            reset_db()
        elif choice == '3':
            print("Exiting tool...")
            break
        else:
            print("Invalid choice. Try again.\n")

if __name__ == "__main__":
    menu()
