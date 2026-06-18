# backend/core/api/v1/attendance/routes.py
from flask import Blueprint, request, jsonify, g
from backend.core.middleware.auth_middleware import token_required
from backend.core.middleware.rbac_middleware import role_required, permission_required
from backend.core.auth.roles import Roles, Permissions
from backend.core.services.attendance_service import AttendanceService

attendance_api = Blueprint('attendance_api', __name__)

@attendance_api.route('/session/init', methods=['POST'])
@token_required
@role_required([Roles.FACULTY, Roles.ADMIN])
@permission_required(Permissions.ATTENDANCE_CREATE)
def init_session():
    """
    Endpoint for faculties to start a session using a timetable_id.
    Validates ownership and loads students via service layer.
    """
    data = request.get_json()
    timetable_id = data.get('timetable_id')
    
    if not timetable_id:
        return jsonify({"message": "timetable_id is required"}), 400
        
    result, status_code = AttendanceService.initialize_faculty_session(timetable_id, g.user_id)
    return jsonify(result), status_code

@attendance_api.route('/session/submit', methods=['POST'])
@token_required
@role_required([Roles.FACULTY, Roles.ADMIN])
def submit_attendance():
    """
    Commits attendance to DB and generates audit trail.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    records = data.get('records') # List of {'student_id': x, 'status': 'Present'}
    
    if not session_id or not records:
        return jsonify({"message": "session_id and records are required"}), 400
        
    result, status_code = AttendanceService.submit_session_attendance(session_id, g.user_id, records)
    return jsonify(result), status_code
