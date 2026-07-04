import pytest
from utils.pg_wrapper import exe, qone

def test_timetable_teacher_clash_detection(client, session, faculty, student):
    faculty_name = faculty.name
    student_division = student.division
    student_dept = student.department
    student_year = student.year

    # 1. Log in as admin
    with client.session_transaction() as sess:
        sess['role'] = 'admin'
        sess['name'] = 'Administrator'
        sess['_csrf_token'] = 'test_csrf_token'

    # Need a subject in DB
    exe("INSERT INTO subjects (name, subject_code, department) VALUES (%s, %s, %s)", ("Math", "M101", student_dept))

    # Add first valid slot: Monday 09:00 - 10:00
    data1 = {
        "day": "Monday",
        "time": "09:00 - 10:00",
        "subject": "Math",
        "teacher": faculty_name,
        "room": "101",
        "division": student_division,
        "semester": "5",
        "slot_type": "Theory"
    }
    
    response1 = client.post("/save_timetable", data=data1)
    assert response1.status_code == 302 # Redirect on success
    
    # Verify the timetable entry was added
    slot1 = qone("SELECT id FROM timetable WHERE day='Monday' AND teacher=%s", (faculty_name,))
    assert slot1 is not None
    slot1_id = slot1["id"]

    # Try to add second slot for the SAME faculty at the same time: Monday 09:00 - 10:00 (Teacher Clash)
    data2 = {
        "day": "Monday",
        "time": "09:00 - 10:00",
        "subject": "Math",
        "teacher": faculty_name,
        "room": "102",  # Different room, but same teacher & time
        "division": student_division,
        "semester": "5",
        "slot_type": "Theory"
    }
    
    response2 = client.post("/save_timetable", data=data2)
    assert response2.status_code == 409
    assert b"Teacher clash" in response2.data

    # Add a separate valid slot for another teacher or another time
    # Let's say: Tuesday 09:00 - 10:00
    data3 = {
        "day": "Tuesday",
        "time": "09:00 - 10:00",
        "subject": "Math",
        "teacher": faculty_name,
        "room": "101",
        "division": student_division,
        "semester": "5",
        "slot_type": "Theory"
    }
    response3 = client.post("/save_timetable", data=data3)
    assert response3.status_code == 302
    
    slot2 = qone("SELECT id FROM timetable WHERE day='Tuesday' AND teacher=%s", (faculty_name,))
    assert slot2 is not None
    slot2_id = slot2["id"]

    # Now edit Tuesday's slot to be Monday 09:00 - 10:00, causing a conflict with the existing Monday slot
    edit_data = {
        "tt_id": slot2_id,
        "day": "Monday",  # Change Tuesday to Monday
        "time": "09:00 - 10:00",
        "subject": "Math",
        "teacher": faculty_name,
        "room": "101",
        "division": student_division,
        "semester": "5",
        "slot_type": "Theory"
    }
    
    response_edit = client.post("/edit_timetable", data=edit_data)
    assert response_edit.status_code == 409
    assert b"Teacher clash" in response_edit.data
