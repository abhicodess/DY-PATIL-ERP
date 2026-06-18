from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from utils.pg_wrapper import qry, qone
from blueprints.auth.decorators import login_required, student_required
import logging
import math
from datetime import datetime
from utils.helpers import safe_int

student_extra_bp = Blueprint('student_extra', __name__)

@student_extra_bp.route("/student_attendance")
@student_required
def student_attendance():
    sid = session.get("student_id")
    name = session.get("name")
    subject = request.args.get("subject", "").strip()

    # Get attendance records
    sql = "SELECT * FROM attendance WHERE student_id = %s"
    params = [sid]
    if subject:
        sql += " AND subject = %s"
        params.append(subject)
    sql += " ORDER BY id DESC"
    records = qry(sql, params)

    # Calculate statistics
    all_att = qry("SELECT subject, status FROM attendance WHERE student_id = %s", (sid,))
    subj_map = {}
    for r in all_att:
        s = r["subject"]
        if s not in subj_map: subj_map[s] = {"total": 0, "present": 0}
        subj_map[s]["total"] += 1
        if str(r.get("status", "")).lower() == "present":
            subj_map[s]["present"] += 1
            
    subject_att = [{"subject": s, "total": v["total"], "present": v["present"],
                    "pct": round(v["present"] * 100 / v["total"], 1) if v["total"] > 0 else 0} 
                   for s, v in subj_map.items()]
    
    total_att = len(all_att)
    pres_att = sum(1 for r in all_att if str(r.get("status", "")).lower() == "present")
    overall_pct = round(pres_att * 100 / total_att, 1) if total_att > 0 else 0

    return render_template("student/student_attendance.html", 
                           records=records, 
                           subject_att=subject_att, 
                           total_att=total_att, 
                           pres_att=pres_att, 
                           overall_pct=overall_pct)

@student_extra_bp.route("/student_marks")
@student_required
def student_marks():
    sid = session.get("student_id")
    try:
        marks = qry("SELECT * FROM marks WHERE student_id = %s ORDER BY date DESC", (sid,))
    except Exception:
        marks = []
    return render_template("student/student_marks.html", marks=marks)

@student_extra_bp.route("/student_timetable")
@student_required
def student_timetable():
    return redirect(url_for('timetable.index'))

@student_extra_bp.route("/student_profile")
@student_required
def student_profile():
    return redirect(url_for('students.profile'))

@student_extra_bp.route("/student_notices")
@student_required
def student_notices():
    return render_template("student/student_notices.html", notices=[])

@student_extra_bp.route("/student_notes")
@student_required
def student_notes():
    return render_template("student/student_notes.html", notes=[])

@student_extra_bp.route("/student_analysis")
@student_required
def student_analysis():
    return render_template("student/analysis.html")

@student_extra_bp.route("/student_settings", methods=["GET", "POST"])
@student_required
def student_settings():
    if request.method == "POST":
        if request.form.get("dark_mode"):
            session["dark_mode"] = True
        else:
            session.pop("dark_mode", None)
        flash("Settings saved successfully", "success")
        return redirect("/student_settings")
    return render_template("student/settings.html")

@student_extra_bp.route("/messages")
@login_required(["student", "faculty", "admin"])
def messages():
    return render_template("messages/messages.html", messages=[])


def att_match_student_sql(prefix=""):
    p = f"{prefix}." if prefix else ""
    return f"({p}student_id = %s OR ({p}student_id IS NULL AND {p}student_name = %s))"

def att_match_student_params(sid, name):
    return sid, name

def marks_match_student_sql(prefix=""):
    p = f"{prefix}." if prefix else ""
    return f"({p}student_id = %s OR ({p}student_id IS NULL AND {p}student_name = %s))"

def marks_match_student_params(sid, name):
    return sid, name

@student_extra_bp.route("/report_card/<int:student_id>")
@login_required(role=["admin", "student"])
def report_card(student_id):
    role = session.get("role")
    if not role:
        return redirect("/login")
    # Students can only see their own report card
    if role == "student" and session.get("student_id") != student_id:
        return redirect("/student_dashboard")
    
    s = qone("SELECT * FROM students WHERE id=%s", (student_id,))
    if not s: 
        return redirect("/students")
    s = dict(s)
    name = s["name"]

    from utils.helpers import pct, grade, get_today_str

    att_rows = qry(
        f"SELECT subject,status FROM attendance WHERE {att_match_student_sql()}",
        att_match_student_params(s["id"], name),
    )
    total_att = len(att_rows)
    pres_att = sum(1 for r in att_rows if r["status"] == "Present")
    overall_pct = pct(pres_att, total_att)

    subj_map = {}
    for r in att_rows:
        subj_map.setdefault(r["subject"], {"t": 0, "p": 0})
        subj_map[r["subject"]]["t"] += 1
        if r["status"] == "Present": 
            subj_map[r["subject"]]["p"] += 1
    subject_att = [{"subject": k, "total": v["t"], "present": v["p"],
                    "pct": pct(v["p"], v["t"])} for k, v in subj_map.items()]

    marks_rows = qry(
        f"SELECT * FROM marks WHERE {marks_match_student_sql()} ORDER BY subject,exam_type",
        marks_match_student_params(s["id"], name),
    )
    marks_with_grade = []
    for m in marks_rows:
        d = dict(m)
        d["pct"] = pct(m["marks"], m["total"])
        d["grade"] = grade(m["marks"], m["total"])
        marks_with_grade.append(d)

    return render_template("student/report_card.html", student=s, overall_pct=overall_pct,
                           total_att=total_att, pres_att=pres_att,
                           subject_att=subject_att, marks=marks_with_grade,
                           generated_on=get_today_str())

@student_extra_bp.route("/report_card_student")
@student_required
def report_card_student():
    sid = session.get("student_id")
    if not sid:
        return redirect("/login")
    return redirect(f"/report_card/{sid}")

# --- Student Attendance Dashboard & Helpers ---

def has_summary(student_id):
    """Return True if attendance_summary has rows for this student."""
    row = qone("SELECT COUNT(*) as c FROM attendance_summary WHERE student_id=%s", (student_id,))
    return row and row["c"] > 0

def shortage_needed(attended, total):
    if total <= 0:
        return 0, 0
    # X = 3T - 4A
    needed = max(0, 3 * total - 4 * attended)
    can_miss = 0
    if needed == 0:
        # M = (4A - 3T) // 3
        can_miss = max(0, (4 * attended - 3 * total) // 3)
    return needed, can_miss

def _cumulative_result_dict(present, total, source):
    absent = max(0, total - present)
    pct_val = round(present / total * 100, 1) if total else 0
    # green >85%, yellow 75-85%, red <75%
    if pct_val > 85:
        status = "Good"
    elif pct_val >= 75:
        status = "Average"
    else:
        status = "Low"
    shortage, can_miss = shortage_needed(present, total)
    return {
        "present":    present,
        "attended":   present,
        "absent":     absent,
        "total":      total,
        "percentage": pct_val,
        "status":     status,
        "source":     source,
        "shortage":   shortage,
        "can_miss":   can_miss,
    }

def get_cumulative(student_id, student_name):
    if has_summary(student_id):
        rows = qry(
            "SELECT attended, total FROM attendance_summary WHERE student_id=%s",
            (student_id,)
        )
        source = "summary"
    else:
        rows_raw = qry(
            f"SELECT status FROM attendance WHERE {att_match_student_sql()}",
            att_match_student_params(student_id, student_name)
        )
        total   = len(rows_raw)
        # Count 'Present' and 'Late' as attended
        present = sum(1 for r in rows_raw if r["status"] in ("Present", "Late"))
        rows = [{"attended": present, "total": total}]
        source = "daily"

    total   = sum(r["total"]   for r in rows)
    present = sum(r["attended"] for r in rows)
    return _cumulative_result_dict(present, total, source)

def get_subjects(student_id, student_name):
    subjects = []
    if has_summary(student_id):
        rows = qry(
            "SELECT id, subject, attended, total FROM attendance_summary WHERE student_id=%s ORDER BY subject",
            (student_id,)
        )
        for r in rows:
            att    = r["attended"]
            tot    = r["total"]
            pct_v  = round(att / tot * 100, 1) if tot else 0
            absent = max(0, tot - att)
            shortage_v, can_miss_v = shortage_needed(att, tot)
            status = "Good" if pct_v > 85 else ("Average" if pct_v >= 75 else "Low")
            subjects.append({
                "summary_row_id": r["id"],
                "subject":    r["subject"],
                "attended":   att,
                "total":      tot,
                "absent":     absent,
                "percentage": pct_v,
                "status":     status,
                "shortage":   shortage_v,
                "can_miss":   can_miss_v,
            })
    else:
        rows = qry(
            f"SELECT subject, status FROM attendance WHERE {att_match_student_sql()} ORDER BY subject",
            att_match_student_params(student_id, student_name)
        )
        data = {}
        for r in rows:
            sub = r["subject"]
            data.setdefault(sub, {"total": 0, "present": 0})
            data[sub]["total"] += 1
            if r["status"] in ("Present", "Late"):
                data[sub]["present"] += 1
        for sub, v in sorted(data.items()):
            att    = v["present"]
            tot    = v["total"]
            pct_v  = round(att / tot * 100, 1) if tot else 0
            absent = max(0, tot - att)
            shortage_v, can_miss_v = shortage_needed(att, tot)
            status = "Good" if pct_v > 85 else ("Average" if pct_v >= 75 else "Low")
            subjects.append({
                "summary_row_id": None,
                "subject":    sub,
                "attended":   att,
                "total":      tot,
                "absent":     absent,
                "percentage": pct_v,
                "status":     status,
                "shortage":   shortage_v,
                "can_miss":   can_miss_v,
            })
    return subjects

def prediction_curve(attended, total, future_steps=20):
    curve = []
    for i in range(1, future_steps + 1):
        new_total   = total + i
        new_present = attended + i
        p = round(new_present / new_total * 100, 1) if new_total else 0
        curve.append(p)
    return curve

def will_reach_75(attended, total, remaining_classes=20):
    needed = max(0, int(0.75 * total - attended) + 1)
    can_reach = needed <= remaining_classes
    return can_reach, needed

@student_extra_bp.route("/student_attendance_dashboard")
@login_required(role=["admin", "faculty", "student"])
def student_attendance_dashboard():
    role = session.get("role")
    
    if role == "student":
        sid = session.get("student_id")
        student_row = qone("SELECT * FROM students WHERE id=%s", (sid,))
        if not student_row:
            return redirect("/auth/logout")
        student = dict(student_row)
        is_admin_view = False
    else:
        sid_param = request.args.get("student_id", "")
        if not sid_param:
            if role == "admin":
                return redirect("/attendance_dashboard")
            else:
                return redirect("/dashboard")
        student_row = qone("SELECT * FROM students WHERE id=%s", (safe_int(sid_param),))
        if not student_row:
            if role == "admin":
                return redirect("/attendance_dashboard")
            else:
                return redirect("/dashboard")
        student = dict(student_row)
        is_admin_view = True

    sid  = student["id"]
    name = student["name"]

    cum = get_cumulative(sid, name)
    subjects = get_subjects(sid, name)
    has_v2_data = has_summary(sid)

    curve = prediction_curve(cum["attended"], cum["total"], future_steps=20)
    can_reach, lectures_needed = will_reach_75(cum["attended"], cum["total"])

    subj_labels = [s["subject"][:20] for s in subjects]
    subj_pcts = [s["percentage"] for s in subjects]

    # --- Heatmap Calculations (Last 30 Days) ---
    from datetime import date as dt_date, timedelta
    records_30 = qry("""
        SELECT date, status FROM attendance 
        WHERE student_id = %s 
        AND date >= CURRENT_DATE - INTERVAL '30 days'
    """, (sid,))
    
    date_status_map = {}
    for r in records_30:
        d_str = str(r["date"])
        status = r["status"]
        date_status_map.setdefault(d_str, [])
        date_status_map[d_str].append(status)
        
    heatmap_data = []
    today_date = datetime.now().date()
    for i in range(29, -1, -1):
        d = today_date - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        day_statuses = date_status_map.get(d_str)
        
        if day_statuses:
            if any(s == 'Absent' for s in day_statuses) and not any(s == 'Present' for s in day_statuses):
                status = 'absent'
            elif any(s == 'Late' for s in day_statuses):
                status = 'late'
            else:
                status = 'present'
        else:
            if d.weekday() in (5, 6):
                status = 'weekend'
            else:
                status = 'holiday'
                
        heatmap_data.append({
            "date": d_str,
            "display_date": d.strftime("%b %d, %Y"),
            "status": status
        })

    # --- Date-wise history table with faculty name and subject ---
    history_records = [dict(r) for r in qry("""
        SELECT a.date, a.subject, a.status, f.name as faculty_name
        FROM attendance a
        LEFT JOIN faculty f ON a.faculty_id = f.id
        WHERE a.student_id = %s
        ORDER BY a.date DESC, a.id DESC
        LIMIT 15
    """, (sid,))]

    return render_template("student/student_attendance_dashboard.html",
        student=student,
        cum=cum,
        subjects=subjects,
        has_v2_data=has_v2_data,
        is_admin_view=is_admin_view,
        prediction_curve=curve,
        can_reach=can_reach,
        lectures_needed=lectures_needed,
        subj_labels=subj_labels,
        subj_pcts=subj_pcts,
        today=datetime.now().strftime("%Y-%m-%d"),
        heatmap_data=heatmap_data,
        history_records=history_records
    )
