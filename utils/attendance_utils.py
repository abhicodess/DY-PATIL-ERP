import re
from datetime import date, datetime


VALID_DIVISIONS = ("A", "B", "C", "D")
VALID_STATUSES = {"Present", "Absent", "Late", "Medical", "Leave"}
VALID_METHODS = {"Manual", "Bulk", "QR", "Geo", "Import"}


def clean_text(value):
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def today_str():
    return date.today().strftime("%Y-%m-%d")


def normalize_status(value, default="Present"):
    raw = clean_text(value).lower()
    if raw in ("p", "present", "1", "yes"):
        return "Present"
    if raw in ("a", "absent", "0", "no"):
        return "Absent"
    if raw in ("late", "l"):
        return "Late"
    if raw in ("medical", "m", "ml"):
        return "Medical"
    if raw in ("leave", "lv"):
        return "Leave"
    return default


def normalize_method(value, default="Manual"):
    text = clean_text(value).title()
    return text if text in VALID_METHODS else default


def normalize_division(value):
    text = clean_text(value).upper()
    return text if text in VALID_DIVISIONS else ""


def normalize_date(value, default=None):
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    text = clean_text(value)
    if not text:
        return default
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return default


def normalize_time_slot(value):
    text = clean_text(value)
    text = re.sub(r"\s*-\s*", "-", text)
    return text


def percentage(attended, total):
    return round((attended / total) * 100, 2) if total else 0.0


def low_attendance(attended, total, threshold=75):
    return percentage(attended, total) < threshold

