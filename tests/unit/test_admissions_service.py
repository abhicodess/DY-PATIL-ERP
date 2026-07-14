"""
Unit tests for AdmissionsService to cover its uncovered paths (89% target).
All DB/external calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import io


class FakeRepo:
    """Mock repository that returns controllable data."""
    def __init__(self):
        self._app_counter = 1
        self._tokens_used = set()

    def get_application_by_token(self, token):
        return None  # Always return None → token unique

    def create_application(self, data):
        return self._app_counter

    def log_timeline(self, **kwargs):
        pass

    def get_application_by_id(self, app_id):
        mock = MagicMock()
        mock.applied_year = "2024"
        mock.token = "TEST_TOKEN_PLACEHOLDER"  # noqa: S105 - test-only mock value
        return mock

    def create_document(self, data):
        return True

    def update_application_status(self, app_id, status, notes=""):
        return True


# ────────────────────────────────────────────────────────
# calculate_merit_score
# ────────────────────────────────────────────────────────
def test_merit_score_full_marks():
    with patch("services.admissions_service.AdmissionsRepository", return_value=FakeRepo()):
        from services.admissions_service import AdmissionsService
        svc = AdmissionsService()
        score = svc.calculate_merit_score({"hsc_percentage": 100, "entrance_score": 100, "bonus_score": 10})
        assert score == 100.0

def test_merit_score_partial():
    with patch("services.admissions_service.AdmissionsRepository", return_value=FakeRepo()):
        from services.admissions_service import AdmissionsService
        svc = AdmissionsService()
        # 80% HSC → 48, 70 entrance → 21, 5 bonus → 74
        score = svc.calculate_merit_score({"hsc_percentage": 80, "entrance_score": 70, "bonus_score": 5})
        assert score == 74.0

def test_merit_score_bonus_capped():
    with patch("services.admissions_service.AdmissionsRepository", return_value=FakeRepo()):
        from services.admissions_service import AdmissionsService
        svc = AdmissionsService()
        # Bonus capped at 10
        score = svc.calculate_merit_score({"hsc_percentage": 0, "entrance_score": 0, "bonus_score": 100})
        assert score == 10.0

def test_merit_score_invalid_inputs():
    with patch("services.admissions_service.AdmissionsRepository", return_value=FakeRepo()):
        from services.admissions_service import AdmissionsService
        svc = AdmissionsService()
        score = svc.calculate_merit_score({"hsc_percentage": "not_a_number"})
        assert score == 0.0

def test_merit_score_missing_fields():
    with patch("services.admissions_service.AdmissionsRepository", return_value=FakeRepo()):
        from services.admissions_service import AdmissionsService
        svc = AdmissionsService()
        score = svc.calculate_merit_score({})
        assert score == 0.0


# ────────────────────────────────────────────────────────
# submit_application
# ────────────────────────────────────────────────────────
VALID_APP_DATA = {
    "applicant_name": "Alice Smith",
    "applicant_email": "alice@example.com",
    "applicant_phone": "9876543210",
    "date_of_birth": "2005-06-15",
    "gender": "Female",
    "category": "Open",
    "domicile_state": "Maharashtra",
    "applied_department": "Computer Engineering",
    "applied_year": "FE",
    "hsc_percentage": 85,
    "entrance_score": 75,
}

def test_submit_application_success(app):
    """submit_application should persist and return the application."""
    with app.app_context():
        fake_repo = FakeRepo()
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo), \
             patch("tasks.notification_tasks.send_application_confirmation") as mock_task:
            mock_task.delay.return_value = MagicMock()
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            result = svc.submit_application(VALID_APP_DATA.copy())
            assert result is not None

def test_submit_application_missing_field(app):
    """submit_application should raise ValueError for missing required fields."""
    with app.app_context():
        fake_repo = FakeRepo()
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo):
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            incomplete = {"applicant_name": "Alice"}  # missing other required fields
            with pytest.raises(ValueError, match="Missing required field"):
                svc.submit_application(incomplete)

def test_submit_application_merit_score_calculated(app):
    """submit_application should include calculated merit score in data."""
    with app.app_context():
        fake_repo = FakeRepo()
        submitted_data = {}
        
        def capture_create(data):
            submitted_data.update(data)
            return 1
        
        fake_repo.create_application = capture_create
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo), \
             patch("tasks.notification_tasks.send_application_confirmation") as mock_task:
            mock_task.delay.return_value = MagicMock()
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            svc.submit_application(VALID_APP_DATA.copy())
            assert "merit_score" in submitted_data
            assert submitted_data["merit_score"] > 0


# ────────────────────────────────────────────────────────
# upload_document
# ────────────────────────────────────────────────────────
def test_upload_document_invalid_extension(app):
    """upload_document should raise ValueError for invalid file types."""
    with app.app_context():
        fake_repo = FakeRepo()
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo):
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            mock_file = MagicMock()
            mock_file.filename = "document.exe"
            with pytest.raises(ValueError, match="Invalid file type"):
                svc.upload_document(1, "SSC_MARKSHEET", mock_file)

def test_upload_document_too_large(app):
    """upload_document should raise ValueError for files over 2MB."""
    with app.app_context():
        fake_repo = FakeRepo()
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo):
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            mock_file = MagicMock()
            mock_file.filename = "document.pdf"
            # Simulate 3MB file
            mock_file.seek = MagicMock()
            mock_file.tell = MagicMock(return_value=3 * 1024 * 1024)
            with pytest.raises(ValueError, match="2MB"):
                svc.upload_document(1, "SSC_MARKSHEET", mock_file)

def test_upload_document_app_not_found(app):
    """upload_document should raise ValueError when application not found."""
    with app.app_context():
        fake_repo = FakeRepo()
        fake_repo.get_application_by_id = MagicMock(return_value=None)
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo):
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            mock_file = MagicMock()
            mock_file.filename = "doc.pdf"
            with pytest.raises(ValueError, match="Application not found"):
                svc.upload_document(9999, "SSC_MARKSHEET", mock_file)

def test_upload_document_magic_mime_validation(app):
    """upload_document should validate real MIME types using magic."""
    with app.app_context():
        fake_repo = FakeRepo()
        with patch("services.admissions_service.AdmissionsRepository", return_value=fake_repo):
            from services.admissions_service import AdmissionsService
            svc = AdmissionsService()
            
            class RealMockFile:
                def __init__(self, filename, content):
                    self.filename = filename
                    self.content = content
                    self.offset = 0
                def seek(self, offset, whence=0):
                    if whence == 0:
                        self.offset = offset
                    elif whence == 2:
                        self.offset = len(self.content)
                def tell(self):
                    return self.offset
                def read(self, size=-1):
                    start = self.offset
                    if size < 0:
                        self.offset = len(self.content)
                    else:
                        self.offset = min(len(self.content), self.offset + size)
                    return self.content[start:self.offset]
            
            # PDF header: %PDF-1.4
            pdf_file = RealMockFile("doc.pdf", b"%PDF-1.4\n" + b"\x00" * 100)
            url = svc.upload_document(1, "SSC_MARKSHEET", pdf_file)
            assert "SSC_MARKSHEET.pdf" in url
            
            # Invalid header disguised as pdf
            bad_file = RealMockFile("fake.pdf", b"executable_code_here_not_pdf")
            with pytest.raises(ValueError, match="Invalid file type"):
                svc.upload_document(1, "SSC_MARKSHEET", bad_file)
