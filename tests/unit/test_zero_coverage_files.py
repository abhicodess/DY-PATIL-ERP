"""
Tests for 0%-coverage utility files:
  - api/utils.py (ApiResponse)
  - api/errors.py (blueprint error handlers)
  - utils/api_logger.py (init_api_logger)
  - utils/report_cleanup.py (delete_expired_reports)
  - services/attendance_ai.py (AttendanceAI)
"""
import pytest
from unittest.mock import MagicMock, patch


# ────────────────────────────────────────────────────────
# api/utils.py — ApiResponse
# ────────────────────────────────────────────────────────
def test_api_response_success(app):
    """ApiResponse.success should return 200 with status=success."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.success({"id": 1}, "Created", 201)
        data = resp.get_json()
        assert code == 201
        assert data["status"] == "success"
        assert data["data"] == {"id": 1}

def test_api_response_success_with_meta(app):
    """ApiResponse.success with meta should include meta key."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.success([1, 2], meta={"total": 2})
        data = resp.get_json()
        assert "meta" in data
        assert data["meta"]["total"] == 2

def test_api_response_error(app):
    """ApiResponse.error should return error status."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.error("Not found", 404)
        data = resp.get_json()
        assert code == 404
        assert data["status"] == "error"

def test_api_response_error_with_details(app):
    """ApiResponse.error with details should include them."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.error("Bad request", 400, details={"field": "name"})
        data = resp.get_json()
        assert "details" in data
        assert data["details"]["field"] == "name"

def test_api_response_unauthorized(app):
    """ApiResponse.unauthorized returns 401."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.unauthorized()
        assert code == 401

def test_api_response_forbidden(app):
    """ApiResponse.forbidden returns 403."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.forbidden()
        assert code == 403

def test_api_response_not_found(app):
    """ApiResponse.not_found returns 404."""
    with app.app_context():
        from api.utils import ApiResponse
        resp, code = ApiResponse.not_found()
        assert code == 404


# ────────────────────────────────────────────────────────
# api/errors.py — blueprint importable
# ────────────────────────────────────────────────────────
def test_api_errors_blueprint_importable():
    """api_errors blueprint should be importable."""
    from api.errors import api_errors_bp
    assert api_errors_bp is not None
    assert api_errors_bp.name == "api_errors"


# ────────────────────────────────────────────────────────
# utils/api_logger.py — init_api_logger
# ────────────────────────────────────────────────────────
def test_api_logger_callable():
    """init_api_logger should be importable."""
    from utils.api_logger import init_api_logger
    assert callable(init_api_logger)

def test_api_logger_registers_hooks():
    """init_api_logger should register before/after request handlers."""
    from flask import Flask
    from utils.api_logger import init_api_logger
    fresh_app = Flask(__name__)
    init_api_logger(fresh_app)
    # Verify before_request and after_request were registered (Flask stores them)
    assert len(fresh_app.before_request_funcs.get(None, [])) > 0
    assert len(fresh_app.after_request_funcs.get(None, [])) > 0

def test_api_logger_non_api_route_skipped(app):
    """Requests to non-/api/ routes should be skipped by logger."""
    with patch("utils.api_logger.exe") as mock_exe:
        with app.test_client() as c:
            c.get("/")  # Non-API route
            # exe should NOT be called (route not /api/)
            mock_exe.assert_not_called()


# ────────────────────────────────────────────────────────
# utils/report_cleanup.py — delete_expired_reports
# ────────────────────────────────────────────────────────
def test_delete_expired_reports_no_rows(app):
    """delete_expired_reports with no expired rows should return 0 deleted."""
    with app.app_context():
        with patch("utils.report_cleanup.qry", return_value=[]), \
             patch("utils.report_cleanup.exe"):
            from utils.report_cleanup import delete_expired_reports
            result = delete_expired_reports()
            assert result["deleted_count"] == 0
            assert result["mb_freed"] == 0.0

def test_delete_expired_reports_with_missing_file(app):
    """delete_expired_reports with a non-existent file should still update DB."""
    with app.app_context():
        fake_rows = [{"id": 1, "job_id": "abc", "file_path": "/nonexistent/path.pdf", "file_size": 1024}]
        with patch("utils.report_cleanup.qry", return_value=fake_rows), \
             patch("utils.report_cleanup.exe") as mock_exe:
            from utils.report_cleanup import delete_expired_reports
            result = delete_expired_reports()
            # File doesn't exist, so deleted_count stays 0 but DB updated
            assert result["deleted_count"] == 0
            mock_exe.assert_called()  # Status updated to expired

def test_delete_expired_reports_with_real_file(app, tmp_path):
    """delete_expired_reports should delete existing files."""
    with app.app_context():
        # Create a temporary file to "expire"
        report_file = tmp_path / "report_abc.pdf"
        report_file.write_bytes(b"%PDF-1.4 content here")
        
        fake_rows = [{"id": 1, "job_id": "abc", "file_path": str(report_file), "file_size": 21}]
        with patch("utils.report_cleanup.qry", return_value=fake_rows), \
             patch("utils.report_cleanup.exe") as mock_exe:
            from utils.report_cleanup import delete_expired_reports
            result = delete_expired_reports()
            assert result["deleted_count"] == 1
            assert result["mb_freed"] > 0
            assert not report_file.exists()  # File was deleted


# ────────────────────────────────────────────────────────
# services/attendance_ai.py — AttendanceAI
# ────────────────────────────────────────────────────────
def test_attendance_ai_get_risk_profiles_no_filter(app):
    """get_risk_profiles with no filters should run query and return list."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[]) as mock_qry:
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_risk_profiles()
            assert isinstance(result, list)
            mock_qry.assert_called_once()

def test_attendance_ai_get_risk_profiles_with_filters(app):
    """get_risk_profiles with dept/year/division should add WHERE clauses."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[{"name": "Alice"}]) as mock_qry:
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_risk_profiles(dept="CS", year="II", division="A")
            call_sql = mock_qry.call_args[0][0]
            assert "department" in call_sql
            assert "year" in call_sql
            assert "division" in call_sql

def test_attendance_ai_get_heatmap_no_dept(app):
    """get_attendance_heatmap with no dept should return full heatmap."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[]) as mock_qry:
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_attendance_heatmap()
            assert isinstance(result, list)

def test_attendance_ai_get_heatmap_with_dept(app):
    """get_attendance_heatmap with dept filter should add filter."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[]) as mock_qry:
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_attendance_heatmap(dept="CS")
            call_sql = mock_qry.call_args[0][0]
            assert "department" in call_sql

def test_attendance_ai_predict_future_defaulters(app):
    """predict_future_defaulters should run query with threshold."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[{"name": "Bob"}]) as mock_qry:
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.predict_future_defaulters(threshold=75)
            assert isinstance(result, list)

def test_attendance_ai_get_department_comparison(app):
    """get_department_comparison should return per-dept data."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[{"department": "CS", "avg_pct": 85}]):
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_department_comparison()
            assert isinstance(result, list)

def test_attendance_ai_get_insights_summary(app):
    """get_insights_summary should return dict with expected keys."""
    with app.app_context():
        mock_critical = {"c": 5}
        mock_top_dept = {"department": "CS"}
        mock_declining = {"c": 3}
        with patch("services.attendance_ai.qone", side_effect=[mock_critical, mock_top_dept, mock_declining]):
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_insights_summary()
            assert "critical_risk_count" in result
            assert "declining_trend_count" in result
            assert "top_performing_dept" in result

def test_attendance_ai_get_insights_summary_exception(app):
    """get_insights_summary should return defaults on DB error."""
    with app.app_context():
        with patch("services.attendance_ai.qone", side_effect=Exception("DB error")):
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_insights_summary()
            assert result["critical_risk_count"] == 0
            assert result["top_performing_dept"] == "N/A"

def test_attendance_ai_get_weekly_trend(app):
    """get_weekly_trend should return list of week labels."""
    with app.app_context():
        with patch("services.attendance_ai.qry", return_value=[{"week_label": "Jun 01", "avg_pct": 80}]):
            from services.attendance_ai import AttendanceAI
            result = AttendanceAI.get_weekly_trend(dept="CS", division="A")
            assert isinstance(result, list)
