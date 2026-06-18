import pytest

def test_attendance_admin_access(client):
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
    response = client.get("/attendance/")
    assert response.status_code == 200

def test_attendance_student_access_denied(client):
    with client.session_transaction() as sess:
        sess['role'] = 'student'
    response = client.get("/attendance/")
    assert response.status_code == 403

def test_attendance_unauthenticated_redirect(client):
    response = client.get("/attendance/")
    assert response.status_code == 302 # Redirect to login
