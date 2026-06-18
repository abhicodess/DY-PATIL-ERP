import json
import time
from sqlalchemy import text
from app import create_app
from extensions import db

app = create_app()

def run_performance_check():
    with app.app_context():
        report = {
            "timestamp": time.time(),
            "slow_queries": [],
            "missing_indexes": [],
            "pool_stats": {},
            "table_bloat": []
        }

        print("--- Running Database Performance Audit ---")

        # 1. Performance of common queries
        common_queries = [
            ("Attendance Lookup", "EXPLAIN ANALYZE SELECT * FROM attendance WHERE student_id = 1 LIMIT 100"),
            ("Student Roll Call", "EXPLAIN ANALYZE SELECT * FROM students WHERE dept = 'Computer' AND division = 'A'"),
            ("Unread Messages", "EXPLAIN ANALYZE SELECT count(*) FROM messages WHERE receiver_id = 1 AND is_read = false"),
        ]

        for desc, sql in common_queries:
            print(f"Analyzing: {desc}...")
            try:
                res = db.session.execute(text(sql)).fetchall()
                report["slow_queries"].append({"description": desc, "plan": [str(r) for r in res]})
            except Exception as e:
                print(f"Error analyzing {desc}: {e}")

        # 2. Check for missing indexes (Sequential scans on large tables)
        print("Checking for missing indexes...")
        missing_idx_sql = """
            SELECT relname, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
            FROM pg_stat_user_tables
            WHERE seq_scan > 100 AND n_live_tup > 1000
            ORDER BY seq_tup_read DESC;
        """
        res = db.session.execute(text(missing_idx_sql)).fetchall()
        report["missing_indexes"] = [dict(r._mapping) for r in res]

        # 3. Table Bloat
        print("Checking for table bloat...")
        bloat_sql = """
            SELECT relname, n_dead_tup, n_live_tup, 
            (n_dead_tup::float / NULLIF(n_live_tup + n_dead_tup, 0))::decimal(4,2) as bloat_ratio
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 500
            ORDER BY n_dead_tup DESC;
        """
        res = db.session.execute(text(bloat_sql)).fetchall()
        report["table_bloat"] = [dict(r._mapping) for r in res]

        # Final Report
        print("\n--- Summary ---")
        print(f"Missing Indexes Found: {len(report['missing_indexes'])}")
        print(f"Tables with Bloat (>500 dead tuples): {len(report['table_bloat'])}")
        
        with open("db_performance_report.json", "w") as f:
            json.dump(report, f, indent=4)
        print("Detailed report saved to db_performance_report.json")

if __name__ == "__main__":
    run_performance_check()
