import os
import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

def seed_load_users():
    # Load .env file
    load_dotenv()
    
    # Retrieve PG connection string from DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL environment variable is not set. Exiting.")
        return
        
    print(f"Connecting to database to seed load test users...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Generate password hash for 'password123'
    pwd_hash = generate_password_hash("password123")
    
    # Seed 100 students
    print("Seeding 100 students (student_1@dypatil.edu to student_100@dypatil.edu)...")
    for i in range(1, 101):
        email = f"student_{i}@dypatil.edu"
        roll = f"LOAD-S-{i:03d}"
        name = f"Student {i}"
        prn = f"PRN{i:05d}"
        cur.execute(
            """
            INSERT INTO students (name, roll, department, year, email, password, division, prn, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (roll) DO UPDATE SET email = EXCLUDED.email, password = EXCLUDED.password
            """,
            (name, roll, "Computer", "TY", email, pwd_hash, "A", prn, True)
        )
        
    # Seed 20 faculty
    print("Seeding 20 faculty (faculty_1@dypatil.edu to faculty_20@dypatil.edu)...")
    for i in range(1, 21):
        email = f"faculty_{i}@dypatil.edu"
        name = f"Faculty {i}"
        cur.execute(
            """
            INSERT INTO faculty (name, email, department, password)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password
            """,
            (name, email, "Computer", pwd_hash)
        )
        
    conn.commit()
    cur.close()
    conn.close()
    print("Load test users seeded successfully!")

if __name__ == "__main__":
    seed_load_users()
