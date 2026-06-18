from flask import Blueprint, jsonify
from services.student_service import StudentService

students_api_bp = Blueprint('students_api', __name__)
student_service = StudentService()

@students_api_bp.route("/", methods=["GET"])
def get_students():
    students = student_service.get_all_students()
    return jsonify([{"id": s.id, "name": s.name} for s in students])
