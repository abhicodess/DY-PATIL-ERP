import pytest

def test_all_routes_exist(app):
    rules = {r.rule: r.endpoint for r in app.url_map.iter_rules()}
    
    # 1. Verify Faculty Extra Routes
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
    for route in expected_faculty_routes:
        assert route in rules

    # 2. Verify timetable_v2_bp routes
    expected_timetable_routes = [
        "/timetable_v2",
        "/api/add_time_slot",
        "/api/copy_day"
    ]
    for route in expected_timetable_routes:
        assert route in rules

    # 3. Verify routes_results_bp routes
    expected_results_routes = [
        "/results_dashboard",
        "/results_analytics",
        "/results_reportcard/<roll>",
        "/results_export_excel",
        "/results_chart_data"
    ]
    for route in expected_results_routes:
        assert route in rules

def test_admin_routes(client, student, session):
    from models.extra_models import Result
    res = Result(
        student_id=student.id,
        student_name=student.name,
        subject="Mathematics",
        exam_type="End Sem",
        marks=80.0,
        total=100.0,
        roll=student.roll,
        department=student.department,
        semester="Semester I",
        year=student.year,
        published=1
    )
    session.add(res)
    session.flush()

    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Admin User'
        sess['user_id'] = 1
        
    for url in [
        "/admin_att_marks_dashboard",
        "/results_dashboard",
        "/timetable_v2",
        "/attendance",
        "/attendance_dashboard",
        "/results_analytics",
        "/shortage_report",
        "/admin/reports/division_attendance",
        "/admin/reports/defaulters",
        f"/results_reportcard/{student.roll}"
    ]:
        resp = client.get(url)
        assert resp.status_code == 200, f"URL {url} failed with status {resp.status_code}. Location: {resp.location if 'Location' in resp.headers else 'None'}"

def test_faculty_routes(client, faculty):
    with client.session_transaction() as sess:
        sess['role'] = 'faculty'
        sess['faculty_id'] = faculty.id
        sess['name'] = faculty.name
        
    for url in [
        "/faculty_marks",
        "/faculty_notices",
        "/faculty_notes",
        "/faculty_timetable",
        "/faculty_profile",
        "/faculty_cumulative",
        "/faculty_results",
        "/faculty_att_marks"
    ]:
        resp = client.get(url)
        assert resp.status_code == 200

def test_student_routes(client, student):
    with client.session_transaction() as sess:
        sess['role'] = 'student'
        sess['student_id'] = student.id
        sess['name'] = student.name
        
    for url in [
        "/student_att_marks",
        "/student_analysis"
    ]:
        resp = client.get(url)
        assert resp.status_code == 200
