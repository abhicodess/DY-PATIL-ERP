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

import os
import shutil
import json
from datetime import datetime, date
import logging
from flask import session
from utils.pg_wrapper import get_db

logger = logging.getLogger("admin_routes")

BACKUP_DIR = "backups"
RESET_TABLES = [
    "messages",
    "timetable_notifications",
    "attendance_summary",
    "qr_sessions",
    "attendance",
    "results",
    "marks",
    "result_summary",
    "cumulative_attendance",
    "faculty_notes",
    "faculty_notices",
    "notifications",
    "events",
    "timetable",
    "subjects",
    "students",
    "faculty",
]

def _quote_ident(name):
    return '"' + str(name).replace('"', '""') + '"'

def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value

def _prune_old_backups(keep=10):
    if not os.path.isdir(BACKUP_DIR):
        return
    backups = []
    for f in os.listdir(BACKUP_DIR):
        if f.startswith("backup_") and (f.endswith(".json") or f.endswith(".db")):
            backups.append(os.path.join(BACKUP_DIR, f))
    backups.sort(key=os.path.getmtime)
    while len(backups) > keep:
        try:
            os.remove(backups.pop(0))
        except Exception as e:
            logger.warning(f"Failed to delete old backup: {e}")

def _create_backup_file():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    conn = get_db()
    backup_path = os.path.join(BACKUP_DIR, f"backup_{stamp}.json")
    
    try:
        from utils.tenant_context import get_tenant_schema
        schema = get_tenant_schema()
    except Exception:
        schema = 'public'

    data = {"created_at": datetime.now().isoformat(timespec="seconds"), "schema": schema, "tables": {}}
    try:
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY table_name",
            (schema,)
        ).fetchall()
        for row in tables:
            table_name = row["table_name"]
            rows = conn.execute(f"SELECT * FROM {_quote_ident(table_name)}").fetchall()
            data["tables"][table_name] = [
                {key: _json_safe(value) for key, value in dict(record).items()}
                for record in rows
            ]
    finally:
        conn.close()

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    _prune_old_backups()
    return backup_path

@admin_bp.route("/backup")
@admin_required
def backup():
    try:
        backup_path = _create_backup_file()
        flash(f"Backup created successfully: {os.path.basename(backup_path)}", "success")
    except Exception as e:
        logger.exception("Backup creation failed")
        flash(f"Backup failed: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route("/reset", methods=["POST"])
@admin_required
def reset_system():
    try:
        backup_path = _create_backup_file()
        logger.warning(
            "Admin %s started full ERP data reset after backup %s",
            session.get("name", "Admin"),
            backup_path,
        )

        try:
            from utils.tenant_context import get_tenant_schema
            schema = get_tenant_schema()
        except Exception:
            schema = 'public'

        conn = get_db()
        try:
            existing = conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=%s AND table_type='BASE TABLE'",
                (schema,)
            ).fetchall()
            existing_names = {row["table_name"] for row in existing}
            tables = [table for table in RESET_TABLES if table in existing_names]
            if tables:
                joined = ", ".join(_quote_ident(table) for table in tables)
                conn.execute(f"TRUNCATE TABLE {joined} RESTART IDENTITY CASCADE")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        flash("All data reset successfully (testing mode)", "warning")
    except Exception as e:
        logger.exception("Full data reset failed")
        flash(f"Reset failed: {str(e)}", "danger")
        return str(e), 500

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
