"""
REPLACE the existing import_final_pdf() function in app.py with this one.
Find it by searching for:  @app.route("/import_final_pdf"
And replace the entire function.

FIXES:
  1. PDF opened only ONCE (was opened twice before)
  2. All DB inserts done in a single transaction (was one connection per row)
  3. Batch collect → bulk write pattern
"""


@app.route("/import_final_pdf", methods=["POST"])
@login_required("admin")
def import_final_pdf():
    """Import DY Patil attendance PDF → attendance_summary (fast batch version)."""
    import tempfile

    f = request.files.get("file")
    if not f:
        return redirect("/attendance_dashboard?error=nofile")

    added = skipped = students_found = 0

    try:
        import pdfplumber
    except ImportError:
        return redirect("/attendance_dashboard?error=pdfplumber_missing")

    # ── Save upload to temp file ──────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    # ── Parse PDF (single open) ───────────────────────────────────────────────
    batch = []   # list of (student_id, student_name, subject, attended, total)

    try:
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 3:
                        continue

                    # ── Find header row ───────────────────────────────────────
                    hdr_idx = None
                    for ri, row in enumerate(table):
                        row_str = " ".join(str(c or "").upper() for c in row)
                        if "NAME" in row_str and ("ROLL" in row_str or "SR" in row_str):
                            hdr_idx = ri
                            break
                    if hdr_idx is None:
                        continue

                    headers   = [str(c or "").strip() for c in table[hdr_idx]]
                    name_col  = next((i for i, h in enumerate(headers) if "NAME" in h.upper()), None)
                    roll_col  = next((i for i, h in enumerate(headers) if "ROLL" in h.upper()), None)
                    if name_col is None:
                        continue

                    # ── Subject columns ───────────────────────────────────────
                    cutoff = max(name_col or 0, roll_col or 0)
                    subj_cols = []
                    for ci, h in enumerate(headers):
                        if ci <= cutoff:
                            continue
                        h_up = h.upper().replace(" ", "")
                        if h_up in ("", "TOTAL", "%", "%OFATTENDANCE", "PERCENTAGEOFATTENDANCE"):
                            break
                        if h:
                            subj_cols.append((ci, h))

                    # ── Total lectures row ────────────────────────────────────
                    total_lecs = {}
                    total_lec_row = None
                    for ri in range(hdr_idx + 1, min(hdr_idx + 5, len(table))):
                        vals = [str(c or "") for c in table[ri]]
                        name_val = vals[name_col] if name_col < len(vals) else ""
                        if (not name_val or name_val.isdigit()) and \
                           any(v.isdigit() and int(v) > 10 for v in vals):
                            total_lec_row = ri
                            break

                    if total_lec_row is not None:
                        for ci, subj in subj_cols:
                            try:
                                v = table[total_lec_row][ci]
                                total_lecs[subj] = int(v) if v else 0
                            except Exception:
                                total_lecs[subj] = 0

                    # ── Student rows → collect into batch ─────────────────────
                    data_start = (total_lec_row + 1) if total_lec_row else (hdr_idx + 1)
                    for row in table[data_start:]:
                        if not row:
                            continue
                        name_v = str(row[name_col] or "").strip() if name_col < len(row) else ""
                        roll_v = str(row[roll_col] or "").strip() if roll_col and roll_col < len(row) else ""

                        if not name_v or name_v.upper() in ("NAME", "NAME OF STUDENT", ""):
                            continue
                        if name_v.lower().startswith(("faculty", "hod", "signature")):
                            break

                        students_found += 1
                        s_id = resolve_student_id(name_v, roll_v)

                        for ci, subj in subj_cols:
                            try:
                                att_val   = row[ci] if ci < len(row) else None
                                att_count = int(att_val) if att_val and str(att_val).strip().isdigit() else 0
                            except Exception:
                                att_count = 0

                            total_v = total_lecs.get(subj, att_count)
                            batch.append((s_id, name_v, subj, att_count, total_v))

    except Exception as e:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return redirect(f"/attendance_dashboard?error=parse_failed&msg={str(e)[:80]}")

    # ── Bulk insert in ONE transaction ────────────────────────────────────────
    if batch:
        conn = get_db()
        try:
            conn.execute("BEGIN")
            for (s_id, name_v, subj, att_count, total_v) in batch:
                try:
                    conn.execute("""
                        INSERT INTO attendance_summary(student_id, student_name, subject, attended, total)
                        VALUES(?,?,?,?,?)
                        ON CONFLICT(student_id, subject) DO UPDATE SET
                            attended = excluded.attended,
                            total    = excluded.total
                    """, (s_id, name_v, subj, att_count, total_v))
                    added += 1
                except Exception:
                    skipped += 1
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            skipped += len(batch)
        finally:
            conn.close()

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    return redirect(
        f"/attendance_dashboard?saved={added}&skipped={skipped}"
        f"&students={students_found}&format=pdf"
    )
