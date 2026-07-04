from flask import render_template, request, session
from blueprints.students import students_bp
from blueprints.auth.decorators import login_required, student_required
from services.student_service import StudentService

student_service = StudentService()

@students_bp.route("/profile")
@student_required
def profile():
    student_id = session.get("student_id")
    student = student_service.repository.get_by_id(student_id)
    return render_template("student/profile.html", student=student)

@students_bp.route("/")
@students_bp.route("/list")
@login_required(["admin", "faculty"])
def list_students():
    from config import DEPARTMENTS, YEARS, DIVISIONS
    q = request.args.get("q", "").strip()
    dept = request.args.get("dept", "").strip()
    year = request.args.get("year", "").strip()
    division = request.args.get("division", "").strip()
    
    filters = {
        "q": q,
        "dept": dept,
        "year": year,
        "division": division
    }
    rows = student_service.get_all_students(filters)
    return render_template(
        "admin/students.html",
        students=rows,
        q=q,
        dept=dept,
        year=year,
        division=division,
        DEPARTMENTS=DEPARTMENTS,
        YEARS=YEARS,
        DIVISIONS=DIVISIONS,
        total=len(rows)
    )

