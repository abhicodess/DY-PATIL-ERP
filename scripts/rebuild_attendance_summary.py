import os
import sys
from dotenv import load_dotenv

# Add parent directory to path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
from utils.pg_wrapper import exe

def rebuild_summary():
    try:
        print("Truncating old attendance_summary...")
        # We don't truncate, we just UPSERT everything to be safe
        
        sql = """
        INSERT INTO attendance_summary 
          (student_id, student_name, subject, attended, total, 
           division, semester, department)
        SELECT 
          student_id,
          MAX(s.name) as student_name,
          a.subject,
          COUNT(*) FILTER (WHERE a.status='Present') as attended,
          COUNT(*) as total,
          a.division,
          a.semester,
          s.department
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        GROUP BY student_id, a.subject, a.division, a.semester, s.department
        ON CONFLICT (student_id, subject) DO UPDATE SET
          student_name = EXCLUDED.student_name,
          attended = EXCLUDED.attended,
          total = EXCLUDED.total,
          division = EXCLUDED.division,
          semester = EXCLUDED.semester,
          department = EXCLUDED.department;
        """
        
        print("Running bulk UPSERT migration... This might take a few seconds.")
        exe(sql)
        print("Success! Migration completed successfully.")
        
    except Exception as e:
        print(f"Error executing migration: {e}")

if __name__ == "__main__":
    rebuild_summary()
