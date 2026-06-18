import re
from datetime import datetime

import pandas as pd


DIVISION_VALUES = {"A", "B", "C", "D"}


def clean_text(value):
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def normalize_header(value):
    text = clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def detect_header_row(raw_df, scan_rows=30):
    max_rows = min(len(raw_df.index), scan_rows)
    for idx in range(max_rows):
        row = [clean_text(v).upper() for v in raw_df.iloc[idx].tolist()]
        joined = " ".join(row)
        if ("ROLL" in joined or "ROLL NO" in joined) and "NAME" in joined:
            return idx
    return None


def drop_empty_and_unnamed_columns(df):
    keep_cols = []
    for col in df.columns:
        label = clean_text(col)
        series = df[col]
        has_values = series.notna().any() and any(clean_text(v) for v in series.tolist())
        if not has_values:
            continue
        if label.lower().startswith("unnamed") and not has_values:
            continue
        keep_cols.append(col)
    return df.loc[:, keep_cols]


def extract_metadata(meta_rows):
    text_lines = []
    for row in meta_rows:
        for value in row:
            cleaned = clean_text(value)
            if cleaned:
                text_lines.append(cleaned)
    meta_text = "\n".join(text_lines)
    upper = meta_text.upper()

    department = ""
    if "AIML" in upper:
        department = "AIML"
    elif re.search(r"AI\s*&?\s*DS|AIDS", upper):
        department = "AIDS"
    elif re.search(r"INFORMATION\s+TECHNOLOGY|\bIT\b", upper):
        department = "IT"
    elif re.search(r"COMP|COMPUTER|CE", upper):
        department = "CS"

    semester = ""
    semester_match = re.search(r"SEM(?:ESTER)?\s*[-: ]\s*(I{1,3}|IV|V|VI{0,3}|[1-8])", upper)
    if semester_match:
        semester = semester_match.group(1)
        semester = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI", "7": "VII", "8": "VIII"}.get(semester, semester)
    elif re.search(r"\bS\.?\s*Y\b|\bSY\b", upper):
        semester = "II"

    division = ""
    division_match = re.search(r"DIV[.\s:-]*([A-D])", upper)
    if division_match:
        division = division_match.group(1).upper()
    if division not in DIVISION_VALUES:
        division = ""

    date_range = {"start": None, "end": None, "raw": ""}
    range_match = re.search(r"FROM\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+TO\s+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", upper)
    if range_match:
        date_range["raw"] = f"{range_match.group(1)} to {range_match.group(2)}"
        date_range["start"] = parse_date_token(range_match.group(1))
        date_range["end"] = parse_date_token(range_match.group(2))

    return {
        "department": department,
        "semester": semester,
        "division": division,
        "date_range": date_range,
        "raw_text": meta_text,
    }


def parse_date_token(token):
    token = clean_text(token)
    for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%y", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def build_subject_columns(header_values, code_values, type_values, total_values, start_idx):
    columns = []
    for pos in range(start_idx, len(header_values)):
        header_text = clean_text(header_values[pos])
        upper = header_text.upper()
        if not header_text:
            continue
        if upper == "TOTAL" or "ATTEND" in upper or upper == "%":
            break
        total = safe_int(total_values[pos] if pos < len(total_values) else 0)
        if total <= 0:
            continue
        columns.append(
            {
                "index": pos,
                "name": normalize_subject_name(header_text),
                "code": clean_subject_code(code_values[pos] if pos < len(code_values) else ""),
                "lecture_type": clean_text(type_values[pos] if pos < len(type_values) else ""),
                "total_classes": total,
            }
        )
    return columns


def normalize_subject_name(name):
    text = clean_text(name)
    text = re.sub(r"\s*-\s*", " - ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def clean_subject_code(value):
    return re.sub(r"\s+", "", clean_text(value)).upper()


def safe_int(value):
    try:
        if value is None or clean_text(value) == "":
            return 0
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def is_valid_roll(roll):
    return re.match(r"^[A-Z]?\d{1,3}[A-Z]?$", clean_text(roll).upper(), re.I) is not None
