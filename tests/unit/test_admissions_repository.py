"""
Repository tests for AdmissionsRepository — all DB calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch


# ────────────────────────────────────────────────────────
# AdmissionsRepository
# ────────────────────────────────────────────────────────
class TestAdmissionsRepository:
    def test_get_all_applications_no_filters(self, app):
        """get_all_applications with no filters returns all."""
        with app.app_context():
            with patch("repositories.admissions_repository.qry", return_value=[{"id": 1}]) as mock_qry:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.get_all_applications()
                assert isinstance(result, list)

    def test_get_all_applications_with_department_filter(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qry", return_value=[]) as mock_qry:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.get_all_applications({"department": "CS"})
                sql = mock_qry.call_args[0][0]
                assert "applied_department" in sql

    def test_get_all_applications_with_all_filters(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qry", return_value=[]) as mock_qry:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.get_all_applications({
                    "department": "CS", "category": "Open",
                    "status": "PENDING", "date_start": "2024-01-01", "date_end": "2024-12-31"
                })
                sql = mock_qry.call_args[0][0]
                assert "applied_department" in sql
                assert "category" in sql
                assert "status" in sql

    def test_get_application_by_id(self, app):
        with app.app_context():
            mock_app = {"id": 1, "token": "ABC123"}
            with patch("repositories.admissions_repository.qone", return_value=mock_app):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.get_application_by_id(1)
                assert result["token"] == "ABC123"

    def test_get_application_by_id_not_found(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qone", return_value=None):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.get_application_by_id(9999)
                assert result is None

    def test_get_application_by_token(self, app):
        with app.app_context():
            mock_app = {"id": 2, "token": "XYZ789"}
            with patch("repositories.admissions_repository.qone", return_value=mock_app):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.get_application_by_token("XYZ789")
                assert result["id"] == 2

    def test_create_application(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qone", return_value={"id": 10}):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                app_id = repo.create_application({
                    "token": "ABC123", "applicant_name": "Alice", "applicant_email": "a@b.com",
                    "applicant_phone": "9876543210", "date_of_birth": "2005-01-01",
                    "gender": "Female", "category": "Open", "domicile_state": "Maharashtra",
                    "applied_department": "CS", "applied_year": "FE",
                    "status": "PENDING", "merit_score": 85.0
                })
                assert app_id == 10

    def test_create_application_failure(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qone", return_value=None):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.create_application({})
                assert result is None

    def test_update_application_status(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.exe") as mock_exe:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.update_application_status(1, "APPROVED", "Congratulations", "admin")
                mock_exe.assert_called_once()

    def test_update_application_rank_with_status(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.exe") as mock_exe:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.update_application_rank(1, 5, status="SHORTLISTED")
                sql = mock_exe.call_args[0][0]
                assert "status" in sql

    def test_update_application_rank_without_status(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.exe") as mock_exe:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.update_application_rank(1, 3)
                sql = mock_exe.call_args[0][0]
                assert "rank_in_department" in sql

    def test_get_documents_by_application(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qry", return_value=[{"id": 1}]):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                docs = repo.get_documents_by_application(1)
                assert isinstance(docs, list)

    def test_create_document(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qone", return_value={"id": 5}):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                doc_id = repo.create_document({
                    "application_id": 1, "document_type": "SSC",
                    "file_name": "ssc.pdf", "file_path": "/path/ssc.pdf", "file_size": 102400
                })
                assert doc_id == 5

    def test_verify_document(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.exe") as mock_exe:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.verify_document(1, admin_id=42)
                mock_exe.assert_called_once()

    def test_log_timeline(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.exe") as mock_exe:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.log_timeline(1, "APPROVED", "admin", "Application approved")
                mock_exe.assert_called_once()

    def test_get_seat_matrix(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qry", return_value=[]) as mock_qry:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.get_seat_matrix("2024-25")
                assert isinstance(result, list)

    def test_get_merit_list(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.qry", return_value=[{"rank": 1}]):
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                result = repo.get_merit_list("CS", "Open", "2024-25")
                assert isinstance(result, list)

    def test_insert_and_finalize_merit_list(self, app):
        with app.app_context():
            with patch("repositories.admissions_repository.exe") as mock_exe:
                from repositories.admissions_repository import AdmissionsRepository
                repo = AdmissionsRepository()
                repo.insert_merit_list_entry({
                    "department": "CS", "category": "Open", "academic_year": "2024-25",
                    "application_id": 1, "merit_score": 85.0, "rank": 1,
                    "status": "PROVISIONAL", "generated_by": "admin"
                })
                repo.finalize_merit_list_entries("CS", "Open", "2024-25")
                repo.clear_provisional_merit_list("CS", "Open", "2024-25")
                assert mock_exe.call_count == 3
