"""
─────────────────────────────────────────────────────────────
  PASTE THIS BLOCK into app.py
  Place it AFTER the /admin_import_results route (around line 3287)
─────────────────────────────────────────────────────────────
"""

@app.route("/admin_import_sem7", methods=["POST"])
@login_required("admin")
def admin_import_sem7():
    """
    Import DY Patil SEM VII Master Sheet (AIDS / IT / COMP tabs).
    Expected format:
      Row 0  → Subject names in merged cells (e.g. "Block Chain Technology UDSPC701")
      Row 2  → Sub-headers: Sr.No. | Student Name | PRN Number | Assignment(10) | … | TOTAL(40) | …
      Row 3+ → Student data
    Each sheet name becomes the department code.
    Inserts one result row per TOTAL column per student.
    """
    f = request.files.get("file")
    if not f:
        return redirect("/admin_results?error=no_file")

    try:
        wb = load_workbook(f, data_only=True)
    except Exception:
        return redirect("/admin_results?error=invalid_file")

    # Grade/result helpers (reuse existing grade() and pct())
    MAX_MARKS = {"AIDS": 510, "IT": 510, "COMP": 485}
    GRADE_TABLE = [(75,"O"),(70,"A+"),(60,"A"),(55,"B+"),(50,"B"),(45,"C"),(0,"F")]

    def sem7_grade(obtained, total):
        if not total:
            return "F"
        p = obtained / total * 100
        for threshold, g in GRADE_TABLE:
            if p >= threshold:
                return g
        return "F"

    added = skipped = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        dept = sheet_name.strip().upper()  # AIDS / IT / COMP

        # ── Identify TOTAL columns and their subject names ──
        subj_row = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        hdr_row  = [str(ws.cell(3, c).value or "").strip() for c in range(1, ws.max_column + 1)]

        total_cols = []   # list of (col_index_1based, subject_name, max_marks)
        last_subj  = "General"
        for i, sv in enumerate(subj_row):
            if sv and str(sv).strip():
                last_subj = str(sv).strip()
            hv = hdr_row[i].upper() if i < len(hdr_row) else ""
            if "TOTAL" in hv and i > 2:
                # Parse max from "TOTAL (40)" → 40
                import re as _re
                m = _re.search(r"\((\d+)\)", hv)
                max_m = int(m.group(1)) if m else 100
                total_cols.append((i + 1, last_subj, max_m))

        if not total_cols:
            continue  # skip sheets with no TOTAL columns

        # ── Iterate student rows (row 4 onwards, 1-indexed = row index 4) ──
        for row_idx in range(4, ws.max_row + 1):
            sr_cell = ws.cell(row_idx, 1).value
            if sr_cell is None:
                continue
            try:
                int(float(str(sr_cell)))
            except (ValueError, TypeError):
                continue

            name = str(ws.cell(row_idx, 2).value or "").strip()
            prn  = str(ws.cell(row_idx, 3).value or "").strip()
            if not name or name.lower() in ("student name", "name", "nan"):
                continue

            # Look up student in DB (optional – enrich dept/year)
            db_student = qone(
                "SELECT roll, department, year FROM students WHERE name=? OR roll=?",
                (name, prn)
            )
            db_dept = db_student["department"] if db_student else dept
            db_year = db_student["year"]       if db_student else "IV"
            db_roll = db_student["roll"]       if db_student else prn

            for col_1, subj_name, max_m in total_cols:
                raw_val = ws.cell(row_idx, col_1).value
                if raw_val is None:
                    continue
                try:
                    marks_val = float(raw_val)
                except (ValueError, TypeError):
                    continue  # "AB" or blank → skip

                g   = sem7_grade(marks_val, max_m)
                res = "Pass" if (marks_val / max_m * 100 >= 40) else "Fail"

                # Avoid duplicate: same name + subject + semester
                existing = qone(
                    "SELECT id FROM results WHERE student_name=? AND subject=? AND semester=?",
                    (name, subj_name, "VII")
                )
                if existing:
                    skipped += 1
                    continue

                try:
                    exe(
                        """INSERT INTO results
                           (student_name, roll, department, year, semester,
                            subject, marks, total, exam_type, grade, result, published)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,0)""",
                        (name, db_roll, db_dept, db_year, "VII",
                         subj_name, marks_val, float(max_m),
                         "Semester Exam", g, res)
                    )
                    added += 1
                except Exception:
                    skipped += 1

    return redirect(f"/admin_results?sem7_imported={added}&sem7_skipped={skipped}")
