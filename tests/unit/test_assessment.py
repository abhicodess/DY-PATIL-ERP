import pytest
from models.assessment import Assessment

def test_faculty_assessment_list_empty(client, faculty):
    with client.session_transaction() as sess:
        sess['faculty_id'] = faculty.id
        sess['role'] = 'faculty'
        sess['name'] = faculty.name

    response = client.get("/faculty/assessments")
    assert response.status_code == 200
    assert b"Welcome to Assessments" in response.data or b"Assessment" in response.data

def test_faculty_save_assessment(client, student, faculty):
    with client.session_transaction() as sess:
        sess['faculty_id'] = faculty.id
        sess['role'] = 'faculty'
        sess['name'] = faculty.name

    # Save details
    data = {
        "student_id": student.id,
        "subject": "Software Engineering",
        "selected_div": "A",
        "selected_dept": "Computer",
        "assignment_1": "Submitted",
        "assignment_2": "9/10",
        "assignment_3": "",
        "assignment_4": "",
        "assignment_5": "",
        "paper_q1": "1 Paper",
        "paper_q2": "",
        "paper_q3": "",
        "paper_q4": "",
        "patent_publication": "1 Patent",
        "copyright": "Registered",
        "project_review_1": "Review 1 Done",
        "project_review_2": "",
        "implementation_documentation": "http://github.com/test",
        "remark": "Excellent progress"
    }
    response = client.post("/faculty/assessments/save", data=data, follow_redirects=True)
    assert response.status_code == 200
    
    # Retrieve and verify database record
    assessment = Assessment.query.filter_by(student_id=student.id, subject="Software Engineering").first()
    assert assessment is not None
    assert assessment.assignment_1 == "Submitted"
    assert assessment.assignment_2 == "9/10"
    assert assessment.paper_q1 == "1 Paper"
    assert assessment.patent_publication == "1 Patent"
    assert assessment.copyright == "Registered"
    assert assessment.project_review_1 == "Review 1 Done"
    assert assessment.implementation_documentation == "http://github.com/test"
    assert assessment.remark == "Excellent progress"

def test_edit_assessment_page(client, student, faculty):
    with client.session_transaction() as sess:
        sess['faculty_id'] = faculty.id
        sess['role'] = 'faculty'
        sess['name'] = faculty.name

    # Access page for editing
    response = client.get(f"/faculty/assessments/edit/{student.id}/Software Engineering")
    assert response.status_code == 200
    assert student.name.encode() in response.data

def test_student_view_assessments(client, student):
    with client.session_transaction() as sess:
        sess['student_id'] = student.id
        sess['role'] = 'student'
        sess['name'] = student.name

    response = client.get("/student/assessments")
    assert response.status_code == 200
    assert b"My Academic Assessments" in response.data
