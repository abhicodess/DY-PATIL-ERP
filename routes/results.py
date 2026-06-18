"""
routes/results.py — Complete Results Dashboard Module
DY Patil University ERP
"""

from flask import (Blueprint, render_template, request, redirect,
                   session, send_file, jsonify)
from functools import wraps
import psycopg2
import psycopg2.extras, os, io
from openpyxl import Workbook
from openpyxl.styles import (Font, PatternFill, Alignment, Border,
                              Side, GradientFill)
from openpyxl.utils import get_column_letter
from datetime import datetime

# ── Config ──────────────────────────────────────────────────
from config import SEMESTERS, DEPARTMENTS, DIVISIONS
SECTIONS = DIVISIONS

# Grade thresholds (DY Patil standard)
GRADE_TABLE = [
    (75, "O",  "Outstanding",  "#059669"),
    (70, "A+", "Excellent",    "#2563eb"),
    (60, "A",  "Very Good",    "#7c3aed"),
    (55, "B+", "Good",         "#d97706"),
    (50, "B",  "Above Average","#ea580c"),
    (45, "C",  "Average",      "#dc2626"),
    (0,  "F",  "Fail",         "#b91c1c"),
]

results_bp = Blueprint("results_bp", __name__)

# ── DB helpers (standalone, same DB as main app) ────────────
from utils.pg_wrapper import get_db, qry as _qry, qone as _qone, exe as _exe


from blueprints.auth.decorators import login_required
admin_required = login_required("admin")

# ═══════════════════════════════════════════════════════════
#  CORE CALCULATION ENGINE
# ═══════════════════════════════════════════════════════════

def calc_grade(percentage):
    """Return (grade_letter, label, hex_color) for a percentage."""
    for threshold, letter, label, color in GRADE_TABLE:
        if percentage >= threshold:
            return letter, label, color
    return "F", "Fail", "#b91c1c"

def calc_result_status(subject_rows):
    """
    PASS  → all subjects ≥ 40% of their total
    ATKT  → 1–2 subjects below 40%
    FAIL  → 3+ subjects below 40%
    Returns (status, below_count, list_of_failed_subjects)
    """
    below = []
    for r in subject_rows:
        marks = r["marks"] if r["marks"] is not None else 0
        total = r["total"] if r["total"] and r["total"] > 0 else 100
        if (marks / total * 100) < 40:
            below.append(r["subject"])
    n = len(below)
    if n == 0:   status = "PASS"
    elif n <= 2: status = "ATKT"
    else:        status = "FAIL"
    return status, n, below

def assign_section(rank, total_students):
    """Assign section A/B/C/D based on rank (1-indexed)."""
    if total_students == 0:
        return "A"
    q = max(1, total_students // 4)
    if   rank <= q:     return "A"
    elif rank <= q * 2: return "B"
    elif rank <= q * 3: return "C"
    else:               return "D"

def build_student_records(dept=None, semester=None, year=None,
                           section_filter=None, status_filter=None,
                           search=None, published_only=False):
    """
    Core engine: fetches all results rows, groups per student,
    computes section / cumulative / percentage / grade / status.
    Returns list of student dicts sorted by roll.
    """
    sql = "SELECT * FROM results WHERE 1=1"
    params = []
    if dept:      sql += " AND department=%s";  params.append(dept)
    if semester:  sql += " AND semester=%s";     params.append(semester)
    if year:      sql += " AND year=%s";         params.append(year)
    if published_only:
        sql += " AND published=1"
    sql += " ORDER BY roll, student_name, subject"
    rows = _qry(sql, params)

    # Group by (roll, student_name)
    student_map = {}  # key = (roll, name) → {subjects: [], meta: {}}
    for r in rows:
        key = (str(r["roll"] or ""), str(r["student_name"] or ""))
        if key not in student_map:
            student_map[key] = {
                "roll":       r["roll"] or "",
                "name":       r["student_name"] or "",
                "dept":       r["department"] or "",
                "year":       r["year"] or "",
                "semester":   r["semester"] or "",
                "subjects":   [],
            }
        student_map[key]["subjects"].append(dict(r))

    # Build ordered list (sorted by roll for section assignment)
    students = sorted(student_map.values(), key=lambda x: x["roll"])
    total_count = len(students)

    result_list = []
    for rank, s in enumerate(students, 1):
        subj_rows = s["subjects"]

        # Cumulative
        cum_obtained = sum(
            (r["marks"] if r["marks"] is not None else 0)
            for r in subj_rows
        )
        cum_max = sum(
            (r["total"] if r["total"] and r["total"] > 0 else 100)
            for r in subj_rows
        )
        pct = round(cum_obtained / cum_max * 100, 2) if cum_max else 0

        grade_letter, grade_label, grade_color = calc_grade(pct)
        status, fail_count, failed_subjs = calc_result_status(subj_rows)
        section = assign_section(rank, total_count)

        # Check if any subject is AB (absent: marks=0 and special flag)
        has_absent = any(
            r.get("exam_type","").upper() == "ABSENT" or
            str(r.get("marks","")).upper() == "AB"
            for r in subj_rows
        )

        record = {
            "rank":          rank,
            "roll":          s["roll"],
            "name":          s["name"],
            "dept":          s["dept"],
            "year":          s["year"],
            "semester":      s["semester"],
            "section":       section,
            "subjects":      subj_rows,
            "cum_obtained":  round(cum_obtained, 1),
            "cum_max":       round(cum_max, 1),
            "percentage":    pct,
            "grade":         grade_letter,
            "grade_label":   grade_label,
            "grade_color":   grade_color,
            "status":        status,
            "fail_count":    fail_count,
            "failed_subjs":  failed_subjs,
            "has_absent":    has_absent,
        }
        result_list.append(record)

    # ── Apply post-computed filters ──
    if section_filter:
        result_list = [r for r in result_list if r["section"] == section_filter]
    if status_filter:
        result_list = [r for r in result_list if r["status"] == status_filter]
    if search:
        q = search.lower()
        result_list = [
            r for r in result_list
            if q in r["name"].lower() or q in r["roll"].lower()
        ]

    return result_list

def get_subject_list(dept=None, semester=None):
    """Return distinct subject names for the given filter."""
    sql = "SELECT DISTINCT subject FROM results WHERE 1=1"
    p = []
    if dept:     sql += " AND department=%s"; p.append(dept)
    if semester: sql += " AND semester=%s";   p.append(semester)
    sql += " ORDER BY subject"
    return [r["subject"] for r in _qry(sql, p)]

# ═══════════════════════════════════════════════════════════
#  ROUTE 1 — MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════

@results_bp.route("/results_dashboard")
@admin_required
def results_dashboard():
    dept     = request.args.get("dept","").strip()
    semester = request.args.get("semester","").strip()
    year     = request.args.get("year","").strip()
    section  = request.args.get("section","").strip()
    status   = request.args.get("status","").strip()
    search   = request.args.get("q","").strip()
    page     = max(1, int(request.args.get("page","1") or 1))
    per_page = 50

    students = build_student_records(
        dept=dept, semester=semester, year=year,
        section_filter=section or None,
        status_filter=status or None,
        search=search or None,
    )

    # ── Summary KPIs ──
    total_students = len(students)
    pass_count  = sum(1 for s in students if s["status"] == "PASS")
    atkt_count  = sum(1 for s in students if s["status"] == "ATKT")
    fail_count  = sum(1 for s in students if s["status"] == "FAIL")
    absent_count= sum(1 for s in students if s["has_absent"])

    avg_pct = round(
        sum(s["percentage"] for s in students) / total_students, 1
    ) if total_students else 0

    topper = max(students, key=lambda s: s["percentage"]) if students else None

    # ── Grade distribution ──
    grade_dist = {"O":0,"A+":0,"A":0,"B+":0,"B":0,"C":0,"F":0}
    for s in students:
        grade_dist[s["grade"]] = grade_dist.get(s["grade"], 0) + 1

    # ── Section-wise summary ──
    sec_summary = {}
    for sec in SECTIONS:
        sec_students = [s for s in students if s["section"] == sec]
        if sec_students:
            sec_summary[sec] = {
                "count": len(sec_students),
                "avg":   round(sum(s["percentage"] for s in sec_students) / len(sec_students), 1),
                "pass":  sum(1 for s in sec_students if s["status"] == "PASS"),
            }

    # ── Pagination ──
    total_pages = max(1, (total_students + per_page - 1) // per_page)
    page = min(page, total_pages)
    paginated = students[(page-1)*per_page : page*per_page]

    # Subject list for table headers
    subjects = get_subject_list(dept or None, semester or None)

    return render_template("results/results_dashboard.html",
        students=paginated,
        all_students=students,
        subjects=subjects,
        # Filters
        dept=dept, semester=semester, year=year,
        section=section, status=status, search=search,
        # KPIs
        total_students=total_students,
        pass_count=pass_count, atkt_count=atkt_count, fail_count=fail_count,
        absent_count=absent_count, avg_pct=avg_pct, topper=topper,
        grade_dist=grade_dist,
        sec_summary=sec_summary,
        # Pagination
        page=page, total_pages=total_pages, per_page=per_page,
        # Config
        DEPARTMENTS=DEPARTMENTS, SEMESTERS=SEMESTERS, SECTIONS=SECTIONS,
        GRADE_TABLE=GRADE_TABLE,
    )

# ═══════════════════════════════════════════════════════════
#  ROUTE 2 — ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════

@results_bp.route("/results_analytics")
@admin_required
def results_analytics():
    dept     = request.args.get("dept","").strip()
    semester = request.args.get("semester","").strip()

    students = build_student_records(dept=dept or None, semester=semester or None)
    subjects = get_subject_list(dept or None, semester or None)

    # ── Subject-wise analytics ──
    subj_analytics = []
    for subj in subjects:
        subj_marks = []
        below40 = 0
        for s in students:
            for r in s["subjects"]:
                if r["subject"] == subj:
                    m = r["marks"] if r["marks"] is not None else 0
                    t = r["total"] if r["total"] and r["total"] > 0 else 100
                    pct_val = m / t * 100
                    subj_marks.append(pct_val)
                    if pct_val < 40:
                        below40 += 1
        if subj_marks:
            subj_analytics.append({
                "subject":  subj,
                "avg":      round(sum(subj_marks) / len(subj_marks), 1),
                "highest":  round(max(subj_marks), 1),
                "lowest":   round(min(subj_marks), 1),
                "below40":  below40,
                "count":    len(subj_marks),
                "pass_rate":round((len(subj_marks)-below40)/len(subj_marks)*100,1),
            })

    # ── Top 10 students ──
    top10 = sorted(students, key=lambda s: s["percentage"], reverse=True)[:10]

    # ── Section-wise breakdown ──
    sec_breakdown = {}
    for sec in SECTIONS:
        sec_s = [s for s in students if s["section"] == sec]
        if not sec_s:
            continue
        sec_breakdown[sec] = {
            "count":       len(sec_s),
            "avg":         round(sum(s["percentage"] for s in sec_s)/len(sec_s),1),
            "pass":        sum(1 for s in sec_s if s["status"]=="PASS"),
            "atkt":        sum(1 for s in sec_s if s["status"]=="ATKT"),
            "fail":        sum(1 for s in sec_s if s["status"]=="FAIL"),
            "topper":      max(sec_s, key=lambda s: s["percentage"]),
        }

    # ── Failed students per subject ──
    failed_per_subj = {subj: 0 for subj in subjects}
    for s in students:
        for subj in s["failed_subjs"]:
            if subj in failed_per_subj:
                failed_per_subj[subj] += 1

    # ── Grade distribution ──
    grade_dist = {"O":0,"A+":0,"A":0,"B+":0,"B":0,"C":0,"F":0}
    for s in students:
        grade_dist[s["grade"]] = grade_dist.get(s["grade"],0) + 1

    total_students = len(students)
    avg_pct = round(sum(s["percentage"] for s in students)/total_students,1) if total_students else 0

    return render_template("results/results_analytics.html",
        dept=dept, semester=semester,
        total_students=total_students, avg_pct=avg_pct,
        subj_analytics=subj_analytics, top10=top10,
        sec_breakdown=sec_breakdown, failed_per_subj=failed_per_subj,
        grade_dist=grade_dist,
        DEPARTMENTS=DEPARTMENTS, SEMESTERS=SEMESTERS,
        GRADE_TABLE=GRADE_TABLE,
    )

# ═══════════════════════════════════════════════════════════
#  ROUTE 3 — INDIVIDUAL REPORT CARD (printable PDF)
# ═══════════════════════════════════════════════════════════

@results_bp.route("/results_reportcard/<roll>")
@admin_required
def results_reportcard(roll):
    dept     = request.args.get("dept","").strip()
    semester = request.args.get("semester","").strip()

    all_students = build_student_records(dept=dept or None, semester=semester or None)
    student = next((s for s in all_students if s["roll"] == roll), None)
    if not student:
        return redirect("/results_dashboard?error=student_not_found")

    # Class rank
    ranked = sorted(all_students, key=lambda s: s["percentage"], reverse=True)
    rank = next((i+1 for i,s in enumerate(ranked) if s["roll"]==roll), "—")

    return render_template("results/results_reportcard.html",
        student=student, rank=rank,
        total_students=len(all_students),
        dept=dept, semester=semester,
        GRADE_TABLE=GRADE_TABLE,
        now=datetime.now().strftime("%d %b %Y"),
    )

# ═══════════════════════════════════════════════════════════
#  ROUTE 4 — EXPORT EXCEL (full formatted workbook)
# ═══════════════════════════════════════════════════════════

@results_bp.route("/results_export_excel")
@admin_required
def results_export_excel():
    dept     = request.args.get("dept","").strip()
    semester = request.args.get("semester","").strip()
    section  = request.args.get("section","").strip()
    status   = request.args.get("status","").strip()

    students = build_student_records(
        dept=dept or None, semester=semester or None,
        section_filter=section or None,
        status_filter=status or None,
    )
    subjects = get_subject_list(dept or None, semester or None)

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"

    # ── Styles ──
    HDR_FONT  = Font(bold=True, color="FFFFFF", size=11)
    HDR_FILL  = PatternFill("solid", fgColor="1E3A5F")
    SUBJ_FILL = PatternFill("solid", fgColor="2563EB")
    ALT_FILL  = PatternFill("solid", fgColor="F8FAFC")
    CENTER    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    THIN_SIDE = Side(style="thin", color="CBD5E1")
    BORDER    = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

    STATUS_COLORS = {"PASS":"C6EFCE","ATKT":"FFEB9C","FAIL":"FFC7CE"}
    GRADE_COLORS  = {
        "O":"A7F3D0","A+":"BFDBFE","A":"DDD6FE",
        "B+":"FDE68A","B":"FED7AA","C":"FECACA","F":"FCA5A5"
    }

    # ── Title row ──
    title = f"Results — {dept or 'All Depts'} | SEM {semester or 'All'}"
    ws.merge_cells(f"A1:{get_column_letter(8 + len(subjects))}1")
    t_cell = ws["A1"]
    t_cell.value = title
    t_cell.font  = Font(bold=True, size=14, color="FFFFFF")
    t_cell.fill  = PatternFill("solid", fgColor="0F172A")
    t_cell.alignment = CENTER
    ws.row_dimensions[1].height = 30

    # ── Header row ──
    base_headers = ["#", "Roll No.", "Student Name", "Section",
                    "Dept", "Semester"]
    all_headers  = base_headers + subjects + ["Total Obtained", "Total Max",
                                               "Percentage", "Grade", "Status"]
    for c, h in enumerate(all_headers, 1):
        cell = ws.cell(2, c, h)
        cell.font      = HDR_FONT
        cell.fill      = SUBJ_FILL if c > len(base_headers) and c <= len(base_headers)+len(subjects) else HDR_FILL
        cell.alignment = CENTER
        cell.border    = BORDER
    ws.row_dimensions[2].height = 36

    # ── Data rows ──
    for ri, s in enumerate(students, 3):
        row_fill = ALT_FILL if ri % 2 == 0 else None
        subj_marks_map = {r["subject"]: r["marks"] for r in s["subjects"]}

        base_vals = [ri-2, s["roll"], s["name"], s["section"],
                     s["dept"], s["semester"]]
        subj_vals = [subj_marks_map.get(subj, "—") for subj in subjects]
        extra_vals = [s["cum_obtained"], s["cum_max"],
                      f"{s['percentage']}%", s["grade"], s["status"]]

        all_vals = base_vals + subj_vals + extra_vals
        for ci, val in enumerate(all_vals, 1):
            cell = ws.cell(ri, ci, val)
            cell.alignment = CENTER
            cell.border    = BORDER
            if row_fill:
                cell.fill = row_fill

            col_count = len(base_headers) + len(subjects)
            if ci == col_count + 3:  # Percentage
                cell.font = Font(bold=True)
            if ci == col_count + 4:  # Grade
                gc = GRADE_COLORS.get(s["grade"])
                if gc:
                    cell.fill = PatternFill("solid", fgColor=gc)
                    cell.font = Font(bold=True)
            if ci == col_count + 5:  # Status
                sc = STATUS_COLORS.get(s["status"])
                if sc:
                    cell.fill = PatternFill("solid", fgColor=sc)
                    cell.font = Font(bold=True)

    # ── Column widths ──
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 8
    ws.column_dimensions["F"].width = 8
    for i in range(len(base_headers)+1, len(base_headers)+len(subjects)+6):
        ws.column_dimensions[get_column_letter(i)].width = 14

    # ── Freeze panes ──
    ws.freeze_panes = "D3"

    # ════ Sheet 2: Subject-wise Analytics ════
    ws2 = wb.create_sheet("Analytics")
    ws2["A1"] = "Subject-wise Analytics"
    ws2["A1"].font = Font(bold=True, size=13)

    ah = ["Subject","Avg %","Highest %","Lowest %","Pass Rate %","Below 40 Count"]
    for c, h in enumerate(ah, 1):
        cell = ws2.cell(2, c, h)
        cell.font = HDR_FONT; cell.fill = HDR_FILL
        cell.alignment = CENTER; cell.border = BORDER

    subjects_analytics = []
    for subj in subjects:
        vals = []
        below40 = 0
        for s in students:
            for r in s["subjects"]:
                if r["subject"] == subj:
                    m = r["marks"] if r["marks"] is not None else 0
                    t = r["total"] if r["total"] and r["total"] > 0 else 100
                    p = m / t * 100
                    vals.append(p)
                    if p < 40: below40 += 1
        if vals:
            avg_v = round(sum(vals)/len(vals),1)
            pr    = round((len(vals)-below40)/len(vals)*100,1)
            subjects_analytics.append([subj, avg_v, round(max(vals),1),
                                        round(min(vals),1), pr, below40])

    for ri, row in enumerate(subjects_analytics, 3):
        for ci, val in enumerate(row, 1):
            cell = ws2.cell(ri, ci, val)
            cell.alignment = CENTER; cell.border = BORDER
            if ci == 2:  # Avg
                fill_col = "C6EFCE" if row[1] >= 60 else ("FFEB9C" if row[1] >= 40 else "FFC7CE")
                cell.fill = PatternFill("solid", fgColor=fill_col)

    for i, w in enumerate([40,12,12,12,14,14], 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    # ════ Sheet 3: Top 10 ════
    ws3 = wb.create_sheet("Top 10")
    ws3["A1"] = "Top 10 Performers"
    ws3["A1"].font = Font(bold=True, size=13)
    top_h = ["Rank","Roll","Name","Section","%","Grade","Status"]
    for c,h in enumerate(top_h,1):
        cell = ws3.cell(2,c,h)
        cell.font=HDR_FONT; cell.fill=HDR_FILL
        cell.alignment=CENTER; cell.border=BORDER
    top10 = sorted(students, key=lambda s: s["percentage"], reverse=True)[:10]
    for ri, s in enumerate(top10, 3):
        for ci,v in enumerate([ri-2,s["roll"],s["name"],s["section"],
                                f"{s['percentage']}%",s["grade"],s["status"]],1):
            cell = ws3.cell(ri,ci,v)
            cell.alignment=CENTER; cell.border=BORDER
            if ri == 3:
                cell.fill = PatternFill("solid",fgColor="FDE68A")

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    fname = f"results_{dept or 'all'}_{semester or 'all'}.xlsx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ═══════════════════════════════════════════════════════════
#  ROUTE 5 — API: Chart data (JSON)
# ═══════════════════════════════════════════════════════════

@results_bp.route("/results_chart_data")
@admin_required
def results_chart_data():
    dept     = request.args.get("dept","").strip()
    semester = request.args.get("semester","").strip()

    students = build_student_records(dept=dept or None, semester=semester or None)
    subjects = get_subject_list(dept or None, semester or None)

    # Grade distribution
    grade_dist = {"O":0,"A+":0,"A":0,"B+":0,"B":0,"C":0,"F":0}
    for s in students:
        grade_dist[s["grade"]] = grade_dist.get(s["grade"],0) + 1

    # Subject avg
    subj_avgs = {}
    for subj in subjects:
        vals = [
            (r["marks"] or 0) / (r["total"] or 100) * 100
            for s in students for r in s["subjects"] if r["subject"]==subj
        ]
        subj_avgs[subj] = round(sum(vals)/len(vals),1) if vals else 0

    # Section performance
    sec_perf = {}
    for sec in SECTIONS:
        ss = [s["percentage"] for s in students if s["section"]==sec]
        sec_perf[sec] = round(sum(ss)/len(ss),1) if ss else 0

    return jsonify({
        "grade_dist":  grade_dist,
        "subj_avgs":   subj_avgs,
        "sec_perf":    sec_perf,
        "status_dist": {
            "PASS":  sum(1 for s in students if s["status"]=="PASS"),
            "ATKT":  sum(1 for s in students if s["status"]=="ATKT"),
            "FAIL":  sum(1 for s in students if s["status"]=="FAIL"),
        },
        "total": len(students),
    })
