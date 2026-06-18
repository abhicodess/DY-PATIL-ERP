from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from utils.pg_wrapper import qry, qone, exe
from utils.api_response import success_response, error_response, paginated_response
from api.v1.auth import jwt_role_required

timetable_bp = Blueprint('timetable', __name__)

@timetable_bp.route("", methods=["GET"])
def search_timetable():
    """
    Search and filter timetable slots (Public Endpoint).
    ---
    tags:
      - Timetable
    parameters:
      - name: day
        in: query
        type: string
        description: Weekday (e.g. Monday)
      - name: division
        in: query
        type: string
      - name: branch
        in: query
        type: string
        description: Department/Branch code
      - name: year
        in: query
        type: string
      - name: semester
        in: query
        type: string
      - name: faculty_id
        in: query
        type: integer
      - name: subject
        in: query
        type: string
        description: Subject name or code
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
        description: List of timetable slots
    """
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    query = """
        SELECT id, day, time, start_time::TEXT as start_time, end_time::TEXT as end_time,
               subject_id, subject, teacher, faculty_id, room, division, branch, year, semester,
               slot_type, color, published
        FROM timetable
        WHERE 1=1
    """
    params = {}

    if request.args.get('day'):
        query += " AND day = :day"
        params['day'] = request.args.get('day')
    if request.args.get('division'):
        query += " AND division = :division"
        params['division'] = request.args.get('division')
    if request.args.get('branch'):
        query += " AND branch = :branch"
        params['branch'] = request.args.get('branch')
    if request.args.get('year'):
        query += " AND year = :year"
        params['year'] = request.args.get('year')
    if request.args.get('semester'):
        query += " AND semester = :semester"
        params['semester'] = request.args.get('semester')
    if request.args.get('faculty_id'):
        query += " AND faculty_id = :faculty_id"
        params['faculty_id'] = int(request.args.get('faculty_id'))
    if request.args.get('subject'):
        query += " AND (subject ILIKE :subject OR (SELECT code FROM subjects WHERE id = subject_id) ILIKE :subject)"
        params['subject'] = f"%{request.args.get('subject')}%"

    count_query = f"SELECT COUNT(*) as cnt FROM ({query}) as src"
    total = qone(count_query, params)['cnt']

    query += " ORDER BY day, start_time LIMIT :limit OFFSET :offset"
    params['limit'] = per_page
    params['offset'] = offset

    records = qry(query, params)
    return paginated_response([dict(r) for r in records], total, page, per_page)

@timetable_bp.route("/<int:slot_id>", methods=["GET"])
def get_slot(slot_id):
    """
    Get details of a single timetable slot.
    ---
    tags:
      - Timetable
    parameters:
      - name: slot_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Slot details retrieved
      404:
        description: Slot not found
    """
    slot = qone("""
        SELECT id, day, time, start_time::TEXT as start_time, end_time::TEXT as end_time,
               subject_id, subject, teacher, faculty_id, room, division, branch, year, semester,
               slot_type, color, published
        FROM timetable
        WHERE id = :id
    """, {"id": slot_id})
    
    if not slot:
        return error_response("Timetable slot not found", "NOT_FOUND", 404)
        
    return success_response(dict(slot), "Slot details retrieved")

@timetable_bp.route("", methods=["POST"])
@jwt_role_required(["admin"])
def create_slot():
    """
    Create a new timetable slot.
    ---
    tags:
      - Timetable
    security:
      - BearerAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - day
            - time
            - subject
          properties:
            day:
              type: string
            time:
              type: string
            start_time:
              type: string
            end_time:
              type: string
            subject_id:
              type: integer
            subject:
              type: string
            teacher:
              type: string
            faculty_id:
              type: integer
            room:
              type: string
            division:
              type: string
            branch:
              type: string
            year:
              type: string
            semester:
              type: string
            slot_type:
              type: string
              default: Theory
            color:
              type: string
    responses:
      200:
        description: Slot created successfully
      422:
        description: Validation errors
    """
    body = request.get_json() or {}
    required = ["day", "time", "subject"]
    for f in required:
        if not body.get(f):
            return error_response(f"Missing required parameter: {f}", "VALIDATION_ERROR", 422)

    # Convert/validate start_time and end_time if provided
    start_time = body.get("start_time") or None
    end_time = body.get("end_time") or None

    res = exe("""
        INSERT INTO timetable (
            day, time, start_time, end_time, subject_id, subject, teacher, faculty_id, room,
            division, branch, year, semester, slot_type, color, published
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true
        ) RETURNING id
    """, (
        body.get("day"), body.get("time"), start_time, end_time, body.get("subject_id"),
        body.get("subject"), body.get("teacher"), body.get("faculty_id"), body.get("room"),
        body.get("division"), body.get("branch"), body.get("year"), body.get("semester"),
        body.get("slot_type", "Theory"), body.get("color")
    ))

    slot_id = res.fetchone()["id"]
    return success_response({"id": slot_id}, "Timetable slot created successfully")

@timetable_bp.route("/<int:slot_id>", methods=["PUT"])
@jwt_role_required(["admin"])
def update_slot(slot_id):
    """
    Update a timetable slot.
    ---
    tags:
      - Timetable
    security:
      - BearerAuth: []
    parameters:
      - name: slot_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
    responses:
      200:
        description: Slot updated successfully
      404:
        description: Slot not found
    """
    slot = qone("SELECT id FROM timetable WHERE id = :id", {"id": slot_id})
    if not slot:
        return error_response("Timetable slot not found", "NOT_FOUND", 404)

    body = request.get_json() or {}
    
    # Dynamically build update SQL
    fields = []
    values = []
    allowed_fields = [
        "day", "time", "start_time", "end_time", "subject_id", "subject", "teacher",
        "faculty_id", "room", "division", "branch", "year", "semester", "slot_type", "color"
    ]
    for key in allowed_fields:
        if key in body:
            fields.append(f"{key} = %s")
            values.append(body[key])

    if not fields:
        return error_response("No valid fields provided for update", "VALIDATION_ERROR", 422)

    values.append(slot_id)
    sql = f"UPDATE timetable SET {', '.join(fields)} WHERE id = %s"
    exe(sql, tuple(values))

    return success_response(None, "Timetable slot updated successfully")

@timetable_bp.route("/<int:slot_id>", methods=["DELETE"])
@jwt_role_required(["admin"])
def delete_slot(slot_id):
    """
    Delete a timetable slot.
    ---
    tags:
      - Timetable
    security:
      - BearerAuth: []
    parameters:
      - name: slot_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Slot deleted successfully
      404:
        description: Slot not found
    """
    slot = qone("SELECT id FROM timetable WHERE id = :id", {"id": slot_id})
    if not slot:
        return error_response("Timetable slot not found", "NOT_FOUND", 404)

    exe("DELETE FROM timetable WHERE id = :id", {"id": slot_id})
    return success_response(None, "Timetable slot deleted successfully")
