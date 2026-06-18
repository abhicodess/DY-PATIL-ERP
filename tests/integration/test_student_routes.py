import pytest

def test_student_list_admin(client):
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
    response = client.get("/admin/students")
    assert response.status_code == 200

def test_add_student_valid(client, session):
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
    
    data = {
        "roll_no": "CS-001",
        "name": "Test Student",
        "email": "test@dypatil.edu",
        "dept": "Computer",
        "division": "A",
        "year": "TY",
        "semester": "5"
    }
    response = client.post("/admin/add_student", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Student added successfully" in response.data
