import pytest
from models.faculty import Faculty
from models.student import Student
from models.timetable import Timetable
from models.attendance import Attendance

def test_faculty_and_admin_endpoints(client, session, app):
    from werkzeug.security import generate_password_hash
    pwd_hash = generate_password_hash("password123")

    # Create faculty member
    faculty = Faculty(
        name="Faculty 1",
        email="faculty_1@dypatil.edu",
        password=pwd_hash,
        department="Computer"
    )
    session.add(faculty)
    
    # Create student
    student = Student(
        name="Student 1",
        roll="CS-001",
        email="student_1@dypatil.edu",
        password=pwd_hash,
        department="Computer",
        division="A",
        year="TY",
        is_active=True
    )
    session.add(student)
    session.flush()

    # Log in as faculty
    login_fac = {
        "username": "faculty_1@dypatil.edu",
        "password": "password123",
        "role": "faculty"
    }
    resp = client.post("/api/v1/auth/login", json=login_fac)
    assert resp.status_code == 200
    fac_token = resp.get_json().get("access_token")
    fac_headers = {"Authorization": f"Bearer {fac_token}"}

    # Test faculty dashboard
    resp_dash = client.get("/api/v1/dashboard/summary", headers=fac_headers)
    assert resp_dash.status_code == 200
    
    # Seed a timetable entry
    t1 = Timetable(
        day="Monday",
        time="09:00 - 10:00",
        subject="Mathematics",
        teacher="Faculty 1",
        room="101",
        division="A",
        year="TY",
        branch="Computer",
        slot_type="Theory",
        faculty_id=faculty.id
    )
    session.add(t1)
    session.flush()

    # Initialize attendance session
    init_data = {"timetable_id": t1.id}
    resp_init = client.post("/api/v1/attendance/session/initialize", json=init_data, headers=fac_headers)
    print("RESP_INIT STATUS:", resp_init.status_code)
    print("RESP_INIT DATA:", resp_init.get_data(as_text=True))
    assert resp_init.status_code == 200
    session_id = resp_init.get_json().get("data", {}).get("session_id")
    assert session_id is not None

    # Submit attendance session
    submit_data = {
        "session_id": session_id,
        "records": [{"student_id": student.id, "status": "Present"}]
    }
    resp_sub = client.post("/api/v1/attendance/submit?is_final=true", json=submit_data, headers=fac_headers)
    assert resp_sub.status_code == 200

    # Log in as admin
    login_adm = {
        "username": "admin",
        "password": "admin123",
        "role": "admin"
    }
    resp_adm = client.post("/api/v1/auth/login", json=login_adm)
    assert resp_adm.status_code == 200
    adm_token = resp_adm.get_json().get("access_token")
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # Test admin dashboard
    resp_adash = client.get("/api/v1/dashboard/summary", headers=adm_headers)
    assert resp_adash.status_code == 200

    # Test admin student list query
    resp_slist = client.get("/api/v1/attendance/?dept=Computer&division=A", headers=adm_headers)
    assert resp_slist.status_code == 200
