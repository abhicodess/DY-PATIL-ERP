"""
PATCH FOR app.py — DY Patil Final Attendance Report v2
=======================================================
Replaces:  _parse_dypatil_final_report()
           _is_dypatil_final_report()
           import_final_attendance_report()

Adds:
  - /cumulative_attendance           (admin: per-student cumulative view)
  - /export_cumulative_attendance    (admin: Excel export)
  - /attendance_section_report       (admin: Div A vs B vs C vs D side-by-side)
  - /import_final_attendance_v2      (smarter importer, auto-detects div + sem)

HOW TO APPLY
------------
1. Replace the three existing functions in app.py with the ones below.
2. Paste the new routes anywhere before `if __name__ == "__main__":`.
"""

# ─────────────────────────────────────────────────────────────
#  ENHANCED DYPATIL FINAL ATTENDANCE REPORT FORMAT
# ─────────────────────────────────────────────────────────────
#
#  Confirmed structure (both Div A and Div B):
#
#  Row 1  : "School of Engineering & Technology"
#  Row 2  : "Department of Computer Engineering"
#  Row 3  : "Academic Year 2025-26,  Semester -II"   ← semester extracted here
#  Row 4  : "Final Attendance Report"
#  Row 5  : "From 19.01.2026 to 10.04.2026"
#  Row 6  : "Program: S. Y.  B. Tech Comp. Engg. (Div. A)"  ← division here
#  Row 7  : SR.NO. | ROLL NO. | NAME OF STUDENT | <subj1> ... | Total | % Attendance
#  Row 8  : Subject codes
#  Row 9  : TH / PR / TUT types
#  Row 10 : TOTAL NO. OF LECTURES CONDUCTED  | <counts> ...
#  Row 11+: Student rows  (sr, roll, name, s1_present, ..., total, pct)
#  Last   : "Faculty Name", "Signature", footer rows  → stop when col-A is not int


# ══════════════════════════════════════════════════════════════
#  DROP-IN REPLACEMENT  ①  _is_dypatil_final_report
# ══════════════════════════════════════════════════════════════

def _is_dypatil_final_report(file_obj):
    """Detect DY Patil Final Attendance Report by signature strings."""
    try:
        wb = load_workbook(file_obj, data_only=True, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=1, max_row=10, values_only=True))
        wb.close()
        file_obj.seek(0)
        if len(rows) >= 7:
            # Row 7 must contain "NAME OF STUDENT"
            r7_text = " ".join(str(v or "").upper() for v in rows[6])
            if "NAME OF STUDENT" in r7_text:
                return True
            # Row 4 contains "FINAL ATTENDANCE REPORT"
            r4_text = " ".join(str(v or "").upper() for v in rows[3])
            if "FINAL ATTENDANCE REPORT" in r4_text:
                return True
        return False
    except Exception:
        file_obj.seek(0)
        return False


# ══════════════════════════════════════════════════════════════
#  DROP-IN REPLACEMENT  ②  _parse_dypatil_final_report
# ══════════════════════════════════════════════════════════════

def _parse_dypatil_final_report(file_obj, division_override="", semester_override=""):
    """
    Parse DY Patil Final Attendance Report.

    Auto-detects:
      - Division  from Row 6  e.g. "(Div. A)" → "A"
      - Semester  from Row 3  e.g. "Semester -II" → "II"

    Handles multiple sheets (skips empty/footer sheets).

    Returns (added, skipped, students_processed)
    """
    wb = load_workbook(file_obj, data_only=True)
    total_added = total_skipped = total_students = 0

    for ws in wb.worksheets:
        # Skip sheets that are obviously empty (max_row < 10)
        if ws.max_row < 10:
            continue

        # ── Auto-detect Division from Row 6 ──────────────────
        row6_text = " ".join(str(ws.cell(6, c).value or "") for c in range(1, ws.max_column + 1))
        division = division_override or ""
        if not division:
            import re as _re
            m = _re.search(r'Div[.\s]*([A-Da-d])', row6_text, _re.IGNORECASE)
            if m:
                division = m.group(1).strip().upper()

        # ── Auto-detect Semester from Row 3 ──────────────────
        row3_text = " ".join(str(ws.cell(3, c).value or "") for c in range(1, ws.max_column + 1))
        semester = semester_override or ""
        if not semester:
            m2 = _re.search(r'Semester\s*[-–]?\s*([IVXivx]+)', row3_text, _re.IGNORECASE)
            if m2:
                semester = m2.group(1).strip().upper()

        # ── Read subject names from Row 7 ────────────────────
        HEADER_ROW    = 7
        TOTAL_LEC_ROW = 10
        DATA_START    = 11
        NAME_COL      = 3   # C
        ROLL_COL      = 2   # B
        SUBJ_START    = 4   # D (1-indexed)

        header_row   = list(ws.iter_rows(min_row=HEADER_ROW, max_row=HEADER_ROW, values_only=True))[0]
        total_lec_row= list(ws.iter_rows(min_row=TOTAL_LEC_ROW, max_row=TOTAL_LEC_ROW, values_only=True))[0]

        subjects = []   # (col_index_0based, subject_name, total_lectures)
        for ci, val in enumerate(header_row):
            if ci < SUBJ_START - 1:
                continue
            name = str(val or "").strip()
            if not name:
                continue
            name_lower = name.lower().replace(" ", "").replace("\n", "")
            # Stop at Total / % columns
            if name_lower in ("total", "%ofattendance", "%ofatend", "%attend",
                              "percentageofattendance", "%ofatten"):
                break
            total_lec = total_lec_row[ci] if ci < len(total_lec_row) else None
            try:
                total_lec = int(total_lec) if total_lec is not None else 0
            except (TypeError, ValueError):
                total_lec = 0
            subj_clean = " ".join(name.split())   # collapse multi-line whitespace
            subjects.append((ci, subj_clean, total_lec))

        if not subjects:
            continue   # sheet has no subject columns → skip

        SYNTHETIC_DATE = "2026-01-01"
        added = skipped = students_processed = 0

        for row in ws.iter_rows(min_row=DATA_START, values_only=True):
            sr   = row[0]
            roll = str(row[ROLL_COL - 1] or "").strip()
            name = str(row[NAME_COL - 1] or "").strip()

            # Stop at footer rows
            if not sr or not isinstance(sr, (int, float)):
                break
            if not name or name.upper() in ("", "NONE"):
                continue

            students_processed += 1
            sid = resolve_student_id(name, roll)

            for (ci, subj_name, total_lec) in subjects:
                if ci >= len(row):
                    continue
                present_val = row[ci]
                try:
                    present_count = int(present_val) if present_val is not None else 0
                except (TypeError, ValueError):
                    present_count = 0

                lectures     = total_lec if total_lec > 0 else present_count
                absent_count = max(0, lectures - present_count)

                for _ in range(present_count):
                    try:
                        exe(
                            "INSERT INTO attendance"
                            "(student_id,student_name,subject,date,status,remark,division,semester)"
                            " VALUES(?,?,?,?,?,?,?,?)",
                            (sid, name, subj_name, SYNTHETIC_DATE,
                             "Present", "Imported from Final Report", division, semester),
                        )
                        added += 1
                    except Exception:
                        skipped += 1

                for _ in range(absent_count):
                    try:
                        exe(
                            "INSERT INTO attendance"
                            "(student_id,student_name,subject,date,status,remark,division,semester)"
                            " VALUES(?,?,?,?,?,?,?,?)",
                            (sid, name, subj_name, SYNTHETIC_DATE,
                             "Absent", "Imported from Final Report", division, semester),
                        )
                        added += 1
                    except Exception:
                        skipped += 1

        total_added    += added
        total_skipped  += skipped
        total_students += students_processed

    return total_added, total_skipped, total_students


# ══════════════════════════════════════════════════════════════
#  ENHANCED ENDPOINT  ③  import_final_attendance_report
# ══════════════════════════════════════════════════════════════

@app.route("/import_final_attendance_v2", methods=["POST"])
@login_required("admin")
def import_final_attendance_v2():
    """
    Dedicated endpoint for DY Patil Final Attendance Report.
    Accepts optional division / semester override from the form.
    """
    f = request.files.get("file")
    if not f:
        return redirect("/attendance?error=nofile")
    division_override = request.form.get("division", "").strip().upper()
    semester_override = request.form.get("semester", "").strip().upper()
    added, skipped, students = _parse_dypatil_final_report(
        f, division_override, semester_override
    )
    return redirect(
        f"/view_attendance?saved={added}&skipped={skipped}"
        f"&students={students}&format=final_report"
    )


# Also keep the old endpoint working (backward compat)
@app.route("/import_final_attendance_report", methods=["POST"])
@login_required("admin")
def import_final_attendance_report():
    f = request.files.get("file")
    if not f:
        return redirect("/attendance?error=nofile")
    added, skipped, students = _parse_dypatil_final_report(f)
    return redirect(
        f"/view_attendance?saved={added}&skipped={skipped}"
        f"&students={students}&format=final_report"
    )


# ══════════════════════════════════════════════════════════════
#  NEW FEATURE  ④  /cumulative_attendance  — per-student summary
# ══════════════════════════════════════════════════════════════

@app.route("/cumulative_attendance")
@login_required("admin")
def cumulative_attendance():
    """
    Per-student cumulative attendance report across ALL subjects.
    Shows: Total classes | Present | Absent | % | Status badge
    Filterable by division, semester, department.
    """
    division  = request.args.get("division",  "").strip()
    semester  = request.args.get("semester",  "").strip()
    dept      = request.args.get("dept",      "").strip()
    threshold = safe_int(request.args.get("threshold", "75"))

    # Build base WHERE for attendance
    where_parts  = ["1=1"]
    where_params = []
    if division:
        where_parts.append("a.division=?");   where_params.append(division)
    if semester:
        where_parts.append("a.semester=?");   where_params.append(semester)

    base_where = " AND ".join(where_parts)

    # Collect all students (filtered by dept if given)
    s_sql    = "SELECT id,name,roll,department,division FROM students"
    s_params = []
    if dept:
        s_sql   += " WHERE department=?"
        s_params = [dept]
    s_sql += " ORDER BY name"
    students_all = qry(s_sql, s_params)

    report = []
    for s in students_all:
        rows = qry(
            f"""SELECT a.subject, a.status
                FROM attendance a
                WHERE {att_match_student_sql('a')} AND {base_where}""",  # nosec B608
            list(att_match_student_params(s["id"], s["name"])) + where_params,
        )
        if not rows:
            continue
        total   = len(rows)
        present = sum(1 for r in rows if r["status"] == "Present")
        absent  = sum(1 for r in rows if r["status"] == "Absent")
        leave   = sum(1 for r in rows if r["status"] in ("Leave", "Late", "Medical"))
        p       = pct(present, total)

        # Per-subject breakdown for expandable row
        subj_map = {}
        for r in rows:
            subj_map.setdefault(r["subject"], {"total": 0, "present": 0})
            subj_map[r["subject"]]["total"]   += 1
            if r["status"] == "Present":
                subj_map[r["subject"]]["present"] += 1
        subjects_detail = [
            {
                "subject": sub,
                "total":   v["total"],
                "present": v["present"],
                "pct":     pct(v["present"], v["total"]),
            }
            for sub, v in sorted(subj_map.items())
        ]

        status_label = "Good" if p >= 75 else "Average" if p >= 50 else "Low"
        report.append({
            "name":     s["name"],
            "roll":     s["roll"] or "",
            "dept":     s["department"] or "",
            "division": s["division"] or "",
            "total":    total,
            "present":  present,
            "absent":   absent,
            "leave":    leave,
            "pct":      p,
            "status":   status_label,
            "low":      p < threshold,
            "subjects": subjects_detail,
        })

    report.sort(key=lambda x: x["pct"])

    # Quick stats
    total_students  = len(report)
    low_count       = sum(1 for r in report if r["low"])
    avg_pct         = round(sum(r["pct"] for r in report) / total_students, 1) if total_students else 0
    good_count      = sum(1 for r in report if r["pct"] >= 75)

    # Available filter options
    divs_list = [
        r["division"]
        for r in qry("SELECT DISTINCT division FROM attendance WHERE division!='' ORDER BY division")
    ]
    sems_list = [
        r["semester"]
        for r in qry("SELECT DISTINCT semester FROM attendance WHERE semester!='' ORDER BY semester")
    ]

    return render_template(
        "cumulative_attendance.html",
        report=report,
        total_students=total_students,
        low_count=low_count,
        good_count=good_count,
        avg_pct=avg_pct,
        threshold=threshold,
        f_division=division,
        f_semester=semester,
        f_dept=dept,
        divs=divs_list,
        sems=sems_list,
        DEPARTMENTS=DEPARTMENTS,
    )


# ══════════════════════════════════════════════════════════════
#  NEW FEATURE  ⑤  /export_cumulative_attendance  Excel export
# ══════════════════════════════════════════════════════════════

@app.route("/export_cumulative_attendance")
@login_required("admin")
def export_cumulative_attendance():
    division  = request.args.get("division",  "").strip()
    semester  = request.args.get("semester",  "").strip()
    dept      = request.args.get("dept",      "").strip()
    threshold = safe_int(request.args.get("threshold", "75"))

    where_parts  = ["1=1"]
    where_params = []
    if division: where_parts.append("a.division=?");  where_params.append(division)
    if semester: where_parts.append("a.semester=?");  where_params.append(semester)
    base_where = " AND ".join(where_parts)

    s_sql = "SELECT id,name,roll,department,division FROM students"
    s_params = []
    if dept: s_sql += " WHERE department=?"; s_params = [dept]
    s_sql += " ORDER BY name"
    students_all = qry(s_sql, s_params)

    wb = Workbook(); ws = wb.active; ws.title = "Cumulative Attendance"
    hdrs = ["#", "Name", "Roll", "Dept", "Division", "Total", "Present", "Absent", "Leave", "% Attendance", "Status"]
    for c, h in enumerate(hdrs, 1):
        cell = ws.cell(1, c, h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1E3A5F")

    row_num = 2
    STATUS_COLORS = {"Good": "C6EFCE", "Average": "FFEB9C", "Low": "FFC7CE"}

    idx = 0
    for s in students_all:
        rows = qry(
            f"""SELECT a.status FROM attendance a
                WHERE {att_match_student_sql('a')} AND {base_where}""",  # nosec B608
            list(att_match_student_params(s["id"], s["name"])) + where_params,
        )
        if not rows:
            continue
        idx += 1
        total   = len(rows)
        present = sum(1 for r in rows if r["status"] == "Present")
        absent  = sum(1 for r in rows if r["status"] == "Absent")
        leave   = total - present - absent
        p       = pct(present, total)
        status  = "Good" if p >= 75 else "Average" if p >= 50 else "Low"

        vals = [idx, s["name"], s["roll"] or "", s["department"] or "",
                s["division"] or "", total, present, absent, leave, f"{p}%", status]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row_num, c, v)
            if c == 11:
                cell.fill = PatternFill("solid", fgColor=STATUS_COLORS.get(status, "FFFFFF"))
        row_num += 1

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = max(
            len(str(col[0].value or "")) + 4, 14
        )

    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    fname = f"cumulative_attendance{'_'+division if division else ''}{'_sem'+semester if semester else ''}.xlsx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ══════════════════════════════════════════════════════════════
#  NEW FEATURE  ⑥  /attendance_section_report  — Div A vs B vs C vs D
# ══════════════════════════════════════════════════════════════

@app.route("/attendance_section_report")
@login_required("admin")
def attendance_section_report():
    """
    Side-by-side attendance comparison across divisions/sections.
    For each division shows: avg%, low attendance count, subject-wise breakdown.
    """
    semester  = request.args.get("semester", "").strip()
    dept      = request.args.get("dept",     "").strip()
    threshold = safe_int(request.args.get("threshold", "75"))

    # All divisions that have attendance data
    divs_rows = qry(
        "SELECT DISTINCT division FROM attendance WHERE division!='' ORDER BY division"
    )
    all_divs = [r["division"] for r in divs_rows]

    section_data = []
    for dv in all_divs:
        where = "a.division=?"
        params = [dv]
        if semester: where += " AND a.semester=?"; params.append(semester)

        # Overall stats for the section
        total   = qone(f"SELECT COUNT(*) as c FROM attendance a WHERE {where}", params)["c"]  # nosec B608
        present = qone(f"SELECT COUNT(*) as c FROM attendance a WHERE {where} AND a.status='Present'", params)["c"]  # nosec B608
        absent  = total - present

        # Student-level stats
        students_in_div = qry(
            "SELECT id,name,roll,department FROM students WHERE division=? ORDER BY name", (dv,)
        )
        low_att_students = []
        pcts = []
        for s in students_in_div:
            rows = qry(
                f"SELECT status FROM attendance a WHERE {att_match_student_sql('a')} AND {where}",  # nosec B608
                list(att_match_student_params(s["id"], s["name"])) + params,
            )
            if not rows: continue
            p = sum(1 for r in rows if r["status"] == "Present")
            sp = pct(p, len(rows))
            pcts.append(sp)
            if sp < threshold:
                low_att_students.append({"name": s["name"], "roll": s["roll"] or "", "pct": sp})

        avg_pct = round(sum(pcts) / len(pcts), 1) if pcts else 0

        # Subject-wise breakdown for this division
        subj_rows = qry(
            f"""SELECT a.subject,
                COUNT(*) as total,
                SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present
                FROM attendance a
                WHERE {where} GROUP BY a.subject ORDER BY a.subject""",  # nosec B608
            params,
        )
        subjects_detail = [
            {
                "subject": r["subject"][:30],
                "total":   r["total"],
                "present": r["present"],
                "pct":     pct(r["present"], r["total"]),
            }
            for r in subj_rows
        ]

        section_data.append({
            "division":    dv,
            "total":       total,
            "present":     present,
            "absent":      absent,
            "overall_pct": pct(present, total),
            "avg_pct":     avg_pct,
            "student_count": len(students_in_div),
            "low_count":   len(low_att_students),
            "low_students": low_att_students[:10],   # top 10 for preview
            "subjects":    subjects_detail,
        })

    sems_list = [
        r["semester"]
        for r in qry("SELECT DISTINCT semester FROM attendance WHERE semester!='' ORDER BY semester")
    ]

    return render_template(
        "attendance_section_report.html",
        section_data=section_data,
        all_divs=all_divs,
        f_semester=semester,
        f_dept=dept,
        threshold=threshold,
        sems=sems_list,
        DEPARTMENTS=DEPARTMENTS,
    )
