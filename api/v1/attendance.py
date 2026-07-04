from flask import Blueprint, request, jsonify, g, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, exe, qry_read, qone_read
from utils.cache import cache_result
from utils.api_response import success_response, error_response, paginated_response
from api.v1.auth import jwt_role_required
from extensions import limiter
from services.attendance_service import AttendanceService, EnterpriseAttendanceService
import datetime

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route("", methods=["GET"])
@jwt_role_required(["admin", "faculty"])
def get_attendance():
    """
    Get list of attendance records with filters.
    ---
    tags:
      - Attendance
    security:
      - BearerAuth: []
    parameters:
      - name: dept
        in: query
        type: string
        description: Department code
      - name: year
        in: query
        type: string
        description: Year (e.g. I, II)
      - name: division
        in: query
        type: string
        description: Division code
      - name: date
        in: query
        type: string
        description: Date (YYYY-MM-DD)
      - name: date_from
        in: query
        type: string
        description: Start Date (YYYY-MM-DD)
      - name: date_to
        in: query
        type: string
        description: End Date (YYYY-MM-DD)
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
      - name: search
        in: query
        type: string
        description: Search student name or subject
      - name: sort_by
        in: query
        type: string
        enum: [date, status, student_name, subject]
        default: date
      - name: sort_dir
        in: query
        type: string
        enum: [asc, desc]
        default: desc
    responses:
      200:
        description: Paginated attendance list
    """
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    sort_dir = request.args.get('sort_dir', 'desc').lower()
    
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'desc'

    allowed_sort_fields = {
        'date': 'a.date',
        'status': 'a.status',
        'student_name': 's.name',
        'subject': 'a.subject'
    }
    sort_col = allowed_sort_fields.get(sort_by, 'a.date')

    query = """
        SELECT a.id, a.date::TEXT as date, a.status, a.subject, s.name as student_name, s.roll as roll_no, s.department as dept, s.division, s.year
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE 1=1
    """
    params = {}

    if request.args.get('dept'):
        query += " AND s.department = :dept"
        params['dept'] = request.args.get('dept')
    if request.args.get('year'):
        query += " AND s.year = :year"
        params['year'] = request.args.get('year')
    if request.args.get('division'):
        query += " AND s.division = :division"
        params['division'] = request.args.get('division')
    if request.args.get('date'):
        query += " AND a.date = :date"
        params['date'] = request.args.get('date')
    if request.args.get('date_from'):
        query += " AND a.date >= :date_from"
        params['date_from'] = request.args.get('date_from')
    if request.args.get('date_to'):
        query += " AND a.date <= :date_to"
        params['date_to'] = request.args.get('date_to')
    if search:
        query += " AND (s.name ILIKE :search OR a.subject ILIKE :search)"
        params['search'] = f"%{search}%"

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone_read(count_query, params)['cnt']

    query += f" ORDER BY {sort_col} {sort_dir} LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry_read(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)

@attendance_bp.route("/session", methods=["POST"])
@jwt_role_required(["faculty"])
def create_session():
    """
    Create a new attendance session and log marks.
    ---
    tags:
      - Attendance
    security:
      - BearerAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - subject_id
            - division
            - date
            - records
          properties:
            subject_id:
              type: integer
            division:
              type: string
            date:
              type: string
              format: date
            records:
              type: array
              items:
                type: object
                required:
                  - student_id
                  - status
                properties:
                  student_id:
                    type: integer
                  status:
                    type: string
                    enum: [Present, Absent, Late]
    responses:
      200:
        description: Session created successfully
      422:
        description: Validation errors
    """
    body = request.get_json() or {}
    subject_id = body.get("subject_id")
    division = body.get("division")
    date = body.get("date")
    records = body.get("records")

    if not subject_id or not division or not date or not records:
        return error_response("Missing required parameters: subject_id, division, date, or records", "VALIDATION_ERROR", 422)

    subj = qone("SELECT name, department FROM subjects WHERE id = :id", {"id": subject_id})
    if not subj:
        return error_response("Subject not found", "NOT_FOUND", 422)

    faculty_id = int(get_jwt_identity())

    # Create Session in Draft first
    res = exe("""
        INSERT INTO attendance_sessions (
            subject_id, subject, division, branch, lecture_date, faculty_id, created_by, created_role, method, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (subject_id, subj["name"], division, subj["department"], date, faculty_id, faculty_id, "faculty", "API", "draft"))
    
    session_id = res.fetchone()["id"]

    # Submit attendance details
    result = EnterpriseAttendanceService.submit_attendance(faculty_id, session_id, records, is_final=True)

    if not result.get("success"):
        return error_response(result.get("error", "Failed to submit attendance"), "SUBMISSION_FAILED", 400)

    # Calculate counts
    total_present = len([r for r in records if r["status"] == "Present"])
    total_absent = len([r for r in records if r["status"] == "Absent"])

    return success_response({
        "session_id": session_id,
        "total_present": total_present,
        "total_absent": total_absent
    }, "Attendance session logged successfully")

def get_faculty_limit_key():
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

@attendance_bp.route("/submit", methods=["POST"])
@jwt_role_required(["faculty"])
@limiter.limit("60 per minute", key_func=get_faculty_limit_key)
def submit_attendance():
    """
    Submit or update attendance (draft or final).
    """
    body = request.get_json() or {}
    session_id = body.get("session_id")
    records = body.get("records")
    is_final = request.args.get("is_final", "true").lower() == "true"

    if not session_id or not isinstance(records, list):
        return error_response("Missing required parameters: session_id or records", "VALIDATION_ERROR", 422)

    faculty_id = int(get_jwt_identity())

    # Call submit attendance service
    result = EnterpriseAttendanceService.submit_attendance(faculty_id, session_id, records, is_final=is_final)
    if not result.get("success"):
        return error_response(result.get("error", "Failed to submit attendance"), "SUBMISSION_FAILED", 400)

    # Calculate count of present, absent, total
    total = len(records)
    present_count = len([r for r in records if r.get("status") == "Present"])
    absent_count = total - present_count

    # Emit socket updates
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
            import datetime
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

    return success_response({
        "session_id": session_id,
        "present_count": present_count,
        "absent_count": absent_count,
        "total": total,
        "is_final": is_final
    }, "Attendance logged successfully")

@attendance_bp.route("/session/initialize", methods=["POST"])
@jwt_role_required(["faculty"])
def initialize_session_route():
    """
    Initialize attendance session from timetable.
    """
    body = request.get_json() or {}
    timetable_id = body.get("timetable_id")
    if not timetable_id:
        return error_response("Missing timetable_id", "VALIDATION_ERROR", 422)

    faculty_id = int(get_jwt_identity())
    result = EnterpriseAttendanceService.initialize_session(faculty_id, timetable_id)
    if not result.get("success"):
        return error_response(result.get("error"), "INITIALIZATION_FAILED", 400)

    details = dict(result["details"])
    if details.get("start_time"):
        details["start_time"] = details["start_time"].strftime("%H:%M:%S")
    if details.get("end_time"):
        details["end_time"] = details["end_time"].strftime("%H:%M:%S")
    if details.get("created_at"):
        details["created_at"] = details["created_at"].isoformat()

    return success_response({
        "session_id": result["session_id"],
        "students": [dict(s) for s in result["students"]],
        "details": details
    }, "Session initialized successfully")

@attendance_bp.route("/session/<int:session_id>", methods=["GET"])
@jwt_role_required(["admin", "faculty"])
def get_session(session_id):
    """
    Get full session details with student records.
    ---
    tags:
      - Attendance
    security:
      - BearerAuth: []
    parameters:
      - name: session_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Session details retrieved
      404:
        description: Session not found
    """
    session_info = qone_read("SELECT id, subject, division, branch as dept, lecture_date::TEXT as date, faculty_id, status FROM attendance_sessions WHERE id = :id", {"id": session_id})
    if not session_info:
        return error_response("Session not found", "NOT_FOUND", 404)

    records = qry_read("""
        SELECT a.id, a.status, s.id as student_id, s.name as student_name, s.roll as roll_no
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.lecture_id = :session_id
        ORDER BY s.roll ASC
    """, {"session_id": session_id})

    return success_response({
        "session": dict(session_info),
        "records": [dict(r) for r in records]
    }, "Session details retrieved")

@cache_result("att_summary:{student_id}:{month}", ttl=300)
def _get_cached_student_summary(student_id, month):
    import calendar
    year, mon = map(int, month.split('-'))
    last_day = calendar.monthrange(year, mon)[1]
    date_from = f"{month}-01"
    date_to = f"{month}-{last_day}"
    
    params = {"student_id": student_id, "date_from": date_from, "date_to": date_to}
    
    stats_overall = qone_read("""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id AND date >= :date_from AND date <= :date_to
    """, params)

    total_classes = stats_overall["total"] or 0
    attended_classes = stats_overall["present"] or 0
    overall_pct = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0

    stats_subjects = qry_read("""
        SELECT subject, COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id AND date >= :date_from AND date <= :date_to
        GROUP BY subject
    """, params)

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
        WHERE student_id = :student_id AND date >= :date_from AND date <= :date_to
        ORDER BY date DESC
    """, params)

    return {
        "overall": {
            "total": total_classes,
            "present": attended_classes,
            "percentage": overall_pct
        },
        "subjects": subject_breakdown,
        "history": [dict(r) for r in day_list]
    }

@attendance_bp.route("/student/<int:student_id>", methods=["GET"])
@jwt_required()
def get_student_attendance(student_id):
    """
    Get student attendance summary and records.
    ---
    tags:
      - Attendance
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
         in: path
         type: integer
         required: true
      - name: date_from
         in: query
         type: string
      - name: date_to
         in: query
         type: string
      - name: subject_id
         in: query
         type: integer
    responses:
      200:
        description: Student attendance details retrieved
      403:
        description: Unauthorized role check
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return error_response("Access forbidden: Cannot view other student profiles", "FORBIDDEN", 403)

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    subject_id = request.args.get('subject_id')

    if not date_from and not date_to and not subject_id:
        month = datetime.datetime.now().strftime("%Y-%m")
        try:
            res_data = _get_cached_student_summary(student_id, month)
            return success_response(res_data, "Student attendance retrieved successfully")
        except Exception as e:
            current_app.logger.error(f"Cached summary fetch failed: {e}")

    # Date filtration
    date_filter = ""
    params = {"student_id": student_id}
    if date_from:
        date_filter += " AND date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        date_filter += " AND date <= :date_to"
        params["date_to"] = date_to
    if subject_id:
        # Resolve subject name first
        sub = qone_read("SELECT name FROM subjects WHERE id = :id", {"id": subject_id})
        if sub:
            date_filter += " AND subject = :subject"
            params["subject"] = sub["name"]

    # Overall stats
    stats_overall = qone_read(f"""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id {date_filter}
    """, params)

    total_classes = stats_overall["total"] or 0
    attended_classes = stats_overall["present"] or 0
    overall_pct = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0

    # Per subject stats
    stats_subjects = qry_read(f"""
        SELECT subject, COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id {date_filter}
        GROUP BY subject
    """, params)

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

    # Day-wise list
    day_list = qry_read(f"""
        SELECT id, date::TEXT as date, subject, status 
        FROM attendance 
        WHERE student_id = :student_id {date_filter}
        ORDER BY date DESC
    """, params)

    return success_response({
        "overall": {
            "total": total_classes,
            "present": attended_classes,
            "percentage": overall_pct
        },
        "subjects": subject_breakdown,
        "history": [dict(r) for r in day_list]
    }, "Student attendance retrieved successfully")

@attendance_bp.route("/defaulters", methods=["GET"])
@jwt_role_required(["admin"])
def get_defaulters():
    """
    Get defaulters below a threshold percentage.
    ---
    tags:
      - Attendance
    security:
      - BearerAuth: []
    parameters:
      - name: dept
        in: query
        type: string
      - name: year
        in: query
        type: string
      - name: threshold
        in: query
        type: integer
        default: 75
    responses:
      200:
        description: List of defaulters
    """
    dept = request.args.get('dept')
    year = request.args.get('year')
    threshold = int(request.args.get('threshold', 75))

    defaulters = AttendanceService.get_defaulters(threshold=threshold, department=dept)
    
    # Filter by year manually since it's not fully filtered in service query
    if year:
        defaulters = [d for d in defaulters if d.get("year") == year]

    return success_response(defaulters, f"Retrieved defaulters below {threshold}%")
