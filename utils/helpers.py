import re
import hmac
from functools import wraps
from datetime import datetime, date
from flask import session, redirect

def safe_int(v, default=0):
    try:
        if v is None: return default
        s = str(v).strip()
        if not s: return default
        return int(float(s))
    except (ValueError, TypeError):
        return default

def safe_str(v, default=""):
    return str(v).strip() if v is not None else default

def safe_float(v, default=0.0):
    try:
        if v is None: return default
        s = str(v).strip()
        if not s: return default
        return float(s)
    except (ValueError, TypeError):
        return default

def safe_date(v, default=None):
    if not v: return default
    if isinstance(v, (date, datetime)): return v
    try:
        return datetime.strptime(str(v).split(' ')[0], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default

def pct(a, b):
    try:
        a, b = float(a), float(b)
        return round((a / b) * 100, 2) if b > 0 else 0.0
    except:
        return 0.0

def normalize_date(raw):
    if isinstance(raw, (datetime, date)):
        return raw.strftime("%Y-%m-%d")
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try: return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError: pass
    return None

def get_today_str():
    return date.today().strftime("%Y-%m-%d")

def login_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            session_role = session.get("role")
            if isinstance(role, (list, tuple, set)):
                if session_role not in role:
                    return redirect("/")
            elif session_role != role:
                return redirect("/")
            return f(*args, **kwargs)
        return wrapper
    return decorator

def safe_redirect_target(raw, default="/view_attendance"):
    """Allow only same-site relative paths; blocks open redirects (//evil.com, https://…)."""
    if not raw or not isinstance(raw, str):
        return default
    s = raw.strip()
    if not s.startswith("/") or s.startswith("//"):
        return default
    if "\n" in s or "\r" in s or "\t" in s:
        return default
    if "://" in s or s.lower().startswith("/\\"):
        return default
    return s

def sort_key_time(ts):
    import re
    m = re.match(r"(\d+):(\d+)", str(ts or ""))
    if not m:
        return 999
    h, mn = int(m.group(1)), int(m.group(2))
    if h < 7:
        h += 12  # handle 1:xx → 13:xx style
    return h * 60 + mn

def _password_is_hashed(value):
    if not value or not isinstance(value, str):
        return False
    return (
        value.startswith("pbkdf2:")
        or value.startswith("scrypt:")
        or value.startswith("argon2")
    )

def hash_password(plain):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(plain or "")

def verify_password(stored, plain):
    if not plain or not stored:
        return False
    if _password_is_hashed(stored):
        from werkzeug.security import check_password_hash
        return check_password_hash(stored, plain)
    return hmac.compare_digest(stored, plain)

def validate_password_change(current_stored, current_input, new_password, confirm_password):
    """Return error code string if invalid, else None."""
    new_password = (new_password or "").strip()
    confirm_password = (confirm_password or "").strip()
    if not new_password:
        return "empty"
    if len(new_password) < 6:
        return "short"
    if new_password != confirm_password:
        return "mismatch"
    if not verify_password(current_stored, (current_input or "").strip()):
        return "current_invalid"
    return None

def normalize_branch(branch_str):
    """Normalize branch names (e.g. 'Artificial Intelligence & Data Science' -> 'AIDS')."""
    if not branch_str: return ""
    branch_lower = str(branch_str).lower().strip()
    branch_map = {
        "artificial intelligence & data science": "AIDS",
        "artificial intelligence and data science": "AIDS",
        "computer engineering": "CS",
        "computer mapping": "CS",
        "computer science": "CS",
        "information technology": "IT",
        "artificial intelligence & machine learning": "AIML",
        "civil engineering": "CIVIL",
        "mechanical engineering": "MECH"
    }
    return branch_map.get(branch_lower, branch_str)

def normalize_division(div_str):
    """Normalize division strings (e.g., 'TE CSE-A' -> 'A')."""
    if not div_str: return ""
    norm = str(div_str).strip()
    if '-' in norm:
        return norm.split('-')[-1].strip()
    if len(norm) > 1:
        # Check if the last word is exactly one letter e.g., "TE CSE A"
        parts = norm.split()
        if parts:
            last_word = parts[-1]
            if len(last_word) == 1 and last_word.isalpha():
                return last_word.upper()
    return norm


def grade(marks, total):
    p = pct(marks, total)
    if p >= 75: return "O"
    if p >= 65: return "A"
    if p >= 55: return "B"
    if p >= 45: return "C"
    if p >= 35: return "D"
    return "F"
