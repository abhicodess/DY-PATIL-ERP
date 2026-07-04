"""
Unit tests for:
  - utils/cumulative_parser.py (private helper functions + parse_attendance_file routing)
  - utils/security_headers.py
  - utils/db_helpers.py
"""
import pytest
from unittest.mock import MagicMock, patch


# ────────────────────────────────────────────────────────
# utils/cumulative_parser.py — private helpers
# ────────────────────────────────────────────────────────
def test_cumulative_safe_int():
    from utils.cumulative_parser import _safe_int
    assert _safe_int("42") == 42
    assert _safe_int("3.7") == 3
    assert _safe_int("") == 0
    assert _safe_int(None) == 0
    assert _safe_int("abc") == 0

def test_cumulative_safe_float():
    from utils.cumulative_parser import _safe_float
    assert _safe_float("3.14") == 3.14
    assert _safe_float("0") == 0.0
    assert _safe_float("abc") == 0.0
    assert _safe_float(None) == 0.0
    assert _safe_float("2.5") == 2.5

def test_detect_meta_with_academic_year():
    from utils.cumulative_parser import _detect_meta
    text = "Academic Year 2024-25, Semester - VI. Program: TE COMP Div. A"
    meta = _detect_meta(text)
    assert meta["year"] == "2024-25"
    assert meta["semester"] == "VI"

def test_detect_meta_aiml_department():
    from utils.cumulative_parser import _detect_meta
    text = "Program: TE AIML Div. B"
    meta = _detect_meta(text)
    assert meta["department"] == "AIML"

def test_detect_meta_aids_department():
    from utils.cumulative_parser import _detect_meta
    text = "Program: TE AIDS Div. A"
    meta = _detect_meta(text)
    assert meta["department"] == "AIDS"

def test_detect_meta_it_department():
    from utils.cumulative_parser import _detect_meta
    text = "Program: TE IT Div. C"
    meta = _detect_meta(text)
    assert meta["department"] == "IT"

def test_detect_meta_cs_fallback():
    from utils.cumulative_parser import _detect_meta
    text = "Program: TE COMP Div. A"
    meta = _detect_meta(text)
    assert meta["department"] == "CS"
    assert meta["division"] == "A"

def test_detect_meta_empty():
    from utils.cumulative_parser import _detect_meta
    meta = _detect_meta("")
    assert meta == {"year": "", "semester": "", "program": "", "department": "", "division": ""}

def test_parse_attendance_file_unsupported():
    from utils.cumulative_parser import parse_attendance_file
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_attendance_file(b"data", "report.txt")

def test_parse_attendance_file_xlsx():
    """parse_attendance_file for xlsx should call parse_excel."""
    import io
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Academic Year 2024-25"])
    ws.append([])
    ws.append([])
    ws.append(["SR NO.", "ROLL NO.", "NAME", "Subject1", "TOTAL", "%"])
    ws.append([1, "CS001", "Alice", 10, 10, 100.0])
    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    from utils.cumulative_parser import parse_attendance_file
    result = parse_attendance_file(xlsx_bytes, "attendance.xlsx")
    if isinstance(result, list):
        result = result[0]
    assert "meta" in result
    assert "students" in result
    assert "subjects" in result


# ────────────────────────────────────────────────────────
# utils/security_headers.py
# ────────────────────────────────────────────────────────
def test_security_headers_added():
    """Security headers module can be imported and register_security_headers is callable."""
    from utils.security_headers import register_security_headers
    # Verify it is a callable function
    assert callable(register_security_headers)
    # We cannot safely re-register on the shared test app after first request;
    # instead, verify the function with a fresh isolated app
    from flask import Flask
    fresh_app = Flask(__name__)
    register_security_headers(fresh_app)  # Should not raise
    # Verify the after_request handler is registered
    assert len(fresh_app.after_request_funcs.get(None, [])) >= 1





# ────────────────────────────────────────────────────────
# utils/db_helpers.py
# ────────────────────────────────────────────────────────
def test_safe_query_returns_results(app):
    with app.app_context():
        with patch("utils.db_helpers.qry", return_value=[{"id": 1}]) as mock_qry:
            from utils.db_helpers import safe_query
            rows = safe_query("SELECT 1")
            assert len(rows) == 1

def test_safe_query_handles_exception(app):
    with app.app_context():
        with patch("utils.db_helpers.qry", side_effect=Exception("DB error")):
            from utils.db_helpers import safe_query
            rows = safe_query("SELECT 1")
            assert rows == []

def test_safe_fetch_one_returns_row(app):
    with app.app_context():
        mock_row = {"id": 1, "name": "Test"}
        with patch("utils.db_helpers.qone", return_value=mock_row):
            from utils.db_helpers import safe_fetch_one
            row = safe_fetch_one("SELECT 1")
            assert row["name"] == "Test"

def test_safe_fetch_one_handles_exception(app):
    with app.app_context():
        with patch("utils.db_helpers.qone", side_effect=Exception("error")):
            from utils.db_helpers import safe_fetch_one
            result = safe_fetch_one("SELECT 1")
            assert result is None

def test_safe_execute_returns_cursor(app):
    with app.app_context():
        mock_cursor = MagicMock()
        with patch("utils.db_helpers.exe", return_value=mock_cursor):
            from utils.db_helpers import safe_execute
            result = safe_execute("UPDATE t SET x=1")
            assert result == mock_cursor

def test_safe_execute_handles_exception(app):
    with app.app_context():
        with patch("utils.db_helpers.exe", side_effect=Exception("error")):
            from utils.db_helpers import safe_execute
            result = safe_execute("DELETE FROM t")
            assert result is None

def test_safe_fetch_scalar_returns_value(app):
    with app.app_context():
        mock_row = MagicMock()
        mock_row.values.return_value = [42]
        with patch("utils.db_helpers.qone", return_value=mock_row):
            from utils.db_helpers import safe_fetch_scalar
            val = safe_fetch_scalar("SELECT COUNT(*) as c FROM t")
            assert val == 42

def test_safe_fetch_scalar_none_row(app):
    with app.app_context():
        with patch("utils.db_helpers.qone", return_value=None):
            from utils.db_helpers import safe_fetch_scalar
            val = safe_fetch_scalar("SELECT COUNT(*) as c FROM t", default=0)
            assert val == 0


# ────────────────────────────────────────────────────────
# utils/cache.py
# ────────────────────────────────────────────────────────
def test_cache_get_hit():
    """Cache.get should deserialize JSON from Redis."""
    import json
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        mock_redis.get.return_value = json.dumps({"key": "val"}).encode()
        result = Cache.get("mykey")
        assert result == {"key": "val"}

def test_cache_get_miss():
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        mock_redis.get.return_value = None
        result = Cache.get("missingkey")
        assert result is None

def test_cache_set():
    import json
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        Cache.set("k", {"a": 1}, ttl=60)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 60

def test_cache_delete():
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        Cache.delete("k")
        mock_redis.delete.assert_called()

def test_cache_invalidate_pattern():
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        mock_redis.keys.return_value = ["key1", "key2"]
        Cache.invalidate_pattern("prefix:*")
        mock_redis.delete.assert_called()

def test_cache_get_redis_unavailable():
    """Cache.get should return None when Redis is down."""
    import redis
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        mock_redis.get.side_effect = redis.exceptions.ConnectionError("down")
        result = Cache.get("k")
        assert result is None

def test_cache_set_redis_unavailable():
    """Cache.set should silently fail when Redis is down."""
    import redis
    from utils.cache import Cache
    with patch("utils.cache.tenant_redis") as mock_redis:
        mock_redis.setex.side_effect = redis.exceptions.ConnectionError("down")
        # Should not raise
        Cache.set("k", {"v": 1})

def test_cache_cached_decorator(app):
    """Cache.cached decorator should call function and cache result."""
    from utils.cache import Cache
    with app.app_context():
        with patch("utils.cache.tenant_redis") as mock_redis:
            mock_redis.get.return_value = None  # Cache miss initially

            call_count = [0]

            @Cache.cached(ttl=60, key_prefix="test_fn")
            def my_func(x):
                call_count[0] += 1
                return x * 2

            result = my_func(5)
            assert result == 10
            assert call_count[0] == 1
