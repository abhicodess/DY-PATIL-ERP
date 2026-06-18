"""
cumulative_routes.py
────────────────────
Paste this entire file's content into app.py  OR  save as cumulative_routes.py
and add these two lines near the top of app.py:

    from routes.cumulative import cumulative_bp
    app.register_blueprint(cumulative_bp)

Also add this to init_db() → executescript (before the final triple-quote):

    CREATE TABLE IF NOT EXISTS cumulative_attendance (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        roll         TEXT NOT NULL,
        student_name TEXT NOT NULL,
        department   TEXT NOT NULL DEFAULT '',
        division     TEXT NOT NULL DEFAULT '',
        semester     TEXT NOT NULL DEFAULT '',
        acad_year    TEXT NOT NULL DEFAULT '',
        subject      TEXT NOT NULL,
        subject_code TEXT DEFAULT '',
        conducted    INTEGER NOT NULL DEFAULT 0,
        attended     INTEGER NOT NULL DEFAULT 0,
        percentage   REAL DEFAULT 0,
        updated_at   TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(roll, subject_code, semester, acad_year)
    );

And add to migrate_db() migrations list:
    ("cumulative_attendance", "division",     "''"),
    ("cumulative_attendance", "subject_code", "''"),
"""

import os, json
from flask import Blueprint, request, redirect, session, jsonify, render_template, send_file
from io import BytesIO

# ── If pasting into app.py, remove this Blueprint wrapper and use app directly ──
try:
    from utils.cumulative_parser import parse_attendance_file
except ImportError:
    from cumulative_parser import parse_attendance_file  # fallback

cumulative_bp = Blueprint("cumulative", __name__)

_CLEAR_ALL_CUMULATIVE_PHRASE = "DELETE ALL CUMULATIVE DATA"

# ─── Helpers (already exist in app.py — skip if pasting) ─────────────────────
# qry, qone, exe, login_required, safe_int  ← use the ones from app.py


# ═══════════════════════════════════════════════════════════════════════════════
#  IMPORT PAGE  /cumulative_import
# ═══════════════════════════════════════════════════════════════════════════════

@cumulative_bp.route("/cumulative_import", methods=["GET", "POST"])
def cumulative_import():
    """Upload one or more PDF/Excel attendance reports and preview before saving."""
    from utils.pg_wrapper import qry, qone, exe
    from blueprints.auth.decorators import login_required

    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "GET":
        return render_template("cumulative/cumulative_import.html")

    # ── POST: process uploaded files ──────────────────────────────────────────
    if parse_attendance_file is None:
        return jsonify({"error": "cumulative_parser.py not found next to app.py"}), 500

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    all_parsed = []
    errors = []

    for f in files:
        if not f.filename:
            continue
        try:
            data = f.read()
            parsed = parse_attendance_file(data, f.filename)
            parsed["filename"] = f.filename
            all_parsed.append(parsed)
        except Exception as e:
            errors.append({"file": f.filename, "error": str(e)})

    return jsonify({"parsed": all_parsed, "errors": errors})


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMIT IMPORT  /cumulative_commit   (JSON POST from preview UI)
# ═══════════════════════════════════════════════════════════════════════════════

@cumulative_bp.route("/cumulative_commit", methods=["POST"])
def cumulative_commit():
    from utils.pg_wrapper import exe
    from blueprints.auth.decorators import login_required

    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    payload = request.get_json(force=True) or {}
    rows    = payload.get("rows", [])
    inserted = updated = skipped = 0

    for r in rows:
        roll     = (r.get("roll") or "").strip()
        name     = (r.get("name") or "").strip()
        dept     = (r.get("department") or "").strip()
        div      = (r.get("division") or "").strip()
        sem      = (r.get("semester") or "").strip()
        year     = (r.get("acad_year") or "").strip()
        subj     = (r.get("subject") or "").strip()
        code     = (r.get("subject_code") or "").strip()
        conducted = int(r.get("conducted") or 0)
        attended  = int(r.get("attended") or 0)
        pct       = round(100.0 * attended / conducted, 2) if conducted else 0.0

        if not roll or not subj:
            skipped += 1
            continue
        try:
            exe("""
                INSERT INTO cumulative_attendance
                    (roll, student_name, department, division, semester, acad_year,
                     subject, subject_code, conducted, attended, percentage)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(roll, subject_code, semester, acad_year)
                DO UPDATE SET
                    attended     = excluded.attended,
                    conducted    = excluded.conducted,
                    percentage   = excluded.percentage,
                    student_name = excluded.student_name,
                    updated_at   = CURRENT_TIMESTAMP
            """, (roll, name, dept, div, sem, year, subj, code,
                  conducted, attended, pct))
            inserted += 1
        except Exception as e:
            skipped += 1

    return jsonify({"inserted": inserted, "skipped": skipped})


@cumulative_bp.route("/cumulative_delete_row", methods=["POST"])
def cumulative_delete_row():
    """Delete one cumulative_attendance row (admin)."""
    from utils.pg_wrapper import exe, qone
    from utils.helpers import safe_redirect_target

    if session.get("role") != "admin":
        return redirect("/login")
    rid = request.form.get("row_id", "").strip()
    roll_chk = (request.form.get("roll", "") or "").strip()
    red = request.form.get("redirect", "/cumulative_report")
    if not rid.isdigit() or not roll_chk:
        return redirect(safe_redirect_target(red, "/cumulative_report"))
    row = qone("SELECT id, roll FROM cumulative_attendance WHERE id=%s", (int(rid),))
    if row and row["roll"] == roll_chk:
        exe("DELETE FROM cumulative_attendance WHERE id=%s", (int(rid),))
    return redirect(safe_redirect_target(red, "/cumulative_report"))


@cumulative_bp.route("/cumulative_clear_all", methods=["POST"])
def cumulative_clear_all():
    """Delete all rows in cumulative_attendance (admin, typed confirmation)."""
    from utils.pg_wrapper import exe
    from utils.helpers import safe_redirect_target

    if session.get("role") != "admin":
        return redirect("/login")
    phrase = (request.form.get("confirm_phrase") or "").strip()
    if phrase != _CLEAR_ALL_CUMULATIVE_PHRASE:
        return redirect("/cumulative_report?error=bad_cumulative_confirm")
    exe("DELETE FROM cumulative_attendance")
    return redirect("/cumulative_report?cumulative_cleared=1")


# ═══════════════════════════════════════════════════════════════════════════════
#  CUMULATIVE REPORT  /cumulative_report
# ═══════════════════════════════════════════════════════════════════════════════

@cumulative_bp.route("/cumulative_report")
def cumulative_report():
    from utils.pg_wrapper import qry
    from blueprints.auth.decorators import login_required
    from config import Config
    DEPARTMENTS = Config.DEPARTMENTS
    DIVISIONS = Config.DIVISIONS
    SEMESTERS = Config.SEMESTERS

    if session.get("role") not in ("admin", "faculty"):
        return redirect("/login")

    dept = request.args.get("dept", "")
    div  = request.args.get("div", "")
    sem  = request.args.get("sem", "")
    year = request.args.get("year", "")
    roll = request.args.get("roll", "")

    filters = "WHERE 1=1"
    params  = []
    if dept: filters += " AND department=%s";  params.append(dept)
    if div:  filters += " AND division=%s";    params.append(div)
    if sem:  filters += " AND semester=%s";    params.append(sem)
    if year: filters += " AND acad_year=%s";   params.append(year)
    if roll: filters += " AND roll LIKE %s";   params.append(f"%{roll}%")

    # Per-student cumulative summary
    students = qry(f"""
        SELECT roll, student_name, department, division,
               COUNT(DISTINCT semester||acad_year) AS sem_count,
               SUM(attended)  AS total_attended,
               SUM(conducted) AS total_conducted,
               ROUND(100.0 * SUM(attended) / NULLIF(SUM(conducted),0), 2) AS cumulative_pct
        FROM cumulative_attendance
        {filters}
        GROUP BY roll, student_name, department, division
        ORDER BY department, division, roll
    """, params)

    # Per-subject breakdown for selected student (exact roll match)
    student_detail = []
    detail_meta = None
    if roll:
        student_detail = qry("""
            SELECT id, student_name, semester, acad_year, subject, subject_code,
                   conducted, attended, percentage
            FROM cumulative_attendance
            WHERE roll=%s
            ORDER BY acad_year, semester, subject
        """, (roll,))
        if student_detail:
            tot_att = sum(int(r["attended"] or 0) for r in student_detail)
            tot_con = sum(int(r["conducted"] or 0) for r in student_detail)
            pct = round(100.0 * tot_att / tot_con, 2) if tot_con else 0.0
            detail_meta = {
                "student_name": (student_detail[0]["student_name"] or "").strip(),
                "total_attended": tot_att,
                "total_conducted": tot_con,
                "cumulative_pct": pct,
            }

    # Available years for filter dropdown
    years = qry("SELECT DISTINCT acad_year FROM cumulative_attendance ORDER BY acad_year DESC")

    # Shortage list (below 75%)
    shortage = [s for s in students if (s["cumulative_pct"] or 0) < 75]

    return render_template("cumulative/cumulative_report.html",
        students=students,
        student_detail=student_detail,
        detail_meta=detail_meta,
        shortage=shortage,
        dept=dept, div=div, sem=sem, year=year, roll=roll,
        DEPARTMENTS=DEPARTMENTS,
        DIVISIONS=DIVISIONS,
        SEMESTERS=SEMESTERS,
        years=years,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  STUDENT PORTAL — cumulative summary  (call from student dashboard route)
# ═══════════════════════════════════════════════════════════════════════════════

def get_student_cumulative(roll: str) -> dict:
    """
    Call this from your student_dashboard route to get cumulative data.
    
    Usage in your route:
        from cumulative_routes import get_student_cumulative
        cum = get_student_cumulative(session["roll"])
        return render_template("student/student_dashboard.html", ..., cumulative=cum)
    """
    from utils.pg_wrapper import qry, qone
    overall = qone("""
        SELECT SUM(attended)  AS tot_att,
               SUM(conducted) AS tot_con,
               ROUND(100.0 * SUM(attended)/NULLIF(SUM(conducted),0), 2) AS cum_pct
        FROM cumulative_attendance WHERE roll=%s
    """, (roll,))

    by_sem = qry("""
        SELECT semester, acad_year,
               SUM(attended) AS att, SUM(conducted) AS con,
               ROUND(100.0*SUM(attended)/NULLIF(SUM(conducted),0), 2) AS pct
        FROM cumulative_attendance WHERE roll=%s
        GROUP BY acad_year, semester
        ORDER BY acad_year, semester
    """, (roll,))

    by_subject = qry("""
        SELECT subject, subject_code, semester, acad_year,
               conducted, attended, percentage
        FROM cumulative_attendance WHERE roll=%s
        ORDER BY acad_year, semester, subject
    """, (roll,))

    return {
        "overall":    dict(overall) if overall else {},
        "by_sem":     [dict(r) for r in by_sem],
        "by_subject": [dict(r) for r in by_subject],
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  EXCEL EXPORT  /cumulative_export
# ═══════════════════════════════════════════════════════════════════════════════

@cumulative_bp.route("/cumulative_export")
def cumulative_export():
    from utils.pg_wrapper import qry
    from blueprints.auth.decorators import login_required
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    if session.get("role") not in ("admin", "faculty"):
        return redirect("/login")

    dept = request.args.get("dept", "")
    sem  = request.args.get("sem", "")
    year = request.args.get("year", "")

    filters = "WHERE 1=1"
    params  = []
    if dept: filters += " AND department=%s"; params.append(dept)
    if sem:  filters += " AND semester=%s";   params.append(sem)
    if year: filters += " AND acad_year=%s";  params.append(year)

    rows = qry(f"""
        SELECT roll, student_name, department, division, semester, acad_year,
               SUM(attended) AS tot_att, SUM(conducted) AS tot_con,
               ROUND(100.0*SUM(attended)/NULLIF(SUM(conducted),0),2) AS pct
        FROM cumulative_attendance {filters}
        GROUP BY roll, student_name, department, division, semester, acad_year
        ORDER BY department, division, roll
    """, params)

    wb = Workbook()
    ws = wb.active
    ws.title = "Cumulative Attendance"

    hdr_fill = PatternFill("solid", fgColor="1F4E79")
    hdr_font = Font(bold=True, color="FFFFFF", size=11)
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ["Roll No", "Name", "Dept", "Div", "Semester", "Year",
               "Total Attended", "Total Conducted", "Cumulative %", "Status"]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = border

    RED  = PatternFill("solid", fgColor="FFCCCC")
    YEL  = PatternFill("solid", fgColor="FFF2CC")
    GRN  = PatternFill("solid", fgColor="CCFFCC")

    for r in rows:
        pct = r["pct"] or 0
        status = "✓ OK" if pct >= 75 else ("⚠ Low" if pct >= 60 else "✗ Shortage")
        ws.append([r["roll"], r["student_name"], r["department"], r["division"],
                   r["semester"], r["acad_year"], r["tot_att"], r["tot_con"],
                   pct, status])
        row_cells = ws[ws.max_row]
        fill = GRN if pct >= 75 else (YEL if pct >= 60 else RED)
        for cell in row_cells:
            cell.border = border
            if cell.column == 9:  # % column
                cell.fill = fill

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(
            len(str(col[0].value or "")), 12)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"cumulative_{dept or 'all'}_{sem or 'all'}_{year or 'all'}.xlsx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
