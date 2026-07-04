from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from utils.pg_wrapper import qry, qone, exe
from utils.api_response import success_response, error_response, paginated_response
from api.v1.auth import jwt_role_required

results_bp = Blueprint('results', __name__)

def calculate_grade(total):
    """Utility to calculate grade from total marks."""
    if total is None:
        return 'F'
    if total >= 90:
        return 'O'
    elif total >= 80:
        return 'A+'
    elif total >= 70:
        return 'A'
    elif total >= 60:
        return 'B+'
    elif total >= 50:
        return 'B'
    elif total >= 40:
        return 'C'
    else:
        return 'F'

@results_bp.route("/bulk", methods=["POST"])
@jwt_role_required(["admin", "faculty"])
def bulk_input_results():
    """
    Bulk submit student results.
    ---
    tags:
      - Results
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
            - semester
            - records
          properties:
            subject_id:
              type: integer
            semester:
              type: string
            records:
              type: array
              items:
                type: object
                required:
                  - student_id
                  - internal_marks
                  - external_marks
                properties:
                  student_id:
                    type: integer
                  internal_marks:
                    type: number
                  external_marks:
                    type: number
                  grade:
                    type: string
                  is_published:
                    type: boolean
    responses:
      200:
        description: Results recorded successfully
      422:
        description: Validation errors
    """
    body = request.get_json() or {}
    subject_id = body.get("subject_id")
    semester = body.get("semester")
    records = body.get("records")

    if not subject_id or not semester or not isinstance(records, list):
        return error_response("Missing required parameters: subject_id, semester, or records", "VALIDATION_ERROR", 422)

    # Validate subject
    subj = qone("SELECT id FROM subjects WHERE id = :id", {"id": subject_id})
    if not subj:
        return error_response("Subject not found", "NOT_FOUND", 422)

    saved_count = 0
    for rec in records:
        student_id = rec.get("student_id")
        internal_marks = rec.get("internal_marks")
        external_marks = rec.get("external_marks")
        
        if student_id is None or internal_marks is None or external_marks is None:
            continue

        # Validate student
        student = qone("SELECT name, roll, department, year FROM students WHERE id = :id AND is_active = TRUE", {"id": student_id})
        if not student:
            continue

        total = float(internal_marks) + float(external_marks)
        grade_val = rec.get("grade") or calculate_grade(total)
        is_published = rec.get("is_published", False)
        pub_status = 1 if is_published else 0
        res_status = "Pass" if (total / 60.0 * 100) >= 35 else "Fail"

        # Check if record exists
        existing = qone("""
            SELECT id FROM results 
            WHERE (roll = :roll OR student_name = :name) AND subject = :subj AND semester = :semester
        """, {"roll": student["roll"], "name": student["name"], "subj": subj["name"], "semester": semester})

        if existing:
            exe("""
                UPDATE results 
                SET marks = %s, total = %s, grade = %s, published = %s, result = %s,
                    ut_marks = %s, pr_or_marks = %s
                WHERE id = %s
            """, (total, 60.0, grade_val, pub_status, res_status, internal_marks, external_marks, existing["id"]))
        else:
            exe("""
                INSERT INTO results (student_name, roll, department, year, semester, subject, marks, total, grade, result, published, ut_marks, pr_or_marks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (student["name"], student["roll"], student["department"], student["year"], semester, subj["name"], total, 60.0, grade_val, res_status, pub_status, internal_marks, external_marks))
        
        saved_count += 1

    return success_response({"submitted_records": saved_count}, f"Recorded {saved_count} student results successfully")

@results_bp.route("/marksheet", methods=["GET"])
@jwt_required()
def get_marksheet():
    """
    Retrieve marks and results sheets with filters.
    ---
    tags:
      - Results
    security:
      - BearerAuth: []
    parameters:
      - name: student_id
        in: query
        type: integer
      - name: subject_id
        in: query
        type: integer
      - name: semester
        in: query
        type: string
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
        description: List of result records
    """
    identity_id = int(get_jwt_identity())
    role = get_jwt().get('role')

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    query = """
        SELECT r.id, r.semester, 
               (COALESCE(r.ut_marks, 0) + COALESCE(r.mse_marks, 0) + COALESCE(r.assignment_marks, 0) + 
                COALESCE(r.attendance_marks, 0) + COALESCE(r.teaching_assessment, 0) + COALESCE(r.tw_marks, 0)) as internal_marks,
               COALESCE(r.pr_or_marks, 0) as external_marks,
               r.marks as total, r.grade, r.published as is_published,
               COALESCE(s.name, r.subject) as subject_name, s.subject_code as subject_code,
               st.id as student_id, st.name as student_name, st.roll as roll_no, st.division
        FROM results r
        LEFT JOIN subjects s ON r.subject = s.name
        JOIN students st ON r.roll = st.roll
        WHERE st.is_active = TRUE
    """
    params = {}

    # Role enforcement
    if role == 'student':
        query += " AND st.id = :caller_student_id AND r.published = 1"
        params['caller_student_id'] = identity_id
    else:
        # Admins or Faculty can filter by student_id
        if request.args.get('student_id'):
            query += " AND st.id = :student_id"
            params['student_id'] = int(request.args.get('student_id'))

    if request.args.get('subject_id'):
        query += " AND s.id = :subject_id"
        params['subject_id'] = int(request.args.get('subject_id'))
    if request.args.get('semester'):
        query += " AND r.semester = :semester"
        params['semester'] = request.args.get('semester')

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone(count_query, params)['cnt']

    query += " ORDER BY st.name, s.name LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)

@results_bp.route("/publish", methods=["POST"])
@jwt_role_required(["admin"])
def publish_results():
    """
    Publish results (set is_published = TRUE).
    ---
    tags:
      - Results
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
            - semester
          properties:
            subject_id:
              type: integer
            semester:
              type: string
            student_id:
              type: integer
    responses:
      200:
        description: Results published successfully
    """
    body = request.get_json() or {}
    subject_id = body.get("subject_id")
    semester = body.get("semester")
    student_id = body.get("student_id")

    if not subject_id or not semester:
        return error_response("Missing required parameters: subject_id or semester", "VALIDATION_ERROR", 422)

    subj = qone("SELECT name FROM subjects WHERE id = :id", {"id": subject_id})
    if not subj:
        return error_response("Subject not found", "NOT_FOUND", 422)
    subj_name = subj["name"]

    query = """
        UPDATE results 
        SET published = 1 
        WHERE subject = %s AND semester = %s
    """
    params = [subj_name, semester]

    if student_id:
        st = qone("SELECT roll FROM students WHERE id = :id", {"id": student_id})
        if st:
            query += " AND roll = %s"
            params.append(st["roll"])

    exe(query, tuple(params))
    return success_response(None, "Results published successfully")
