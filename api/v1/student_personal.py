from flask_smorest import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry_read, qone_read
from utils.api_response import success_response, error_response
from api.v1.auth import jwt_role_required
from extensions import limiter

student_personal_bp = Blueprint('student_personal', __name__, url_prefix='/api/v1/student', description="Student personal API")

def get_student_limit_key():
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is not None:
            return str(identity)
    except Exception:
        pass
    from flask import request
    return request.remote_addr

limiter.limit("100 per minute", key_func=get_student_limit_key)(student_personal_bp)

@student_personal_bp.route("/attendance", methods=["GET"])
@jwt_role_required(["student"])
def get_logged_in_student_attendance():
    """
    Get logged in student attendance summary.
    """
    student_id = int(get_jwt_identity())
    
    stats_overall = qone_read("""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id
    """, {"student_id": student_id})

    total_classes = stats_overall["total"] or 0
    attended_classes = stats_overall["present"] or 0
    overall_pct = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0

    stats_subjects = qry_read("""
        SELECT subject, COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id
        GROUP BY subject
    """, {"student_id": student_id})

    subject_breakdown = []
    for s in stats_subjects:
        tot = s["total"]
        pres = s["present"]
        subject_breakdown.append({
            "subject": s["subject"],
            "total": tot,
            "present": pres,
            "percentage": round((pres / tot) * 100, 2) if tot > 0 else 0.0
        })

    day_list = qry_read("""
        SELECT id, date::TEXT as date, subject, status 
        FROM attendance 
        WHERE student_id = :student_id
        ORDER BY date DESC
    """, {"student_id": student_id})

    return success_response({
        "overall": {
            "total": total_classes,
            "present": attended_classes,
            "percentage": overall_pct
        },
        "subjects": subject_breakdown,
        "history": [dict(r) for r in day_list]
    }, "Student attendance retrieved successfully")

@student_personal_bp.route("/results", methods=["GET"])
@jwt_role_required(["student"])
def get_logged_in_student_results():
    """
    Get logged in student results.
    """
    student_id = int(get_jwt_identity())
    
    student = qone_read("SELECT name, roll FROM students WHERE id = :id", {"id": student_id})
    if not student:
        return success_response([], "Student results retrieved successfully")
    
    query = """
        SELECT r.id, r.semester, 
               (COALESCE(r.ut_marks, 0) + COALESCE(r.mse_marks, 0) + COALESCE(r.assignment_marks, 0) + 
                COALESCE(r.attendance_marks, 0) + COALESCE(r.teaching_assessment, 0) + COALESCE(r.tw_marks, 0)) as internal_marks,
               COALESCE(r.pr_or_marks, 0) as external_marks,
               r.marks as total, r.grade, r.published as is_published,
               COALESCE(s.name, r.subject) as subject_name, s.subject_code as subject_code
        FROM results r
        LEFT JOIN subjects s ON r.subject = s.name
        WHERE (r.roll = :roll OR r.student_name = :name) AND r.published = 1
    """
    rows = qry_read(query, {"roll": student["roll"], "name": student["name"]})
    return success_response([dict(r) for r in rows], "Student results retrieved successfully")
