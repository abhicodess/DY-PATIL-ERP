from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, qry_read, qone_read
from utils.api_response import success_response, error_response
from utils.cache import cache_result
import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@cache_result("admin_stats:{date}", ttl=120)
def _get_cached_admin_stats(date):
    import datetime as dt_module
    dt = dt_module.datetime.strptime(date, "%Y-%m-%d")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day = days[dt.weekday()]
    
    students_count = qone_read("SELECT COUNT(*) as cnt FROM students WHERE is_active = TRUE")["cnt"]
    faculty_count = qone_read("SELECT COUNT(*) as cnt FROM faculty WHERE is_active = TRUE")["cnt"]
    timetable_count = qone_read("SELECT COUNT(*) as cnt FROM timetable WHERE day = :day", {"day": day})["cnt"]
    sessions_today = qone_read("SELECT COUNT(*) as cnt FROM attendance_sessions WHERE lecture_date = :date", {"date": date})["cnt"]
    
    return {
        "total_students": students_count,
        "total_faculty": faculty_count,
        "sessions_scheduled_today": timetable_count,
        "attendance_logs_today": sessions_today
    }

@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_dashboard_summary():
    """
    Get consolidated dashboard metrics based on user role.
    ---
    tags:
      - Dashboard
    security:
      - BearerAuth: []
    responses:
      200:
        description: Dashboard metrics retrieved
    """
    identity_id = int(get_jwt_identity())
    claims = get_jwt()
    role = claims.get("role")

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day = days[datetime.date.today().weekday()]

    if role == "admin":
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        metrics = _get_cached_admin_stats(date_str)

        return success_response({
            "role": "admin",
            "metrics": metrics
        }, "Admin dashboard summary retrieved")

    elif role == "faculty":
        today_sessions = qone_read("SELECT COUNT(*) as cnt FROM timetable WHERE faculty_id = :id AND day = :day", 
                             {"id": identity_id, "day": day})["cnt"]
        total_subjects = qone_read("SELECT COUNT(DISTINCT subject_id) as cnt FROM timetable WHERE faculty_id = :id", 
                             {"id": identity_id})["cnt"]
        recent_sessions = qry_read("""
            SELECT id, subject, division, branch as dept, lecture_date::TEXT as date, status 
            FROM attendance_sessions 
            WHERE faculty_id = :id 
            ORDER BY lecture_date DESC, created_at DESC 
            LIMIT 5
        """, {"id": identity_id})

        return success_response({
            "role": "faculty",
            "metrics": {
                "today_sessions": today_sessions,
                "total_subjects": total_subjects,
                "recent_sessions": [dict(s) for s in recent_sessions]
            }
        }, "Faculty dashboard summary retrieved")

    elif role == "student":
        # Get student's details first
        student = qone_read("SELECT division, year, department FROM students WHERE id = :id AND is_active = TRUE", {"id": identity_id})
        if not student:
            return error_response("Student not found", "NOT_FOUND", 404)

        # Attendance calculation
        att_stats = qone_read("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
            FROM attendance
            WHERE student_id = :id
        """, {"id": identity_id})
        
        tot = att_stats["total"] or 0
        pres = att_stats["present"] or 0
        att_percentage = round((pres / tot) * 100, 2) if tot > 0 else 0.0

        # Published results
        results_count = qone_read("SELECT COUNT(*) as cnt FROM results WHERE student_id = :id AND is_published = TRUE", {"id": identity_id})["cnt"]

        # Today's lectures
        today_lectures = qone_read("""
            SELECT COUNT(*) as cnt FROM timetable 
            WHERE division = :div AND year = :yr AND branch = :dept AND day = :day
        """, {"div": student["division"], "yr": student["year"], "dept": student["department"], "day": day})["cnt"]

        return success_response({
            "role": "student",
            "metrics": {
                "attendance_percentage": att_percentage,
                "total_classes": tot,
                "classes_attended": pres,
                "published_results": results_count,
                "today_lectures": today_lectures
            }
        }, "Student dashboard summary retrieved")

    else:
        return error_response("Invalid role", "FORBIDDEN", 403)
