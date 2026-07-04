import pytest
from utils.pg_wrapper import exe

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Admin User'
    return 'admin'

def test_stats_endpoint_returns_all_keys(client, logged_in_admin):
    resp = client.get('/api/admin/timetable/stats')
    assert resp.status_code == 200
    data = resp.get_json()
    keys = [
        "master_total", "faculty_approved", "pending_review",
        "rejected_today", "resubmissions", "faculty_active", "divisions_covered"
    ]
    for k in keys:
        assert k in data

def test_stats_pending_count_matches_db(client, logged_in_admin):
    exe("DELETE FROM faculty_timetable")
    # Insert 3 pending slots
    for i in range(3):
        exe(f"""
            INSERT INTO faculty_timetable (faculty_id, faculty_name, day, time_slot, subject, division, status)
            VALUES (999, 'Prof. Test Faculty', 'Monday', '8:30-9:30', 'Subject {i}', 'SE CSE-A', 'pending')
        """)
        
    resp = client.get('/api/admin/timetable/stats')
    assert resp.status_code == 200
    assert resp.get_json()['pending_review'] >= 3

def test_activity_endpoint_returns_list(client, logged_in_admin):
    # Insert a dummy notification
    exe("DELETE FROM admin_notifications")
    exe("""
        INSERT INTO admin_notifications (event_type, faculty_id, faculty_name, message)
        VALUES ('timetable_submitted', 999, 'Prof. Test Faculty', 'Submitted timetable')
    """)
    
    resp = client.get('/api/admin/timetable/activity?limit=5')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]['faculty_name'] == 'Prof. Test Faculty'

def test_coverage_endpoint_returns_divisions(client, logged_in_admin):
    # Seed a slot in master timetable
    exe("DELETE FROM timetable")
    exe("""
        INSERT INTO timetable (day, time, subject, teacher, room, slot_type, division, semester)
        VALUES ('Monday', '8:30-9:30', 'Maths', 'Prof. Test Faculty', '101', 'Theory', 'SE CSE-A', 'I')
    """)
    
    resp = client.get('/api/admin/timetable/coverage')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'SE CSE-A' in data
    assert 'Monday' in data['SE CSE-A']
    assert data['SE CSE-A']['Monday']['total'] == 1

def test_dashboard_page_loads(client, logged_in_admin):
    resp = client.get('/admin/timetable-dashboard')
    assert resp.status_code == 200
    assert b'Faculty Timetable' in resp.data
