from flask import Blueprint, jsonify
from services.attendance_service import AttendanceService

attendance_api_bp = Blueprint('attendance_api', __name__)
attendance_service = AttendanceService()

@attendance_api_bp.route("/stats/<int:student_id>", methods=["GET"])
def get_stats(student_id):
    stats = attendance_service.get_student_stats(student_id)
    return jsonify(stats)
