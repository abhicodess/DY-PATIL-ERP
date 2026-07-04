import pytest
from flask_jwt_extended import create_access_token
from models.student import Student
from models.attendance import Attendance
from models.extra_models import Result, Subject

def test_student_personal_endpoints(client, session, app):
    # Create test student
    from werkzeug.security import generate_password_hash
    pwd_hash = generate_password_hash("password123")
    
    student = Student(
        name="John Doe",
        roll="CS-002",
        email="john.doe@dypatil.edu",
        password=pwd_hash,
        department="Computer",
        division="A",
        year="TY",
        is_active=True
    )
    session.add(student)
    session.flush()
    
    # Login via Auth API
    login_data = {
        "username": "john.doe@dypatil.edu",
        "password": "password123",
        "role": "student"
    }
    
    resp = client.post("/api/v1/auth/login", json=login_data)
    assert resp.status_code == 200
    token = resp.get_json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Seed mock attendance
    att1 = Attendance(
        student_id=student.id,
        student_name="John Doe",
        date="2026-06-24",
        subject="Mathematics",
        status="Present",
        division="A",
        semester="V"
    )
    session.add(att1)
    session.flush()
    
    # Test attendance endpoint
    resp_att = client.get("/api/v1/student/attendance", headers=headers)
    assert resp_att.status_code == 200
    data_att = resp_att.get_json()
    assert data_att["success"] is True
    assert data_att["data"]["overall"]["total"] == 1
    assert data_att["data"]["overall"]["present"] == 1
    
    # Seed mock subject and result
    subj = Subject(
        name="Mathematics",
        subject_code="MATH101",
        department="Computer",
        semester="V",
        division="A"
    )
    session.add(subj)
    session.flush()
    
    res1 = Result(
        student_name="John Doe",
        roll="CS-002",
        department="Computer",
        year="TY",
        semester="V",
        subject="Mathematics",
        marks=50.0,
        total=60.0,
        grade="O",
        result="Pass",
        published=1
    )
    session.add(res1)
    session.flush()
    
    # Test results endpoint
    resp_res = client.get("/api/v1/student/results", headers=headers)
    assert resp_res.status_code == 200
    data_res = resp_res.get_json()
    assert data_res["success"] is True
    assert len(data_res["data"]) == 1
    assert data_res["data"][0]["subject_name"] == "Mathematics"
    assert data_res["data"][0]["subject_code"] == "MATH101"
    assert data_res["data"][0]["total"] == 50.0
    
    # Test student dashboard endpoint
    resp_dash = client.get("/api/v1/dashboard/summary", headers=headers)
    assert resp_dash.status_code == 200
    data_dash = resp_dash.get_json()
    assert data_dash["success"] is True
    assert data_dash["data"]["metrics"]["attendance_percentage"] == 100.0
    assert data_dash["data"]["metrics"]["published_results"] == 1
