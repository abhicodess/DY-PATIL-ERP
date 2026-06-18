from flask import redirect, send_file

from models.attendance import fetch_batch_backup, persist_attendance_upload, restore_attendance_upload
from services.excel_parser import AttendanceParseError, parse_attendance_excel


def is_attendance_upload_allowed(session_obj):
    return session_obj.get("role") in {"admin", "faculty"}


def process_attendance_upload(file_storage, session_obj):
    if not is_attendance_upload_allowed(session_obj):
        return {"ok": False, "error": "Unauthorized", "status": 403}
    try:
        parse_result = parse_attendance_excel(file_storage)
        parse_result.metadata["source_filename"] = getattr(file_storage, "filename", "") or ""
        uploader_id = session_obj.get("faculty_id") if session_obj.get("role") == "faculty" else 1
        saved = persist_attendance_upload(parse_result, session_obj.get("role", "admin"), uploader_id)
        return {"ok": True, "result": saved}
    except AttendanceParseError as exc:
        return {"ok": False, "error": str(exc), "status": 400}
    except Exception as exc:
        return {"ok": False, "error": f"Attendance upload failed: {exc}", "status": 500}


def download_attendance_backup(batch_id):
    batch = fetch_batch_backup(batch_id)
    if not batch:
        return "Backup not found", 404
    return send_file(batch["backup_path"], as_attachment=True)


def restore_attendance_backup(batch_id):
    try:
        new_batch_id = restore_attendance_upload(batch_id)
        return redirect(f"/attendance_dashboard?restored=1&batch_id={new_batch_id}")
    except Exception as exc:
        return redirect(f"/attendance_dashboard?error=restore_failed&msg={str(exc)[:120]}")
