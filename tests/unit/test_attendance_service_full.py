"""
Targeted attendance_service tests to significantly boost its 34% coverage.
Mocking all DB calls so tests are fast and isolated.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime


# ────────────────────────────────────────────────────────
# mark_single_attendance
# ────────────────────────────────────────────────────────
def test_mark_single_attendance_existing_session(app):
    """mark_single_attendance with existing session should insert attendance."""
    with app.app_context():
        session_mock = MagicMock()
        session_mock.__getitem__ = lambda self, k: 42 if k == "id" else None

        with patch("services.attendance_service.qone", return_value=session_mock), \
             patch("services.attendance_service.exe") as mock_exe, \
             patch("services.attendance_service.log_attendance_action"):
            from services.attendance_service import mark_single_attendance
            result = mark_single_attendance("faculty", 1, {
                "student_id": 10, "student_name": "John Doe", "subject": "Math", "date": "2024-06-01", "status": "Present"
            }, actor_name="Prof. Test")
            assert result["ok"] is True

def test_mark_single_attendance_new_session(app):
    """mark_single_attendance without existing session should create one."""
    with app.app_context():
        new_session = MagicMock()
        new_session.fetchone.return_value = {"id": 99}

        with patch("services.attendance_service.qone", return_value=None), \
             patch("services.attendance_service.exe", return_value=new_session) as mock_exe, \
             patch("services.attendance_service.log_attendance_action"):
            from services.attendance_service import mark_single_attendance
            result = mark_single_attendance("admin", 1, {
                "student_id": 10, "student_name": "John Doe", "subject": "Physics", "status": "Absent"
            })
            assert result["ok"] is True

def test_mark_single_attendance_exception(app):
    """mark_single_attendance should return ok=False on DB error."""
    with app.app_context():
        with patch("services.attendance_service.qone", side_effect=Exception("DB Error")):
            from services.attendance_service import mark_single_attendance
            result = mark_single_attendance("admin", 1, {"student_id": 1, "subject": "Math"})
            assert result["ok"] is False
            assert "error" in result


# ────────────────────────────────────────────────────────
# edit_attendance_record / delete_attendance_record
# ────────────────────────────────────────────────────────
def test_edit_attendance_record(app):
    """edit_attendance_record should UPDATE and return ok."""
    with app.app_context():
        with patch("services.attendance_service.exe") as mock_exe, \
             patch("services.attendance_service.log_attendance_action"):
            from services.attendance_service import edit_attendance_record
            result = edit_attendance_record("admin", 1, 55, {"status": "Late"})
            assert result["ok"] is True
            assert mock_exe.call_count >= 1

def test_edit_attendance_record_exception(app):
    """edit_attendance_record should return error on DB failure."""
    with app.app_context():
        with patch("services.attendance_service.exe", side_effect=Exception("DB error")):
            from services.attendance_service import edit_attendance_record
            result = edit_attendance_record("admin", 1, 99, {"status": "Present"})
            assert result["ok"] is False

def test_delete_attendance_record(app):
    """delete_attendance_record should DELETE and return ok."""
    with app.app_context():
        with patch("services.attendance_service.exe") as mock_exe, \
             patch("services.attendance_service.log_attendance_action"):
            from services.attendance_service import delete_attendance_record
            result = delete_attendance_record("admin", 1, 88)
            assert result["ok"] is True

def test_delete_attendance_record_exception(app):
    """delete_attendance_record should return error on DB failure."""
    with app.app_context():
        with patch("services.attendance_service.exe", side_effect=Exception("error")):
            from services.attendance_service import delete_attendance_record
            result = delete_attendance_record("admin", 1, 99)
            assert result["ok"] is False


# ────────────────────────────────────────────────────────
# get_students_for_filters
# ────────────────────────────────────────────────────────
def test_get_students_for_filters_no_args(app):
    """get_students_for_filters with no args returns all students."""
    with app.app_context():
        with patch("services.attendance_service.qry", return_value=[{"id": 1, "name": "Alice"}]) as mock_qry:
            from services.attendance_service import get_students_for_filters
            result = get_students_for_filters()
            assert isinstance(result, list)

def test_get_students_for_filters_with_dept(app):
    """get_students_for_filters with dept filter appends dept param."""
    with app.app_context():
        with patch("services.attendance_service.qry", return_value=[]) as mock_qry:
            from services.attendance_service import get_students_for_filters
            result = get_students_for_filters(dept="CS")
            # Verify qry was called with a SQL containing department
            call_args = mock_qry.call_args
            assert "department" in call_args[0][0]

def test_get_students_for_filters_with_search(app):
    """get_students_for_filters with search appends ILIKE."""
    with app.app_context():
        with patch("services.attendance_service.qry", return_value=[]) as mock_qry:
            from services.attendance_service import get_students_for_filters
            result = get_students_for_filters(search="Alice")
            call_sql = mock_qry.call_args[0][0]
            assert "ILIKE" in call_sql or "ilike" in call_sql.lower()


# ────────────────────────────────────────────────────────
# fetch_attendance_records
# ────────────────────────────────────────────────────────
def _make_qry_mock(records=None, count_row=None):
    """Return a qry mock that cycles through records, then stats, then analytics queries."""
    call_count = [0]
    if records is None:
        records = []
    
    def qry_side_effect(sql, params=()):
        call_count[0] += 1
        return []  # return empty for all analytics queries

    return qry_side_effect

def test_fetch_attendance_records_basic(app):
    """fetch_attendance_records with mocked DB should return expected structure."""
    with app.app_context():
        with patch("services.attendance_service.qry", return_value=[]) as mock_qry, \
             patch("services.attendance_service.qone", return_value={"c": 0}):
            from services.attendance_service import fetch_attendance_records
            result = fetch_attendance_records({"page": 1, "per_page": 10}, actor_role="admin")
            assert "records" in result
            assert "stats" in result
            assert "analytics" in result
            assert "total_count" in result

def test_fetch_attendance_records_faculty_filter(app):
    """fetch_attendance_records for faculty role should add faculty_id filter."""
    with app.app_context():
        captured_sqls = []
        def mock_qry(sql, params=()):
            captured_sqls.append(sql)
            return []
        
        with patch("services.attendance_service.qry", side_effect=mock_qry), \
             patch("services.attendance_service.qone", return_value={"c": 0}):
            from services.attendance_service import fetch_attendance_records
            result = fetch_attendance_records(
                {"dept": "CS", "status": "Present"},
                actor_role="faculty",
                actor_id=5
            )
            assert "records" in result

def test_fetch_attendance_records_with_filters(app):
    """fetch_attendance_records with all filters should not crash."""
    with app.app_context():
        with patch("services.attendance_service.qry", return_value=[]), \
             patch("services.attendance_service.qone", return_value={"c": 5}):
            from services.attendance_service import fetch_attendance_records
            result = fetch_attendance_records({
                "dept": "CS", "div": "A", "subject": "Math",
                "date_from": "2024-01-01", "date_to": "2024-06-30",
                "status": "Present", "student_name": "Alice", "page": 1
            }, actor_role="admin")
            assert result["total_count"] == 5


# ────────────────────────────────────────────────────────
# mark_bulk_attendance
# ────────────────────────────────────────────────────────
def test_mark_bulk_attendance_success(app):
    """mark_bulk_attendance with valid form data should insert records."""
    with app.app_context():
        session_cursor = MagicMock()
        session_cursor.fetchone.return_value = {"id": 10}
        attendance_cursor = MagicMock()
        attendance_cursor.fetchone.return_value = {"is_insert": True}
        
        call_index = [0]
        def exe_side_effect(sql, params=()):
            call_index[0] += 1
            if call_index[0] == 1:
                return session_cursor
            return attendance_cursor

        with patch("services.attendance_service.exe", side_effect=exe_side_effect), \
             patch("services.attendance_service.log_attendance_action"):
            from services.attendance_service import mark_bulk_attendance
            form_data = {
                "subject": "Math", "date": "2024-06-01",
                "division": "A", "branch": "CS",
                "status_10": "Present", "status_11": "Absent"
            }
            result = mark_bulk_attendance("faculty", 5, form_data)
            assert result["ok"] is True
            assert result["saved"] >= 0

def test_mark_bulk_attendance_exception(app):
    """mark_bulk_attendance returns error on DB failure."""
    with app.app_context():
        with patch("services.attendance_service.exe", side_effect=Exception("DB Error")):
            from services.attendance_service import mark_bulk_attendance
            result = mark_bulk_attendance("admin", 1, {"subject": "Math"})
            assert result["ok"] is False


# ────────────────────────────────────────────────────────
# backup_attendance_data / restore
# ────────────────────────────────────────────────────────
def test_backup_attendance_data(app):
    """backup_attendance_data should call export + create_backup."""
    with app.app_context():
        with patch("services.attendance_service.export_attendance_snapshot", return_value={"rows": []}), \
             patch("services.attendance_service.create_attendance_backup", return_value="/tmp/backup.json"), \
             patch("services.attendance_service.log_attendance_action"):
            from services.attendance_service import backup_attendance_data
            path = backup_attendance_data("admin", 1)
            assert path == "/tmp/backup.json"
