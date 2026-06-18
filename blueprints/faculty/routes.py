from flask import render_template, request, session
from blueprints.faculty import faculty_bp
from blueprints.auth.decorators import login_required, faculty_required
from services.faculty_service import FacultyService

faculty_service = FacultyService()

@faculty_bp.route("/profile")
@faculty_required
def profile():
    faculty_id = session.get("faculty_id")
    faculty = faculty_service.repository.get_by_id(faculty_id)
    return render_template("faculty/profile.html", faculty=faculty)

@faculty_bp.route("/")
@faculty_bp.route("/list")
@login_required(["admin"])
def list_faculty():
    filters = request.args.to_dict()
    rows = faculty_service.get_all_faculty(filters)
    return render_template("faculty/faculty.html", faculty_list=rows)
