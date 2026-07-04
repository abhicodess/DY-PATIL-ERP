import pytest
from repositories.student_repository import StudentRepository
from repositories.faculty_repository import FacultyRepository
from repositories.timetable_repository import TimetableRepository
from repositories.exams_repository import ExamsRepository
from repositories.payroll_repository import PayrollRepository
from repositories.results_repository import ResultsRepository
from repositories.admissions_repository import AdmissionsRepository
from repositories.attendance_repository import AttendanceRepository
from models.student import Student
from models.faculty import Faculty
from models.timetable import Timetable
from models.exams import Exam
from models.payroll import FacultySalary
from models.results import Mark
from models.admissions import Application
from models.attendance import Attendance

def test_student_repository(session):
    repo = StudentRepository()
    student = repo.create(
        roll="CS-0001",
        name="John Doe",
        email="john@dypatil.edu",
        department="Computer",
        division="A",
        year="TY"
    )
    assert student.id is not None
    
    fetched = repo.get_by_id(student.id)
    assert fetched.name == "John Doe"
    
    fetched_roll = repo.get_by_roll("CS-0001")
    assert fetched_roll.id == student.id
    
    results = repo.search(q="John", dept="Computer", division="A")
    assert len(results) >= 1
    assert any(r.id == student.id for r in results)
    
    repo.update(student.id, name="John Updated")
    assert repo.get_by_id(student.id).name == "John Updated"
    
    assert repo.delete(student.id) is True
    assert repo.get_by_id(student.id) is None

def test_faculty_repository(session):
    repo = FacultyRepository()
    faculty = repo.create(name="Dr. Smith", email="smith@dypatil.edu", department="Computer")
    assert faculty.id is not None
    assert repo.get_by_id(faculty.id).name == "Dr. Smith"
    
    assert len(repo.get_all()) >= 1
    assert repo.delete(faculty.id) is True

def test_timetable_repository(session):
    repo = TimetableRepository()
    tt = repo.create(
        day="Monday",
        time="09:00 AM - 10:00 AM",
        subject="Python",
        division="A",
        branch="Computer",
        year="TY",
        semester="V"
    )
    assert tt.id is not None
    
    fac_tt = repo.get_by_faculty(999)
    assert len(fac_tt) == 0
    assert repo.delete(tt.id) is True

def test_exams_repository(session):
    repo = ExamsRepository()
    exam = repo.create(name="MidSem", exam_type="Regular")
    assert exam.id is not None
    
    slots = repo.get_slots(exam.id)
    assert len(slots) == 0
    assert repo.delete(exam.id) is True

def test_payroll_repository(session):
    repo = PayrollRepository()
    sal = repo.create(faculty_id=1, basic_salary=50000.0, hra=5000.0, da=2000.0)
    assert sal.id is not None
    
    fetched = repo.get_salary_info(1)
    assert fetched.basic_salary == 50000.0
    assert repo.delete(sal.id) is True

def test_results_repository(session):
    repo = ResultsRepository()
    mark = repo.create(student_name="Alice", subject="Math", exam_type="Unit Test", marks=18.0, total=20.0)
    assert mark.id is not None
    
    assert len(repo.get_by_student(999)) == 0
    assert repo.delete(mark.id) is True

def test_admissions_repository(monkeypatch):
    import repositories.admissions_repository
    monkeypatch.setattr(repositories.admissions_repository, "qry", lambda query, params=None: [{"id": 1, "applicant_name": "Bob"}])
    monkeypatch.setattr(repositories.admissions_repository, "qone", lambda query, params=None: {"id": 1, "applicant_name": "Bob"})
    monkeypatch.setattr(repositories.admissions_repository, "exe", lambda query, params=None: None)
    
    repo = AdmissionsRepository()
    apps = repo.get_all_applications()
    assert len(apps) == 1
    assert apps[0]["applicant_name"] == "Bob"
    
    app = repo.get_application_by_id(1)
    assert app["applicant_name"] == "Bob"
