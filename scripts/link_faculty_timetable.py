import os
import sys
import argparse
import psycopg2
from psycopg2.extras import DictCursor

def main():
    parser = argparse.ArgumentParser(description="Link timetable rows to faculty IDs based on teacher name.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without committing to database.")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback to a default if common in the project, but usually environment is preferred
        db_url = "postgresql://postgres:2233@localhost:5432/antigravity_db"
        print(f"WARNING: DATABASE_URL not set. Using default: {db_url}")

    try:
        conn = psycopg2.connect(db_url)
        # Use DictCursor for easier column access
        cur = conn.cursor(cursor_factory=DictCursor)
    except Exception as e:
        print(f"CRITICAL: Failed to connect to database: {e}")
        sys.exit(1)

    print(f"--- Timetable Faculty Linker ({'DRY RUN' if args.dry_run else 'LIVE MODE'}) ---")

    # 1. Fetch rows from timetable that lack faculty_id
    cur.execute("SELECT id, teacher, subject FROM timetable WHERE faculty_id IS NULL")
    rows = cur.fetchall()

    if not rows:
        print("No rows found in timetable with NULL faculty_id. Everything is linked!")
        conn.close()
        return

    matched_count = 0
    unmatched_count = 0
    unmatched_teachers = set()
    updates = []

    for row in rows:
        timetable_id = row['id']
        teacher_raw = row['teacher']
        subject = row['subject']

        if not teacher_raw:
            unmatched_count += 1
            continue

        teacher_name = teacher_raw.strip()

        # 2. Try to find matching faculty
        # We use ILIKE for case-insensitive matching
        cur.execute("SELECT id, name FROM faculty WHERE name ILIKE %s", (teacher_name,))

        matches = cur.fetchall()

        if len(matches) == 1:
            faculty_id = matches[0]['id']
            faculty_name = matches[0]['name']
            
            if args.dry_run:
                print(f"[DRY-RUN] Would link: Timetable ID {timetable_id} | '{teacher_name}' -> Faculty '{faculty_name}' (ID: {faculty_id})")
            
            updates.append((faculty_id, timetable_id))
            matched_count += 1
        else:
            unmatched_count += 1
            unmatched_teachers.add(teacher_name)
            if len(matches) > 1:
                print(f"[INFO] Multiple matches for '{teacher_name}': {[m['name'] for m in matches]}")

    # 3. Apply updates if not dry-run
    if not args.dry_run and updates:
        print(f"Applying {len(updates)} updates...")
        try:
            for faculty_id, tt_id in updates:
                cur.execute("UPDATE timetable SET faculty_id = %s WHERE id = %s", (faculty_id, tt_id))
            conn.commit()
            print("Changes committed successfully.")
        except Exception as e:
            conn.rollback()
            print(f"Error during update: {e}")
            sys.exit(1)
    elif updates:
        print(f"\n[DRY-RUN] Skipped applying {len(updates)} updates.")

    # 4. Print Summary
    print("\n" + "="*40)
    print("SUMMARY")
    print("="*40)
    print(f"Successfully Matched: {matched_count}")
    print(f"Unmatched Rows:      {unmatched_count}")
    
    if unmatched_teachers:
        print("\nTHE FOLLOWING TEACHER NAMES COULD NOT BE MATCHED (Manual Fix Required):")
        for name in sorted(list(unmatched_teachers)):
            print(f" - {name}")
    print("="*40)

    conn.close()

if __name__ == "__main__":
    main()
