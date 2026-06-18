from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, exe
from utils.api_response import success_response, error_response, paginated_response
from api.v1.auth import jwt_role_required
from services.faculty_service import FacultyService
import datetime

faculty_bp = Blueprint('faculty', __name__)
faculty_service = FacultyService()

@faculty_bp.route("", methods=["GET"])
@jwt_role_required(["admin"])
def get_faculties():
    """
    Get paginated list of faculty with filters.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: dept
        in: query
        type: string
        description: Department code
      - name: search
        in: query
        type: string
        description: Search by name or email
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
      - name: sort_by
        in: query
        type: string
        enum: [name, email, department]
        default: name
      - name: sort_dir
        in: query
        type: string
        enum: [asc, desc]
        default: asc
    responses:
      200:
        description: Paginated faculty list
    """
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'name')
    sort_dir = request.args.get('sort_dir', 'asc').lower()

    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'asc'

    allowed_sort_fields = {
        'name': 'name',
        'email': 'email',
        'department': 'department'
    }
    sort_col = allowed_sort_fields.get(sort_by, 'name')

    query = "SELECT id, name, email, department, designation, phone, qualification, joining_date FROM faculty WHERE is_active = TRUE"
    params = {}

    if request.args.get('dept'):
        query += " AND department = :dept"
        params['dept'] = request.args.get('dept')
    if search:
        query += " AND (name ILIKE :search OR email ILIKE :search)"
        params['search'] = f"%{search}%"

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone(count_query, params)['cnt']

    query += f" ORDER BY {sort_col} {sort_dir} LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)

@faculty_bp.route("/<int:faculty_id>", methods=["GET"])
@jwt_required()
def get_faculty(faculty_id):
    """
    Get full profile of a single faculty.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: faculty_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Faculty profile retrieved
      403:
        description: Unauthorized profile check
      404:
        description: Faculty not found
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'faculty' and identity_id != faculty_id:
        return error_response("Access forbidden: Cannot view other faculty profiles", "FORBIDDEN", 403)

    faculty = qone("SELECT id, name, email, department, designation, phone, qualification, joining_date, photo FROM faculty WHERE id = :id AND is_active = TRUE", {"id": faculty_id})
    if not faculty:
        return error_response("Faculty not found", "NOT_FOUND", 404)

    return success_response(dict(faculty), "Faculty profile retrieved successfully")

@faculty_bp.route("", methods=["POST"])
@jwt_role_required(["admin"])
def create_faculty():
    """
    Create a new faculty profile.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - department
          properties:
            name:
              type: string
            email:
              type: string
            department:
              type: string
            designation:
              type: string
            phone:
              type: string
            qualification:
              type: string
            joining_date:
              type: string
            password:
              type: string
    responses:
      200:
        description: Faculty created successfully
      422:
        description: Input validation error
    """
    body = request.get_json() or {}
    required = ['name', 'email', 'department']
    for f in required:
        if not body.get(f):
            return error_response(f"Missing required field: {f}", "VALIDATION_ERROR", 422)

    # Check unique email
    existing = qone("SELECT id FROM faculty WHERE email = :email", {"email": body.get("email")})
    if existing:
        return error_response("Faculty with this email already exists", "DUPLICATE_ENTRY", 422)

    try:
        faculty = faculty_service.create_faculty(body)
        return success_response({
            "id": faculty.id,
            "name": faculty.name,
            "email": faculty.email,
            "department": faculty.department
        }, "Faculty profile created successfully")
    except Exception as e:
        return error_response(str(e), "CREATE_FAILED", 422)

@faculty_bp.route("/<int:faculty_id>", methods=["PUT"])
@jwt_role_required(["admin"])
def update_faculty(faculty_id):
    """
    Update a faculty profile.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: faculty_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            email:
              type: string
            department:
              type: string
            designation:
              type: string
            phone:
              type: string
            qualification:
              type: string
            joining_date:
              type: string
    responses:
      200:
        description: Faculty updated successfully
      404:
        description: Faculty not found
    """
    existing = qone("SELECT id FROM faculty WHERE id = :id AND is_active = TRUE", {"id": faculty_id})
    if not existing:
        return error_response("Faculty not found", "NOT_FOUND", 404)

    body = request.get_json() or {}
    try:
        updated = faculty_service.update_faculty(faculty_id, body)
        return success_response({
            "id": updated.id,
            "name": updated.name,
            "email": updated.email,
            "department": updated.department
        }, "Faculty profile updated successfully")
    except Exception as e:
        return error_response(str(e), "UPDATE_FAILED", 422)

@faculty_bp.route("/<int:faculty_id>", methods=["DELETE"])
@jwt_role_required(["admin"])
def delete_faculty(faculty_id):
    """
    Soft-delete a faculty profile.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: faculty_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Faculty profile deleted successfully
      404:
        description: Faculty not found
    """
    existing = qone("SELECT id FROM faculty WHERE id = :id AND is_active = TRUE", {"id": faculty_id})
    if not existing:
        return error_response("Faculty not found", "NOT_FOUND", 404)

    # Perform soft delete by setting is_active = FALSE
    exe("UPDATE faculty SET is_active = FALSE WHERE id = :id", {"id": faculty_id})
    return success_response(None, "Faculty profile deleted successfully")

@faculty_bp.route("/<int:faculty_id>/timetable", methods=["GET"])
@jwt_required()
def get_timetable(faculty_id):
    """
    Get timetable of a single faculty.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: faculty_id
        in: path
        type: integer
        required: true
      - name: day
        in: query
        type: string
        description: Weekday name
    responses:
      200:
        description: Faculty timetable retrieved
      403:
        description: Unauthorized profile check
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'faculty' and identity_id != faculty_id:
        return error_response("Access forbidden: Cannot view other faculty timetables", "FORBIDDEN", 403)

    day = request.args.get('day')
    if not day:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day = days[datetime.date.today().weekday()]

    # check if faculty exists
    existing = qone("SELECT id FROM faculty WHERE id = :id AND is_active = TRUE", {"id": faculty_id})
    if not existing:
        return error_response("Faculty not found", "NOT_FOUND", 404)

    sql = """
        SELECT id, start_time::TEXT as time, subject_id, 
               (SELECT name FROM subjects WHERE id = subject_id) as subject,
               room, division, dept as branch, year, semester,
               COALESCE(slot_type, 'Lecture') as slot_type
        FROM timetable
        WHERE faculty_id = :faculty_id AND day = :day
        ORDER BY start_time
    """
    slots = qry(sql, {"faculty_id": faculty_id, "day": day})
    return success_response([dict(s) for s in slots], "Timetable retrieved successfully")

@faculty_bp.route("/<int:faculty_id>/sessions", methods=["GET"])
@jwt_required()
def get_faculty_sessions(faculty_id):
    """
    Get attendance sessions logged by a faculty member.
    ---
    tags:
      - Faculty
    security:
      - BearerAuth: []
    parameters:
      - name: faculty_id
        in: path
        type: integer
        required: true
      - name: subject
        in: query
        type: string
        description: Subject name
      - name: date
        in: query
        type: string
        description: Date (YYYY-MM-DD)
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 20
    responses:
      200:
        description: Paginated sessions list
      403:
        description: Unauthorized profile check
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'faculty' and identity_id != faculty_id:
        return error_response("Access forbidden: Cannot view other faculty sessions", "FORBIDDEN", 403)

    # Check if faculty exists
    existing = qone("SELECT id FROM faculty WHERE id = :id AND is_active = TRUE", {"id": faculty_id})
    if not existing:
        return error_response("Faculty not found", "NOT_FOUND", 404)

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    query = """
        SELECT id, subject, division, branch as dept, lecture_date::TEXT as date, status, is_locked, created_at::TEXT as created_at
        FROM attendance_sessions
        WHERE faculty_id = :faculty_id
    """
    params = {"faculty_id": faculty_id}

    if request.args.get('subject'):
        query += " AND subject ILIKE :subject"
        params['subject'] = f"%{request.args.get('subject')}%"
    if request.args.get('date'):
        query += " AND lecture_date = :date"
        params['date'] = request.args.get('date')

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone(count_query, params)['cnt']

    query += " ORDER BY lecture_date DESC, created_at DESC LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)
