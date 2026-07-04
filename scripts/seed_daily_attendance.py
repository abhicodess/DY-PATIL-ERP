import os
import random
import psycopg2
import psycopg2.extras
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

def seed_daily_attendance():
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL environment variable is not set. Exiting.")
        return

    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Clear existing daily attendance
    print("Clearing existing daily attendance records...")
    cur.execute("DELETE FROM attendance")

    # Get all students
    cur.execute("SELECT id, name, division, department FROM students")
    students = cur.fetchall()
    if not students:
        print("No students found. Run seed_load_users.py first.")
        cur.close()
        conn.close()
        return

    print(f"Found {len(students)} students. Generating daily attendance for the last 45 days...")

    subjects = [
        "Cloud Computing", 
        "Blockchain Technology", 
        "Data Warehousing", 
        "AI & Machine Learning", 
        "Cybersecurity"
    ]
    faculties = ["Dr. K. Patel", "Prof. R. Sharma", "Dr. S. Joshi", "Prof. A. Patil", "Dr. M. Deshmukh"]

    # Generate dates: last 45 days
    today = date.today()
    date_list = [today - timedelta(days=i) for i in range(45)]
    
    records_to_insert = []
    
    for dt in date_list:
        # Skip Sundays
        if dt.weekday() == 6:
            continue
            
        dt_str = dt.strftime("%Y-%m-%d")
        
        # Pick 2 random subjects for this day
        daily_subjects = random.sample(subjects, 2)
        
        for subj in daily_subjects:
            fac = faculties[subjects.index(subj)]
            
            for s in students:
                s_id, s_name, s_div, s_dept = s
                
                # 80% chance of lecture happening for this student
                if random.random() > 0.8:
                    continue
                    
                # Status: 78% Present, 12% Absent, 5% Late, 3% Medical, 2% Leave
                r = random.random()
                if r < 0.78:
                    status = 'Present'
                elif r < 0.90:
                    status = 'Absent'
                elif r < 0.95:
                    status = 'Late'
                elif r < 0.98:
                    status = 'Medical'
                else:
                    status = 'Leave'
                    
                records_to_insert.append((
                    s_name, subj, dt_str, status, fac, s_div or 'A', 'VII', s_id
                ))

    print(f"Prepared {len(records_to_insert)} attendance records. Inserting in bulk...")
    
    # Bulk insert
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO attendance (student_name, subject, date, status, faculty, division, semester, student_id)
        VALUES %s
        """,
        records_to_insert
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print("Successfully seeded daily attendance records!")

if __name__ == "__main__":
    seed_daily_attendance()
