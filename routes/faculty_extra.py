from flask import Blueprint, request, redirect, session, render_template, send_file, jsonify
from datetime import datetime, date
import re
import io
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from utils.pg_wrapper import qry, qone, exe
from blueprints.auth.decorators import login_required
from utils.helpers import pct, safe_int
from config import Config

faculty_extra_bp = Blueprint("faculty_extra", __name__)

DEPARTMENTS = Config.DEPARTMENTS
DIVISIONS = Config.DIVISIONS
SEMESTERS = Config.SEMESTERS
DAYS = Config.DAYS
DAY_ORD = Config.DAY_ORD

# ── Helpers ──────────────────────────────────────────────────

def today_str():
    return date.today().strftime("%Y-%m-%d")

def normalise_date(raw):
    if isinstance(raw, (datetime, date)):
        return raw.strftime("%Y-%m-%d")
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def normalize_time(t):
    if not t:
        return t
    t = str(t).strip()
    parts = re.split(r'\s*-\s*', t)
    result = []
    for part in parts:
        m = re.match(r'^(\d{1,2}):(\d{2})$', part.strip())
        if m:
            result.append(f"{int(m.group(1)):02d}:{m.group(2)}")
        else:
            result.append(part.strip())
    return '-'.join(result)

def grade(marks, total):
    p = pct(marks, total)
    if p >= 90: return "A+"
    if p >= 75: return "A"
    if p >= 60: return "B+"
    if p >= 50: return "B"
    if p >= 40: return "C"
    return "F"

def resolve_student_id(name, roll=None):
    if not name or not str(name).strip():
        return None
    name = str(name).strip()
    r = str(roll).strip() if roll is not None and str(roll).strip() else None
    if r:
        row = qone("SELECT id FROM students WHERE name=%s AND roll=%s", (name, r))
        if row:
            return row["id"]
    row = qone("SELECT id FROM students WHERE name=%s ORDER BY id LIMIT 1", (name,))
    return row["id"] if row else None

def marks_match_student_params(sid, name):
    return sid, name

def marks_match_student_sql(prefix=""):
    p = f"{prefix}." if prefix else ""
    return f"({p}student_id = %s OR ({p}student_id IS NULL AND {p}student_name = %s))"

def validate_password_change(stored_hash, current_pw, new_pw, confirm_pw):
    from werkzeug.security import check_password_hash
    from utils.password_policy import validate_password
    if not check_password_hash(stored_hash, current_pw):
        return "invalid_current"
    if not new_pw:
        return "empty_new"
    if new_pw != confirm_pw:
        return "mismatch"
    is_valid, err_msg = validate_password(new_pw)
    if not is_valid:
        return err_msg
    return None

def hash_password(plain):
    from werkzeug.security import generate_password_hash
    return generate_password_hash(plain)

def _cumulative_marks_data_aggregated(dept="", student_filter="", faculty_id=None):
    data = []

    def _add(name, roll, d_dept, obtained, total_m, exams):
        if not total_m:
            return
        pv = round(obtained / total_m * 100, 1) if total_m else 0
        data.append({
            "name": name,
            "roll": roll or "",
            "dept": d_dept or "",
            "obtained": obtained,
            "total": total_m,
            "pct": pv,
            "grade": grade(obtained, total_m),
            "exams": exams,
        })

    wh = ["m.student_id IS NOT NULL"]
    params = []
    if faculty_id is not None:
        wh.append("m.faculty_id=%s")
        params.append(faculty_id)
    if dept:
        wh.append("m.department=%s")
        params.append(dept)
    if student_filter:
        wh.append("m.student_name LIKE %s")
        params.append(f"%{student_filter}%")
    ws = " AND ".join(wh)
    
    rows_std = qry(f"""
        SELECT MAX(m.student_name) AS student_name, MAX(m.roll) AS roll,
        MAX(m.department) AS department, SUM(m.marks) AS obtained,
        SUM(m.total) AS total_m, COUNT(*) AS exams
        FROM marks m WHERE {ws} GROUP BY m.student_id HAVING SUM(m.total) > 0
    """, params)
    for r in rows_std:
        _add(r["student_name"], r["roll"], r["department"], r["obtained"], r["total_m"], r["exams"])

    wh2 = ["m.student_id IS NULL"]
    params2 = []
    if faculty_id is not None:
        wh2.append("m.faculty_id=%s")
        params2.append(faculty_id)
    if dept:
        wh2.append("m.department=%s")
        params2.append(dept)
    if student_filter:
        wh2.append("m.student_name LIKE %s")
        params2.append(f"%{student_filter}%")
    ws2 = " AND ".join(wh2)
    
    rows_legacy = qry(f"""
        SELECT MAX(m.student_name) AS student_name, MAX(m.roll) AS roll,
        MAX(m.department) AS department, SUM(m.marks) AS obtained,
        SUM(m.total) AS total_m, COUNT(*) AS exams
        FROM marks m WHERE {ws2}
        GROUP BY m.student_name, m.roll, m.department HAVING SUM(m.total) > 0
    """, params2)
    for r in rows_legacy:
        _add(r["student_name"], r["roll"], r["department"], r["obtained"], r["total_m"], r["exams"])

    data.sort(key=lambda x: -x["pct"])
    return data

# ── Routes ───────────────────────────────────────────────────

@faculty_extra_bp.route("/faculty_marks")
@login_required("faculty")
def faculty_marks():
    fid = session["faculty_id"]
    students_list = qry("SELECT name,roll FROM students ORDER BY name")
    my_subjects   = qry("SELECT * FROM subjects WHERE teacher LIKE %s ORDER BY name", (f"%{session['name']}%",))
    marks         = qry("SELECT * FROM marks WHERE faculty_id=%s ORDER BY id DESC", (fid,))
    return render_template("faculty/faculty_marks.html",
                           students=students_list, my_subjects=my_subjects,
                           marks=marks, today=today_str())

@faculty_extra_bp.route("/faculty_save_marks", methods=["POST"])
@login_required("faculty")
def faculty_save_marks():
    fid = session["faculty_id"]
    student_name = request.form.get("student_name","").strip()
    roll_row = qone("SELECT id,roll,department FROM students WHERE name=%s", (student_name,))
    stu_id = roll_row["id"]         if roll_row else None
    roll   = roll_row["roll"]       if roll_row else request.form.get("roll","")
    dept   = roll_row["department"] if roll_row else request.form.get("department","")

    exam_type = request.form.get("exam_type", "Semester Exam")

    if exam_type == "Semester Exam":
        assignment_m = min(float(request.form.get("assignment_marks",   0) or 0), 5.0)
        attendance_m = min(float(request.form.get("attendance_marks",   0) or 0), 5.0)
        teaching_m   = min(float(request.form.get("teaching_assessment",0) or 0), 10.0)
        ut_m         = min(float(request.form.get("ut_marks",           0) or 0), 20.0)
        mse_m        = min(float(request.form.get("mse_marks",          0) or 0), 20.0)
        marks_val    = assignment_m + attendance_m + teaching_m + ut_m + mse_m
        if marks_val == 0:
            marks_val = min(float(request.form.get("marks", 0) or 0), 60.0)
        marks_val = min(marks_val, 60.0)
        total_val = 60.0
    else:
        assignment_m = attendance_m = teaching_m = ut_m = mse_m = 0.0
        marks_val = float(request.form.get("marks", 0) or 0)
        total_val = float(request.form.get("total", 60) or 60)
        total_val = min(total_val, 60.0)
        marks_val = min(marks_val, total_val)

    exe("""INSERT INTO marks(faculty_id,student_id,student_name,roll,subject,department,
                             marks,total,exam_type,date,
                             assignment_marks,attendance_marks,teaching_assessment,
                             ut_marks,mse_marks)
           VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (fid, stu_id, student_name, roll,
         request.form.get("subject",""),
         dept,
         marks_val, total_val,
         exam_type,
         request.form.get("date", today_str()),
         assignment_m, attendance_m, teaching_m, ut_m, mse_m))
    return redirect("/faculty_marks?success=1")

@faculty_extra_bp.route("/faculty_delete_marks", methods=["POST"])
@login_required("faculty")
def faculty_delete_marks():
    exe("DELETE FROM marks WHERE id=%s AND faculty_id=%s",
        (request.form.get("marks_id",""), session["faculty_id"]))
    return redirect("/faculty_marks")

@faculty_extra_bp.route("/faculty/api/students_by_subject")
@login_required("faculty")
def api_students_by_subject():
    subj_name = request.args.get("subject", "").strip()
    s_info = qone("SELECT division, department FROM subjects WHERE name=%s", (subj_name,))
    if not s_info:
        return jsonify([])
    
    div = s_info['division']
    dept = s_info['department']
    
    students = qry("""SELECT id, name, roll FROM students 
                      WHERE (division=%s OR %s='') AND (department=%s OR %s='')
                      ORDER BY name""", (div, div, dept, dept))
    return jsonify([dict(s) for s in students])

@faculty_extra_bp.route("/faculty_leaves")
@login_required("faculty")
def faculty_leaves():
    fid = session["faculty_id"]
    my_leaves = qry("SELECT * FROM leave_applications WHERE faculty_id=%s ORDER BY created_at DESC", (fid,))
    return render_template("faculty/faculty_leaves.html", leaves=my_leaves)

@faculty_extra_bp.route("/faculty_apply_leave", methods=["POST"])
@login_required("faculty")
def faculty_apply_leave():
    fid = session["faculty_id"]
    lt  = request.form.get("leave_type")
    f_d = request.form.get("from_date")
    t_d = request.form.get("to_date")
    res = request.form.get("reason")
    
    exe("""INSERT INTO leave_applications (faculty_id, leave_type, from_date, to_date, reason)
           VALUES (%s, %s, %s, %s, %s)""", (fid, lt, f_d, t_d, res))
    return redirect("/faculty_leaves?applied=1")

@faculty_extra_bp.route("/faculty_notices")
@login_required("faculty")
def faculty_notices():
    fid = session["faculty_id"]
    notices = qry("SELECT * FROM faculty_notices WHERE faculty_id=%s ORDER BY id DESC", (fid,))
    return render_template("faculty/faculty_notices.html", notices=notices)

@faculty_extra_bp.route("/faculty_save_notice", methods=["POST"])
@login_required("faculty")
def faculty_save_notice():
    exe("INSERT INTO faculty_notices(faculty_id,title,message) VALUES(%s,%s,%s)",
        (session["faculty_id"], request.form.get("title",""), request.form.get("message","")))
    return redirect("/faculty_notices?success=1")

@faculty_extra_bp.route("/faculty_delete_notice", methods=["POST"])
@login_required("faculty")
def faculty_delete_notice():
    exe("DELETE FROM faculty_notices WHERE id=%s AND faculty_id=%s",
        (request.form.get("notice_id",""), session["faculty_id"]))
    return redirect("/faculty_notices")

@faculty_extra_bp.route("/faculty_notes")
@login_required("faculty")
def faculty_notes():
    fid = session["faculty_id"]
    f_subject = request.args.get("subject","").strip()
    my_subjects = qry("SELECT name FROM subjects WHERE teacher LIKE %s ORDER BY name", (f"%{session['name']}%",))
    sql = "SELECT fn.*, f.name as faculty_name FROM faculty_notes fn JOIN faculty f ON fn.faculty_id=f.id WHERE fn.faculty_id=%s"
    params = [fid]
    if f_subject: 
        sql += " AND fn.subject=%s"
        params.append(f_subject)
    sql += " ORDER BY fn.id DESC"
    notes = qry(sql, params)
    return render_template("faculty/faculty_notes.html", notes=notes, my_subjects=my_subjects, f_subject=f_subject)

@faculty_extra_bp.route("/faculty_save_note", methods=["POST"])
@login_required("faculty")
def faculty_save_note():
    exe("INSERT INTO faculty_notes(faculty_id,subject,title,content,note_type) VALUES(%s,%s,%s,%s,%s)",
        (session["faculty_id"], request.form.get("subject",""), request.form.get("title",""),
         request.form.get("content",""), request.form.get("note_type","Lecture Note")))
    return redirect("/faculty_notes?success=1")

@faculty_extra_bp.route("/faculty_edit_note", methods=["POST"])
@login_required("faculty")
def faculty_edit_note():
    exe("UPDATE faculty_notes SET title=%s,content=%s,note_type=%s WHERE id=%s AND faculty_id=%s",
        (request.form.get("title",""), request.form.get("content",""), request.form.get("note_type",""),
         request.form.get("note_id",""), session["faculty_id"]))
    return redirect("/faculty_notes")

@faculty_extra_bp.route("/faculty_delete_note", methods=["POST"])
@login_required("faculty")
def faculty_delete_note():
    exe("DELETE FROM faculty_notes WHERE id=%s AND faculty_id=%s",
        (request.form.get("note_id",""), session["faculty_id"]))
    return redirect("/faculty_notes")

@faculty_extra_bp.route("/faculty_timetable")
@login_required("faculty")
def faculty_timetable():
    view    = request.args.get("view","grid")
    f_day   = request.args.get("day","").strip()
    f_type  = request.args.get("slot_type","").strip()
    f_branch = request.args.get("branch","").strip()
    f_year = request.args.get("year","").strip()
    f_div = request.args.get("division","").strip()
    f_subj = request.args.get("subject_id","").strip()

    fac_id  = session.get("faculty_id")

    all_entries = [dict(e) for e in qry(f"SELECT t.*, f.name as teacher FROM timetable t JOIN faculty f ON t.faculty_id = f.id WHERE t.faculty_id=%s ORDER BY {DAY_ORD}, t.start_time", (fac_id,))]
    for e in all_entries: 
        e["time"] = normalize_time(e.get("time",""))

    entries = all_entries
    if f_day:  entries = [e for e in entries if e["day"]==f_day]
    if f_type: entries = [e for e in entries if (e.get("slot_type") or "Theory")==f_type]
    if f_branch: entries = [e for e in entries if e.get("branch")==f_branch]
    if f_year: entries = [e for e in entries if e.get("year")==f_year]
    if f_div: entries = [e for e in entries if e.get("division")==f_div]
    if f_subj: entries = [e for e in entries if str(e.get("subject_id"))==str(f_subj)]

    seen=set(); raw=[]
    for e in all_entries:
        t=e["time"]
        if t and t not in seen: 
            seen.add(t)
            raw.append(t)

    def _sk(ts):
        m=re.match(r"(\d+):(\d+)",ts)
        if not m: return 999
        h=int(m.group(1)); mn=int(m.group(2))
        if h<7: h+=12
        return h*60+mn

    time_slots = sorted(raw, key=_sk)
    grid = {d:{t:[] for t in time_slots} for d in DAYS}
    for e in all_entries:
        if e["day"] in grid and e["time"] in grid[e["day"]]:
            grid[e["day"]][e["time"]].append(e)

    total   = len(all_entries)
    theory  = sum(1 for e in all_entries if (e.get("slot_type") or "Theory")=="Theory")
    lab     = sum(1 for e in all_entries if e.get("slot_type")=="Lab")
    days_active = len(set(e["day"] for e in all_entries))

    return render_template("faculty/faculty_timetable.html",
        entries=entries, all_entries=all_entries,
        grid=grid, time_slots=time_slots,
        DAYS=DAYS, view=view, f_day=f_day, f_type=f_type,
        total=total, theory=theory, lab=lab,
        days_active=days_active,
        today_name=date.today().strftime("%A")
    )

@faculty_extra_bp.route("/faculty_profile")
@login_required("faculty")
def faculty_profile():
    profile = qone("SELECT * FROM faculty WHERE id=%s", (session["faculty_id"],))
    return render_template("faculty/faculty_profile.html", profile=dict(profile) if profile else {})

@faculty_extra_bp.route("/faculty_update_profile", methods=["POST"])
@login_required("faculty")
def faculty_update_profile():
    fid = session["faculty_id"]
    name = request.form.get("name","").strip()
    phone= request.form.get("phone","").strip()
    qual = request.form.get("qualification","").strip()
    current_pw = request.form.get("current_password","").strip()
    new_pw = request.form.get("new_password","").strip() or request.form.get("password","").strip()
    confirm_pw = request.form.get("confirm_password","").strip() or new_pw
    
    if name:
        exe("UPDATE faculty SET name=%s,phone=%s,qualification=%s WHERE id=%s", (name,phone,qual,fid))
        session["name"] = name
        
    if new_pw:
        row = qone("SELECT password FROM faculty WHERE id=%s", (fid,))
        err = validate_password_change(row["password"] if row else "", current_pw, new_pw, confirm_pw)
        if err:
            return redirect(f"/faculty_profile?error={err}")
        exe("UPDATE faculty SET password=%s WHERE id=%s", (hash_password(new_pw), fid))
        
    return redirect("/faculty_profile?success=1")

@faculty_extra_bp.route("/faculty_cumulative")
@login_required("faculty")
def faculty_cumulative():
    fid     = session["faculty_id"]
    student = request.args.get("student","").strip()

    data = _cumulative_marks_data_aggregated(dept="", student_filter=student, faculty_id=fid)

    return render_template("cumulative/cumulative_marks.html",
        data=data, dept="", student=student,
        DEPARTMENTS=DEPARTMENTS,
        total_students=len(data),
        role="faculty")

@faculty_extra_bp.route("/import_marks_v2", methods=["POST"])
@login_required("faculty")
def import_marks_v2():
    f = request.files.get("file")
    if not f: return redirect("/faculty_marks")
    fid = session["faculty_id"]
    wb = load_workbook(f, data_only=True); ws = wb.active
    added = 0
    hdr_row = 1
    for i in range(1, min(ws.max_row+1, 10)):
        vals = [str(ws.cell(i,c).value or "").lower() for c in range(1,8)]
        if any("name" in v or "student" in v or "mark" in v for v in vals): hdr_row=i; break
    hdrs = [str(ws.cell(hdr_row,c).value or "").lower().strip() for c in range(1,ws.max_column+1)]
    def gcol(kws):
        for k in kws:
            for i,h in enumerate(hdrs):
                if k in h: return i+1
        return None
    cn=gcol(["name","student"]); cr=gcol(["roll"])
    cs=gcol(["subject"]); cm=gcol(["marks","obtained"])
    ct=gcol(["total"]); ce=gcol(["exam","type"]); cd=gcol(["date"])
    if not cn or not cm: return redirect("/faculty_marks?error=bad_format")
    for row in ws.iter_rows(min_row=hdr_row+1, values_only=True):
        name = str(row[cn-1] or "").strip() if cn <= len(row) else ""
        if not name: continue
        roll    = str(row[cr-1] or "").strip() if cr and cr <= len(row) else ""
        subj    = str(row[cs-1] or "").strip() if cs and cs <= len(row) else ""
        marks_v = row[cm-1] if cm <= len(row) else 0
        total_v = row[ct-1] if ct and ct <= len(row) else 100
        exam_t  = str(row[ce-1] or "Unit Test 1").strip() if ce and ce <= len(row) else "Unit Test 1"
        d_raw   = row[cd-1] if cd and cd <= len(row) else None
        att_date= normalise_date(d_raw) if d_raw else today_str()
        try:
            marks_f = float(marks_v or 0)
            total_f = float(total_v or 100)
        except: continue
        stu_id = resolve_student_id(name, roll)
        sr = qone("SELECT roll,department FROM students WHERE id=%s", (stu_id,)) if stu_id else None
        if sr:
            roll = sr["roll"] or roll
            dept = sr["department"]
        else:
            dept = ""

        exe(
            "INSERT INTO marks(faculty_id,student_id,student_name,roll,subject,department,marks,total,exam_type,date) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (fid, stu_id, name, roll, subj, dept, marks_f, total_f, exam_t, att_date),
        )
        added += 1
    return redirect(f"/faculty_marks?imported={added}")

@faculty_extra_bp.route("/export_marks_excel")
@login_required("faculty")
def export_marks_excel():
    fid     = session["faculty_id"]
    subject = request.args.get("subject","").strip()
    student = request.args.get("student","").strip()

    sql = "SELECT * FROM marks WHERE faculty_id=%s"
    params = [fid]
    if subject: sql += " AND subject=%s"; params.append(subject)
    if student:
        sid = resolve_student_id(student)
        sql += f" AND ({marks_match_student_sql()})"
        params.extend(marks_match_student_params(sid, student))
    sql += " ORDER BY student_name, subject, exam_type"
    rows = qry(sql, params)

    wb = Workbook()
    ws = wb.active
    ws.title = "Marks"

    hdrs = ["Student Name","Roll","Subject","Dept","Exam Type","Marks","Total","Percentage","Grade","Date"]
    for c,h in enumerate(hdrs,1):
        cell = ws.cell(1,c,h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="1E3A5F")
        cell.font = Font(bold=True, color="FFFFFF")

    for r,row in enumerate(rows,2):
        p = round(row["marks"]/row["total"]*100,1) if row["total"] else 0
        g = grade(row["marks"], row["total"])
        vals = [row["student_name"],row["roll"],row["subject"],row["department"],
                row["exam_type"],row["marks"],row["total"],f"{p}%",g,row["date"]]
        for c,v in enumerate(vals,1):
            ws.cell(r,c,v)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(len(str(col[0].value or ""))+4, 14)

    fname = f"marks{'_'+subject if subject else ''}{'_'+student if student else ''}.xlsx"
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@faculty_extra_bp.route("/faculty_results")
@login_required("faculty")
def faculty_results():
    fid = session["faculty_id"]
    my_subjects = qry("SELECT name FROM subjects WHERE teacher LIKE %s ORDER BY name",
                      (f"%{session['name']}%",))
    results = qry("SELECT * FROM results WHERE faculty_id=%s ORDER BY id DESC", (fid,))
    students_list = qry("SELECT name,roll FROM students ORDER BY name")
    return render_template("faculty/faculty_results.html",
        results=results, my_subjects=my_subjects,
        students=students_list, today=today_str(), SEMESTERS=SEMESTERS)

@faculty_extra_bp.route("/faculty_save_result", methods=["POST"])
@login_required("faculty")
def faculty_save_result():
    fid = session["faculty_id"]
    student_name = request.form.get("student_name","").strip()
    roll_row = qone("SELECT roll,department,year FROM students WHERE name=%s", (student_name,))
    roll = roll_row["roll"] if roll_row else ""
    dept = roll_row["department"] if roll_row else ""
    yr   = roll_row["year"] if roll_row else ""

    assignment_m   = min(float(request.form.get("assignment_marks",   0) or 0), 5.0)
    attendance_m   = min(float(request.form.get("attendance_marks",   0) or 0), 5.0)
    teaching_m     = min(float(request.form.get("teaching_assessment",0) or 0), 10.0)
    ut_m           = min(float(request.form.get("ut_marks",           0) or 0), 20.0)
    mse_m          = min(float(request.form.get("mse_marks",          0) or 0), 20.0)

    marks_val = assignment_m + attendance_m + teaching_m + ut_m + mse_m
    if marks_val == 0:
        marks_val = min(float(request.form.get("marks", 0) or 0), 60.0)

    marks_val = min(marks_val, 60.0)
    total_val = 60.0
    g   = grade(marks_val, total_val)
    res = "Pass" if pct(marks_val, total_val) >= 40 else "Fail"

    exe("""INSERT INTO results(student_name,roll,department,year,semester,subject,
                               marks,total,exam_type,grade,result,faculty_id,published,
                               assignment_marks,attendance_marks,teaching_assessment,
                               ut_marks,mse_marks)
           VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s)""",
        (student_name, roll, dept, yr,
         request.form.get("semester","IV"),
         request.form.get("subject",""),
         marks_val, total_val,
         request.form.get("exam_type","Semester Exam"),
         g, res, fid,
         assignment_m, attendance_m, teaching_m, ut_m, mse_m))
    return redirect("/faculty_results?success=1")

@faculty_extra_bp.route("/faculty_edit_result", methods=["POST"])
@login_required("faculty")
def faculty_edit_result():
    rid = request.form.get("result_id", "")
    fid = session["faculty_id"]
    assignment_m = min(float(request.form.get("assignment_marks", 0) or 0), 5.0)
    attendance_m = min(float(request.form.get("attendance_marks", 0) or 0), 5.0)
    teaching_m = min(float(request.form.get("teacher_assessment", 0) or 0), 10.0)
    ut_m = min(float(request.form.get("ut_marks", 0) or 0), 20.0)
    mse_m = min(float(request.form.get("mse_marks", 0) or 0), 20.0)
    tw_m = float(request.form.get("tw_marks", 0) or 0)
    pr_or_m = float(request.form.get("pr_or_marks", 0) or 0)

    marks_val = assignment_m + attendance_m + teaching_m + ut_m + mse_m + tw_m + pr_or_m
    if marks_val == 0:
        marks_val = min(float(request.form.get("marks", 0) or 0), 60.0)

    marks_val = min(marks_val, 60.0)
    total_val = 60.0
    g = grade(marks_val, total_val)
    res = "Pass" if pct(marks_val, total_val) >= 40 else "Fail"
    exe("""UPDATE results SET semester=%s,subject=%s,marks=%s,total=%s,
           exam_type=%s,grade=%s,result=%s, assignment_marks=%s, attendance_marks=%s,
           teaching_assessment=%s, ut_marks=%s, mse_marks=%s, tw_marks=%s, pr_or_marks=%s
           WHERE id=%s AND faculty_id=%s""",
        (request.form.get("semester", ""), request.form.get("subject", ""),
         marks_val, total_val, request.form.get("exam_type", ""),
         g, res, assignment_m, attendance_m, teaching_m, ut_m, mse_m, tw_m, pr_or_m,
         rid, fid))
    return redirect("/faculty_results?updated=1")

@faculty_extra_bp.route("/faculty_delete_result", methods=["POST"])
@login_required("faculty")
def faculty_delete_result():
    exe("DELETE FROM results WHERE id=%s AND faculty_id=%s",
        (request.form.get("result_id",""), session["faculty_id"]))
    return redirect("/faculty_results")

@faculty_extra_bp.route("/cumulative_marks")
@login_required("admin")
def cumulative_marks():
    dept    = request.args.get("dept","").strip()
    student = request.args.get("student","").strip()

    data = _cumulative_marks_data_aggregated(dept=dept, student_filter=student, faculty_id=None)

    return render_template("cumulative/cumulative_marks.html",
        data=data, dept=dept, student=student,
        DEPARTMENTS=DEPARTMENTS,
        total_students=len(data),
        role="admin")

@faculty_extra_bp.route("/export_cumulative_excel")
@login_required("admin")
def export_cumulative_excel():
    dept    = request.args.get("dept","").strip()
    student = request.args.get("student","").strip()

    data = _cumulative_marks_data_aggregated(dept=dept, student_filter=student, faculty_id=None)

    wb = Workbook()
    ws = wb.active
    ws.title = "Cumulative Marks"

    hdrs = ["Student Name", "Roll", "Dept", "Obtained", "Total", "Percentage", "Grade", "Exams"]
    for c, h in enumerate(hdrs, 1):
        cell = ws.cell(1, c, h)
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="1E3A5F")
        cell.font = Font(bold=True, color="FFFFFF")

    for r, row in enumerate(data, 2):
        vals = [row["name"], row["roll"], row["dept"], row["obtained"], row["total"], f"{row['pct']}%", row["grade"], row["exams"]]
        for c, v in enumerate(vals, 1):
            ws.cell(r, c, v)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(len(str(col[0].value or "")) + 4, 14)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="cumulative_marks.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
