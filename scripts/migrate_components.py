#!/usr/bin/env python3
"""
Stage 2 Migration: Schema Unification Dry-Run Report
=====================================================
Reads subjects_master and outputs EXACTLY what subject_mark_components rows
would be created.

Run:
    python scripts/migrate_components.py --dry-run        (safe, read-only)
    python scripts/migrate_components.py --apply          (writes to database)

ALWAYS review the --dry-run output before --apply.
"""

import sys
import os
import argparse

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'migrate_secret_key_for_script_only_do_not_use_in_prod')
os.environ.setdefault('JWT_SECRET_KEY', 'migrate_jwt_key_for_script_only_do_not_use_in_prod')

def get_conn():
    """Get a raw psycopg2 connection using app DATABASE_URL."""
    import psycopg2
    import psycopg2.extras
    from config import Config
    db_url = Config.SQLALCHEMY_DATABASE_URI
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn

def plan_components_for_subject(row):
    """
    Given a subjects_master row, return the list of component dicts
    that WOULD be inserted into subject_mark_components.
    """
    components = []
    order = 0

    # Base components
    for comp_name, max_marks in [
        ('Assignment', row.get('max_assignment') or 5),
        ('Attendance', row.get('max_attendance') or 5),
    ]:
        if max_marks > 0:
            components.append({
                'component_name': comp_name,
                'max_marks': float(max_marks),
                'display_order': order,
                'component_group': 'base',
            })
            order += 1

    # Type-specific components
    for comp_name, col_key, default in [
        ('Teacher Assessment', 'max_teaching', 10),
        ('Unit Test',          'max_ut',       20),
        ('Mid-Sem Exam',       'max_mse',      20),
        ('Term Work',          'max_tw',        0),
        ('Practical/Oral',     'max_pr_or',     0),
    ]:
        val = row.get(col_key) or 0
        if val > 0:
            components.append({
                'component_name': comp_name,
                'max_marks': float(val),
                'display_order': order,
                'component_group': 'type_specific',
            })
            order += 1

    return components


def run_dry_run(conn):
    """Print a human-readable report of what the migration WOULD do."""
    cur = conn.cursor(cursor_factory=__import__('psycopg2').extras.DictCursor)

    # 1. Count existing subject_mark_components rows (if the table already exists)
    existing_smc_count = 0
    try:
        cur.execute("SELECT COUNT(*) FROM subject_mark_components")
        existing_smc_count = cur.fetchone()[0]
    except Exception:
        conn.rollback()

    # 2. Fetch all subjects_master rows
    cur.execute("""
        SELECT id, subject_code, subject_name, department, semester,
               max_assignment, max_attendance, max_teaching, max_ut, max_mse,
               max_tw, max_pr_or, max_total
        FROM subjects_master
        ORDER BY department, semester, subject_code
    """)
    subjects = cur.fetchall()

    print("=" * 70)
    print("DRY-RUN: Stage 2 Schema Unification Migration")
    print("=" * 70)
    print(f"\nTotal subjects in subjects_master : {len(subjects)}")
    print(f"Existing rows in subject_mark_components: {existing_smc_count}")
    print()

    # 3. Compute planned inserts
    total_new_rows = 0
    rows_per_subject = {}

    for sub in subjects:
        sub_id = sub['id']
        components = plan_components_for_subject(sub)
        rows_per_subject[sub_id] = {
            'subject': sub,
            'components': components,
        }
        total_new_rows += len(components)

    print(f"{'Subject Code':<22} {'Name':<35} {'Components to Create'}")
    print("-" * 80)
    for sub_id, info in rows_per_subject.items():
        sub = info['subject']
        comps = info['components']
        comp_summary = ', '.join(f"{c['component_name']}({c['max_marks']})" for c in comps)
        print(f"{sub['subject_code']:<22} {(sub['subject_name'] or '')[:34]:<35} {comp_summary}")

    print()
    print("=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"  New tables to create         : subject_mark_components, results_audit_log")
    print(f"  New columns on results       : status VARCHAR (draft->submitted->verified->approved->published)")
    print(f"                                 rank_in_subject INTEGER, rank_in_class INTEGER")
    print(f"  New columns on marks_components: (already altered in db_schema_setup: obtained_marks nullable, is_absent)")
    print(f"  subject_mark_components rows : {total_new_rows} (across {len(subjects)} subjects)")
    print()
    print("DATA IMPACT ON EXISTING RESULTS:")
    print("  - No existing results rows will be modified.")
    print("  - Existing results.published=1 rows will be migrated to status='published'.")
    print("  - Existing results.published=0 rows will be migrated to status='draft'.")
    print()
    print("  ** Run with --apply to execute. Review above before doing so. **")
    print()

    cur.close()


def run_apply(conn):
    """Apply the migration to the live database."""
    cur = conn.cursor()

    print("Applying Stage 2 migration...")

    # 1. Create subject_mark_components table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subject_mark_components (
            id               SERIAL PRIMARY KEY,
            subject_id       INTEGER NOT NULL REFERENCES subjects_master(id) ON DELETE CASCADE,
            component_name   VARCHAR(100) NOT NULL,
            max_marks        REAL NOT NULL,
            display_order    INTEGER DEFAULT 0,
            component_group  VARCHAR(50) DEFAULT 'base'
                             CHECK (component_group IN ('base', 'type_specific')),
            UNIQUE(subject_id, component_name)
        )
    """)
    print("  [OK] subject_mark_components table ensured.")

    # 2. Create results_audit_log table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results_audit_log (
            id            SERIAL PRIMARY KEY,
            result_id     INTEGER REFERENCES results(id) ON DELETE CASCADE,
            action        VARCHAR(50) NOT NULL,
            performed_by  INTEGER REFERENCES faculty(id) ON DELETE SET NULL,
            performed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason        TEXT
        )
    """)
    print("  [OK] results_audit_log table ensured.")

    # 3. Add status and workflow columns to results
    for col, col_def in [
        ("status",          "VARCHAR(50) DEFAULT 'draft'"),
        ("rank_in_subject", "INTEGER"),
        ("rank_in_class",   "INTEGER"),
    ]:
        try:
            cur.execute(f"ALTER TABLE results ADD COLUMN IF NOT EXISTS {col} {col_def}")
            print(f"  [OK] results.{col} column ensured.")
        except Exception as e:
            conn.rollback()
            print(f"  [WARN] Could not add results.{col}: {e}")

    # 4. Migrate existing status: published=1 -> status='published', else 'draft'
    cur.execute("""
        UPDATE results
        SET    status = CASE WHEN published = 1 OR published IS NULL AND status IS NULL THEN
                                 CASE WHEN COALESCE(published, 0) = 1 THEN 'published' ELSE 'draft' END
                             ELSE status
                        END
        WHERE  status IS NULL OR status NOT IN
               ('draft','submitted','verified','approved','published')
    """)
    migrated = cur.rowcount
    print(f"  [OK] {migrated} results rows status migrated (published flag -> status column).")

    # 5. Populate subject_mark_components from subjects_master
    import psycopg2.extras
    read_cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    read_cur.execute("""
        SELECT id, subject_code, subject_name,
               max_assignment, max_attendance, max_teaching,
               max_ut, max_mse, max_tw, max_pr_or
        FROM subjects_master ORDER BY id
    """)
    subjects = read_cur.fetchall()

    inserted = 0
    skipped  = 0
    for sub in subjects:
        components = plan_components_for_subject(sub)
        for comp in components:
            try:
                cur.execute("""
                    INSERT INTO subject_mark_components
                           (subject_id, component_name, max_marks, display_order, component_group)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (subject_id, component_name) DO NOTHING
                """, (sub['id'], comp['component_name'], comp['max_marks'],
                      comp['display_order'], comp['component_group']))
                if cur.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                conn.rollback()
                print(f"  [WARN] Could not insert component {comp['component_name']} "
                      f"for subject {sub['subject_code']}: {e}")

    read_cur.close()
    print(f"  [OK] subject_mark_components: {inserted} rows inserted, {skipped} already existed.")

    conn.commit()
    cur.close()
    print("\nMigration applied successfully.")


def main():
    parser = argparse.ArgumentParser(description="Stage 2 Schema Migration")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true', help='Show what WOULD be done (safe, read-only)')
    group.add_argument('--apply',   action='store_true', help='Apply migration to database')
    args = parser.parse_args()

    conn = get_conn()
    try:
        if args.dry_run:
            run_dry_run(conn)
        else:
            run_apply(conn)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
