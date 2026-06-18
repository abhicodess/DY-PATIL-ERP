from flask_smorest import Blueprint
from flask import jsonify, g
from utils.pg_wrapper import qry, qone, exe
from utils.tenant_jwt import tenant_jwt_required, role_required
from schemas.students import StudentCreateSchema, StudentUpdateSchema, StudentResponseSchema, StudentListQuerySchema
from schemas.common import PaginatedResponseSchema, ErrorSchema
from schemas.attendance import AttendanceSummarySchema
from schemas.results import ResultResponseSchema
from services.student_service import StudentService

students_bp = Blueprint(
    'students_api_v1', __name__, url_prefix='/api/v1/students',
    description="Student management endpoints"
)
student_service = StudentService()

@students_bp.route('/', methods=['GET'])
@students_bp.arguments(StudentListQuerySchema, location='query')
@students_bp.response(200, PaginatedResponseSchema)
@students_bp.doc(
    summary="List students",
    description="Returns a paginated list of students. Faculty can only see their own division. Admin sees all.",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin', 'faculty')
def list_students(query_args):
    page = query_args.get('page', 1)
    per_page = query_args.get('per_page', 20)
    offset = (page - 1) * per_page
    search = query_args.get('search', '').strip()
    sort_by = query_args.get('sort_by', 'name')
    sort_dir = query_args.get('order', 'asc').lower()

    allowed_sort_fields = {
        'name': 'name',
        'roll': 'roll',
        'prn': 'prn'
    }
    sort_col = allowed_sort_fields.get(sort_by, 'name')

    query = "SELECT id, name, roll, department, year, email, division, prn FROM students WHERE is_active = TRUE"
    params = {}

    if query_args.get('department'):
        query += " AND department = :department"
        params['department'] = query_args.get('department')
    if query_args.get('year'):
        query += " AND year = :year"
        params['year'] = query_args.get('year')
    if query_args.get('division'):
        query += " AND division = :division"
        params['division'] = query_args.get('division')
    if search:
        query += " AND (name ILIKE :search OR roll ILIKE :search OR prn ILIKE :search)"
        params['search'] = f"%{search}%"

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total_row = qone(count_query, params)
    total = total_row['cnt'] if total_row else 0

    query += f" ORDER BY {sort_col} {sort_dir} LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
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

@students_bp.route('/<int:student_id>', methods=['GET'])
@students_bp.response(200, StudentResponseSchema)
@students_bp.alt_response(404, schema=ErrorSchema, description="Student not found")
@students_bp.doc(
    summary="Get student by ID",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
def get_student(student_id):
    from flask_jwt_extended import get_jwt_identity, get_jwt
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return {"error": "Access forbidden: Cannot view other student profiles", "code": "FORBIDDEN"}, 403

    student = qone("SELECT id, name, roll, department, year, email, division, prn FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
    if not student:
        return {"error": "Student not found", "code": "NOT_FOUND"}, 404

    return dict(student)

@students_bp.route('/', methods=['POST'])
@students_bp.arguments(StudentCreateSchema)
@students_bp.response(201, StudentResponseSchema)
@students_bp.alt_response(409, schema=ErrorSchema, description="Roll number already exists")
@students_bp.alt_response(422, schema=ErrorSchema, description="Validation error")
@students_bp.doc(
    summary="Create student",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin')
def create_student(student_data):
    # Check unique roll
    existing = qone("SELECT id FROM students WHERE roll = :roll", {"roll": student_data.get("roll")})
    if existing:
        return {"error": "Student with this roll number already exists", "code": "DUPLICATE_ENTRY"}, 409

    try:
        student = student_service.create_student(student_data)
        return {
            "id": student.id,
            "name": student.name,
            "roll": student.roll,
            "department": student.department,
            "year": int(student.year) if student.year and student.year.isdigit() else 1,
            "division": student.division,
            "semester": 1,
            "email": student.email,
            "phone": student_data.get("phone", "")
        }, 201
    except Exception as e:
        return {"error": str(e), "code": "CREATE_FAILED"}, 422

@students_bp.route('/<int:student_id>', methods=['PATCH'])
@students_bp.arguments(StudentUpdateSchema)
@students_bp.response(200, StudentResponseSchema)
@students_bp.doc(
    summary="Partially update student",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin')
def update_student(student_data, student_id):
    existing = qone("SELECT id FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
    if not existing:
        return {"error": "Student not found", "code": "NOT_FOUND"}, 404

    try:
        updated = student_service.update_student(student_id, student_data)
        return {
            "id": updated.id,
            "name": updated.name,
            "roll": updated.roll,
            "department": updated.department,
            "year": int(updated.year) if updated.year and updated.year.isdigit() else 1,
            "division": updated.division,
            "semester": 1,
            "email": updated.email,
            "phone": student_data.get("phone", "")
        }
    except Exception as e:
        return {"error": str(e), "code": "UPDATE_FAILED"}, 422

@students_bp.route('/<int:student_id>', methods=['DELETE'])
@students_bp.response(204)
@students_bp.alt_response(404, schema=ErrorSchema)
@students_bp.doc(
    summary="Soft-delete student",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
@role_required('admin')
def delete_student(student_id):
    existing = qone("SELECT id FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
    if not existing:
        return {"error": "Student not found", "code": "NOT_FOUND"}, 404

    exe("UPDATE students SET is_active = FALSE WHERE id = :id", {"id": student_id})
    return "", 204

@students_bp.route('/<int:student_id>/attendance', methods=['GET'])
@students_bp.response(200, AttendanceSummarySchema)
@students_bp.doc(
    summary="Get student attendance summary",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
def get_student_attendance(student_id):
    from flask_jwt_extended import get_jwt_identity, get_jwt
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return {"error": "Access forbidden", "code": "FORBIDDEN"}, 403

    stats_overall = qone("""
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = :student_id
    """, {"student_id": student_id})

    total_classes = stats_overall["total"] or 0
    attended_classes = stats_overall["present"] or 0
    overall_pct = round((attended_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0

    return {
        "student_id": student_id,
        "attended": attended_classes,
        "total": total_classes,
        "percentage": overall_pct
    }

@students_bp.route('/<int:student_id>/results', methods=['GET'])
@students_bp.response(200, ResultResponseSchema(many=True))
@students_bp.doc(
    summary="Get student results",
    tags=["Students"],
    security=[{"BearerAuth": []}]
)
@tenant_jwt_required
def get_student_results(student_id):
    from flask_jwt_extended import get_jwt_identity, get_jwt
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')
    if role == 'student' and identity_id != student_id:
        return {"error": "Access forbidden", "code": "FORBIDDEN"}, 403

    query = """
        SELECT r.id, r.semester, r.marks as total, r.grade, r.published as is_published,
               r.student_id, r.subject as subject_id
        FROM results r
        WHERE r.student_id = :student_id
    """
    params = {"student_id": student_id}
    if role == 'student':
        query += " AND r.published = 1"

    rows = qry(query, params)
    return [dict(r) for r in rows]
