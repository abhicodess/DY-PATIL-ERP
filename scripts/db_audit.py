import sys
import os
sys.path.append(os.getcwd())

from utils.pg_wrapper import qry, qone

def run_audit():
    try:
        print("--- DATABASE INTEGRITY AUDIT ---")
        
        # 1. Attendance without students
        res = qone("SELECT COUNT(*) FROM attendance WHERE student_id NOT IN (SELECT id FROM students)")
        orphaned_att = res[0] if res else 0
        print(f"Orphaned attendance records (no student): {orphaned_att}")
        
        # 2. Sessions without faculty
        res = qone("SELECT COUNT(*) FROM attendance_sessions WHERE faculty_id NOT IN (SELECT id FROM faculty)")
        orphaned_sess = res[0] if res else 0
        print(f"Orphaned sessions (no faculty): {orphaned_sess}")
        
        # 3. Students without departments
        res = qone("SELECT COUNT(*) FROM students WHERE department IS NULL OR department = ''")
        missing_dept = res[0] if res else 0
        print(f"Students missing department: {missing_dept}")
        
        # 4. Duplicate attendance
        dupes = qry("""
            SELECT student_id, lecture_id, COUNT(*) 
            FROM attendance 
            GROUP BY student_id, lecture_id 
            HAVING COUNT(*) > 1
        """)
        print(f"Duplicate attendance entries (student/session pairs): {len(dupes)}")
        
    except Exception as e:
        print(f"Audit failed: {e}")

if __name__ == "__main__":
    run_audit()
