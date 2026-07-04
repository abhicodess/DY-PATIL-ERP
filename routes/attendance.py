from flask import jsonify, redirect, send_file

from models.attendance_model import attendance_backup_row
from services.attendance_service import (
    backup_attendance_data,
    delete_attendance_record,
    edit_attendance_record,
    fetch_attendance_records,
    get_students_for_filters,
    mark_bulk_attendance,
    mark_single_attendance,
    process_attendance_import,
    reset_attendance_data,
    restore_attendance_data,
    get_student_prediction_stats,
    submit_correction_request,
    is_attendance_locked,
)


def attendance_role_allowed(session_obj):
    return session_obj.get("role") in {"admin", "faculty"}


def _clean(err_msg):
    if not err_msg:
        return ""
    return str(err_msg)[:160].replace('\r', '').replace('\n', ' ')



from utils.api_utils import json_success

def students_api_response(request_args):
    dept = request_args.get("dept", "").strip()
    division = request_args.get("div", "").strip()
    search = request_args.get("q", "").strip()
    return json_success(data=get_students_for_filters(dept=dept, division=division, search=search))


def handle_single_mark(request_form, session_obj):
    role = session_obj.get("role", "")
    actor_id = session_obj.get("faculty_id") if role == "faculty" else 1
    
    # Check if session is locked
    subject = request_form.get("subject")
    lecture_date = request_form.get("date")
    from utils.pg_wrapper import qone
    session_row = qone("SELECT id FROM attendance_sessions WHERE subject=%s AND lecture_date=%s AND faculty_id=%s", 
                       (subject, lecture_date, actor_id if role == "faculty" else None))
    if session_row and is_attendance_locked(session_row["id"]):
        target = "/faculty/attendance_portal" if role == "faculty" else "/attendance"
        return redirect(f"{target}?error=Attendance session is locked (edit window expired).")

    result = mark_single_attendance(role, actor_id, request_form, session_obj.get("name", ""))
    if result["ok"]:
        target = "/faculty/attendance_portal?saved=1&tab=view" if role == "faculty" else "/attendance?saved=1"
        return redirect(target)
    target = "/faculty/attendance_portal" if role == "faculty" else "/attendance"
    return redirect(f"{target}?error={_clean(result['error'])}")


def handle_bulk_mark(request_form, session_obj):
    role = session_obj.get("role", "")
    actor_id = session_obj.get("faculty_id") if role == "faculty" else 1
    result = mark_bulk_attendance(role, actor_id, request_form, session_obj.get("name", ""))
    if result["ok"]:
        target = "/faculty/attendance_portal?tab=view" if role == "faculty" else "/view_attendance"
        return redirect(f"{target}?saved={result['saved']}&updated={result['updated']}")
    target = "/faculty/attendance_portal" if role == "faculty" else "/attendance"
    return redirect(f"{target}?error={_clean(result['error'])}")


def handle_view_records(request_args, session_obj):
    role = session_obj.get("role", "")
    actor_id = session_obj.get("faculty_id") if role == "faculty" else 1
    return fetch_attendance_records(request_args, actor_role=role or "admin", actor_id=actor_id, actor_name=session_obj.get("name", ""))


def handle_edit_record(request_form, session_obj):
    role = session_obj.get("role", "")
    actor_id = session_obj.get("faculty_id") if role == "faculty" else 1
    
    # Check if session is locked
    att_id = request_form.get("att_id", "")
    from utils.pg_wrapper import qone
    att_row = qone("SELECT lecture_id FROM attendance WHERE id=%s", (att_id,))
    if att_row and is_attendance_locked(att_row["lecture_id"]):
        target = request_form.get("redirect") or ("/faculty/attendance_portal?tab=view" if role == "faculty" else "/view_attendance")
        return redirect(f"{target.split('?')[0]}?error=Attendance record is locked (edit window expired).")

    result = edit_attendance_record(role, actor_id, att_id, request_form)
    target = request_form.get("redirect") or ("/faculty/attendance_portal?tab=view" if role == "faculty" else "/view_attendance")
    if result["ok"]:
        return redirect(target)
    return redirect(f"{target.split('?')[0]}?error={_clean(result['error'])}")


def handle_delete_record(request_form, session_obj):
    role = session_obj.get("role", "")
    actor_id = session_obj.get("faculty_id") if role == "faculty" else 1
    result = delete_attendance_record(role, actor_id, request_form.get("att_id", ""))
    target = request_form.get("redirect") or ("/faculty/attendance_portal?tab=view" if role == "faculty" else "/view_attendance")
    if result["ok"]:
        return redirect(target)
    return redirect(f"{target.split('?')[0]}?error={_clean(result['error'])}")


def handle_import(file_storage, session_obj, subject_override=""):
    result = process_attendance_import(file_storage, session_obj, subject_override=subject_override)
    if result["ok"]:
        saved = result["result"]
        target = "/faculty/attendance_portal?tab=view" if session_obj.get("role") == "faculty" else "/attendance_dashboard"
        return redirect(f"{target}?saved={saved['saved']}&students={saved['students']}&batch_id={saved['batch_id']}")
    target = "/faculty/attendance_portal?tab=import" if session_obj.get("role") == "faculty" else "/attendance"
    return redirect(f"{target}&error={_clean(result['error'])}" if "?" in target else f"{target}?error={_clean(result['error'])}")


def handle_backup(session_obj):
    path = backup_attendance_data(session_obj.get("role", "admin"), session_obj.get("faculty_id") or 1)
    return send_file(path, as_attachment=True)


def handle_restore(session_obj, backup_path=None):
    if not backup_path:
        latest = attendance_backup_row()
        backup_path = latest["path"] if latest else ""
    result = restore_attendance_data(session_obj.get("role", "admin"), session_obj.get("faculty_id") or 1, backup_path)
    if result["ok"]:
        return redirect("/attendance_dashboard?restored=1")
    return redirect(f"/attendance_dashboard?error={_clean(result['error'])}")


def handle_reset(session_obj):
    result = reset_attendance_data(session_obj.get("role", "admin"), session_obj.get("faculty_id") or 1)
    if result["ok"]:
        return redirect("/attendance_dashboard?reset=1")
    return redirect(f"/attendance_dashboard?error={_clean(result['error'])}")


def handle_student_prediction(session_obj, student_id=None):
    """Returns prediction stats for a student."""
    sid = student_id or session_obj.get("student_id")
    if not sid:
        return jsonify({"ok": False, "error": "No student ID found."})
    return jsonify(get_student_prediction_stats(sid))


def handle_correction_request(request_form, session_obj):
    """Submits an attendance correction request."""
    student_id = session_obj.get("student_id")
    student_name = session_obj.get("name")
    record_id = request_form.get("record_id")
    reason = request_form.get("reason")
    
    if not record_id or not reason:
        return redirect("/student_attendance?error=Missing information")
        
    result = submit_correction_request(student_id, student_name, record_id, reason)
    if result["ok"]:
        return redirect("/student_attendance?saved=1")
    return redirect(f"/student_attendance?error={_clean(result['error'])}")
