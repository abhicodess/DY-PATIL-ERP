import sys
import os

# Set environment and path
os.environ['FLASK_ENV'] = 'development'
sys.path.insert(0, '.')

from app import create_app

def run_tests():
    print("Initializing Flask App...")
    try:
        app = create_app()
        app.testing = True
        client = app.test_client()
        print("Flask App created successfully!\n")
    except Exception as e:
        print(f"FAILED to initialize Flask App: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    print("Checking registered route rules:")
    rules = {r.rule: r.endpoint for r in app.url_map.iter_rules()}
    
    # 1. Verify New Faculty Extra Routes
    expected_faculty_routes = [
        "/faculty_marks",
        "/faculty_save_marks",
        "/faculty_delete_marks",
        "/faculty/api/students_by_subject",
        "/faculty_notices",
        "/faculty_save_notice",
        "/faculty_delete_notice",
        "/faculty_notes",
        "/faculty_save_note",
        "/faculty_edit_note",
        "/faculty_delete_note",
        "/faculty_timetable",
        "/faculty_profile",
        "/faculty_update_profile",
        "/faculty_cumulative",
        "/import_marks_v2",
        "/export_marks_excel",
        "/faculty_results",
        "/faculty_save_result",
        "/faculty_edit_result",
        "/faculty_delete_result"
    ]
    
    print("\n[TEST 1] Verifying Faculty Extra blueprint routes:")
    faculty_failures = 0
    for route in expected_faculty_routes:
        if route in rules:
            print(f"  [OK] Found: {route} -> {rules[route]}")
        else:
            print(f"  [MISSING] MISSING: {route}")
            faculty_failures += 1
            
    # 2. Verify timetable_v2_bp routes
    expected_timetable_routes = [
        "/timetable_v2",
        "/api/add_time_slot",
        "/api/copy_day"
    ]
    print("\n[TEST 2] Verifying Timetable V2 blueprint routes:")
    timetable_failures = 0
    for route in expected_timetable_routes:
        if route in rules:
            print(f"  [OK] Found: {route} -> {rules[route]}")
        else:
            print(f"  [MISSING] MISSING: {route}")
            timetable_failures += 1

    # 3. Verify routes_results_bp routes
    expected_results_routes = [
        "/results_dashboard",
        "/results_analytics",
        "/results_reportcard/<roll>",
        "/results_export_excel",
        "/results_chart_data",
        "/results_import"
    ]
    print("\n[TEST 3] Verifying Results Dashboard blueprint routes:")
    results_failures = 0
    for route in expected_results_routes:
        if route in rules:
            print(f"  [OK] Found: {route} -> {rules[route]}")
        else:
            print(f"  [MISSING] MISSING: {route}")
            results_failures += 1

    # 3b. Verify advanced_att_marks_bp routes
    expected_att_marks_routes = [
        "/admin_att_marks_dashboard",
        "/admin_student_att_marks/<int:student_id>",
        "/export_att_marks_excel",
        "/faculty_att_marks",
        "/student_att_marks",
        "/api/student_att_marks_summary/<int:student_id>",
        "/api/att_marks_dept_stats"
    ]
    print("\n[TEST 3b] Verifying Advanced Attendance + Marks blueprint routes:")
    att_marks_failures = 0
    for route in expected_att_marks_routes:
        if route in rules:
            print(f"  [OK] Found: {route} -> {rules[route]}")
        else:
            print(f"  [MISSING] MISSING: {route}")
            att_marks_failures += 1

    # 4. Verify Health Route and basic redirects
    print("\n[TEST 4] Verifying basic connectivity & redirect routes:")
    try:
        # Test Health
        resp = client.get("/health")
        print(f"  [OK] GET /health -> Status Code: {resp.status_code}, Data: {resp.json}")
        
        # Test /faculty_dashboard redirects (should redirect to auth or dashboard)
        resp = client.get("/faculty_dashboard")
        print(f"  [OK] GET /faculty_dashboard -> Status Code: {resp.status_code} (Redirect: {resp.location})")
        
        # Test /student_dashboard redirects
        resp = client.get("/student_dashboard")
        print(f"  [OK] GET /student_dashboard -> Status Code: {resp.status_code} (Redirect: {resp.location})")

        # Test results blueprint redirecting admin to /results_dashboard
        with client.session_transaction() as sess:
            sess['role'] = 'admin'
            sess['faculty_id'] = 1
            sess['name'] = 'Admin User'
            
        resp = client.get("/results/")
        print(f"  [OK] GET /results/ (as Admin) -> Status Code: {resp.status_code} (Redirect: {resp.location})")
        
    except Exception as e:
        print(f"  [FAIL] Connectivity test failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    total_failures = faculty_failures + timetable_failures + results_failures + att_marks_failures
    if total_failures == 0:
        print("\nALL ROUTING TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"\nROUTING TESTS FAILED with {total_failures} missing routes.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
