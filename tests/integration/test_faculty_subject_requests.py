import pytest
from utils.pg_wrapper import qone, exe, qry

@pytest.fixture
def logged_in_faculty(client):
    with client.session_transaction() as sess:
        sess['faculty_id'] = 999
        sess['name'] = 'Prof. Test Faculty'
        sess['role'] = 'faculty'
    return 999

@pytest.fixture
def logged_in_admin(client):
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Admin User'
    return 'admin'

def test_request_subject_returns_201_and_pending(client, logged_in_faculty):
    payload = {
        "subject_name": "Distributed Systems",
        "division": "A",
        "class_name": "TY",
        "department": "Computer",
        "semester": "V"
    }
    resp = client.post('/api/faculty/subjects/request', json=payload)
    assert resp.status_code == 201

    # Check in DB
    row = qone("SELECT status FROM faculty_subject_assignments WHERE faculty_id = %s AND subject_name = %s", (999, "Distributed Systems"))
    assert row is not None
    assert row[0] == 'pending'

def test_request_subject_notifies_admin(client, logged_in_faculty):
    payload = {
        "subject_name": "Compiler Construction",
        "division": "B",
        "class_name": "TY",
        "department": "Computer",
        "semester": "V"
    }
    resp = client.post('/api/faculty/subjects/request', json=payload)
    assert resp.status_code == 201

    # Check notification in DB
    notif = qone("SELECT message FROM admin_notifications WHERE event_type = %s ORDER BY id DESC LIMIT 1", ('subject_assignment_requested',))
    assert notif is not None
    assert "Prof. Prof. Test Faculty requested to teach Compiler Construction for B" in notif['message']

def test_duplicate_subject_request_returns_409(client, logged_in_faculty):
    payload = {
        "subject_name": "Cryptography",
        "division": "A",
        "class_name": "TY",
        "department": "Computer",
        "semester": "V"
    }
    resp1 = client.post('/api/faculty/subjects/request', json=payload)
    assert resp1.status_code == 201

    resp2 = client.post('/api/faculty/subjects/request', json=payload)
    assert resp2.status_code == 409
    assert "Request already exists" in resp2.get_json()['error']

def test_faculty_cannot_approve_own_request(client, logged_in_faculty):
    row = qone("""
        INSERT INTO faculty_subject_assignments
        (faculty_id, subject_name, division, class_name, department, semester, status)
        VALUES (999, 'Network Security', 'A', 'TY', 'Computer', 'V', 'pending')
        RETURNING id
    """)
    req_id = row[0]

    # Trying to call admin endpoint as faculty
    resp = client.patch(f'/api/admin/subject-requests/{req_id}/approve')
    assert resp.status_code == 403

def test_admin_approve_sets_approved(client, logged_in_admin):
    row = qone("""
        INSERT INTO faculty_subject_assignments
        (faculty_id, subject_name, division, class_name, department, semester, status)
        VALUES (999, 'Artificial Intelligence', 'A', 'TY', 'Computer', 'VI', 'pending')
        RETURNING id
    """)
    req_id = row[0]

    resp = client.patch(f'/api/admin/subject-requests/{req_id}/approve')
    assert resp.status_code == 200

    row_db = qone("SELECT status FROM faculty_subject_assignments WHERE id = %s", (req_id,))
    assert row_db[0] == 'approved'

def test_admin_reject_with_note(client, logged_in_admin):
    row = qone("""
        INSERT INTO faculty_subject_assignments
        (faculty_id, subject_name, division, class_name, department, semester, status)
        VALUES (999, 'Data Mining', 'A', 'TY', 'Computer', 'VI', 'pending')
        RETURNING id
    """)
    req_id = row[0]

    resp = client.patch(f'/api/admin/subject-requests/{req_id}/reject', json={"note": "Assigned to Senior Professor"})
    assert resp.status_code == 200

    row_db = qone("SELECT status, admin_note FROM faculty_subject_assignments WHERE id = %s", (req_id,))
    assert row_db['status'] == 'rejected'
    assert row_db['admin_note'] == 'Assigned to Senior Professor'

def test_delete_pending_request_allowed(client, logged_in_faculty):
    row = qone("""
        INSERT INTO faculty_subject_assignments
        (faculty_id, subject_name, division, class_name, department, semester, status)
        VALUES (999, 'Data Warehousing', 'A', 'TY', 'Computer', 'VI', 'pending')
        RETURNING id
    """)
    req_id = row[0]

    resp = client.delete(f'/api/faculty/subjects/{req_id}')
    assert resp.status_code == 204

def test_delete_approved_request_returns_403(client, logged_in_faculty):
    row = qone("""
        INSERT INTO faculty_subject_assignments
        (faculty_id, subject_name, division, class_name, department, semester, status)
        VALUES (999, 'Image Processing', 'A', 'TY', 'Computer', 'VI', 'approved')
        RETURNING id
    """)
    req_id = row[0]

    resp = client.delete(f'/api/faculty/subjects/{req_id}')
    assert resp.status_code == 403
