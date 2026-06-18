import io
from dataclasses import dataclass

try:
    import pandas as pd
except ImportError:
    pd = None
from openpyxl import load_workbook

from utils.data_cleaner import (
    build_subject_columns,
    clean_text,
    detect_header_row,
    drop_empty_and_unnamed_columns,
    extract_metadata,
    is_valid_roll,
    normalize_header,
    safe_int,
)


class AttendanceParseError(Exception):
    pass


@dataclass
class AttendanceParseResult:
    metadata: dict
    students: list
    normalized_rows: list
    analytics: dict


def validate_excel_upload(file_storage):
    if not file_storage:
        raise AttendanceParseError("No file uploaded.")
    filename = (getattr(file_storage, "filename", "") or "").strip()
    if not filename.lower().endswith(".xlsx"):
        raise AttendanceParseError("Only .xlsx files are supported.")
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size <= 0:
        raise AttendanceParseError("Uploaded file is empty.")
    return filename


def parse_attendance_excel(file_storage):
    if pd is None:
        raise AttendanceParseError("pandas is not installed. Please contact the system administrator.")
    filename = validate_excel_upload(file_storage)
    try:
        binary = file_storage.read()
        file_storage.seek(0)
        raw_df = pd.read_excel(io.BytesIO(binary), header=None, dtype=object, engine="openpyxl")
        if raw_df.empty:
            raise AttendanceParseError("Excel file is empty.")
        header_idx = detect_header_row(raw_df)
        if header_idx is None:
            raise AttendanceParseError("Could not detect attendance table header. Expected a row with Roll No and Name.")

        meta_rows = raw_df.iloc[:header_idx].fillna("").values.tolist()
        metadata = extract_metadata(meta_rows)

        header_values = [clean_text(v) for v in raw_df.iloc[header_idx].tolist()]
        code_values = raw_df.iloc[header_idx + 1].tolist() if header_idx + 1 < len(raw_df.index) else []
        type_values = raw_df.iloc[header_idx + 2].tolist() if header_idx + 2 < len(raw_df.index) else []

        total_row_idx = None
        for idx in range(header_idx + 1, min(header_idx + 8, len(raw_df.index))):
            row_text = " ".join(clean_text(v).upper() for v in raw_df.iloc[idx].tolist())
            if "LECTURES" in row_text and ("TOTAL" in row_text or "CONDUCTED" in row_text):
                total_row_idx = idx
                break
        if total_row_idx is None:
            raise AttendanceParseError("Could not detect the total lectures row in this report.")
        total_values = raw_df.iloc[total_row_idx].tolist()

        normalized_headers = [normalize_header(v) for v in header_values]
        name_idx = next((i for i, value in enumerate(normalized_headers) if "name" in value), None)
        roll_idx = next((i for i, value in enumerate(normalized_headers) if "roll" in value), None)
        if name_idx is None or roll_idx is None:
            raise AttendanceParseError("Required columns Roll No and Name are missing.")

        subject_columns = build_subject_columns(header_values, code_values, type_values, total_values, name_idx + 1)
        if not subject_columns:
            raise AttendanceParseError("No valid subject columns were detected in the report.")

        data_df = raw_df.iloc[total_row_idx + 1 :].copy()
        data_df.columns = [f"col_{idx}" for idx in range(len(data_df.columns))]
        data_df = drop_empty_and_unnamed_columns(data_df)

        students = []
        normalized_rows = []
        student_subject_percentages = []

        for _, row in data_df.iterrows():
            roll_no = clean_text(row.iloc[roll_idx] if roll_idx < len(row.index) else "")
            student_name = clean_text(row.iloc[name_idx] if name_idx < len(row.index) else "")
            row_preview = " ".join(clean_text(v).upper() for v in row.iloc[: min(6, len(row.index))].tolist())
            if "FACULTY" in row_preview or "SIGNATURE" in row_preview:
                break
            if not roll_no or not student_name or not is_valid_roll(roll_no):
                continue

            student_entry = {
                "roll_no": roll_no.upper(),
                "student_name": student_name,
                "department": metadata["department"],
                "division": metadata["division"],
                "semester": metadata["semester"],
            }
            students.append(student_entry)

            subject_groups = {}
            for subject in subject_columns:
                idx = subject["index"]
                attended = safe_int(row.iloc[idx] if idx < len(row.index) else 0)
                if subject["name"] not in subject_groups:
                    subject_groups[subject["name"]] = {
                        "subject": subject["name"],
                        "subject_code": subject["code"],
                        "lecture_type": subject["lecture_type"],
                        "attended_classes": 0,
                        "total_classes": 0,
                    }
                subject_groups[subject["name"]]["attended_classes"] += attended
                subject_groups[subject["name"]]["total_classes"] += subject["total_classes"]

            for group in subject_groups.values():
                total_classes = group["total_classes"]
                attended_classes = group["attended_classes"]
                percentage = round((attended_classes / total_classes) * 100, 2) if total_classes else 0.0
                normalized = {
                    "roll_no": student_entry["roll_no"],
                    "student_name": student_entry["student_name"],
                    "department": metadata["department"],
                    "division": metadata["division"],
                    "semester": metadata["semester"],
                    "report_start_date": metadata["date_range"]["start"],
                    "report_end_date": metadata["date_range"]["end"],
                    "subject": group["subject"],
                    "subject_code": group["subject_code"],
                    "lecture_type": group["lecture_type"],
                    "attended_classes": attended_classes,
                    "total_classes": total_classes,
                    "percentage": percentage,
                }
                normalized_rows.append(normalized)
                student_subject_percentages.append(percentage)

        if not normalized_rows:
            raise AttendanceParseError("No attendance rows were found after cleaning the report.")

        analytics = build_analytics(normalized_rows, student_subject_percentages)
        return AttendanceParseResult(metadata=metadata, students=students, normalized_rows=normalized_rows, analytics=analytics)
    except AttendanceParseError:
        raise
    except Exception as exc:
        raise AttendanceParseError(f"Failed to parse attendance report: {exc}") from exc


def build_analytics(normalized_rows, percentages):
    subject_stats = {}
    student_stats = {}
    for row in normalized_rows:
        subject_stats.setdefault(row["subject"], []).append(row["percentage"])
        student_stats.setdefault(row["roll_no"], []).append(row["percentage"])

    subject_wise = {
        subject: round(sum(values) / len(values), 2)
        for subject, values in subject_stats.items()
        if values
    }
    student_wise = {
        roll_no: round(sum(values) / len(values), 2)
        for roll_no, values in student_stats.items()
        if values
    }
    low_attendance = [
        {"roll_no": roll_no, "percentage": percentage}
        for roll_no, percentage in student_wise.items()
        if percentage < 75
    ]

    return {
        "subject_wise": subject_wise,
        "student_wise": student_wise,
        "low_attendance": low_attendance,
        "total_students": len(student_wise),
        "avg_attendance": round(sum(percentages) / len(percentages), 2) if percentages else 0.0,
        "defaulters": len(low_attendance),
    }

