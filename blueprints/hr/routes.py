from flask import render_template, request, flash, redirect, url_for
from blueprints.hr import hr_bp
from services.payroll_service import PayrollService
from services.faculty_service import FacultyService
from blueprints.auth.decorators import login_required

payroll_service = PayrollService()
faculty_service = FacultyService()

@hr_bp.route("/faculty_list")
@login_required
def faculty_list():
    # HR/Admin only check would go here or in decorator
    faculties = faculty_service.get_all_faculty()
    return render_template("hr/faculty_list.html", faculties=faculties)

@hr_bp.route("/generate_payslip", methods=["POST"])
@login_required
def generate_payslip():
    fid = request.form.get("faculty_id")
    month = request.form.get("month")
    year = request.form.get("year")
    
    payroll_service.generate_payslip(fid, month, year)
    flash("Payslip generated successfully", "success")
    return redirect(url_for('hr.faculty_list'))
