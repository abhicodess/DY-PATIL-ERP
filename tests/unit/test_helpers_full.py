"""
Comprehensive tests for utils/helpers.py — targeting uncovered paths for max coverage.
"""
import pytest
from datetime import date, datetime


# ────────────────────────────────────────────────────────
# safe_int / safe_str / safe_float / safe_date
# ────────────────────────────────────────────────────────
def test_safe_int_normal():
    from utils.helpers import safe_int
    assert safe_int("42") == 42
    assert safe_int(3.7) == 3
    assert safe_int("3.14") == 3

def test_safe_int_edge_cases():
    from utils.helpers import safe_int
    assert safe_int(None) == 0
    assert safe_int("") == 0
    assert safe_int("abc") == 0
    assert safe_int(None, default=99) == 99

def test_safe_str():
    from utils.helpers import safe_str
    assert safe_str("  hello  ") == "hello"
    assert safe_str(None) == ""
    assert safe_str(42) == "42"

def test_safe_float_normal():
    from utils.helpers import safe_float
    assert safe_float("3.14") == 3.14
    assert safe_float(10) == 10.0

def test_safe_float_edge_cases():
    from utils.helpers import safe_float
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("nan_value") == 0.0

def test_safe_date_from_string():
    from utils.helpers import safe_date
    d = safe_date("2024-06-01")
    assert d == date(2024, 6, 1)

def test_safe_date_from_datetime():
    from utils.helpers import safe_date
    dt = datetime(2024, 6, 1, 12, 0, 0)
    assert safe_date(dt) == dt  # returns the datetime itself

def test_safe_date_with_time():
    from utils.helpers import safe_date
    d = safe_date("2024-06-01 12:00:00")
    assert d == date(2024, 6, 1)

def test_safe_date_none():
    from utils.helpers import safe_date
    assert safe_date(None) is None
    assert safe_date("") is None
    assert safe_date("invalid") is None


# ────────────────────────────────────────────────────────
# pct
# ────────────────────────────────────────────────────────
def test_pct_normal():
    from utils.helpers import pct
    assert pct(75, 100) == 75.0
    assert pct(1, 3) == pytest.approx(33.33, rel=1e-2)

def test_pct_zero_denominator():
    from utils.helpers import pct
    assert pct(10, 0) == 0.0

def test_pct_invalid():
    from utils.helpers import pct
    assert pct("abc", "def") == 0.0


# ────────────────────────────────────────────────────────
# normalize_date
# ────────────────────────────────────────────────────────
def test_normalize_date_iso():
    from utils.helpers import normalize_date
    assert normalize_date("2024-06-15") == "2024-06-15"

def test_normalize_date_slash():
    from utils.helpers import normalize_date
    assert normalize_date("15/06/2024") == "2024-06-15"

def test_normalize_date_dash():
    from utils.helpers import normalize_date
    assert normalize_date("15-06-2024") == "2024-06-15"

def test_normalize_date_from_date_object():
    from utils.helpers import normalize_date
    assert normalize_date(date(2024, 6, 15)) == "2024-06-15"

def test_normalize_date_invalid():
    from utils.helpers import normalize_date
    assert normalize_date("not_a_date") is None

def test_get_today_str():
    from utils.helpers import get_today_str
    today = get_today_str()
    assert len(today) == 10
    assert today[4] == "-"
    assert today[7] == "-"


# ────────────────────────────────────────────────────────
# safe_redirect_target
# ────────────────────────────────────────────────────────
def test_safe_redirect_valid():
    from utils.helpers import safe_redirect_target
    assert safe_redirect_target("/view_attendance") == "/view_attendance"
    assert safe_redirect_target("/admin/dashboard") == "/admin/dashboard"

def test_safe_redirect_open_redirect_blocked():
    from utils.helpers import safe_redirect_target
    assert safe_redirect_target("//evil.com") == "/view_attendance"
    assert safe_redirect_target("https://evil.com") == "/view_attendance"
    assert safe_redirect_target("http://evil.com") == "/view_attendance"

def test_safe_redirect_newlines_blocked():
    from utils.helpers import safe_redirect_target
    assert safe_redirect_target("/path\nwith\nnewlines") == "/view_attendance"

def test_safe_redirect_none():
    from utils.helpers import safe_redirect_target
    assert safe_redirect_target(None) == "/view_attendance"
    assert safe_redirect_target("") == "/view_attendance"

def test_safe_redirect_custom_default():
    from utils.helpers import safe_redirect_target
    assert safe_redirect_target("https://evil.com", default="/home") == "/home"


# ────────────────────────────────────────────────────────
# sort_key_time
# ────────────────────────────────────────────────────────
def test_sort_key_time_normal():
    from utils.helpers import sort_key_time
    assert sort_key_time("10:30") == 10 * 60 + 30
    assert sort_key_time("14:00") == 14 * 60

def test_sort_key_time_am_adjustment():
    from utils.helpers import sort_key_time
    # Hours < 7 get 12 added to sort correctly (e.g., 1:00 PM)
    key_1am = sort_key_time("1:00")
    key_13 = sort_key_time("13:00")
    assert key_1am == key_13

def test_sort_key_time_invalid():
    from utils.helpers import sort_key_time
    assert sort_key_time(None) == 999
    assert sort_key_time("invalid") == 999


# ────────────────────────────────────────────────────────
# password utilities
# ────────────────────────────────────────────────────────
def test_password_is_hashed():
    from utils.helpers import _password_is_hashed
    assert _password_is_hashed("pbkdf2:sha256:abc123") is True
    assert _password_is_hashed("scrypt:hash") is True
    assert _password_is_hashed("plain_text") is False
    assert _password_is_hashed(None) is False
    assert _password_is_hashed("") is False

def test_hash_and_verify_password():
    from utils.helpers import hash_password, verify_password
    plain = "MySecurePass1!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(hashed, plain) is True
    assert verify_password(hashed, "wrong_password") is False

def test_verify_password_plain():
    """Unhashed passwords compared directly via hmac."""
    from utils.helpers import verify_password
    assert verify_password("same_plain", "same_plain") is True
    assert verify_password("plain1", "plain2") is False

def test_verify_password_empty():
    from utils.helpers import verify_password
    assert verify_password("", "password") is False
    assert verify_password("password", "") is False


# ────────────────────────────────────────────────────────
# validate_password_change
# ────────────────────────────────────────────────────────
def test_validate_password_change_success():
    from utils.helpers import validate_password_change, hash_password
    stored = hash_password("CurrentPass1!")
    result = validate_password_change(stored, "CurrentPass1!", "NewPass1234!", "NewPass1234!")
    assert result is None  # no error

def test_validate_password_change_empty_new():
    from utils.helpers import validate_password_change
    result = validate_password_change("stored", "current", "", "")
    assert result == "empty"

def test_validate_password_change_too_short():
    from utils.helpers import validate_password_change
    result = validate_password_change("stored", "current", "abc", "abc")
    assert result == "short"

def test_validate_password_change_mismatch():
    from utils.helpers import validate_password_change
    result = validate_password_change("stored", "current", "NewPass1!", "Different1!")
    assert result == "mismatch"

def test_validate_password_change_wrong_current():
    from utils.helpers import validate_password_change, hash_password
    stored = hash_password("RealCurrent1!")
    result = validate_password_change(stored, "WrongCurrent!", "NewPass1234!", "NewPass1234!")
    assert result == "current_invalid"


# ────────────────────────────────────────────────────────
# normalize_branch / normalize_division
# ────────────────────────────────────────────────────────
def test_normalize_branch():
    from utils.helpers import normalize_branch
    assert normalize_branch("Computer Engineering") == "CS"
    assert normalize_branch("Information Technology") == "IT"
    assert normalize_branch("Artificial Intelligence & Data Science") == "AIDS"
    assert normalize_branch("Artificial Intelligence & Machine Learning") == "AIML"
    assert normalize_branch("Civil Engineering") == "CIVIL"
    assert normalize_branch("") == ""
    assert normalize_branch(None) == ""
    assert normalize_branch("Unknown Branch") == "Unknown Branch"  # passthrough

def test_normalize_division():
    from utils.helpers import normalize_division
    assert normalize_division("TE CSE-A") == "A"
    assert normalize_division("TE CSE A") == "A"
    assert normalize_division("B") == "B"
    assert normalize_division("") == ""
    assert normalize_division(None) == ""


# ────────────────────────────────────────────────────────
# grade
# ────────────────────────────────────────────────────────
def test_grade_outstanding():
    from utils.helpers import grade
    assert grade(75, 100) == "O"
    assert grade(80, 100) == "O"

def test_grade_a():
    from utils.helpers import grade
    assert grade(65, 100) == "A"
    assert grade(74, 100) == "A"

def test_grade_b():
    from utils.helpers import grade
    assert grade(55, 100) == "B"
    assert grade(64, 100) == "B"

def test_grade_c():
    from utils.helpers import grade
    assert grade(45, 100) == "C"
    assert grade(54, 100) == "C"

def test_grade_d():
    from utils.helpers import grade
    assert grade(35, 100) == "D"
    assert grade(44, 100) == "D"

def test_grade_fail():
    from utils.helpers import grade
    assert grade(0, 100) == "F"
    assert grade(34, 100) == "F"
    assert grade(0, 0) == "F"  # 0/0 → 0%
