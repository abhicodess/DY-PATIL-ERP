from flask import render_template, request, redirect, url_for, flash, session
from blueprints.attendance import attendance_bp
from blueprints.auth.decorators import login_required, faculty_required
from services.attendance_service import AttendanceService
from services.student_service import StudentService
from utils.helpers import get_today_str

attendance_service = AttendanceService()
student_service = StudentService()

@attendance_bp.route("/")
@login_required(["admin", "faculty"])
def index():
    return redirect("/attendance")

@attendance_bp.route("/mark", methods=["POST"])
@faculty_required
def mark():
    student_id = request.form.get("student_id")
    subject = request.form.get("subject")
    status = request.form.get("status")
    
    attendance_service.mark_attendance(
        student_id=student_id,
        subject=subject,
        status=status,
        faculty_id=session.get("faculty_id")
    )
    flash("Attendance marked successfully", "success")
    return redirect(url_for('attendance.index'))

@attendance_bp.route("/view")
@login_required(["admin", "faculty", "student"])
def view():
    # Implementation for viewing attendance records
    return render_template("attendance/view_attendance.html")
