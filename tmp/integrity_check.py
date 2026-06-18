
from utils.pg_wrapper import get_db, qry

def run_checks():
    checks = [
        ("Students without department", "SELECT COUNT(*) FROM students WHERE department IS NULL OR department = ''"),
        ("Attendance records without students", "SELECT COUNT(*) FROM attendance a LEFT JOIN students s ON a.student_id = s.id WHERE s.id IS NULL"),
        ("Attendance sessions without faculty", "SELECT COUNT(*) FROM attendance_sessions WHERE faculty_id IS NULL"),
        ("Null subject names in sessions", "SELECT COUNT(*) FROM attendance_sessions WHERE subject IS NULL OR subject = ''"),
        ("Duplicate attendance entries", "SELECT student_id, lecture_id, COUNT(*) FROM attendance GROUP BY student_id, lecture_id HAVING COUNT(*) > 1"),
        ("Students without department short code", "SELECT COUNT(*) FROM students s LEFT JOIN departments d ON s.department = d.short_code WHERE d.id IS NULL")
    ]
    
    print("--- Database Integrity Audit ---")
    for msg, sql in checks:
        try:
            res = qry(sql)
            if "Duplicate" in msg:
                print(f"{msg}: {len(res)} clusters found")
            else:
                print(f"{msg}: {res[0][0]}")
        except Exception as e:
            print(f"Error running check '{msg}': {e}")

if __name__ == "__main__":
    run_checks()
