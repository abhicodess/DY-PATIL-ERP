from flask import Blueprint, jsonify
from services.faculty_service import FacultyService

faculty_api_bp = Blueprint('faculty_api', __name__)
faculty_service = FacultyService()

@faculty_api_bp.route("/", methods=["GET"])
def get_faculty():
    faculty = faculty_service.get_all_faculty()
    return jsonify([{"id": f.id, "name": f.name} for f in faculty])
