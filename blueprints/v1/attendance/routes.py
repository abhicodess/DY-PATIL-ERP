from flask_smorest import Blueprint
from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, exe, qry_read, qone_read
from utils.tenant_jwt import tenant_jwt_required, role_required
from schemas.attendance import AttendanceSubmitSchema, AttendanceRecordSchema, AttendanceQuerySchema, AttendanceSummarySchema
from schemas.common import PaginatedResponseSchema, ErrorSchema
from services.attendance_service import AttendanceService, EnterpriseAttendanceService
import datetime

attendance_bp = Blueprint(
    'attendance_api_v1', __name__, url_prefix='/api/v1/attendance',
    description="Attendance management endpoints"
)

@attendance_bp.route('/', methods=['GET'])
@attendance_bp.arguments(AttendanceQuerySchema, location='query')
@attendance_bp.response(200, PaginatedResponseSchema)
@attendance_bp.doc(
    summary="Get list of attendance records",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin', 'faculty')
def get_attendance(query_args):
    page = query_args.get('page', 1)
    per_page = query_args.get('per_page', 20)
    offset = (page - 1) * per_page
    student_id = query_args.get('student_id')
    subject = query_args.get('subject')
    start_date = query_args.get('start_date')
    end_date = query_args.get('end_date')

    query = """
        SELECT a.id, a.date::TEXT as date, a.status, a.subject, s.name as student_name, s.roll as roll_no, s.department as dept, s.division, s.year
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    """
    params = {}

    if student_id:
        query += " AND a.student_id = :student_id"
        params['student_id'] = student_id
    if subject:
        query += " AND a.subject ILIKE :subject"
        params['subject'] = f"%{subject}%"
    if start_date:
        query += " AND a.date >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND a.date <= :end_date"
        params['end_date'] = end_date

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total_row = qone_read(count_query, params)
    total = total_row['cnt'] if total_row else 0

    query += f" ORDER BY a.date DESC LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry_read(query, params)
    data = [dict(r) for r in records]
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    return {
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }

@attendance_bp.route('/session', methods=['POST'])
@attendance_bp.arguments(AttendanceSubmitSchema)
@attendance_bp.response(200, AttendanceSummarySchema)
@attendance_bp.doc(
    summary="Create a new attendance session",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('faculty')
def create_session(session_data):
    subject = session_data.get("subject")
    division = session_data.get("division")
    date_val = session_data.get("date")
    records = session_data.get("records")
    semester = session_data.get("semester")

    # Resolve subject
    subj = qone("SELECT id, department FROM subjects WHERE name = :name", {"name": subject})
    if not subj:
        # fallback
        subj = qone("SELECT id, department FROM subjects ORDER BY id LIMIT 1")
    
    subject_id = subj["id"] if subj else 1
    dept = subj["department"] if subj else "CS"
    faculty_id = int(get_jwt_identity())

    # Create Session in Draft first
    res = exe("""
        INSERT INTO attendance_sessions (
            subject_id, subject, division, branch, lecture_date, faculty_id, created_by, created_role, method, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (subject_id, subject, division, dept, date_val, faculty_id, faculty_id, "faculty", "API", "draft"))
    
    session_id = res.fetchone()["id"]

    # Submit attendance details
    submit_records = [{"student_id": r["student_id"], "status": r["status"]} for r in records]
    result = EnterpriseAttendanceService.submit_attendance(faculty_id, session_id, submit_records, is_final=True)

    if not result.get("success"):
        return {"error": result.get("error", "Failed to submit attendance"), "code": "SUBMISSION_FAILED"}, 400

    total_present = len([r for r in records if r["status"] == "Present"])
    total_classes = len(records)
    pct = round((total_present / total_classes) * 100, 2) if total_classes > 0 else 0.0

    return {
        "student_id": faculty_id,
        "student_name": "Faculty Session Log",
        "subject": subject,
        "attended": total_present,
        "total": total_classes,
        "percentage": pct
    }

@attendance_bp.route('/submit', methods=['POST'])
@attendance_bp.response(200)
@attendance_bp.doc(
    summary="Submit or update attendance",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('faculty')
def submit_attendance():
    body = request.get_json() or {}
    session_id = body.get("session_id")
    records = body.get("records")
    is_final = request.args.get("is_final", "true").lower() == "true"

    if not session_id or not isinstance(records, list):
        return {"error": "Missing required parameters: session_id or records", "code": "VALIDATION_ERROR"}, 422

    faculty_id = int(get_jwt_identity())

    # Call submit attendance service
    result = EnterpriseAttendanceService.submit_attendance(faculty_id, session_id, records, is_final=is_final)
    if not result.get("success"):
        return {"error": result.get("error", "Failed to submit attendance"), "code": "SUBMISSION_FAILED"}, 400

    total = len(records)
    present_count = len([r for r in records if r.get("status") == "Present"])
    absent_count = total - present_count

    try:
        from extensions import socketio
        socketio.emit(
            "attendance_update",
            {
                "session_id": session_id,
                "present_count": present_count,
                "absent_count": absent_count,
                "total": total
            },
            namespace="/attendance",
            room=f"session_{session_id}"
        )
        if is_final:
            socketio.emit(
                "session_locked",
                {
                    "session_id": session_id,
                    "locked_at": datetime.datetime.utcnow().isoformat() + "Z"
                },
                namespace="/attendance",
                room=f"session_{session_id}"
            )
    except Exception as e:
        current_app.logger.error(f"Socket emit failed during submit: {e}")

    return {
        "session_id": session_id,
        "present_count": present_count,
        "absent_count": absent_count,
        "total": total,
        "is_final": is_final
    }

@attendance_bp.route('/session/initialize', methods=['POST'])
@attendance_bp.response(200)
@attendance_bp.doc(
    summary="Initialize attendance session from timetable",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('faculty')
def initialize_session():
    body = request.get_json() or {}
    timetable_id = body.get("timetable_id")
    if not timetable_id:
        return {"error": "Missing timetable_id", "code": "VALIDATION_ERROR"}, 422

    faculty_id = int(get_jwt_identity())
    result = EnterpriseAttendanceService.initialize_session(faculty_id, timetable_id)
    if not result.get("success"):
        return {"error": result.get("error"), "code": "INITIALIZATION_FAILED"}, 400

    details = dict(result["details"])
    if details.get("start_time"):
        details["start_time"] = details["start_time"].strftime("%H:%M:%S")
    if details.get("end_time"):
        details["end_time"] = details["end_time"].strftime("%H:%M:%S")
    if details.get("created_at"):
        details["created_at"] = details["created_at"].isoformat()

    return {
        "session_id": result["session_id"],
        "students": [dict(s) for s in result["students"]],
        "details": details
    }

@attendance_bp.route('/session/<int:session_id>', methods=['GET'])
@attendance_bp.response(200)
@attendance_bp.doc(
    summary="Get session details by ID",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin', 'faculty')
def get_session(session_id):
    session_info = qone_read("SELECT id, subject, division, branch as dept, lecture_date::TEXT as date, faculty_id, status FROM attendance_sessions WHERE id = :id", {"id": session_id})
    if not session_info:
        return {"error": "Session not found", "code": "NOT_FOUND"}, 404

    records = qry_read("""
        SELECT a.id, a.status, s.id as student_id, s.name as student_name, s.roll as roll_no
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.lecture_id = :session_id
        ORDER BY s.roll ASC
    """, {"session_id": session_id})

    return {
        "session": dict(session_info),
        "records": [dict(r) for r in records]
    }

@attendance_bp.route('/student/<int:student_id>', methods=['GET'])
@attendance_bp.response(200, AttendanceSummarySchema)
@attendance_bp.doc(
    summary="Get student attendance summary and history",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
def get_student_attendance(student_id):
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return {"error": "Access forbidden: Cannot view other student profiles", "code": "FORBIDDEN"}, 403

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    subject_id = request.args.get('subject_id')

    date_filter = ""
    params = {"student_id": student_id}
    if date_from:
        date_filter += " AND date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        date_filter += " AND date <= :date_to"
        params["date_to"] = date_to
    if subject_id:
        sub = qone_read("SELECT name FROM subjects WHERE id = :id", {"id": subject_id})
        if sub:
            date_filter += " AND subject = :subject"
            params["subject"] = sub["name"]

    stats_overall = qone_read(f"""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id {date_filter}
    """, params)

    total_classes = stats_overall["total"] or 0
    attended_classes = stats_overall["present"] or 0
    overall_pct = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0

    return {
        "student_id": student_id,
        "attended": attended_classes,
        "total": total_classes,
        "percentage": overall_pct
    }

@attendance_bp.route('/defaulters', methods=['GET'])
@attendance_bp.response(200, AttendanceSummarySchema(many=True))
@attendance_bp.doc(
    summary="Get list of defaulters below threshold",
    tags=["Attendance"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin')
def get_defaulters():
    dept = request.args.get('dept')
    year = request.args.get('year')
    threshold = int(request.args.get('threshold', 75))

    defaulters = AttendanceService.get_defaulters(threshold=threshold, department=dept)
    if year:
        defaulters = [d for d in defaulters if d.get("year") == year]

    result = []
    for d in defaulters:
        result.append({
            "student_id": d.get("student_id", 0),
            "student_name": d.get("name", ""),
            "subject": "Overall",
            "attended": int(d.get("attended", 0)),
            "total": int(d.get("total", 0)),
            "percentage": float(d.get("percentage", 0.0))
        })
    return result
