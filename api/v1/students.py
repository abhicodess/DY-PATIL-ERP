from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, exe
from utils.api_response import success_response, error_response, paginated_response
from api.v1.auth import jwt_role_required
from services.student_service import StudentService
from werkzeug.security import generate_password_hash

students_bp = Blueprint('students', __name__)
student_service = StudentService()

@students_bp.route("", methods=["GET"])
@jwt_role_required(["admin", "faculty"])
def get_students():
    """
    Get paginated list of students with filters.
    ---
    tags:
      - Students
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
        description: Academic year (e.g. I, II, III, IV)
      - name: division
        in: query
        type: string
        description: Division code
      - name: search
        in: query
        type: string
        description: Search by student name, roll number or PRN
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
        enum: [name, roll, prn]
        default: name
      - name: sort_dir
        in: query
        type: string
        enum: [asc, desc]
        default: asc
    responses:
      200:
        description: Paginated student list
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
        'roll': 'roll',
        'prn': 'prn'
    }
    sort_col = allowed_sort_fields.get(sort_by, 'name')

    query = "SELECT id, name, roll, department, year, email, division, prn FROM students WHERE is_active = TRUE"
    params = {}

    if request.args.get('dept'):
        query += " AND department = :dept"
        params['dept'] = request.args.get('dept')
    if request.args.get('year'):
        query += " AND year = :year"
        params['year'] = request.args.get('year')
    if request.args.get('division'):
        query += " AND division = :division"
        params['division'] = request.args.get('division')
    if search:
        query += " AND (name ILIKE :search OR roll ILIKE :search OR prn ILIKE :search)"
        params['search'] = f"%{search}%"

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone(count_query, params)['cnt']

    query += f" ORDER BY {sort_col} {sort_dir} LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)

@students_bp.route("/<int:student_id>", methods=["GET"])
@jwt_required()
def get_student(student_id):
    """
    Get full profile of a single student.
    ---
    tags:
      - Students
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Student profile retrieved
      403:
        description: Unauthorized profile check
      404:
        description: Student not found
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return error_response("Access forbidden: Cannot view other student profiles", "FORBIDDEN", 403)

    student = qone("SELECT id, name, roll, department, year, email, division, prn, photo FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
    if not student:
        return error_response("Student not found", "NOT_FOUND", 404)

    return success_response(dict(student), "Student profile retrieved successfully")

@students_bp.route("", methods=["POST"])
@jwt_role_required(["admin"])
def create_student():
    """
    Create a new student profile.
    ---
    tags:
      - Students
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
            - roll
            - department
            - year
          properties:
            name:
              type: string
            roll:
              type: string
            department:
              type: string
            year:
              type: string
            division:
              type: string
            email:
              type: string
            prn:
              type: string
            password:
              type: string
    responses:
      200:
        description: Student created successfully
      422:
        description: Input validation error
    """
    body = request.get_json() or {}
    required = ['name', 'roll', 'department', 'year']
    for f in required:
        if not body.get(f):
            return error_response(f"Missing required field: {f}", "VALIDATION_ERROR", 422)

    # Check unique roll
    existing = qone("SELECT id FROM students WHERE roll = :roll", {"roll": body.get("roll")})
    if existing:
        return error_response("Student with this roll number already exists", "DUPLICATE_ENTRY", 422)

    try:
        student = student_service.create_student(body)
        return success_response({
            "id": student.id,
            "name": student.name,
            "roll": student.roll,
            "department": student.department
        }, "Student profile created successfully")
    except Exception as e:
        return error_response(str(e), "CREATE_FAILED", 422)

@students_bp.route("/<int:student_id>", methods=["PUT"])
@jwt_role_required(["admin"])
def update_student(student_id):
    """
    Update a student profile.
    ---
    tags:
      - Students
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
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
            roll:
              type: string
            department:
              type: string
            year:
              type: string
            division:
              type: string
            email:
              type: string
            prn:
              type: string
    responses:
      200:
        description: Student updated successfully
      404:
        description: Student not found
    """
    existing = qone("SELECT id FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
    if not existing:
        return error_response("Student not found", "NOT_FOUND", 404)

    body = request.get_json() or {}
    try:
        updated = student_service.update_student(student_id, body)
        return success_response({
            "id": updated.id,
            "name": updated.name,
            "roll": updated.roll,
            "department": updated.department
        }, "Student profile updated successfully")
    except Exception as e:
        return error_response(str(e), "UPDATE_FAILED", 422)

@students_bp.route("/<int:student_id>", methods=["DELETE"])
@jwt_role_required(["admin"])
def delete_student(student_id):
    """
    Soft-delete a student profile.
    ---
    tags:
      - Students
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Student profile deleted successfully
      404:
        description: Student not found
    """
    existing = qone("SELECT id FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
    if not existing:
        return error_response("Student not found", "NOT_FOUND", 404)

    # Perform soft delete by setting is_active = FALSE
    exe("UPDATE students SET is_active = FALSE WHERE id = :id", {"id": student_id})
    return success_response(None, "Student profile deleted successfully")

@students_bp.route("/<int:student_id>/attendance", methods=["GET"])
@jwt_required()
def get_student_attendance_summary(student_id):
    """
    Get student attendance summary.
    ---
    tags:
      - Students
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Student attendance breakdown
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return error_response("Access forbidden: Cannot view other student profiles", "FORBIDDEN", 403)

    # Call attendance summary logic
    stats_overall = qone("""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id
    """, {"student_id": student_id})

    total_classes = stats_overall["total"] or 0
    attended_classes = stats_overall["present"] or 0
    overall_pct = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0

    stats_subjects = qry("""
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

    return success_response({
        "overall": {
            "total": total_classes,
            "present": attended_classes,
            "percentage": overall_pct
        },
        "subjects": subject_breakdown
    }, "Student attendance summary retrieved successfully")

@students_bp.route("/<int:student_id>/results", methods=["GET"])
@jwt_required()
def get_student_results(student_id):
    """
    Get student marks and academic results.
    ---
    tags:
      - Students
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Student marksheet list
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return error_response("Access forbidden: Cannot view other student profiles", "FORBIDDEN", 403)

    # Student can only view published results
    query = """
        SELECT r.id, r.semester, r.internal_marks, r.external_marks, r.total, r.grade, r.is_published,
               s.name as subject_name, s.code as subject_code
        FROM results r
        JOIN subjects s ON r.subject_id = s.id
        WHERE r.student_id = :student_id
    """
    params = {"student_id": student_id}
    
    if role == 'student':
        query += " AND r.is_published = TRUE"

    rows = qry(query, params)
    return success_response([dict(r) for r in rows], "Student results retrieved successfully")
