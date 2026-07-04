import pytest
import os
from services.student_service import StudentService
from services.faculty_service import FacultyService
from services.tenant_service import TenantService
from services.timetable_service import TimetableService
from services.exam_service import ExamService
from models.timetable_model import TimetableEntry

def test_student_service(session, monkeypatch):
    monkeypatch.setenv("DEFAULT_STUDENT_PASSWORD", "password123")
    
    service = StudentService()
    student = service.create_student({
        "roll": "CS-0002",
        "name": "JaneUniqueXYZ",
        "email": "jane@dypatil.edu",
        "department": "Computer",
        "division": "A",
        "year": "TY",
        "password": "my-password"
    })
    assert student.id is not None
    assert student.name == "JaneUniqueXYZ"
    
    verified = service.verify_credentials("CS-0002", "my-password")
    assert verified is not None
    assert verified.id == student.id

    assert service.verify_credentials("CS-0002", "wrong-password") is None
    
    students = service.get_all_students({"q": "JaneUniqueXYZ"})
    assert len(students) == 1
    
    service.update_student(student.id, {"name": "JaneUniqueXYZ Updated"})
    assert service.repository.get_by_id(student.id).name == "JaneUniqueXYZ Updated"
    
    assert service.delete_student(student.id) is True

def test_faculty_service(session, monkeypatch):
    monkeypatch.setenv("DEFAULT_FACULTY_PASSWORD", "password123")
    
    service = FacultyService()
    faculty = service.create_faculty({
        "name": "Prof. Alan",
        "email": "alan@dypatil.edu",
        "department": "Computer",
        "password": "faculty-password"
    })
    assert faculty.id is not None
    assert faculty.name == "Prof. Alan"
    
    verified = service.verify_credentials("alan@dypatil.edu", "faculty-password")
    assert verified is not None
    assert verified.id == faculty.id
    
    faculties = service.get_all_faculty({"q": "Alan"})
    assert len(faculties) == 1
    
    assert service.delete_faculty(faculty.id) is True

def test_tenant_service(monkeypatch):
    import services.tenant_service
    mock_redis = type("MockRedis", (object,), {
        "get": lambda self, k: None,
        "setex": lambda self, k, t, v: None,
        "delete": lambda self, *a: None
    })()
    monkeypatch.setattr(services.tenant_service, "redis_client", mock_redis)
    monkeypatch.setattr(services.tenant_service, "qone", lambda q, p=None: {
        "id": 1,
        "slug": "dypatil",
        "schema_name": "public",
        "is_active": True,
        "created_at": None,
        "expires_at": None
    })
    monkeypatch.setattr(services.tenant_service, "exe", lambda q, p=None: None)
    
    tenant = TenantService.get_by_subdomain("dypatil")
    assert tenant is not None
    assert tenant["slug"] == "dypatil"
    
    tenant_id = TenantService.get_by_id(1)
    assert tenant_id is not None
    assert tenant_id["id"] == 1

def test_timetable_service(session):
    service = TimetableService()
    entry = TimetableEntry(
        id=None,
        day="Tuesday",
        time="10:00 - 11:00",
        subject="Compiler Design",
        division="A",
        semester="VI",
        department="Computer",
        teacher="Prof. X",
        room="303"
    )
    
    res = service.add_or_update_slot(entry)
    assert res["ok"] is True
    assert res["id"] is not None

    res_copy = service.copy_day_schedule("Tuesday", "Wednesday")
    assert res_copy["ok"] is True
    assert res_copy["count"] >= 1

def test_exam_service(session, student, faculty):
    service = ExamService()
    service.attendance_service.mark_attendance(student.id, "Math", "Present", faculty.id)
    assert service.validate_eligibility(student.id) is True
    
    exams = service.get_upcoming_exams()
    assert len(exams) == 0

def test_admissions_service(monkeypatch):
    from services.admissions_service import AdmissionsService
    from repositories.admissions_repository import AdmissionsRepository
    
    service = AdmissionsService()
    
    # 1. Test calculate_merit_score
    score = service.calculate_merit_score({
        "hsc_percentage": 80,
        "entrance_score": 90,
        "bonus_score": 8
    })
    assert score == 83.0
    
    score = service.calculate_merit_score({
        "hsc_percentage": 100,
        "entrance_score": 100,
        "bonus_score": 20
    })
    assert score == 100.0
    
    assert service.calculate_merit_score({"hsc_percentage": "invalid"}) == 0.0

    # 2. Test submit_application
    class MockApp:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
        def __getitem__(self, item):
            return getattr(self, item)
        def get(self, item, default=None):
            return getattr(self, item, default)

    created_app = MockApp(id=10, applied_year="2025-26", token="DUMMYTOK", status="PENDING")
    monkeypatch.setattr(AdmissionsRepository, "get_application_by_token", lambda self, token: None)
    monkeypatch.setattr(AdmissionsRepository, "create_application", lambda self, data: 10)
    monkeypatch.setattr(AdmissionsRepository, "log_timeline", lambda self, **kw: None)
    monkeypatch.setattr(AdmissionsRepository, "get_application_by_id", lambda self, app_id: created_app)
    
    import tasks.notification_tasks
    monkeypatch.setattr(tasks.notification_tasks.send_application_confirmation, "delay", lambda app_id: None)
    monkeypatch.setattr(tasks.notification_tasks.send_status_update, "delay", lambda app_id, status: None)
    monkeypatch.setattr(tasks.notification_tasks.send_offer_letter, "delay", lambda app_id: None)

    app_data = {
        'applicant_name': 'Bob Ross',
        'applicant_email': 'bob@ross.com',
        'applicant_phone': '1234567890',
        'date_of_birth': '1990-01-01',
        'gender': 'Male',
        'category': 'General',
        'domicile_state': 'Maharashtra',
        'applied_department': 'Computer',
        'applied_year': '2025-26'
    }
    
    app = service.submit_application(app_data)
    assert app["id"] == 10
    
    with pytest.raises(ValueError):
        service.submit_application({'applicant_name': ''})

    # 3. Test upload_document
    class MockFile:
        def __init__(self, filename):
            self.filename = filename
        def seek(self, offset, whence=0):
            pass
        def tell(self):
            return 500
            
    mock_file = MockFile("test.png")
    monkeypatch.setattr(AdmissionsRepository, "create_document", lambda self, data: 5)
    monkeypatch.setenv("AWS_S3_BUCKET", "my-bucket")
    
    url = service.upload_document(10, "SSC_MARKSHEET", mock_file)
    assert "my-bucket.s3.amazonaws.com/admissions/2025-26/DUMMYTOK/SSC_MARKSHEET.png" in url
    
    class LargeFile:
        filename = "big.pdf"
        def seek(self, offset, whence=0):
            pass
        def tell(self):
            return 3 * 1024 * 1024
    with pytest.raises(ValueError, match="exceeds the 2MB limit"):
        service.upload_document(10, "SSC_MARKSHEET", LargeFile())

    # 4. Test verify_document
    import services.admissions_service
    monkeypatch.setattr(services.admissions_service, "qone", lambda q, p=None: {"application_id": 10, "document_type": "SSC_MARKSHEET"})
    monkeypatch.setattr(AdmissionsRepository, "verify_document", lambda self, doc_id, admin_id: None)
    monkeypatch.setattr(AdmissionsRepository, "get_documents_by_application", lambda self, app_id: [
        {"document_type": "SSC_MARKSHEET", "verified": True},
        {"document_type": "HSC_MARKSHEET", "verified": True},
        {"document_type": "LEAVING_CERTIFICATE", "verified": True},
        {"document_type": "PHOTO", "verified": True},
        {"document_type": "SIGNATURE", "verified": True}
    ])
    monkeypatch.setattr(AdmissionsRepository, "update_application_status", lambda self, app_id, status, remarks, admin_id: None)
    
    service.verify_document(5, 1)

    # 5. Test generate_merit_list
    monkeypatch.setattr(services.admissions_service, "qry", lambda q, p=None: [{"id": 10, "merit_score": 83.0}])
    monkeypatch.setattr(AdmissionsRepository, "clear_provisional_merit_list", lambda self, *a: None)
    monkeypatch.setattr(AdmissionsRepository, "insert_merit_list_entry", lambda self, data: None)
    monkeypatch.setattr(AdmissionsRepository, "update_application_rank", lambda self, *a: None)
    
    merit_list = service.generate_merit_list("Computer", "General", "2025-26", 1)
    assert len(merit_list) == 1
    assert merit_list[0]["rank"] == 1

    # 6. Test finalize_merit_list
    monkeypatch.setattr(services.admissions_service, "qry", lambda q, p=None: [
        {"app_id": 10, "rank": 1, "applicant_name": "Bob Ross"}
    ])
    monkeypatch.setattr(AdmissionsRepository, "get_seat_matrix_entry", lambda self, *a: {"available_seats": 5})
    monkeypatch.setattr(AdmissionsRepository, "finalize_merit_list_entries", lambda self, *a: None)
    monkeypatch.setattr(AdmissionsRepository, "update_seat_matrix_filled", lambda self, *a: None)
    
    assert service.finalize_merit_list("Computer", "General", "2025-26", 1) is True

    # 7. Test check_application_status
    monkeypatch.setattr(AdmissionsRepository, "get_application_by_token", lambda self, t: created_app)
    monkeypatch.setattr(services.admissions_service, "qry", lambda q, p=None: [{"action": "APPLICATION_SUBMITTED"}])
    monkeypatch.setattr(AdmissionsRepository, "get_documents_by_application", lambda self, app_id: [])
    
    status = service.check_application_status("DUMMYTOK")
    assert status["application"]["token"] == "DUMMYTOK"
    assert len(status["timeline"]) == 1

    monkeypatch.setattr(AdmissionsRepository, "get_seat_matrix", lambda self, yr: [{"department": "Computer"}])
    assert len(service.get_seat_matrix("2025-26")) == 1

def test_payroll_service(monkeypatch):
    from services.payroll_service import PayrollService
    from repositories.payroll_repository import PayrollRepository
    
    service = PayrollService()
    
    # 1. No salary info
    monkeypatch.setattr(PayrollRepository, "get_salary_info", lambda self, fid: None)
    assert service.calculate_monthly_salary(1) == 0
    
    # 2. Has salary info
    class MockSal:
        basic_salary = 50000.0
        hra = 5000.0
        da = 2000.0
        pf_deduction = 4000.0
        
    mock_sal = MockSal()
    monkeypatch.setattr(PayrollRepository, "get_salary_info", lambda self, fid: mock_sal)
    
    res = service.calculate_monthly_salary(1)
    assert res['gross'] == 57000.0
    assert res['net'] == 53000.0
    assert res['pf'] == 4000.0
    
    # Test generate_payslip
    res_payslip = service.generate_payslip(1, 10, 2026)
    assert res_payslip == res

def test_results_service(monkeypatch):
    from services.results_service import ResultsService
    from repositories.results_repository import ResultsRepository
    
    service = ResultsService()
    monkeypatch.setattr(ResultsRepository, "get_by_student", lambda self, sid: [{"subject": "Math"}])
    
    assert len(service.get_student_results(1)) == 1
    assert service.calculate_gpa(1, "V") is None

def test_intelligence_service(session, monkeypatch):
    from services.intelligence_service import IntelligenceService
    from models.student import Student
    from models.attendance import Attendance

    import services.intelligence_service
    orig_qry = services.intelligence_service.qry
    dummy_insights = {
        "risk_profiles": [{"id": 1, "name": "Alice Defaulter", "percentage": 33.3}],
        "attendance_trend": [{"week": "2026-25", "avg_pct": 80.0}],
        "subject_anomalies": [{"subject": "Math", "avg_pct": 50.0}]
    }
    def mock_qry(sql, params=None, timeout=30):
        if "date_trunc" in sql or "INTERVAL" in sql:
            return dummy_insights["attendance_trend"]
        elif "anomaly_sql" in sql or "HAVING" in sql:
            return dummy_insights["subject_anomalies"]
        elif "risk_sql" in sql:
            return dummy_insights["risk_profiles"]
        return orig_qry(sql, params, timeout)

    monkeypatch.setattr(services.intelligence_service, "qry", mock_qry)

    s1 = Student(name="Alice Defaulter", roll="CS-101", department="Computer", division="A", year="TY", email="alice@dypatil.edu")
    s2 = Student(name="Bob Topper", roll="CS-102", department="Computer", division="A", year="TY", email="bob@dypatil.edu")
    session.add_all([s1, s2])
    session.commit()

    a1 = Attendance(student_id=s1.id, student_name=s1.name, subject="Math", date="2026-06-20", status="Absent")
    a2 = Attendance(student_id=s1.id, student_name=s1.name, subject="Math", date="2026-06-21", status="Absent")
    a3 = Attendance(student_id=s1.id, student_name=s1.name, subject="Math", date="2026-06-22", status="Present")
    
    a4 = Attendance(student_id=s2.id, student_name=s2.name, subject="Math", date="2026-06-20", status="Present")
    a5 = Attendance(student_id=s2.id, student_name=s2.name, subject="Math", date="2026-06-21", status="Present")
    a6 = Attendance(student_id=s2.id, student_name=s2.name, subject="Math", date="2026-06-22", status="Present")
    a7 = Attendance(student_id=s2.id, student_name=s2.name, subject="Math", date="2026-06-23", status="Present")
    session.add_all([a1, a2, a3, a4, a5, a6, a7])
    session.commit()

    insights = IntelligenceService.get_attendance_insights("Computer", "TY", "A")
    assert insights is not None
    assert len(insights["risk_profiles"]) > 0
    assert len(insights["attendance_trend"]) > 0
    assert len(insights["subject_anomalies"]) > 0

    prediction_alice = IntelligenceService.predict_defaulters(s1.id)
    assert prediction_alice["risk"] == "high"

    prediction_bob = IntelligenceService.predict_defaulters(s2.id)
    assert prediction_bob["risk"] == "low"
    
    prediction_none = IntelligenceService.predict_defaulters(999)
    assert prediction_none["risk"] == "low"

def test_export_service():
    from services.export_service import ExportService
    data = [
        ["Alice", 85],
        ["Bob", 92]
    ]
    headers = ["Name", "Score"]
    result = ExportService.to_excel(data, headers, title="Student Scores")
    assert result is not None
    content = result.read()
    assert len(content) > 0
    assert content.startswith(b"PK")

def test_job_service(monkeypatch):
    from services.job_service import JobService
    import json
    
    class MockRedis:
        def __init__(self):
            self.data = {}
            self.called_get = False
            self.called_setex = False
            
        def get(self, key):
            self.called_get = True
            return self.data.get(key)
            
        def setex(self, key, ttl, value):
            self.called_setex = True
            self.data[key] = value
            
    mock_redis = MockRedis()
    mock_redis.data["job:test-job-id"] = json.dumps({
        "id": "test-job-id",
        "type": "IMPORT",
        "user_id": 1,
        "status": "PENDING",
        "progress": 0,
        "result_url": None,
        "error": None
    })
    
    import services.job_service
    monkeypatch.setattr(services.job_service, "redis_client", mock_redis)
    
    job_id = JobService.create_job("IMPORT", 1)
    assert job_id is not None
    assert mock_redis.called_setex is True
    
    mock_redis.called_setex = False
    JobService.update_status("test-job-id", "COMPLETED", progress=100, result_url="http://download.xlsx")
    assert mock_redis.called_get is True
    assert mock_redis.called_setex is True
    
    status = JobService.get_status("test-job-id")
    assert status is not None
    assert status["status"] == "COMPLETED"


