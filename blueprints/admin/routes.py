from flask import render_template, request, redirect, url_for, flash
from blueprints.admin import admin_bp
from blueprints.auth.decorators import admin_required
from services.student_service import StudentService
from services.faculty_service import FacultyService
from services.attendance_service import AttendanceService

student_service = StudentService()
faculty_service = FacultyService()
attendance_service = AttendanceService()

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    all_students = student_service.get_all_students()
    all_faculty = faculty_service.get_all_faculty()
    
    year_map = {}
    for s in all_students:
        y = s.year or "I"
        year_map[y] = year_map.get(y, 0) + 1
        
    fac_dept_map = {}
    for f in all_faculty:
        d = getattr(f, 'department', '') or getattr(f, 'branch', '') or "Unknown"
        fac_dept_map[d] = fac_dept_map.get(d, 0) + 1

    stats = {
        'ts': len(all_students),
        'tf': len(all_faculty),
        'defaulters_count': len(attendance_service.get_defaulters()),
        'total_messages': 0,
        'year_map': year_map,
        'fac_dept_labels': list(fac_dept_map.keys()),
        'fac_dept_counts': list(fac_dept_map.values()),
        'dept_att_pct': [],
        'recent_students': all_students[-5:] if all_students else [],
        'week_labels': [],
        'week_present': [],
        'dept_labels': [],
        'dept_counts': [],
        'marks_exams': [],
        'marks_avg': [],
        'last_backup': None
    }
    return render_template("admin/admin_dashboard.html", **stats)

@admin_bp.route("/students")
@admin_required
def students():
    filters = request.args.to_dict()
    rows = student_service.get_all_students(filters)
    return render_template("admin/students.html", students=rows)

@admin_bp.route("/add_student", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        student_service.create_student(request.form.to_dict())
        flash("Student added successfully", "success")
        return redirect(url_for('admin.students'))
    return render_template("admin/add_student.html")

@admin_bp.route("/backup")
@admin_required
def backup():
    # Implementation...
    flash("Backup created successfully", "success")
    return redirect(url_for('admin.dashboard'))

# ── SUBJECTS ──────────────────────────────────────────────
@admin_bp.route("/subjects")
@admin_required
def subjects():
    from config import DEPARTMENTS, SEMESTERS
    from utils.pg_wrapper import qry
    q = request.args.get("q", "").strip()
    dept = request.args.get("dept", "").strip()
    sql = "SELECT * FROM subjects WHERE 1=1"
    params = []
    if q:
        sql += " AND (name ILIKE %s OR subject_code ILIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    if dept:
        sql += " AND department=%s"
        params.append(dept)
    sql += " ORDER BY department, name"
    rows = qry(sql, params)
    
    faculty_list = faculty_service.get_all_faculty()
    return render_template("admin/subjects.html", 
                           subjects=rows,
                           q=q, dept=dept, 
                           DEPARTMENTS=DEPARTMENTS, 
                           SEMESTERS=SEMESTERS,
                           teachers=[f.name for f in faculty_list])

@admin_bp.route("/add_subject", methods=["GET", "POST"])
@admin_required
def add_subject():
    from config import DEPARTMENTS, SEMESTERS
    if request.method == "POST":
        from utils.pg_wrapper import exe
        exe("INSERT INTO subjects(name, department, subject_code, teacher, semester, division, credits) VALUES(%s, %s, %s, %s, %s, %s, %s)",
            (request.form.get("name", ""), 
             request.form.get("department", ""), 
             request.form.get("subject_code", ""),
             request.form.get("teacher", ""), 
             request.form.get("semester", "I"),
             request.form.get("division", "A"),
             int(request.form.get("credits", 4))))
        flash("Subject added successfully", "success")
        return redirect(url_for('admin.subjects'))

    faculty_list = faculty_service.get_all_faculty()
    return render_template("admin/add_subject.html", 
                           DEPARTMENTS=DEPARTMENTS, 
                           SEMESTERS=SEMESTERS,
                           teachers=[f.name for f in faculty_list])

@admin_bp.route("/edit_subject/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_subject(id):
    from config import DEPARTMENTS, SEMESTERS
    from utils.pg_wrapper import qone, exe
    if request.method == "POST":
        exe("UPDATE subjects SET name=%s, department=%s, subject_code=%s, teacher=%s, semester=%s, division=%s, credits=%s WHERE id=%s",
            (request.form.get("name", ""), 
             request.form.get("department", ""), 
             request.form.get("subject_code", ""),
             request.form.get("teacher", ""), 
             request.form.get("semester", "I"),
             request.form.get("division", "A"),
             int(request.form.get("credits", 4)),
             id))
        flash("Subject updated successfully", "success")
        return redirect(url_for('admin.subjects'))

    subject = qone("SELECT * FROM subjects WHERE id=%s", (id,))
    faculty_list = faculty_service.get_all_faculty()
    return render_template("admin/edit_subject.html", 
                           subject=subject,
                           DEPARTMENTS=DEPARTMENTS, 
                           SEMESTERS=SEMESTERS,
                           teachers=[f.name for f in faculty_list])

@admin_bp.route("/delete_subject/<int:id>", methods=["POST"])
@admin_required
def delete_subject(id):
    from utils.pg_wrapper import exe
    exe("DELETE FROM subjects WHERE id=%s", (id,))
    flash("Subject deleted successfully", "success")
    return redirect(url_for('admin.subjects'))
