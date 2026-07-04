import os
import sys
import argparse
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Professional Faculty-Timetable Auto-Linker & Assignment Generator")
    parser.add_argument("--dry-run", action="store_true", help="Print operations without performing them.")
    parser.add_argument("--faculty", type=str, help="Fix only one specific faculty by name search.")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres:2233@localhost:5432/antigravity_db"
        print(f"DEBUG: No DATABASE_URL found, using default.")

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=DictCursor)
    except Exception as e:
        print(f"CRITICAL: DB Connection failed: {e}")
        sys.exit(1)

    print(f"\n--- DY Patil ERP: Faculty Link Fixer ({'DRY RUN' if args.dry_run else 'LIVE'}) ---")

    # 1. Enable pg_trgm for fuzzy matching if available
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    except:
        conn.rollback()
        print("INFO: pg_trgm extension not available, falling back to basic TRIM/ILIKE.")
    else:
        conn.commit()

    # Define the matching logic
    # We strip all spaces and use ILIKE for robustness against "Prof. Shubham" vs "Prof.Shubham"
    match_sql = """
        UPDATE timetable t
        SET faculty_id = f.id
        FROM faculty f
        WHERE t.faculty_id IS NULL
        AND (
            TRIM(REPLACE(t.teacher, ' ', '')) ILIKE TRIM(REPLACE(f.name, ' ', ''))
            OR (f.name ILIKE '%' || t.teacher || '%')
            OR (t.teacher ILIKE '%' || f.name || '%')
        )
    """
    
    if args.faculty:
        match_sql += f" AND f.name ILIKE '%{args.faculty}%'"

    # Pre-check stats
    cur.execute("SELECT COUNT(*) FROM timetable WHERE faculty_id IS NULL")
    pre_null_count = cur.fetchone()[0]

    if args.dry_run:
        print(f"[DRY-RUN] Analyzing {pre_null_count} timetable rows with NULL faculty_id...")
        # For dry run, we select first to show what would happen
        check_sql = """
            SELECT t.id as tt_id, t.teacher, f.name as fac_name, f.id as fac_id, t.subject
            FROM timetable t, faculty f
            WHERE t.faculty_id IS NULL
            AND (
                TRIM(REPLACE(t.teacher, ' ', '')) ILIKE TRIM(REPLACE(f.name, ' ', ''))
                OR (f.name ILIKE '%' || t.teacher || '%')
            )
        """
        if args.faculty: check_sql += f" AND f.name ILIKE '%{args.faculty}%'"
        
        cur.execute(check_sql)
        planned = cur.fetchall()
        for p in planned:
            print(f"  > Match: '{p['teacher']}' -> '{p['fac_name']}' (Subject: {p['subject']})")
        print(f"[DRY-RUN] Total matches found: {len(planned)}")
    else:
        cur.execute(match_sql)
        conn.commit()
    
    # Post-check stats
    cur.execute("SELECT COUNT(*) FROM timetable WHERE faculty_id IS NULL")
    post_null_count = cur.fetchone()[0]
    fixed_count = pre_null_count - post_null_count
    
    # 2. Populate subject assignments
    print("\n--- Syncing Faculty Subject Assignments ---")
    assign_sql = """
        INSERT INTO faculty_subject_assignments (faculty_id, subject_name, class_name, department, semester, division)
        SELECT DISTINCT faculty_id, subject, (COALESCE(branch, 'CORE') || '-' || COALESCE(division, 'A')), 
               COALESCE(branch, 'CORE'), COALESCE(semester, '1'), COALESCE(division, 'A')
        FROM timetable
        WHERE faculty_id IS NOT NULL
        ON CONFLICT (faculty_id, subject_name, class_name) DO NOTHING
        RETURNING id
    """
    
    if args.dry_run:
        print("[DRY-RUN] Would generate assignments from unique (faculty_id, subject, division) pairs in timetable.")
        inserted_count = 0 
    else:
        cur.execute(assign_sql)
        res = cur.fetchall()
        inserted_count = len(res)
        conn.commit()

    # 3. Unmatched summary
    cur.execute("SELECT DISTINCT teacher FROM timetable WHERE faculty_id IS NULL")
    unmatched = cur.fetchall()

    print("\n" + "="*50)
    print("FINAL SUMMARY")
    print("="*50)
    print(f"Timetable Rows Fixed:  {fixed_count}")
    print(f"New Assignments added: {inserted_count}")
    print(f"Remaining Unmatched:   {len(unmatched)}")
    
    if unmatched:
        print("\nUNMATCHED TEACHER NAMES (Action Required):")
        for u in unmatched:
            print(f" - {u['teacher']}")
    print("="*50 + "\n")

    conn.close()

if __name__ == "__main__":
    main()
