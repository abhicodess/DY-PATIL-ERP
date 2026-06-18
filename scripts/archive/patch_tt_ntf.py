import re

def patch():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update faculty timetable filters
    fac_tt_target = """    f_day   = request.args.get("day","").strip()
    f_type  = request.args.get("slot_type","").strip()

    fac_id  = session.get("faculty_id")"""

    fac_tt_repl = """    f_day   = request.args.get("day","").strip()
    f_type  = request.args.get("slot_type","").strip()
    f_branch = request.args.get("branch","").strip()
    f_year = request.args.get("year","").strip()
    f_div = request.args.get("division","").strip()
    f_subj = request.args.get("subject_id","").strip()

    fac_id  = session.get("faculty_id")"""

    fac_tt_filter_target = """    # filtered entries for list
    entries = all_entries
    if f_day:  entries = [e for e in entries if e["day"]==f_day]
    if f_type: entries = [e for e in entries if (e.get("slot_type") or "Theory")==f_type]"""

    fac_tt_filter_repl = """    # filtered entries for list
    entries = all_entries
    if f_day:  entries = [e for e in entries if e["day"]==f_day]
    if f_type: entries = [e for e in entries if (e.get("slot_type") or "Theory")==f_type]
    if f_branch: entries = [e for e in entries if e.get("branch")==f_branch]
    if f_year: entries = [e for e in entries if e.get("year")==f_year]
    if f_div: entries = [e for e in entries if e.get("division")==f_div]
    if f_subj: entries = [e for e in entries if str(e.get("subject_id"))==str(f_subj)]"""

    if fac_tt_target in content:
        content = content.replace(fac_tt_target, fac_tt_repl)
    if fac_tt_filter_target in content:
        content = content.replace(fac_tt_filter_target, fac_tt_filter_repl)


    # 2. Add full API Routes
    api_routes = """
# ════════════════════════════════════════════════════════════
# TIMETABLE NOTIFICATION SYSTEM
# ════════════════════════════════════════════════════════════

@app.route("/api/faculty_send_timetable", methods=["POST"])
@login_required("faculty")
def api_faculty_send_timetable():
    fac_id = session.get("faculty_id")
    f_branch = request.form.get("branch","").strip()
    f_year = request.form.get("year","").strip()
    f_div = request.form.get("division","").strip()
    f_subj = request.form.get("subject_id","").strip()

    sql = "SELECT DISTINCT branch, year, division FROM timetable WHERE faculty_id=%s AND branch != '' AND branch IS NOT NULL"
    params = [fac_id]
    if f_branch: sql += " AND branch=%s"; params.append(f_branch)
    if f_year: sql += " AND year=%s"; params.append(f_year)
    if f_div: sql += " AND division=%s"; params.append(f_div)
    if f_subj: sql += " AND subject_id=%s"; params.append(f_subj)

    classes = qry(sql, params)
    if not classes:
        return jsonify({"error": "No matching classes found in your timetable for these filters"}), 404

    message = request.form.get("message", f"Your timetable has been officially updated by Faculty ID {fac_id}.")

    conn = get_db()
    c = 0
    try:
        cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor()
        inserts = []
        for row in classes:
            b, y, d = row["branch"], row["year"], row["division"]
            students = qry("SELECT id FROM students WHERE department=%s AND year=%s AND division=%s", (b, y, d))
            for st in students:
                inserts.append((fac_id, "faculty", st["id"], message))
                c += 1
                
        if inserts:
            import psycopg2.extras
            psycopg2.extras.execute_values(
                cur, 
                "INSERT INTO timetable_notifications (sender_id, sender_role, student_id, message) VALUES %s", 
                inserts
            )
            if hasattr(conn, 'conn'): conn.conn.commit()
            else: conn.commit()
    except Exception as e:
        if hasattr(conn, 'conn'): conn.conn.rollback()
        else: conn.rollback()
        raise e
    finally:
        conn.close()

    return jsonify({"success": True, "sent_count": c})

@app.route("/api/admin_send_timetable", methods=["POST"])
@login_required("admin")
def api_admin_send_timetable():
    admin_id = 1
    f_branch = request.form.get("branch","").strip()
    f_year = request.form.get("year","").strip()
    f_div = request.form.get("division","").strip()
    send_all = request.form.get("send_all")

    sql = "SELECT id FROM students WHERE 1=1"
    params = []
    if not send_all:
        if f_branch: sql += " AND department=%s"; params.append(f_branch)
        if f_year: sql += " AND year=%s"; params.append(f_year)
        if f_div: sql += " AND division=%s"; params.append(f_div)

    students = qry(sql, params)
    if not students:
        return jsonify({"error": "No matching students found"}), 404

    message = request.form.get("message", "Global Timetable Update Published by Administration.")
    
    conn = get_db()
    c = 0
    try:
        cur = conn.cur if hasattr(conn, 'cur') else conn.conn.cursor()
        inserts = []
        for st in students:
            inserts.append((admin_id, "admin", st["id"], message))
            c += 1

        if inserts:
            import psycopg2.extras
            psycopg2.extras.execute_values(
                cur, 
                "INSERT INTO timetable_notifications (sender_id, sender_role, student_id, message) VALUES %s", 
                inserts
            )
            if hasattr(conn, 'conn'): conn.conn.commit()
            else: conn.commit()
    except Exception as e:
        if hasattr(conn, 'conn'): conn.conn.rollback()
        else: conn.rollback()
        raise e
    finally:
        conn.close()

    return jsonify({"success": True, "sent_count": c})

@app.route("/student_notifications", methods=["GET"])
@login_required("student")
def student_notifications():
    sid = session.get("student_id")
    notifs = qry("SELECT * FROM timetable_notifications WHERE student_id=%s ORDER BY created_at DESC", (sid,))
    # Serialize datetime explicitly to avoid JSON default errors
    import datetime
    out = []
    for n in notifs:
        d = dict(n)
        if isinstance(d.get("created_at"), datetime.datetime):
            d["created_at"] = d["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        out.append(d)
    return jsonify({"notifications": out})

"""

    if "/api/faculty_send_timetable" not in content:
        content = content.replace('if __name__ == "__main__":', api_routes + '\nif __name__ == "__main__":')

    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Notification routes injected.")

if __name__ == "__main__":
    patch()
