from flask import render_template, request, session, abort
from blueprints.exams import exams_bp
from services.exam_service import ExamService
from blueprints.auth.decorators import login_required

exam_service = ExamService()

@exams_bp.route("/schedule")
@login_required
def schedule():
    exams = exam_service.get_upcoming_exams()
    return render_template("exams/schedule.html", exams=exams)

@exams_bp.route("/hall_ticket")
@login_required
def hall_ticket():
    student_id = session.get("student_id")
    if not student_id: abort(403)
    
    eligible = exam_service.validate_eligibility(student_id)
    if not eligible:
        return render_template("exams/not_eligible.html")
        
    return render_template("exams/hall_ticket.html")
